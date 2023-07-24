# -*- coding: utf-8 -*-
from siteinterface.mod_mode import bp_mode
from siteinterface import app
from flask import request, jsonify
from logic.StandardPointName import *
from openpyxl import Workbook
import os
from datetime import datetime
import traceback
from .. BEOPMySqlDBContainer import BEOPMySqlDBContainer
from siteinterface.BEOPSqliteAccess import *
from siteinterface.BEOPDataAccess import BEOPDataAccess
import logging
import xlrd
import re
from siteinterface import app
from siteinterface.mod_mode.utils import *


def modeIdExistsInMode(modeId):
    """
    检查modeId是否已存在于mode表中
    """
    res = False
    try:
        rvConduct = BEOPDataAccess.getInstance().modeIdExistsInMode(modeId)
        if rvConduct and len(rvConduct):
            if len(rvConduct[0]):
                if rvConduct[0][0] > 0:
                    res = True

    except Exception as e:
        strLog = "ERROR in modeIdExistsInMode: %s" % e.__str__()
        logging.error(strLog)

    finally:
        return res

def isValidDate(strDate, strFormat):
    res = False
    try:
        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res

def envIdExistsInEnv(envid):
    """
    检查evnid是否已存在于env表中
    """
    res = False
    try:
        rvConduct = BEOPDataAccess.getInstance().envIdExistsInEnv(envid)
        if rvConduct and len(rvConduct):
            if len(rvConduct[0]):
                if rvConduct[0][0] > 0:
                    res = True

    except Exception as e:
        strLog = "ERROR in envIdExistsInDB: %s" % e.__str__()
        logging.error(strLog)

    finally:
        return res

def isValidTime(strPat, strTime):
    res = False
    try:
        res = re.match(strPat, strTime)
        if res:
            res = True
    except:
        pass
    return res

@bp_mode.route("/copyOneMode", methods=["POST"])
def copy_one_mode():
    try:
        rcv = request.get_json()
        fromModeId = rcv.get("fromModeId") if rcv.get("fromModeId") is not None else None
        modeName = rcv.get("name") if rcv.get("name") is not None else None
        creator = rcv.get("creator") if rcv.get("creator") is not None else None

        if fromModeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))
        if not isinstance(fromModeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为整数"))
        if not modeIdExistsInMode(fromModeId):
            return jsonify(dict(err=1, msg="该模式不存在"))

        if modeName is None:
            return jsonify(dict(err=1, msg="模式名称不能为空"))
        if not isinstance(modeName, str):
            return jsonify(dict(err=1, msg="模式名称必须是一个字符串"))

        if creator is None:
            return jsonify(dict(err=1, msg="创建者不能为空"))
        if not isinstance(creator, str):
            return jsonify(dict(err=1, msg="creator必须为字符串"))

        maxId = BEOPDataAccess.getInstance().getMaxIdInTable("mode")
        modeid = maxId + 1

        # 檢查模式名稱是否已被使用
        modeNameCheck = BEOPDataAccess.getInstance().nameUsedByOtherMode(modeName, modeid)
        if modeNameCheck["code"] > 0:
            return jsonify(dict(err=1, msg="检查模式名称失败"))
        else:
            if modeNameCheck["data"]:
                return jsonify(dict(err=1, msg="该模式名称已被使用，请换一个"))

        tplData = BEOPDataAccess.getInstance().getModeInfoForCopy(fromModeId)
        if tplData is None:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试"))

        if not tplData or len(tplData) < 2:
            return jsonify(dict(err=1, msg="获取欲复制的目标模式内容失败"))

        resultMode = BEOPDataAccess.getInstance().createMode(modeid, tplData[0][0], tplData[0][1], modeName.strip(), tplData[0][2], tplData[0][3], creator, datetime.now())

        bSucModeDetail = True
        if len(tplData[1]):
            bSucModeDetail = BEOPDataAccess.getInstance().insertMultiModeDetail(modeid, tplData[1])

        if resultMode.get("success") and bSucModeDetail:
            return jsonify(dict(err=0, msg="复制成功", data=modeid))
        return jsonify(dict(err=1, msg="复制失败", data=None))

    except Exception as e:
        strLog = "ERROR in copyOneMode: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="复制失败: %s" % e.__str__(), data=False))

@bp_mode.route("/create", methods=["POST"])
def create():
    try:
        rcv = request.get_json()
        type = rcv.get("type") if rcv.get("type") is not None else None
        ena = rcv.get("enabled") if rcv.get("enabled") is not None else 1
        name = rcv.get("name") if rcv.get("name") else None
        description = rcv.get("description") if rcv.get("description") is not None else ""
        tags = rcv.get("tags") if rcv.get("tags") else ""
        creator = rcv.get("creator") if rcv.get("creator") else None
        createtime = datetime.now()

        """
        type:

        0:冷站
        1:热站
        2:BA
        3:照明
        """
        if type is None:
            return jsonify(dict(err=1, msg="type不能为空"))

        if not isinstance(type, int):
            return jsonify(dict(err=1, msg="type必须是一个整数"))

        if ena is None:
            return jsonify(dict(err=1, msg="ena必须是一个整数"))

        if not isinstance(ena, int):
            return jsonify(dict(err=1, msg="enabled 必须是一个整数(0或1)"))

        if not name:
            return jsonify(dict(err=1, msg="模式名称不能为空"))

        if not isinstance(name, str):
            return jsonify(dict(err=1, msg="模式名称必须是一个字符串"))

        if description:
            if not isinstance(description, str):
                return jsonify(dict(err=1, msg="模式描述必须是一个字符串"))

        if not isinstance(tags, str):
            return jsonify(dict(err=1, msg="模式标签必须是一个字符串"))

        if not creator:
            return jsonify(dict(err=1, msg="模式创建者不能为空"))

        if not isinstance(creator, str):
            return jsonify(dict(err=1, msg="模式创建者必须是一个字符串"))

        # 去除模式名称前后的空格
        name = name.strip()

        maxId = BEOPDataAccess.getInstance().getMaxIdInTable("mode")
        modeid = maxId + 1

        # 檢查模式名稱是否已被使用
        modeNameCheck = BEOPDataAccess.getInstance().nameUsedByOtherMode(name, modeid)
        if modeNameCheck["code"] > 0:
            return jsonify(dict(err=1, msg="检查模式名称失败"))
        else:
            if modeNameCheck["data"]:
                return jsonify(dict(err=1, msg="该模式名称已被使用，请换一个"))

        rvConduct = BEOPDataAccess.getInstance().createMode(modeid, type, ena, name, description, tags, creator, createtime)

        if rvConduct:
            return jsonify(dict(err=0, msg="创建成功"))
        else:
            return jsonify(dict(err=1, msg="创建失败"))

    except Exception as e:
        strLog = "ERROR in /mode/create: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="创建失败: %s" % e.__str__()))


@bp_mode.route("/getAll")
def get_all():
    try:
        dData = BEOPDataAccess.getInstance().getAllMode()

        if dData.get("err") > 0:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试", data=[]))

        dMode = dData.get("data", {})
        if not dMode:
            return jsonify(dict(err=0, msg="无模式数据", data=[]))

        minModeId = min(dMode.keys())
        maxModeId = max(dMode.keys())

        idx = minModeId
        dataList = []
        while idx <= maxModeId:
            try:
                dInfo = dMode.get(idx, None)
                if dInfo is None:
                    continue

                dataList.append({
                    "id": dInfo.get("id"),
                    "type": dInfo.get("type"),
                    "enabled": dInfo.get("enabled"),
                    "name": dInfo.get("name"),
                    "description": dInfo.get("description"),
                    "tags": dInfo.get("tags"),
                    "creator": dInfo.get("creator"),
                    "createtime": dInfo.get("createtime").strftime("%Y-%m-%d %H:%M:%S") if dInfo.get("createtime") is not None else ""
                })
            except:
                pass
            finally:
                idx += 1

        return jsonify(dict(err=0, msg="获取成功", data=dataList))

    except Exception as e:
        strLog = "ERROR in /mode/getAll: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="获取失败", data=list()))

@bp_mode.route("/getContentById", methods=["POST"])
def get_by_id():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId")

        if not modeId:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        rvConduct = BEOPDataAccess.getInstance().getModeById(modeId)
        if rvConduct is None:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试"))

        arrMode = rvConduct[0]
        arrDetail = rvConduct[1]

        if len(arrMode):
            dData = {
                    "modeId": arrMode[0][0],
                    "type": arrMode[0][1],
                    "enabled": arrMode[0][2],
                    "name": arrMode[0][3],
                    "description": arrMode[0][4],
                    "tags": arrMode[0][5],
                    "creator": arrMode[0][6],
                    "createtime": arrMode[0][7].strftime("%Y-%m-%d %H:%M:%S"),
                    "detail": []
                }

            arrayDetail = []
            if len(arrDetail):
                for item in arrDetail:
                    arrayDetail.append({
                        "triggerTime": item[3],
                        "envId": item[1],
                        "envName": item[4],
                        "triggerTimeType": item[2],
                        "SystemTimePointName": item[5],
                        "actionOnce": item[6]
                    })

                #sort
                if len(arrayDetail)>=2:
                    for i in range(len(arrayDetail)-1):
                        for j in range(i, len(arrayDetail)):
                            if arrayDetail[i]["triggerTimeType"]==2 and arrayDetail[j]["triggerTimeType"]<2:
                                tt = arrayDetail[i]
                                arrayDetail[i] = arrayDetail[j]
                                arrayDetail[j] = tt
                            elif arrayDetail[i]["triggerTimeType"]== arrayDetail[j]["triggerTimeType"]:
                                if arrayDetail[i]["triggerTime"]> arrayDetail[j]["triggerTime"]:
                                    tt = arrayDetail[i]
                                    arrayDetail[i] = arrayDetail[j]
                                    arrayDetail[j] = tt


                dData["detail"] = arrayDetail

            return jsonify(dict(err=0, msg="获取成功", data=dData))
        else:
            return jsonify(dict(err=1, msg="不存在ID为{0}的记录".format(modeId), data=dict()))

    except Exception as e:
        strLog = "ERROR in /mode/getById: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败", data=dict()))

@bp_mode.route("/remove", methods=["POST"])
def remove():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None

        if not modeId:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        strSource = rcv.get("source", "")
        strIP = request.remote_addr
        strLog = '[IMPORTANT]removeMode: 来自IP:%s, 用户:%s, modeId:%s' % (strIP, strSource, modeId)
        log_info_to_file("dompysite_mode_env_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d")), strLog)

        bSuc = BEOPDataAccess.getInstance().removeMode(modeId)

        if bSuc:
            return jsonify(dict(err=0, msg="删除成功"))
        else:
            return jsonify(dict(err=1, msg="删除失败"))

    except Exception as e:
        strLog = "ERROR in /mode/remove: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="删除失败", data=dict()))

"""
timeType: 0-系统时间；1-绝对时间；2-隔日时间
"""
@bp_mode.route("/addContent", methods=["POST"])
def add_content():
    try:
        rcv = request.get_json()

        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        triggerTime = rcv.get("triggerTime") if rcv.get("triggerTime") else None
        envId = rcv.get("envId") if rcv.get("envId") is not None else None
        timeType = rcv.get("timeType") if rcv.get("timeType") is not None else None
        actionOnce = rcv.get("actionOnce", None)

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        if not triggerTime:
            return jsonify(dict(err=1, msg="触发时间不能为空"))

        if not isinstance(triggerTime, str):
            return jsonify(dict(err=1, msg="触发时间必须是一个字符串"))

        if envId is None:
            return jsonify(dict(err=1, msg="场景ID不能为空"))

        if not isinstance(envId, int):
            return jsonify(dict(err=1, msg="场景ID必须是一个整数"))

        if timeType is None:
            return jsonify(dict(err=1, msg="timeType不能为空"))

        if not isinstance(timeType, int):
            return jsonify(dict(err=1, msg="timeType必须为一个整数"))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在"))

        if not envIdExistsInEnv(envId):
            return jsonify(dict(err=1, msg="场景ID不存在"))

        if actionOnce is not None:
            if actionOnce not in [0, 1]:
                return jsonify(dict(err=1, msg="actionOnce必须为0或者1"))

        if actionOnce is None:
            actionOnce = 0

        # 绝对时间
        if timeType == 1:
            # 检查触发时间的格式
            if not isValidDate(triggerTime, "%H:%M"):
                return jsonify(dict(err=1, msg="triggerTime格式不正确"))

            if not isValidTime("^[0-9]{2}:[0-9]{2}$", triggerTime):
                return jsonify(dict(err=1, msg="触发时间格式不对（必须形如：09:00）"))

        # 隔日时间
        elif timeType == 2:
            if not isValidDate(triggerTime, "%H:%M"):
                return jsonify(dict(err=1, msg="触发时间有误"))

            # 隔日时间做处理，加24小时
            tTriggerTime = datetime.strptime(triggerTime, "%H:%M")
            hour = tTriggerTime.hour
            minute = tTriggerTime.minute
            newHour = 24 + hour

            if newHour >= 48:
                return jsonify(dict(err=1, msg="第二天的触发时间不能大于等于48"))

            triggerTime = "%02d:%02d" % (newHour, minute)

        elif timeType == 0:
            if not BEOPSqliteAccess.getInstance().pointExists(triggerTime):
                return jsonify(dict(err=1, msg="该点不存在: {0}".format(triggerTime), data=False))

        removeSuc = BEOPDataAccess.getInstance().removeModeDetailContent(modeId, triggerTime, envId)

        if not removeSuc:
            return jsonify(dict(err=1, msg="清除mode_detail中的旧记录失败"))

        result = BEOPDataAccess.getInstance().insertIntoModeDetail(modeId, triggerTime, timeType, envId, actionOnce)

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result["msg"], data=result["data"]))
        else:
            return jsonify(dict(err=0, msg=result["msg"], data=result["data"]))

    except Exception as e:
        strLog = "ERROR in /mode/addContent: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="保存失败：%s" % e.__str__(), data=False))

@bp_mode.route("/edit", methods=["POST"])
def edit():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        type = rcv.get("type") if rcv.get("type") is not None else None
        ena = rcv.get("enabled") if rcv.get("enabled") is not None else 1
        name = rcv.get("name") if rcv.get("name") else None
        description = rcv.get("description") if rcv.get("description") else None
        tags = rcv.get("tags") if rcv.get("tags") else None
        creator = rcv.get("creator") if rcv.get("creator") else None

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空", data=""))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为一个整数", data=""))

        if type:
            if not isinstance(type, int):
                return jsonify(dict(err=1, msg="type 必须是一个整数或空字符串"))

        if ena:
            if not isinstance(ena, int):
                return jsonify(dict(err=1, msg="enabled 必须是一个整数或者不传入（不传入默认为1）"))

        if not name:
            return jsonify(dict(err=1, msg="无模式名称"))

        if not isinstance(name, str):
            return jsonify(dict(err=1, msg="模式名称必须是一个字符串"))

        if description:
            if not isinstance(description, str):
                return jsonify(dict(err=1, msg="模式描述必须是一个字符串"))

        if tags:
            if not isinstance(tags, str):
                return jsonify(dict(err=1, msg="模式标签必须是一个字符串"))

        if not creator:
            return jsonify(dict(err=1, msg="无模式创建者"))

        if not isinstance(creator, str):
            return jsonify(dict(err=1, msg="模式创建者必须是一个字符串"))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在"))

        strSource = rcv.get("source", "")
        strIP = request.remote_addr
        strLog = '[IMPORTANT]editMode: 来自IP:%s, 用户:%s, type:%s  modeId:%s' % (strIP, strSource, type, modeId)
        log_info_to_file("dompysite_mode_env_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d")), strLog)

        # 去除模式名称前后的空格
        name = name.strip()

        # 檢查模式名稱是否已被使用
        modeNameCheck = BEOPDataAccess.getInstance().nameUsedByOtherMode(name, modeId)
        if modeNameCheck["code"] > 0:
            return jsonify(dict(err=1, msg="检查模式名称失败"))
        else:
            if modeNameCheck["data"]:
                return jsonify(dict(err=1, msg="该模式名称已被使用，请换一个"))

        paramList = []
        strSetList = []
        for item in [(type, "type"), (ena, "enabled"), (name, "name"), (description, "description"), (tags, "tags"), (creator, "creator")]:
            if item[0] is not None:
                paramList.append(item[0])
                strSetList.append("{0}=%s".format(item[1]))

        rvConduct = BEOPDataAccess.getInstance().editMode(paramList, strSetList, modeId)
        if type is not None:
            bCalendarUpdate = BEOPDataAccess.getInstance().updateModeTypeInModeCalendar(modeId, type)

        if rvConduct:
            return jsonify(dict(err=0, msg="修改成功"))
        else:
            return jsonify(dict(err=1, msg="修改失败"))

    except Exception as e:
        strLog = "ERROR in /mode/edit: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="删除失败：%s" % e.__str__()))

@bp_mode.route("/removeContent", methods=["POST"])
def remove_content():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        triggerTime = rcv.get("triggerTime") if rcv.get("triggerTime") else None
        envId = rcv.get("envId") if rcv.get("envId") is not None else None
        triggerTimeType = rcv.get("triggerTimeType") if rcv.get("triggerTimeType") is not None else None
        systemTimePointName = rcv.get("systemTimePointName") if rcv.get("systemTimePointName") is not None else None

        if not modeId:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        if not triggerTime:
            return jsonify(dict(err=1, msg="触发时间不能为空"))

        if not isinstance(triggerTime, str):
            return jsonify(dict(err=1, msg="触发时间必须是一个字符串"))

        if not envId:
            return jsonify(dict(err=1, msg="场景ID不能为空"))

        if not isinstance(envId, int):
            return jsonify(dict(err=1, msg="场景ID必须为一个整数"))

        if triggerTimeType is None:
            return jsonify(dict(err=1, msg="triggerTimeType不能为空"))

        if not isinstance(triggerTimeType, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        if systemTimePointName is None:
            return jsonify(dict(err=1, msg="systemTimePointName不能为空"))

        if not isinstance(systemTimePointName, str):
            return jsonify(dict(err=1, msg="systemTimePointName必须是一个字符串"))

        triggerTimeOrPointName = triggerTime
        if triggerTimeType == 0:
            triggerTimeOrPointName = systemTimePointName
        elif triggerTimeType == 2:
            # 隔日时间做处理，加24小时
            tTriggerTime = datetime.strptime(triggerTime, "%H:%M")
            hour = tTriggerTime.hour
            minute = tTriggerTime.minute
            newHour = 24 + hour

            triggerTimeOrPointName = "%02d:%02d" % (newHour, minute)

        bSuc = BEOPDataAccess.getInstance().removeModeDetailContent(modeId, triggerTimeOrPointName, envId)

        if bSuc:
            return jsonify(dict(err=0, msg="删除成功"))
        else:
            return jsonify(dict(err=1, msg="删除失败"))

    except Exception as e:
        strLog = "ERROR in /mode/removeContent: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="删除失败：%s" % e.__str__(), data=dict()))

@bp_mode.route("/getConfig", methods=["GET"])
def get_config():
    try:
        rv = BEOPDataAccess.getInstance().getSystemTimeDefine()

        if rv.get("err") == 1:
            return jsonify(err=1, msg="4db文件不存在", data=list())

        elif rv.get("err") == 2:
            return jsonify(err=1, msg="无系统时间配置项", data=list())

        elif rv.get("err") == 3:
            return jsonify(err=1, msg=rv.get("msg"), data=list())

        else:
            return jsonify(err=0, msg="获取成功", data=rv.get("data"))

    except Exception as e:
        strLog = "ERROR in /mode/getConfig: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败：%s" % e.__str__(), data=list()))

@bp_mode.route("/getModeByType", methods=["POST"])
def get_mode_by_type():
    try:
        rcv = request.get_json()
        type = rcv.get("type") if rcv.get("type") is not None else None

        # if type is None:
        #     return jsonify(dict(err=1, msg="type不能为空"))
        #
        # if not isinstance(type, int):
        #     return jsonify(dict(err=1, msg="type必须为一个整数"))

        result = BEOPDataAccess.getInstance().getModeByType(type)

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=result.get("data")))
        else:
            return jsonify(dict(err=0, msg=result.get("msg"), data=result.get("data")))

    except Exception as e:
        strLog = "ERROR in /mode/getModeByType: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败：%s" % e.__str__(), data=[]))

'''
golding add for upload to cloud
'''
@bp_mode.route("/getTodayModeListOfAllType", methods=["POST"])
def get_today_mode_list_of_all_type():
    try:
        rcv = request.get_json()

        strTimeToday = datetime.now().strftime("%Y-%m-%d")

        dMode = BEOPDataAccess.getInstance().getModeByType(None)

        if dMode.get("code") > 0:
            return jsonify(dict(err=1, msg=dMode.get("msg"), data=dMode.get("data")))
        if not len(dMode.get("data")):
            return jsonify(dict(err=0, msg="获取成功", data=[]))

        todayMode = BEOPDataAccess.getInstance().getModeByTime(strTimeToday)

        if todayMode.get("code") > 0:
            return jsonify(dict(err=1, msg=todayMode.get("msg"), data=[]))

        modeList = []
        for mode in dMode.get("data"):
            mode["active"] = 0
            if mode.get("modeId") in todayMode.get("data"):
                mode["active"] = 1
            modeList.append(mode)

        return jsonify(dict(err=0, msg="获取成功", data=modeList))

    except Exception as e:
        strLog = "ERROR in /mode/getTodayModeListOfAllType: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败：%s" % e.__str__(), data=[]))

@bp_mode.route("/getTodayModeList", methods=["POST"])
def get_today_mode_list():
    try:
        rcv = request.get_json()
        type = rcv.get("type") if rcv.get("type") is not None else None

        if type is None:
            return jsonify(dict(err=1, msg="type不能为空"))

        if not isinstance(type, int):
            return jsonify(dict(err=1, msg="type必须为一个整数"))

        strTimeToday = datetime.now().strftime("%Y-%m-%d")

        dMode = BEOPDataAccess.getInstance().getModeByType(type)

        if dMode.get("code") > 0:
            return jsonify(dict(err=1, msg=dMode.get("msg"), data=dMode.get("data")))
        if not len(dMode.get("data")):
            return jsonify(dict(err=0, msg="获取成功", data=[]))

        todayMode = BEOPDataAccess.getInstance().getModeByTypeAndTime(strTimeToday, type)

        if todayMode.get("code") > 0:
            return jsonify(dict(err=1, msg=todayMode.get("msg"), data=[]))

        modeList = []
        for mode in dMode.get("data"):
            mode["active"] = 0
            if mode.get("modeId") == todayMode.get("data"):
                mode["active"] = 1
            modeList.append(mode)

        return jsonify(dict(err=0, msg="获取成功", data=modeList))

    except Exception as e:
        strLog = "ERROR in /mode/getTodayModeList: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败：%s" % e.__str__(), data=[]))


@bp_mode.route("/getTodayModeListOfTypes", methods=["POST"])
def get_today_mode_list_of_types():
    try:
        rcv = request.get_json()
        typeList = rcv.get("type") if rcv.get("type") is not None else None
        strDate = rcv.get("date", datetime.now().strftime("%Y-%m-%d"))

        if typeList is None:
            return jsonify(dict(err=1, msg="type不能为空"))

        if not isinstance(typeList, list):
            typeList = [typeList]

        if not len(typeList):
            return jsonify(dict(err=1, msg="type列表不能为空"))

        for nType in typeList:
            if not isinstance(nType, int):
                return jsonify(dict(err=1, msg="type必须为整数"))

        if not isinstance(strDate, str):
            return jsonify(dict(err=1, msg="日期必须为字符串"))

        allModeDict = BEOPDataAccess.getInstance().getModeByTypeList(typeList)

        if allModeDict.get("code") > 0:
            return jsonify(dict(err=1, msg=allModeDict.get("msg"), data=allModeDict.get("data")))
        if not len(allModeDict.get("data")):
            return jsonify(dict(err=0, msg="获取成功", data=[]))

        modeGroupDict = {0: "冷站", 1: "热站", 2: "BA末端", 3: "照明", 4: "自定义1", 5: "自定义2", 6: "自定义3", 7: "自定义4", 8: "自定义5"}
        dModeGroup = BEOPSqliteAccess.getInstance().getModeGroupDefine()
        if dModeGroup:
            modeGroupDict = dModeGroup

        todayModeDict = BEOPDataAccess.getInstance().getModeByTypeListAndTime(strDate, typeList)

        if todayModeDict.get("code") > 0:
            return jsonify(dict(err=1, msg=todayModeDict.get("msg"), data=[]))

        resultList = []
        for nType, lMode in allModeDict.get("data").items():
            modeList = []
            for mode in lMode:
                mode["active"] = 0
                if mode.get("modeId") == todayModeDict.get("data").get(nType):
                    mode["active"] = 1
                modeList.append(mode)

            # 按模式id升序排列
            for i in range(len(modeList)):
                for j in range(len(modeList)-i-1):
                    if modeList[j].get("modeId") > modeList[j+1].get("modeId"):
                        modeList[j], modeList[j+1] = modeList[j+1], modeList[j]

            try:
                strName = modeGroupDict.get(nType)
            except:
                strName = ""
            resultList.append({"type": nType, "modeList": modeList, "name": strName, "date": strDate})

        return jsonify(dict(err=0, msg="获取成功", data=resultList))

    except Exception as e:
        strLog = "ERROR in /mode/getTodayModeList: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败：%s" % e.__str__(), data=[]))


"""
timeType: 0-系统时间(读取一个值为时间字符串的点值作为时间)；1-绝对时间；2-隔日时间
SystemTimePointName: 用于携带时间的点名，若需要修改则传入旧点名
"""
@bp_mode.route("/editContent", methods=["POST"])
def edit_content():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        systemTimePointName = rcv.get("SystemTimePointName") if rcv.get("SystemTimePointName") is not None else None

        oldTime = rcv.get("oldTime") if rcv.get("oldTime") is not None else None
        oldTimeType = rcv.get("oldTimeType") if rcv.get("oldTimeType") is not None else None
        oldEnvId = rcv.get("oldEnvId") if rcv.get("oldEnvId") is not None else None

        newTime = rcv.get("newTime") if rcv.get("newTime") is not None else None
        newTimeType = rcv.get("newTimeType") if rcv.get("newTimeType") is not None else None
        newEnvId = rcv.get("newEnvId") if rcv.get("newEnvId") is not None else None

        actionOnce = rcv.get("actionOnce", None)

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须是一个整数"))

        if oldTime is None:
            return jsonify(dict(err=1, msg="oldTime不能为空"))

        if not isinstance(oldTime, str):
            return jsonify(dict(err=1, msg="oldTime必须为字符串"))

        if oldTimeType is None:
            return jsonify(dict(err=1, msg="oldTimeType不能为空"))

        if not isinstance(oldTimeType, int):
            return jsonify(dict(err=1, msg="oldTimeType必须为整数"))

        if not oldEnvId:
            return jsonify(dict(err=1, msg="oldEnvId不能为空"))

        if not isinstance(oldEnvId, int):
            return jsonify(dict(err=1, msg="oldEnvId必须为整数"))

        # 若旧时间为隔日时间则处理一下
        if oldTimeType == 2:
            tOldTime = datetime.strptime(oldTime, "%H:%M")
            hour = tOldTime.hour
            minute = tOldTime.minute
            newHour = 24 + hour
            oldTime = "%02d:%02d" % (newHour, minute)

        if newTime:
            if newTimeType is None:
                return jsonify(dict(err=1, msg="当修改时间时newTimeType不能为空"))

            if not isinstance(newTime, str):
                return jsonify(dict(err=1, msg="newTime必须为字符串"))

            if not isinstance(newTimeType, int):
                return jsonify(dict(err=1, msg="newTimeType必须为整数"))

            if newTimeType == 1 and not isValidDate(newTime, "%H:%M"):
                return jsonify(dict(err=1, msg="newTime格式不正确"))

            if newTimeType == 1 and not isValidTime("^[0-9]{2}:[0-9]{2}$", newTime):
                return jsonify(dict(err=1, msg="触发时间格式不对（必须形如：09:00）"))

            # 若为隔日，则增加24小时
            if newTimeType == 2:

                if not isValidDate(newTime, "%H:%M"):
                    return jsonify(dict(err=1, msg="触发时间有误"))

                tNewTime = datetime.strptime(newTime, "%H:%M")
                hour = tNewTime.hour
                minute = tNewTime.minute
                newHour = 24 + hour

                if newHour >= 48:
                    return jsonify(dict(err=1, msg="第二天的触发时间不能大于等于48"))

                newTime = "%02d:%02d" % (newHour, minute)
        else:
            # 若不修改时间则使用旧的
            newTimeType = oldTimeType
            if oldTimeType == 1:
                newTime = oldTime
            else:
                newTime = systemTimePointName

        if newEnvId:
            if not isinstance(newEnvId, int):
                return jsonify(dict(err=1, msg="newEnvId必须为整数"))

        # 若不传newEnvId则用oldEnvId赋值
        if newEnvId is None:
            newEnvId = oldEnvId

        if not envIdExistsInEnv(newEnvId):
            return jsonify(dict(err=1, msg="newEnvId不存在"))

        oldTimeInDB = systemTimePointName if oldTimeType == 0 else oldTime

        strSource = rcv.get("source", "")
        strIP = request.remote_addr
        strLog = '[IMPORTANT]editContent: 来自IP:%s, 用户:%s, modeId:%s' % (strIP, strSource, modeId)
        log_info_to_file("dompysite_mode_env_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d")), strLog)

        res = BEOPDataAccess.getInstance().updateModeDetail(modeId, oldTimeInDB, oldTimeType, oldEnvId, newTime, newTimeType, newEnvId, actionOnce)

        if res["code"] > 0:
            return jsonify(dict(err=1, msg=res["msg"], data=False))
        else:
            return jsonify(dict(err=0, msg=res["msg"], data=True))

    except Exception as e:
        strLog = "ERROR in /mode/editContent: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="修改失败：%s" % e.__str__(), data=False))


@bp_mode.route("/batchDelete", methods=["POST"])
def batch_delete_mode():
    try:
        rcv = request.get_json()
        nType = rcv.get("type", None)
        if nType is None:
            return jsonify(dict(err=1, msg="模式类型不能为空", data=False))
        if not isinstance(nType, int):
            return jsonify(dict(err=1, msg="模式类型必须为整数", data=False))

        strSource = rcv.get("source", "")
        strIP = request.remote_addr
        strLog = '[IMPORTANT]batchDelete: 来自IP:%s, 用户:%s, type:%s' % (strIP, strSource, nType)
        log_info_to_file("dompysite_mode_env_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d")), strLog)

        typeModeDict = BEOPDataAccess.getInstance().getModeTypeDict()
        if typeModeDict.get("code") > 0:
            return jsonify(dict(err=1, msg="删除失败", data=False))

        if nType not in typeModeDict.get("data").keys():
            return jsonify(dict(err=1, msg="所输入的模式类型不存在", data=False))

        bSuc = BEOPDataAccess.getInstance().batchDeleteMode(nType, typeModeDict.get("data").get(nType))

        if bSuc:
            return jsonify(dict(err=0, msg="删除成功", data=True))
        return jsonify(dict(err=1, msg="删除失败", data=False))

    except Exception as e:
        logging.error("ERROR in /mode/batchDelete: %s" % e.__str__())
        return jsonify(dict(err=1, msg="删除失败: %s" % e.__str__(), data=False))
