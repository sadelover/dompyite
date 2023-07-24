from flask import request, json, jsonify

import logging, uuid
from siteinterface.mod_project import bp_project
from siteinterface import app
import os
import shutil
from siteinterface.mod_project.utils import *
import traceback
from ..sqlite_manager import SqliteManager
from siteinterface.utils import get_proj_name, isValidDate
import requests
from datetime import datetime

@bp_project.route('/getList')
def get_project_list():
    res = list()
    try:
        strProjPrefix = "projectdb"
        strDomdb = "domdb"
        cf = ConfigObj("config.ini", encoding="UTF8")
        res.append({"projId":1, "projName": cf.get("cloud").get("projectname")})
        for key in cf.keys():
            if key.startswith(strProjPrefix) and len(key.replace(strProjPrefix, "")):
                res.append({"projId": int(cf.get(key).get("dbFileName").split(".")[0].replace(strDomdb, "")),
                            "projName": cf.get(key).get("dbprojectName")})
    except:
        return jsonify(dict(err=1, msg='获取项目列表失败', data=list()))
    return jsonify(dict(err=0, msg='', data=res))


@bp_project.route('/createProject', methods=["POST"])
def create_project():
    bSuccessDbFile = False
    bSuccessConfigini = False
    try:
        data = request.get_json()
        strProjName = data.get("projName")
        strCorePath = app.config["CORE_PATH"]

        if not isinstance(strProjName, str):
            return jsonify(dict(err=1, msg='新建项目失败，项目名称必须为字符串', data=dict()))
        elif len(strProjName) == 0:
            return jsonify(dict(err=1, msg="新建项目失败，项目名称不能为空", data=dict()))

        strSysDBPath  = os.path.join(app.static_folder, "projectdblib")
        str4dbSrc = os.path.join(strSysDBPath, "sys.4db")

        strDomdb = "domdb"
        list4dbFile = list()
        for root, dirs, files in os.walk(strCorePath):
            for file in files:
                if file.startswith(strDomdb) and file.endswith("4db"):
                    list4dbFile.append(file)

        listProjNum = list()
        for file in list4dbFile:
            projNum = os.path.splitext(file)[0].replace(strDomdb, "")
            if projNum:
                listProjNum.append(int(projNum))

        latestProjId = 1
        if len(listProjNum):
            latestProjId = max(listProjNum)
        projId = latestProjId + 1

        bSuccessDbFile = create_domdb_file_for_new_proj(projId, str4dbSrc, strCorePath)

        bSuccessConfigini = add_proj_to_config_ini(projId, strProjName)

        if bSuccessDbFile and bSuccessConfigini:
            return jsonify(dict(err=0, msg='新建项目成功', data={}))
        else:
            return jsonify(dict(err=1, msg='新建项目失败', data={}))
    except:
        return jsonify(dict(err=1, msg='新建项目失败', data={}))


@bp_project.route('/removeProject', methods=["POST"])
def remove_project():
    bSuccessDbFile = False
    bSuccessConfigini = False
    try:
        data = request.get_json()
        strCorePath = app.config["CORE_PATH"]
        projId = data.get("projId")
        if not isinstance(projId, int):
            return jsonify(dict(err=1, msg="删除项目失败，项目id必须为整数"))

        bSuccessDbFile = remove_domdb_file(projId, strCorePath)

        bSuccessConfigini = remove_proj_from_config_ini(projId)

        if bSuccessDbFile and bSuccessConfigini:
            return jsonify(dict(err=0, msg='删除项目成功', data={}))
        else:
            return jsonify(dict(err=1, msg='删除项目失败', data={}))
    except:
        return jsonify(dict(err=1, msg='删除项目失败', data={}))


@bp_project.route("/editProjectName", methods=["POST"])
def edit_project_name():
    try:
        data = request.get_json()
        projName = data.get("projName")
        projId = data.get("projId")
        if not isinstance(projName, str):
            return jsonify(dict(err=1, msg="修改失败，项目名称必须为字符串"))
        elif len(projName) == 0:
            return jsonify(dict(err=1, msg="修改失败，项目名称不能为空"))
        elif not isinstance(projId, int):
            return jsonify(dict(err=1, msg="修改失败，项目id必须为整数"))

        cf = ConfigObj("config.ini", encoding="UTF8")
        projKey = "projectdb%03d" % projId
        if cf.get(projKey):
            cf[projKey]["dbprojectName"] = projName
            cf.write()
            return jsonify(dict(err=0, msg="项目名称修改成功", data=list()))
        return jsonify(dict(err=1, msg="无此项目", data=list()))
    except:
        return jsonify(dict(err=1, msg="项目名称修改失败", data=list()))

@bp_project.route("/getEquipTree", methods=["POST"])
def get_equip_tree():
    try:
        data = request.get_json()
        projId = data.get("projId")
        if not isinstance(projId, int):
            return jsonify(dict(err=1, msg="项目ID必须为整数", data=list()))
        if projId <= 0:
            return jsonify(dict(err=1, msg="项目ID必须大于零", data=list()))

        projdbKey = "projectdb" if projId == 1 else "projectdb%03d" % projId

        cf = ConfigObj("config.ini", encoding="UTF8")
        if cf.get(projdbKey) is None:
            return jsonify(dict(err=1, msg="无此项目", data=list()))

        dbfileName = cf.get(projdbKey).get("dbFileName")

        dbfileDir = os.path.dirname(app.config.get("USE_4DB_NAME"))

        domdbFile = os.path.join(dbfileDir, dbfileName)

        count = 0
        with SqliteManager(domdbFile) as sdb:
            str_sql = '''SELECT
                            count( * ) AS count
                        FROM
                            project_config
                        WHERE
                            ProjectID = ?'''
            listData = sdb.exec_query(str_sql, (projId,))
            if len(listData):
                count = listData[0].get("count")
        if count == 0:
            return jsonify(dict(err=1, msg="无此项目", data=list()))

        roomName = ""
        with SqliteManager(domdbFile) as sdb:
            str_sql = '''SELECT
                            content
                        FROM
                            local_config
                        WHERE
                            name = "globalconfig"'''
            listData = sdb.exec_query(str_sql)
        if len(listData) == 0:
            return jsonify(dict(err=1, msg="无全局设备系统定义", data=list()))
        else:
            try:
                configJson = listData[0].get("content").decode("utf-8") if listData[0] is not None else ""
            except:
                configJson = listData[0].get("content").decode("gbk") if listData[0] is not None else ""
            roomName = list(eval(configJson).keys())[0]

        roomPrefix = ""
        with SqliteManager(domdbFile) as sdb:
            str_sql = '''SELECT
                            unitproperty06 AS prop06
                        FROM
                            list_unit13'''
            listData = sdb.exec_query(str_sql)
        if len(listData) > 0:
            for item in listData:
                byteTemp = item.get("prop06").decode("gbk")
                temp = ""
                if byteTemp:
                    temp = eval(byteTemp)
                if len(temp) > 0:
                    if len(temp[0].get("1")) > 0:
                        roomPrefix = temp[0].get("1")
                        break

        with SqliteManager(domdbFile) as sdb:
            str_sql = '''SELECT
                            name,
                            ch_description AS description
                        FROM
                            list_point'''
            pointList = sdb.exec_query(str_sql)

        dictRes = dict()
        for point in pointList:
            pointName = point.get("name").decode("gbk")
            description = point.get("description").decode("gbk")
            if not is_integer(point.get("name")[-2:]):
                continue
            for equip in equip_category:
                equipType = match_catetory(pointName.replace(roomPrefix, ""), equip.get("equipList"))
                if equipType:
                    systemCategory = equip.get("systemCategory")  #chwSystem
                    equipNo = pointName[-2:]
                    if dictRes.get(systemCategory):
                        if dictRes.get(systemCategory).get(equipType):
                            resolve = False
                            for item in dictRes.get(systemCategory).get(equipType):
                                if item.get("number") == equipNo:
                                    item.get("pointList").append({
                                        "name": pointName,
                                        "description": description
                                    })
                                    resolve = True
                            if not resolve:
                                dictRes.get(systemCategory).get(equipType).append({
                                    "prefix": equipType,
                                    "number": equipNo,
                                    "pointList": [{
                                        "name": pointName,
                                        "description": description
                                    }]
                                })
                        else:
                            dictRes.get(systemCategory).update({
                                equipType: [{
                                    "prefix": equipType,
                                    "number": equipNo,
                                    "pointList": [{
                                        "name": pointName,
                                        "description": description
                                    }]
                                }]
                            })
                    else:
                        dictRes.update({
                            systemCategory: {
                                equipType: [{
                                    "prefix": equipType,
                                    "number": equipNo,
                                    "pointList": [{
                                        "name": pointName,
                                        "description": description
                                    }]
                                }]
                            }
                        })

        return jsonify(dict(err=0, msg="设备结构树生成成功", data={roomName: dictRes}))
    except:
        traceback.print_exc()
        return jsonify(dict(err=0, msg="设备结构树生成失败", data=dict()))


@bp_project.route("/getWorkConditionByProjectTimeRange", methods=["POST"])
def project_get_work_condition_by_project_time_range():
    rcv = request.get_json()
    strFrom = rcv.get("timeFrom", "")
    strTo = rcv.get("timeTo", "")
    sortColumn = rcv.get("sortColumn", None)
    roomName = rcv.get("roomName", "")
    projectName = rcv.get("projectName", "")

    if not strFrom or not strTo:
        return jsonify(dict(err=1, msg="开始时间和结束时间不能为空", data=[]))
    if not isinstance(strFrom, str) or not isinstance(strTo, str):
        return jsonify(dict(err=1, msg="开始时间和结束时间必须为字符串", data=[]))
    if not isValidDate(strFrom, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="开始时间格式有误", data=[]))
    if not isValidDate(strTo, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="结束时间格式有误", data=[]))

    headers = {"content-type": "application/json"}
    postData = {"timeFrom": strFrom, "timeTo": strTo, "projectName": projectName, "roomName": roomName, "sortColumn": sortColumn}
    rt = requests.post("http://dom.inwhile.com/api/bigData/getWorkConditionByProjectTimeRange",
                       data=json.dumps(postData), timeout=30, headers=headers)

    if rt.status_code != 200:
        return jsonify(dict(err=1, msg="请求返回有误", data=[]))

    dData = json.loads(rt.text)
    if not isinstance(dData, dict):
        return jsonify(dict(err=1, msg="请求返回有误", data=[]))

    if dData.get("err") > 0:
        return jsonify(dict(err=1, msg=dData.get("msg"), data=[]))

    return jsonify(dData)


@bp_project.route("/insertWorkConditionProjectAtTime", methods=["POST"])
def project_insert_work_condition_project_at_time():
    rcv = request.get_json()
    strTime = rcv.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    dataList = rcv.get("dataList", [])

    if not strTime:
        return jsonify(dict(err=1, msg="时间不能为空", data=[]))
    if not isinstance(strTime, str):
        return jsonify(dict(err=1, msg="时间必须为字符串", data=[]))
    if not isValidDate(strTime, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="时间格式有误", data=[]))
    if not isinstance(dataList, list):
        return jsonify(dict(err=1, msg="数据列表必须为list", data=[]))

    if not len(dataList):
        return jsonify(dict(err=1, msg="数据列表不能为空", data=[]))

    headers = {"content-type": "application/json"}
    postData = {"projectName": get_proj_name(), "time": strTime, "dataList": dataList}

    rt = requests.post("http://dom.inwhile.com/api/bigData/insertWorkConditionProjectAtTime",
                       headers=headers, data=json.dumps(postData), timeout=30)

    if rt.status_code != 200:
        return jsonify(dict(err=1, msg="云端接口返回有误", data=False))

    rtData = json.loads(rt.text)
    if not isinstance(rtData, dict):
        return jsonify(dict(err=1, msg="云端接口返回有误", data=False))

    return jsonify(rtData)

@bp_project.route("/getIdentityFromCloud", methods=["POST"])
def get_project_identity_from_cloud():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    projectId = rcv.get("projectId", None)
    if not isinstance(projectId, int):
        return jsonify(dict(err=1, msg="项目id必须为整数", data=""))

    postData = {"projectId": projectId}
    headers = {"Content-Type": "application/json"}
    try:
        rsp = requests.post("http://47.100.17.99/api/getProjectIdentity", data=json.dumps(postData), headers=headers, timeout=30)
    except Exception as e:
        return jsonify(dict(err=1, msg=e.__str__(), data=""))

    if rsp == None:
        return jsonify(dict(err=1, msg="云端接口请求失败", data=""))
    if rsp.status_code != 200:
        return jsonify(dict(err=1, msg="云端接口返回结果的状态码不等于200", data=""))
    dJson = {}
    try:
        dJson = json.loads(rsp.text)
    except:
        pass

    if dJson.get("err", 1) == 1:
        return jsonify(dict(err=1, msg=dJson.get("msg",""), data=""))
    return jsonify(dict(err=0, msg="", data=dJson.get("data", "")))






