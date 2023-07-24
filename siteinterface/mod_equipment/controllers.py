
from siteinterface.mod_equipment import bp_equipment
from flask import request, jsonify
from .utils import equipCategoryList
from siteinterface.BEOPSqliteAccess import *
from siteinterface.BEOPDataAccess import BEOPDataAccess
from flask import Response, render_template
import qrcode
from io import BytesIO
from bson import ObjectId
from siteinterface.mod_equipment.utils import get_equipment_template_type
from siteinterface.mod_equipment.utils import fetchImportAssetTmplTable, is_digit


@bp_equipment.route("/getRoomEquipmentListAndStatus")
def get_room_equipment_list_and_status():
    try:
        globalconfig = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig("globalconfig")

        if not globalconfig:
            return jsonify(dict(err=1, msg="获取设备系统自定义失败", data=[]))

        dGlobalconfig = json.loads(globalconfig)

        roomList = dGlobalconfig.get("ChillerPlantRoom", [])

        pList = []
        plantList = []
        for room in roomList:
            roomNameZh = room.get("RoomNameCHS", "")
            roomNameEn = room.get("RoomName", "")
            equipList = []
            for category in equipCategoryList:
                noList = []
                strEquipGroup = room.get(category.get("key"), None)

                if not strEquipGroup:
                    continue

                for equipGroup in strEquipGroup.split("|"):
                    noList.extend(equipGroup.split(","))

                numList = list(set(noList))

                for equipNum in numList:
                    OnOffSettingPointName = "{plant}{prefix}OnOffSetting{num:0>2d}".format(plant=roomNameEn, prefix=category.get("prefix"), num=int(equipNum))
                    OnOffPointName = "{plant}{prefix}OnOff{num:0>2d}".format(plant=roomNameEn, prefix=category.get("prefix"), num=int(equipNum))
                    equipName = "{num:0>2d}#{name_zh}".format(num=int(equipNum), name_zh=category.get("name_zh"))

                    if OnOffSettingPointName not in pList:
                        pList.append(OnOffSettingPointName)
                    if OnOffPointName not in pList:
                        pList.append(OnOffPointName)

                    equipList.append(dict(equipName=equipName, OnOffSettingPointName=OnOffSettingPointName, OnOffPointName=OnOffPointName))

            plantList.append({
                "RoomNameCHS": roomNameZh,
                "EquipmentList": equipList,
                "RoomName": roomNameEn
            })

        pointDataList, pointDataDict = BEOPDataAccess.getInstance().getInputTable(pList)

        resList = []
        for plant in plantList:
            facilityList = []
            for facility in plant.get("EquipmentList"):
                OnOffSettingPointName = facility.get("OnOffSettingPointName")
                OnOffPointName = facility.get("OnOffPointName")
                onoffSettingValue = pointDataDict.get(OnOffSettingPointName)
                onoffValue = pointDataDict.get(OnOffPointName)

                if onoffSettingValue is None or onoffValue is None:
                    continue

                facility.update({
                    "OnOffSettingValue": onoffSettingValue,
                    "OnOffValue": onoffValue
                })

                facilityList.append(facility)

            resList.append(dict(RoomNameCHS=plant.get("RoomNameCHS"), EquipmentList=facilityList, RoomName=plant.get("RoomName", "")))

        return jsonify(dict(err=0, msg="", data=resList))

    except Exception as e:
        logging.error("ERROR in /equipment/getRoomEquipmentListAndStatus: %s" % e.__str__())
        return jsonify(dict(err=1, msg="获取失败", data=[]))


"""
设备管理首页：
pageSize: 需要获取第一页的页面大小

:return：dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
               'data' = 正常返回的是设备list的第一页数据，否则是None, 'total' = 总共记录的数量，出错时为-1)
"""
@bp_equipment.route('/firstPage', methods=["POST"])
def equipment_management():

    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}

    try:
        targetPage = 1
        data = request.get_json()
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        pageSize = int(data.get('pageSize'))
        if 'projectId' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        projectId = int(data.get('projectId'))

        print(pageSize)
        # data, pageNum = getPage(posts, targetPage, pageSize)
        data, total = BEOPDataAccess.getInstance().getEquipmentsList(targetPage, pageSize, projectId)
        result['total'] = total
        result['data'] = data
        print("kkkk")
    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
        result['data'] = None
        result['total'] = -1
    return json.dumps(result, ensure_ascii=False)


"""
设备添加功能：
    request中需要包含应添加的设备各字段（除id）信息，json格式
    pageSize：所需获取的当前页面大小
    设备各字段参见本文件头
:return: dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
'data' = 正常返回的是设备的id，否则是None， 'total' = 总共记录的数量，出错时为-1)
"""
@bp_equipment.route('/add', methods=["POST"])
def equipment_add():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()

        if 'type' not in data:
            raise Exception('设备类型信息不存在')
        type = data.get('type')

        if 'area_id' not in data:
            raise Exception('设备位置信息不存在')
        area_id = data.get('area_id')

        if 'model_id' not in data:
            raise Exception('设备模板类型信息不存在')
        model_id = data.get('model_id')

        if 'system_id' not in data:
            raise Exception('没有选择系统归类')
        system_id = data.get('system_id')

        if 'projectId' not in data:
            projectId = 0
        else:
            projectId = int(data.get('projectId'))

        if 'name' not in data:
            raise Exception('设备名称信息不存在')
        name = data.get('name').strip()

        if 'description' not in data:
            description = ""
        else:
            description = data.get('description')

        if 'online_addr' not in data:
            online_addr = ""
        else:
            online_addr = data.get('online_addr')

        if 'installLocation' not in data:
            installLocation = ""
        else:
            installLocation = data.get('installLocation').strip()

        if 'communicateStatus' not in data:
            communicateStatus = 0
        else:
            communicateStatus = int(data.get('communicateStatus'))

        if 'maintenanceStatus' not in data:
            maintenanceStatus = 0
        else:
            maintenanceStatus = int(data.get('maintenanceStatus'))

        if 'repairStatus' not in data:
            repairStatus = 0
        else:
            repairStatus = int(data.get('repairStatus'))

        if 'repairResponsiblePerson' not in data:
            repairResponsiblePerson = ""
        else:
            repairResponsiblePerson = data.get('repairResponsiblePerson')

        if 'warningStatus' not in data:
            warningStatus = 0
        else:
            warningStatus = int(data.get('warningStatus'))

        if name == '':
            raise Exception('设备名称不能为空或仅为空格')

        if communicateStatus < 0:
             raise Exception('通信状态信息应为自然数')
        if maintenanceStatus < 0:
             raise Exception('保养状态信息应为自然数')
        if repairStatus < 0:
             raise Exception('维修状态信息应为自然数')
        if warningStatus < 0:
             raise Exception('告警状态信息应为自然数')

        post = {
            "type": type,
            "projectId": projectId,
            "name": name,
            "description": description,
            "online_addr": online_addr,
            "installLocation": installLocation,
            "communicateStatus": communicateStatus,
            "maintenanceStatus": maintenanceStatus,
            "repairStatus": repairStatus,
            "repairResponsiblePerson": repairResponsiblePerson,
            "warningStatus": warningStatus,
            "area_id": area_id,
            "model_id": model_id,
            "system_id": system_id
        }

        post = [type, projectId, name, description, online_addr, maintenanceStatus, repairStatus,
                repairResponsiblePerson, installLocation, communicateStatus, warningStatus,area_id,model_id,system_id]

        # print(json.dumps(post, ensure_ascii=False))

        # 在insert完后。post发生了改变。自动添加了 '_id' 这个字段。如果直接进行dumps则会出现
        # ObjectId 无法序列化json错误
        # 已改成 mysql 存储  没有此问题了

        pageSize = 1
        postId, total = BEOPDataAccess.getInstance().addEquipment(post, pageSize)
        result['data'] = str(postId)
        result['total'] = total
    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
        result['data'] = None
        result['total'] = -1

    return json.dumps(result, ensure_ascii=False)


"""
设备删除功能：
    delArray: 应删除的设备id数组
    curPage: 当前页面中显示的设备list的page
    pageSize: 所需获取的页面大小
    设备删除后，返回DB中设备list当前page中所有设备信息，用以更新页面
:return: dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
              'data' = 正常返回的是DB中删除设备后的当前页的所有设备信息，否则是None，
               'total' = 总共记录的数量，出错时为-1
              )
"""
@bp_equipment.route('/delete', methods=["POST"])
def equipment_delete():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        print(data)
        if 'projectId' not in data:
            raise Exception('请求中项目Id信息不存在')
        projectId = int(data.get('projectId'))
        if 'delArray' not in data:
            raise Exception('所要删除的数据_id信息不存在')
        delArray = data['delArray']
        if 'curPage' not in data:
            raise Exception('当前列表所处页信息不存在')
        curPage = int(data['curPage'])
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        pageSize = int(data.get('pageSize'))

        #删除且获取更新后的当前页面
        data, total = BEOPDataAccess.getInstance().delEquipments(projectId, delArray, pageSize, curPage)

        result['data'] = data
        result['total'] = total

        for equip_id in delArray:
            BEOPDataAccess.getInstance().delAsset(equip_id, projectId)

    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
        result['total']= 0

    return json.dumps(result, ensure_ascii=False)


"""
设备信息修改功能：
    request中需要包含应修改的设备各字段信息，json格式
    设备各字段参见本文件头
:return:dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
              'data' = 正常返回的是设备的id，否则是None)
"""
@bp_equipment.route('/modify', methods=["POST"])
def equipment_modify():
    result = {'status':True, 'msg':'ok', 'data':None}
    try:
        data = request.get_json()
        print(data)
        if 'id' not in data:
            raise Exception('设备id信息不存在')
        id = int(data.get('id'))

        if 'type' not in data:
            raise Exception('设备类型信息不存在')
        type = data.get('type')

        if 'projectId' not in data:
            projectId = 0
        else:
            projectId = int(data.get('projectId'))

        if 'name' not in data:
            raise Exception('设备名称信息不存在')
        name = data.get('name').strip()

        if 'description' not in data:
            description = ""
        else:
            description = data.get('description')

        if 'online_addr' not in data:
            online_addr = ""
        else:
            online_addr = data.get('online_addr')

        if 'installLocation' not in data:
            installLocation = ""
        else:
            installLocation = data.get('installLocation').strip()

        if 'communicateStatus' not in data:
            communicateStatus = 0
        else:
            communicateStatus = int(data.get('communicateStatus'))

        if 'maintenanceStatus' not in data:
            maintenanceStatus = 0
        else:
            maintenanceStatus = int(data.get('maintenanceStatus'))

        if 'repairStatus' not in data:
            repairStatus = 0
        else:
            repairStatus = int(data.get('repairStatus'))

        if 'repairResponsiblePerson' not in data:
            repairResponsiblePerson = ""
        else:
            repairResponsiblePerson = data.get('repairResponsiblePerson')

        if 'warningStatus' not in data:
            warningStatus = 0
        else:
            warningStatus = int(data.get('warningStatus'))

        if 'area_id' not in data:
            raise Exception('设备类型信息不存在')
        area_id = data.get('area_id')

        if 'model_id' not in data:
            raise Exception('设备模板类型信息不存在')
        model_id = data.get('model_id')

        if 'system_id' not in data:
            raise Exception('没有选择系统归类')
        system_id = data.get('system_id')


        # 判断一堆的参数是否符合条件
        if name == '':
            raise Exception('设备名称不能为空或仅为空格')
        if communicateStatus < 0:
             raise Exception('通信状态信息应为自然数')
        if maintenanceStatus < 0:
             raise Exception('保养状态信息应为自然数')
        if repairStatus < 0:
             raise Exception('维修状态信息应为自然数')
        if warningStatus < 0:
             raise Exception('告警状态信息应为自然数')

        post = [type, projectId, name, description, online_addr, maintenanceStatus, repairStatus,
                repairResponsiblePerson, installLocation, communicateStatus, warningStatus,area_id,model_id,system_id,id]

        BEOPDataAccess.getInstance().modifyEquipment(post)
        result['data'] = id
    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


"""
设备列表分页获取功能：
    pageSize: 获取的页面大小
    targetPage: 需要获取的设备list的第targetPage页 (页面编号从1开始)
:return:dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
              'data' = 正常返回的是DB中设备list当前页的所有设备信息，否则是None，
              'total' = 总共记录的数量，出错时为-1)
"""
@bp_equipment.route('/getPage', methods=["POST"])
def equipment_getPage():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'projectId' not in data:
            raise Exception('请求中项目Id信息不存在')
        projectId = int(data.get('projectId'))
        if 'targetPage' not in data:
            raise Exception('请求中不存在目标页面字段')
        targetPage = int(data.get('targetPage'))
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        pageSize = int(data.get('pageSize'))

        data, total = BEOPDataAccess.getInstance().getEquipmentsList(targetPage, pageSize, projectId)
        result['data'] = data
        result['total'] = total

    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

"""
设备搜索功能（支持设备名称，安装位置，负责人名称字段）：
    searchKey: 关键字
    pageSize: 获取的页面大小
    targetPage: 目标页
:return:dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,
            'status' = False or True，出错为False
            'flag' = False or True  True代表查询有结果，False代表查询关键词没有结果，此时返回的是设备第一页的信息
              'data' = 正常返回的是DB中符合搜索词的所有设备信息，否则是None，
              'total' = 总共满足条件的记录的数量，出错时为-1,如果为0，则)
"""
@bp_equipment.route('/search', methods=["POST"])
def equipment_search():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1, 'flag': True}
    try:
        data = request.get_json()
        if 'projectId' not in data:
            raise Exception('请求中项目Id信息不存在')
        projectId = int(data.get('projectId'))
        if 'searchKey' not in data:
            raise Exception('请求中不存在搜索关键字字段')
        searchKey = data.get('searchKey').strip()
        if 'targetPage' not in data:
            raise Exception('请求中不存在目标页面字段')
        targetPage = int(data.get('targetPage'))
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        pageSize = int(data.get('pageSize'))

        system_id=""
        if 'system_id' in data:
            system_id = data.get('system_id')

        data = []
        flag = False
        total = 0
        data, total, flag = BEOPDataAccess.getInstance().searchEquipment(projectId, searchKey,system_id, pageSize, targetPage)
        result['data'] = data
        result['total'] = total
        result['flag'] = flag

    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

"""
设备搜索功能（支持设备名称，安装位置，负责人名称字段）：
    _id: 关键字
:return:dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,
            'status' = False or True，出错为False
              'data' = 正常返回的是_id对应的设备信息，不存在或者出错返回None根据status判断，
"""
@bp_equipment.route('/searchById', methods=['POST'])
def equipment_searchById():
    result = {'status':True, 'msg':'ok', 'data':None}
    try:
        data = request.get_json()
        if '_id' not in data:
            raise Exception('请求中项目Id信息不存在')
        _id = data.get('_id')
        data = BEOPDataAccess.getInstance().getEquipmentById(_id)
        result['data'] = data
    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:取得模板列表
auth:huangzhijun
param:{"project_id":"280"}
return:{"status": true, "data": [{"name": "水泵模板", "id": 1}, {"name": "主机模板", "id": 2}], "msg": "ok"}
'''
@bp_equipment.route('/getAssetTemplates', methods=['POST'])
def get_AssetTemplates():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'project_id' not in data:
            raise Exception('请求中项目Id信息不存在')

        project_id = data.get('project_id')
        data = BEOPDataAccess.getInstance().getAssetTemplates(project_id)

        resList = []
        for key, value in data.items():
            resList.append({
                "id": key,
                "name": value
            })

        result['data'] = resList
    except Exception as e:
        print('interface getAssetTemplates error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:新增资产信息
auth:huangzhijun
param:{"project_id":280,"equip_id":34,"assetData":[{"input_power":"2200"},
{"rated_current":"4"},
{"voltage":"220"},
{"speed":"3000"},
{"rated_power":"550"},
{"power_factor":"1"},
{"frequency":"10"},
{"attachment":"5米电源线"},
{"lift":"10"},
{"commissioning_date":"2018-08-09"},
{"brand":"美泰"},
{"model":"JSB3564875"},
{"equip_no":"JS0021223"}]}
return:{"msg": "ok", "data": None, "status": true}

'''
@bp_equipment.route('/addAsset', methods=['POST'])
def add_Asset():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'equip_id' not in data:
            raise Exception('请求中项目equip_id信息不存在')

        if 'project_id' not in data:
            raise Exception('请求中项目project_id信息不存在')

        if 'assetData' not in data:
            raise Exception('请求中项目assetData信息不存在')

        project_id = data.get('project_id')
        equip_id = data.get('equip_id')
        assetData = data.get('assetData')
        assetList = []

        for item in assetData:
            if isinstance(item, dict):
                for key in item:
                    post = [equip_id, key, item[key], project_id]
                    assetList.append(post)

        BEOPDataAccess.getInstance().updateAsset(equip_id,project_id,assetList)

        list = []
        if 'files' in data:
            files= data.get('files')
            for file in files:
                fileName=file.get('fileName')
                filePath=file.get('filePath')
                postFile=[fileName, filePath ,equip_id]
                list.append(postFile)

            BEOPDataAccess.getInstance().updateAssetFile(equip_id,list)

    except Exception as e:
        print('interface getAddInitAsset error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:用于初始化字段与字段值
auth:huangzhijun
param:
return:
'''
@bp_equipment.route('/getInitAsset', methods=['POST'])
def get_InitAsset():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'project_id' not in data:
            raise Exception('请求中项目Id信息不存在')

        if 'template_id' not in data:
            raise Exception('请求中项目template_id信息不存在')

        if 'equip_id' not in data:
            raise Exception('请求中项目equip_id信息不存在')

        project_id = data.get('project_id')
        equip_id = data.get('equip_id')
        template_id = data.get('template_id')

        data = BEOPDataAccess.getInstance().getUpdateInitAsset(template_id,equip_id,project_id)

        result['data'] = data
    except Exception as e:
        print('interface getAssetTemplates error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)



'''
title:修改资产信息
auth:huangzhijun
param:{"project_id":280,"equip_id":34,"assetData":[{"input_power":"2200"},
{"rated_current":"4"},
{"voltage":"220"},
{"speed":"3000"},
{"rated_power":"550"},
{"power_factor":"1"},
{"frequency":"10"},
{"attachment":"5米电源线"},
{"lift":"10"},
{"commissioning_date":"2018-08-09"},
{"brand":"美泰"},
{"model":"JSB3564875"},
{"equip_no":"JS0021223"}]}
'''
@bp_equipment.route('/updateAsset', methods=['POST'])
def update_Asset():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'project_id' not in data:
            project_id = 0
        else:
            project_id = data.get('project_id')

        if 'equip_id' not in data:
            raise Exception('请求中项目equip_id信息不存在')
        equip_id = data.get('equip_id')

        if 'assetData' not in data:
            raise Exception('请求中项目assetData信息不存在')
        assetData = data.get('assetData')

        assetList = []
        equip_no_val = None
        for item in assetData:
            if isinstance(item, dict):
                for key in item:

                    vlu = item[key]
                    if vlu == None:
                        vlu = ""

                    post = [equip_id, key, vlu, project_id]
                    if key=='equip_no':
                        equip_no_val = item[key]
                        print("1:" +equip_no_val)
                    assetList.append(post)

        if not len(assetList):
            raise Exception('未发现需修改的资产配置项')

        BEOPDataAccess.getInstance().updateAsset(equip_id, project_id, assetList)
        if equip_no_val is not None and equip_no_val!='':
            print("2:" + equip_no_val)
            BEOPDataAccess.getInstance().updateEquipQrcode(equip_id, equip_no_val)

        list = []
        if 'files' in data:
            files = data.get('files')
            if len(files) > 0:
                for file  in files:
                    fileName = file.get('fileName')
                    filePath = file.get('filePath')
                    postFile = [fileName, filePath, equip_id]
                    list.append(postFile)

                BEOPDataAccess.getInstance().updateAssetFile(equip_id, list)

    except Exception as e:
        print('interface updateAssetValue error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:查询对比参数
auth:huangzhijun
param:{"equip_id":34,"pageSize":4,"targetPage":1}
return:{"status": true, "flag": true, "msg": "ok", "total": 2, "data": [{"id": 2, "maxValue": 31, 
"minValue": 11, "paramName": "冷却水温度", "paramCode": "CHW-LOAD-INSTANT2", "paramUnit": "℃"}]}
'''
@bp_equipment.route('/getEquipParamList', methods=["POST"])
def get_EquipParamList():
    result = {'status': True, 'msg': 'ok', 'data': None, 'total': -1}
    try:
        data = request.get_json()

        if 'equip_id' not in data:
            raise Exception('请求中equip_id字段不存在')

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')

        equip_id = data.get('equip_id')
        targetPage = int(data.get('targetPage'))
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getEquipParamList(equip_id,pageSize, targetPage)

    except Exception as e:
        print('interface getEquipParamList error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
    return json.dumps(result, ensure_ascii=False)

@bp_equipment.route('/getAddInitParam', methods=['POST'])
def get_AddInitParam():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()

        if 'template_id' not in data:
            raise Exception('请求中项目template_id信息不存在')

        template_id = data.get('template_id')
        data = BEOPDataAccess.getInstance().getAddInitParam(template_id)
        result['data'] = data
    except Exception as e:
        print('interface getAddInitParam error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:用于初始化参数字段与字段值
auth:huangzhijun
param:{"project_id":280,"template_id":2,"equip_id":34}
return:{"msg": "ok", "data": [ {"paramName": "蒸发器进水温度", "paramCode": "ChAMPS06", "id": null, 
"maxValue": null, "minValue": null, "sort_num": 8, "paramUnit": null}], "status": true}
'''
@bp_equipment.route('/getInitParam', methods=['POST'])
def get_InitParam():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()

        if 'equip_id' not in data:
            raise Exception('请求中项目equip_id信息不存在')

        equip_id = data.get('equip_id')
        data = BEOPDataAccess.getInstance().getInitParam(equip_id)
        result['data'] = data
    except Exception as e:
        print('interface getInitParam error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:修改对比参数
auth:huangzhijun
param:{"id":3,"paramName":"冷冻水温度","paramCode":"CHW-LOAD-INSTANT3","minValue":"10","maxValue":"31","paramUnit":"℃"}
return:{'status': True, 'msg': 'ok', 'data': None}
'''
@bp_equipment.route('/updateEquipParam', methods=['POST'])
def update_EquipParam():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'equip_id' not in data:
            raise Exception('请求中项目equip_id信息不存在')
        if 'paramData' not in data:
            raise Exception('请求中项目paramData信息不存在')

        equip_id = data.get('equip_id')
        paramData = data.get('paramData')
        paramList = []

        for item in paramData:
                post = [equip_id, item['paramCode'],item['paramName'],item['minValue'], item['maxValue'], item['paramUnit'], json.dumps(item['paramCommand'])]
                paramList.append(post)

        BEOPDataAccess.getInstance().updateEquipParam(equip_id,paramList)

    except Exception as e:
        print('interface updateEquipParam error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:查询投产记录
auth:huangzhijun
param:{"projectId":280,"searchKey":"","pageSize":4,"targetPage":1}
return:{"status": true, "total": 2, "msg": "ok", "data": [{"responsible_name": "张三", "describe": "更换主机", "id": 1, "operate_time": "2018-08-15 16:03:09"}, 
{"responsible_name": "李车", "describe": "更换水泵", "id": 2, "operate_time": "2018-08-06 16:03:25"}], "flag": true}
'''
@bp_equipment.route('/searchOperation', methods=["POST"])
def search_Operation():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getEquipOperationList(searchKey,projectId,pageSize, targetPage)

    except Exception as e:
        print('interface search_Operation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:删除投产记录
auth:huangzhijun
param:{"ids":[4,3]}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/delEquipOperation', methods=['POST'])
def del_EquipOperation():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'ids' not in data:
            raise Exception('请求中项目ids信息不存在')

        ids = data.get('ids')
        BEOPDataAccess.getInstance().delEquipOperationList(ids)

    except Exception as e:
        print('interface delEquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:新增投产记录
auth:huangzhijun
param:{"projectId":280,"describe":"换风机","operate_time":"2018-08-07","responsible_name":"李四"}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/addEquipOperation', methods=['POST'])
def add_EquipOperation():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'describe' not in data:
            raise Exception('请求中项目describe信息不存在')
        if 'operate_time' not in data:
            raise Exception('请求中项目operate_time信息不存在')
        if 'responsible_name' not in data:
            raise Exception('请求中项目responsible_name信息不存在')
        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')

        projectId = int(data.get('projectId'))
        describe = data.get('describe')
        operate_time = data.get('operate_time')
        responsible_name = data.get('responsible_name')

        post = [describe, operate_time, responsible_name,projectId]
        BEOPDataAccess.getInstance().addEquipOperationList(post)

    except Exception as e:
        print('interface add_EquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:修改投产记录
auth:huangzhijun
param:{"id":2,"projectId":280,"describe":"换风机22","operate_time":"2018-08-07","responsible_name":"李四"}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/updateEquipOperation', methods=['POST'])
def update_EquipOperation():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'id' not in data:
            raise Exception('请求中项目id信息不存在')
        if 'describe' not in data:
            raise Exception('请求中项目describe信息不存在')
        if 'operate_time' not in data:
            raise Exception('请求中项目operate_time信息不存在')
        if 'responsible_name' not in data:
            raise Exception('请求中项目responsible_name信息不存在')

        id = data.get('id')
        describe = data.get('describe')
        operate_time = data.get('operate_time')
        responsible_name = data.get('responsible_name')

        BEOPDataAccess.getInstance().updateEquipOperationList(id,describe, operate_time, responsible_name)

    except Exception as e:
        print('interface add_EquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:新增资产模板定义
auth:huangzhijun
param:{"projectId":280,"name":"冷风机","describe":"好冷风"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/addAssetTmplDef', methods=['POST'])
def add_AssetTmplDef():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'describe' not in data:
            raise Exception('请求中项目describe信息不存在')
        if 'name' not in data:
            raise Exception('请求中项目name信息不存在')
        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')

        projectId = int(data.get('projectId'))
        describe = data.get('describe')
        name = data.get('name')


        post = [name, projectId, describe]
        BEOPDataAccess.getInstance().addAssetTmplDef(post)

    except Exception as e:
        print('interface addAssetTmplDef error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:删除模板定义
auth:huangzhijun
param:{"ids":[4,3]}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/delAssetTmplDef', methods=['POST'])
def del_AssetTmplDef():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'ids' not in data:
            raise Exception('请求中项目ids信息不存在')

        ids = data.get('ids')
        BEOPDataAccess.getInstance().delAssetTmplDef(ids)

    except Exception as e:
        print('interface delAssetTmplDef error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:修改资产模板定义
auth:huangzhijun
param:{"id":4,"projectId":280,"name":"冷风机1","describe":"好冷风2"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/updateAssetTmplDef', methods=['POST'])
def update_AssetTmplDef():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'id' not in data:
            raise Exception('请求中项目id信息不存在')
        if 'describe' not in data:
            raise Exception('请求中项目describe信息不存在')
        if 'name' not in data:
            raise Exception('请求中项目name信息不存在')

        id = data.get('id')
        describe = data.get('describe')
        name = data.get('name')

        BEOPDataAccess.getInstance().updateAssetTmplDef(id,name,describe)

    except Exception as e:
        print('interface add_EquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)



'''
title:查询资产模板定义
auth:huangzhijun
param:{"projectId":280,"searchKey":"","pageSize":4,"targetPage":1}
return:{"msg": "ok", "status": true, "flag": true, "data": [ {"id": 2, "name": "主机模板", "describe": null}], "total": 2}
'''
@bp_equipment.route('/searchAssetTmplDef', methods=["POST"])
def search_AssetTmplDef():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getAssetTmplDefList(searchKey,projectId,pageSize,targetPage)

    except Exception as e:
        print('interface search_Operation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:新增资产模板
auth:huangzhijun
param:{"projectId":280,"tmpl_def_id":"1","cn_name":"输入功率1","en_name":"input_power","ui_type":"1","group_num":"0","sort_num":"15"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/addAssetTmpl', methods=['POST'])
def add_AssetTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'tmpl_def_id' not in data:
            raise Exception('请求中项目tmpl_def_id信息不存在')
        if 'cn_name' not in data:
            raise Exception('请求中项目cn_name信息不存在')
        if 'en_name' not in data:
            raise Exception('请求中项目en_name信息不存在')
        if 'ui_type' not in data:
            raise Exception('请求中项目ui_type信息不存在')
        if 'group_num' not in data:
            raise Exception('请求中项目group_num信息不存在')
        if 'sort_num' not in data:
            raise Exception('请求中项目sort_num信息不存在')
        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')

        tmpl_def_id = data.get('tmpl_def_id')
        cn_name = data.get('cn_name')
        en_name = data.get('en_name')
        ui_type = data.get('ui_type')
        group_num = data.get('group_num')
        sort_num = data.get('sort_num')
        projectId = int(data.get('projectId'))

        post = [tmpl_def_id, cn_name, en_name,ui_type,group_num,sort_num,projectId]
        BEOPDataAccess.getInstance().addAssetTmpl(post)

    except Exception as e:
        print('interface addAssetTmpl error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:删除资产模板
auth:huangzhijun
param:{"ids":[31,311]}
return:{"status": true, "msg": "ok", "data": null}

'''
@bp_equipment.route('/delAssetTmpl', methods=['POST'])
def del_AssetTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'ids' not in data:
            raise Exception('请求中项目ids信息不存在')

        ids = data.get('ids')
        BEOPDataAccess.getInstance().delAssetTmpl(ids)

    except Exception as e:
        print('interface delAssetTmpl error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:修改资产模板
auth:huangzhijun
param:{"id":31,"projectId":280,"tmpl_def_id":"1","cn_name":"输入功率2","en_name":"input_power","ui_type":"1","group_num":"0","sort_num":"15"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/updateAssetTmpl', methods=['POST'])
def update_AssetTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'id' not in data:
            raise Exception('请求中项目id信息不存在')

        if 'cn_name' not in data:
            raise Exception('请求中项目cn_name信息不存在')
        if 'en_name' not in data:
            raise Exception('请求中项目en_name信息不存在')
        if 'ui_type' not in data:
            raise Exception('请求中项目ui_type信息不存在')
        if 'group_num' not in data:
            raise Exception('请求中项目group_num信息不存在')
        if 'sort_num' not in data:
            raise Exception('请求中项目sort_num信息不存在')

        id = data.get('id')
        cn_name = data.get('cn_name')
        en_name = data.get('en_name')
        ui_type = data.get('ui_type')
        group_num = data.get('group_num')
        sort_num = data.get('sort_num')

        BEOPDataAccess.getInstance().updateAssetTmpl(id,cn_name, en_name,ui_type,group_num,sort_num)

    except Exception as e:
        print('interface add_EquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:查询资产模板
auth:huangzhijun
param:{"projectId":280,"searchKey":"","tmpl_def_id":1,"pageSize":1,"targetPage":1}
return:{"total": 13, "data": [{"cn_name": "额定电流", "en_name": "rated_current", "group_num": 0,
 "tmpl_def_id": 1, "sort_num": 4, "ui_type": 1, "id": 2}], "msg": "ok", "flag": true, "status": true}

'''
@bp_equipment.route('/searchAssetTmplList', methods=["POST"])
def search_AssetTmplList():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'tmpl_def_id' not in data:
            raise Exception('请求中tmpl_def_id字段不存在')
        tmpl_def_id = data.get('tmpl_def_id')

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getAssetTmplList(searchKey,tmpl_def_id,projectId,pageSize, targetPage)

    except Exception as e:
        print('interface searchAssetTmplList error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:新增参数模板
auth:huangzhijun
param:{"tmpl_def_id":2,"paramName":"冷冻水温度22","paramCode":"ChAMPS0322","sort_num":"4"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/addParamTmpl', methods=['POST'])
def add_ParamTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'tmpl_def_id' not in data:
            raise Exception('请求中项目tmpl_def_id信息不存在')
        if 'paramName' not in data:
            raise Exception('请求中项目paramName信息不存在')
        if 'paramCode' not in data:
            raise Exception('请求中项目paramCode信息不存在')
        if 'minValue' not in data:
            raise Exception('请求中项目minValue信息不存在')
        if 'maxValue' not in data:
            raise Exception('请求中项目maxValue信息不存在')
        if 'paramUnit' not in data:
            raise Exception('请求中项目paramUnit信息不存在')
        if 'sort_num' not in data:
            raise Exception('请求中sort_num字段不存在')
        # if 'paramCommand' not in data:
        #     raise Exception('请求中paramCommand字段不存在')

        tmpl_def_id = data.get('tmpl_def_id')
        paramName = data.get('paramName')
        paramCode = data.get('paramCode')
        minValue = data.get('minValue')
        maxValue = data.get('maxValue')
        paramUnit = data.get('paramUnit')
        sort_num = data.get('sort_num')
        # paramCommand = data.get('paramCommand')

        post = [tmpl_def_id, paramName, paramCode,minValue,maxValue,paramUnit,sort_num]   # paramCommand
        BEOPDataAccess.getInstance().addParamTmpl(post)

    except Exception as e:
        print('interface addParamTmpl error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:删除参数模板
auth:huangzhijun
param:{"ids":[4,3]}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/delParamTmpl', methods=['POST'])
def del_ParamTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'ids' not in data:
            raise Exception('请求中项目ids信息不存在')

        ids = data.get('ids')
        BEOPDataAccess.getInstance().delParamTmpl(ids)

    except Exception as e:
        print('interface delParamTmpl error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:修改参数模板
auth:huangzhijun
param:{"id":4,"tmpl_def_id":2,"paramName":"冷冻水温度222","paramCode":"ChAMPS0322","sort_num":"4"}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/updateParamTmpl', methods=['POST'])
def update_ParamTmpl():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'id' not in data:
            raise Exception('请求中项目id信息不存在')

        if 'paramName' not in data:
            raise Exception('请求中项目paramName信息不存在')
        if 'paramCode' not in data:
            raise Exception('请求中项目paramCode信息不存在')
        if 'sort_num' not in data:
            raise Exception('请求中sort_num字段不存在')

        paramName = data.get('paramName')
        paramCode = data.get('paramCode')
        minValue = data.get('minValue')
        maxValue = data.get('maxValue')
        paramUnit = data.get('paramUnit')
        sort_num = data.get('sort_num')
        id = data.get('id')

        BEOPDataAccess.getInstance().updateParamTmpl(id, paramName, paramCode,maxValue,minValue,paramUnit,sort_num)

    except Exception as e:
        print('interface add_EquipOperation error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:查询参数模板
auth:huangzhijun
param:{"projectId":280,"searchKey":"","tmpl_def_id":1,"pageSize":1,"targetPage":1}
return:{"total": 2, "msg": "ok", "flag": true, "data": [{"sort_num": 1, "tmpl_def_id": 2, 
"paramCode": "ChAMPS01", "paramName": "冷冻水温度", "id": 1}], "status": true}
'''
@bp_equipment.route('/searchParamTmpl', methods=["POST"])
def search_ParamTmpl():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'tmpl_def_id' not in data:
            raise Exception('请求中tmpl_def_id字段不存在')
        tmpl_def_id = data.get('tmpl_def_id')

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getParamTmplList(searchKey,tmpl_def_id,projectId,pageSize, targetPage)

    except Exception as e:
        print('interface getParamTmplList error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:新增系统设备
auth:huangzhijun
param:{"projId":280,"system_name":"主机系统11","system_desc":"主机系统描述","system_img":""}
return:{"data": null, "msg": "ok", "status": true}
'''
@bp_equipment.route('/addSystem', methods=['POST'])
def add_System():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'projId' not in data:
            raise Exception('请求中项目projId信息不存在')
        if 'system_name' not in data:
            raise Exception('请求中项目system_name信息不存在')
        if 'system_desc' not in data:
            raise Exception('请求中项目system_desc信息不存在')
        if 'system_img' not in data:
            raise Exception('请求中system_img字段不存在')

        projId = data.get('projId')
        system_name = data.get('system_name')
        system_desc = data.get('system_desc')
        system_img = data.get('system_img')


        post = [system_name, system_desc, system_img,projId]
        BEOPDataAccess.getInstance().addSystem(post)

    except Exception as e:
        print('interface addSystem error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

'''
title:删除系统设备
auth:huangzhijun
param:{"ids":[4,3]}
return:{"status": true, "msg": "ok", "data": null}
'''
@bp_equipment.route('/delSystem', methods=['POST'])
def del_System():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'ids' not in data:
            raise Exception('请求中项目ids信息不存在')

        ids = data.get('ids')
        BEOPDataAccess.getInstance().delSystem(ids)

    except Exception as e:
        print('interface delSystem error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:修改系统信息
auth:huangzhijun
param:{"id":5,"projId":280,"system_name":"主机系统121","system_desc":"主机系统描述2","system_img":""}
return:{"status": true, "data": null, "msg": "ok"}
'''
@bp_equipment.route('/updateSystem', methods=['POST'])
def update_System():
    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        data = request.get_json()
        if 'id' not in data:
            raise Exception('请求中id信息不存在')

        if 'projId' not in data:
            raise Exception('请求中projId信息不存在')
        if 'system_name' not in data:
            raise Exception('请求中system_name信息不存在')
        if 'system_desc' not in data:
            raise Exception('请求中system_desc信息不存在')
        if 'system_img' not in data:
            raise Exception('请求中system_img字段不存在')

        projId = data.get('projId')
        system_name = data.get('system_name')
        system_desc = data.get('system_desc')
        system_img = data.get('system_img')
        id = data.get('id')

        BEOPDataAccess.getInstance().updateSystem(id,system_name, system_desc ,system_img)

    except Exception as e:
        print('interface updateSystem error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


'''
title:查询系统设备信息
auth:huangzhijun
param:{"projectId":280,"searchKey":"","pageSize":1,"targetPage":1}
return:{"flag": true, "msg": "ok", "data": [{"id": 1, "system_name": "主机1", "sort_num": null, "createTime": "2018-09-03 09:35:31",
 "system_desc": "描述1"}], "total": 5, "status": true}
'''
@bp_equipment.route('/searchSystem', methods=["POST"])
def search_System():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getSystemList(searchKey,projectId,pageSize, targetPage)

    except Exception as e:
        print('interface searchSystem error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)

@bp_equipment.route('/download/<filename>', methods=['GET'])
def file_download(filename):
    filePath = os.path.join(app.static_folder, "file", "equipAsset", filename)
    if not os.path.exists(filePath):
        return Response(None, content_type='application/octet-stream')

    with open(filePath, 'rb') as target_file:
        data = target_file.read()
    response = Response(data, content_type='application/octet-stream')

    return responsesearchOperation

'''
二维码数据生成
:param text:设备编码
:return: 图片的字节流
'''
@bp_equipment.route('/code/<text>', methods=["GET"])
def make_qr(text):
    qr = qrcode.QRCode(
        version=4,  # 生成二维码尺寸的大小 1-40 1:21*21（21+(n-1)*4）
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # L:7% M:15% Q:25% H:30%
        box_size=10,  # 每个格子的像素大小
        border=2,  # 边框的格子宽度大小
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image()
    buf = BytesIO()
    img.save(buf)
    buf_str = buf.getvalue()
    response = app.make_response(buf_str)
    response.headers['Content-Type'] = 'image/gif'
    return response


@bp_equipment.route('/importFile', methods=["POST"])
def importFile():
    file = request.files.get('commfile')
    project_id = request.form['project_id']

    if not file:
        return json.dumps(dict(msg="no file found", status=False), ensure_ascii=False)

    reFileName = ObjectId().__str__()
    static_path = app.static_folder

    try:
        fileName = file.filename

        if not fileName.endswith(".xlsx") and not fileName.endswith(".xls"):
            return json.dumps(dict(msg="only .xlsx or .xlx file supported", status=False), ensure_ascii=False)

        strFilePath = os.path.join(static_path, 'file')
        if not os.path.exists(strFilePath):
            os.mkdir(strFilePath)

        strFileExcelPath = os.path.join(strFilePath, 'equipExcel')
        if not os.path.exists(strFileExcelPath):
            os.mkdir(strFileExcelPath)

        strAbsFile = os.path.join(strFileExcelPath, "{name}{ext}".format(name=reFileName, ext=os.path.splitext(fileName)[1]))
        filePath = strAbsFile
        file.stream.read()
        file.stream.seek(0)
        file.save(filePath)

        if not os.path.exists(filePath):
            return json.dumps(dict(msg="file doesn't exist", status=False), ensure_ascii=False)

        BEOPDataAccess.getInstance().importEquipmentExcel(filePath, project_id)
        os.remove(filePath)

        return json.dumps(dict(msg="导入成功", status=True), ensure_ascii=False)

    except Exception as e:
        result = {}
        result['msg'] = e.__str__()
        result['status'] = False

        return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/importEquipFile', methods=["POST"])
def importEquipFile():
    result = {'status': True, 'msg': 'ok', 'data': None, 'total': -1}
    file = request.files.get('commfile')
    project_id = request.form['project_id']

    if not file:
        raise Exception('there is no upload file')

    reFileName = ObjectId().__str__()
    static_path = app.static_folder
    relativePath = ''
    rv = {}
    try:
        fileName = file.filename
        index = fileName.rindex(".")
        outFilePath = ""
        if index > 0:
            ext = fileName[index:len(fileName)]
            strFilePath = os.path.join(static_path, 'file')
            strFileExcelPath = os.path.join(strFilePath, 'equipExcel')
            strAbsFile = os.path.join(strFileExcelPath, reFileName + ext)
            filePath = strAbsFile
            file.stream.read()
            file.stream.seek(0)
            file.save(filePath)
            if os.path.exists(filePath):
                if file.filename.endswith('xlsx') or file.filename.endswith('xls'):
                    BEOPDataAccess.getInstance().importEquipExcel(filePath,project_id)
                os.remove(filePath)

    except Exception as e:
        print('interface importFile error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/searchRiskFactor', methods=["POST"])
def search_RiskFactor():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'searchKey' not in data:
            raise Exception('请求中searchKey字段不存在')
        searchKey = data.get('searchKey').strip()

        if 'projectId' not in data:
            raise Exception('请求中projectId字段不存在')
        projectId = int(data.get('projectId'))

        if 'targetPage' not in data:
            raise Exception('请求中targetPage字段不存在')
        targetPage = int(data.get('targetPage'))

        if 'pageSize' not in data:
            raise Exception('请求中pageSize字段不存在')
        pageSize = int(data.get('pageSize'))

        result = BEOPDataAccess.getInstance().getRiskFactorList(searchKey, projectId, pageSize, targetPage)

    except Exception as e:
        print('interface searchRiskFactor error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/addRiskFactor', methods=["POST"])
def add_RiskFactor():
    result = {'status': True, 'msg': 'ok', 'data': None}
    data = request.get_json()
    factorName = data.get('factorName')
    factorCode = data.get('factorCode')
    type = data.get('type')
    num = data.get('num')
    remark = data.get('remark')
    deviceId = data.get('deviceId')
    deviceName = data.get('deviceName')
    add_detail_Data = data.get('add_detail_Data')
    project_id = data.get('projectId')
    try:
        post = [factorName, factorCode, type, num,remark, 1,project_id,deviceId,deviceName]
        result['status'] = BEOPDataAccess.getInstance().addRiskFactor(post,add_detail_Data)

    except Exception as e:
        print('interface addRiskFactor error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/updateRiskFactor', methods=["POST"])
def update_RiskFactor():
    result = {'status': True, 'msg': 'ok', 'data': None}
    data = request.get_json()
    id = data.get('id')
    factorName = data.get('factorName')
    factorCode = data.get('factorCode')
    type = data.get('type')
    num = data.get('num')
    remark = data.get('remark')
    status = data.get('status')
    add_detail_Data = data.get('add_detail_Data')
    del_detail_Data = data.get('del_detail_Data')

    try:
        result['status'] = BEOPDataAccess.getInstance().updateRiskFactor(id, factorName, factorCode, type, num,remark,add_detail_Data,del_detail_Data)

    except Exception as e:
        print('interface updateRiskFactor error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/getRiskFactorByFactorId', methods=["POST"])
def get_RiskFactorByFactorId():
    result = {'status': True, 'msg': 'ok', 'data': None}
    data = request.get_json()
    id = data.get('id')
    try:
        result['data'] = BEOPDataAccess.getInstance().getRiskFactorByFactorId(id)
    except Exception as e:
        print('interface getRiskFactorByFactorId error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/enableRiskFactor', methods=["POST"])
def enable_RiskFactor():
    result = {'status': True, 'msg': 'ok', 'data': None}
    data = request.get_json()
    id = data.get('id')
    status = data.get('status')
    try:
        result['status'] = BEOPDataAccess.getInstance().enableRiskFactor(status,id)
    except Exception as e:
        print('interface enableRiskFactor error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False


@bp_equipment.route('/delRiskFactor', methods=["POST"])
def del_RiskFactor():
    result = {'status': True, 'msg': 'ok', 'data': None}
    data = request.get_json()
    ids = data.get('ids')
    try:
        result['status'] = BEOPDataAccess.getInstance().delRiskFactor(ids)

    except Exception as e:
        print('interface delRiskFactor error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route('/<projectId>/<equipmentId>')
def read_project_equipment_from_mobile(projectId, equipmentId):
    try:
        if projectId is None:
            return render_template('m_equipment.html', data={})

        if equipmentId is None:
            return render_template('m_equipment.html', data={})

        rt = BEOPDataAccess.getInstance().readProjectEquipmentFromMobile(projectId, equipmentId)

        if rt.get("code") > 0:
            return render_template('m_equipment.html', data={})

        return render_template('m_equipment.html', data=json.dumps(rt.get("data")))

    except Exception as e:
        logging.error("ERROR in /equipment/readProjectEquipmentFromMobile: %s" % e.__str__())
        return render_template('m_equipment.html', data={})

@bp_equipment.route("/getEquipRatingParam", methods=["POST"])
def get_equip_rating_param():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    pointName = rcv.get("ratingParamPointName", None)
    if not isinstance(pointName, str):
        return jsonify(dict(err=1, msg="ratingParam点名不能为空", data=[]))
    if not len(pointName):
        return jsonify(dict(err=1, msg="ratingParam点名不能为空", data=[]))

    if len(pointName) <= 2:
        return jsonify(dict(err=1, msg="ratingParam点名有误", data=[]))

    strObj = pointName[:-2]
    strObj = strObj.replace("RatingParam", "")

    if not len(strObj):
        return jsonify(dict(err=1, msg="ratingParam点名有误", data=[]))

    identity = strObj + pointName[-2:]
    equipType, strTypeIncluded = get_equipment_template_type(identity)
    if not equipType:
        return jsonify(dict(err=1, msg='未知的设备模板类型，目前仅支持以下类型：%s' % strTypeIncluded, data=[]))

    templateId = BEOPDataAccess.getInstance().getEquipmentTemplateId(equipType)
    if templateId is None:
        return jsonify(dict(err=1, msg='"%s"对应的模板ID获取失败，请检查是否存在"%s"对应的模板类型' % (equipType, equipType), data=[]))

    equipmentId = BEOPDataAccess.getInstance().getEquipmentId(identity)
    if equipmentId is None:
        return jsonify(dict(err=1, msg='"%s"对应的设备ID获取失败，资产管理中或许不存在"%s"对应的设备' % (identity, identity), data=[]))

    projectId = 0
    data = BEOPDataAccess.getInstance().getUpdateInitAsset(templateId, equipmentId, projectId)

    return jsonify(dict(err=0, msg="", data=data))


@bp_equipment.route("/getInitAssetByIdentity", methods=["POST"])
def equipment_get_init_asset_by_identity():
    rcv = request.get_json()
    identity = rcv.get("identity")
    if not len(identity):
        return json.dumps({'status': False, 'msg': '标识符不能为空', 'data': None}, ensure_ascii=False)

    equipType, strTypeIncluded = get_equipment_template_type(identity)
    if not equipType:
        return json.dumps({'status': False, 'msg': '未知的设备模板类型，目前仅支持以下类型：%s' % strTypeIncluded, 'data': None}, ensure_ascii=False)

    result = {'status': True, 'msg': 'ok', 'data': None}
    try:
        templateId = BEOPDataAccess.getInstance().getEquipmentTemplateId(equipType)
        if templateId is None:
            return json.dumps({'status': False, 'msg': '"%s"对应的模板ID获取失败，请检查是否存在"%s"对应的模板类型' % (equipType, equipType), 'data': None}, ensure_ascii=False)

        equipmentId = BEOPDataAccess.getInstance().getEquipmentId(identity)
        if equipmentId is None:
            return json.dumps({'status': False, 'msg': '"%s"对应的设备ID获取失败，资产管理中或许不存在"%s"对应的设备' % (identity, identity), 'data': None}, ensure_ascii=False)

        projectId = 0
        data = BEOPDataAccess.getInstance().getUpdateInitAsset(templateId, equipmentId, projectId)

        result['data'] = data
    except Exception as e:
        print('interface getAssetTemplates error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


@bp_equipment.route("/importAssetTmpl", methods=["POST"])
def import_asset_tmpl():
    saveFilePath = None
    try:
        excelTable = request.files.get("file")
        tmplId = request.form.get("tmplId", None)
        if tmplId is None:
            return jsonify(dict(err=1, msg="模板ID不能为空", data=False))
        if not excelTable:
            return jsonify(dict(err=1, msg="表格不能为空", data=False))
        if not BEOPDataAccess.getInstance().tmplDefIdExists(tmplId):
            return jsonify(dict(err=1, msg="模板ID不存在", data=False))

        fileName = excelTable.filename
        if not fileName.endswith(".xlsx"):
            return jsonify(dict(err=1, msg="表格只支持.xlsx文件", data=False))

        saveFilePath = fetchImportAssetTmplTable(excelTable, fileName)
        if not saveFilePath:
            return jsonify(dict(err=1, msg="获取导入的表格失败", data=False))

        book = xlrd.open_workbook(saveFilePath)
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        if nrows <= 1:
            return jsonify(dict(err=1, msg="表格中无内容", data=False))

        # projectId默认为0
        projectId = 0

        enNameList = []
        chNameList = []
        dataList = []
        for idx in range(nrows):
            if idx < 1:
                continue

            values = sheet.row_values(idx)
            chName = values[0]
            enName = values[1]
            strType = values[2]
            strGroup = values[3]
            if not len(chName) or not len(enName):
                return jsonify(dict(err=1, msg="表格内容有误，某个中文名称或英文名称为空", data=False))
            if strType not in ["单选框", "多选框"]:
                return jsonify(dict(err=1, msg="表格内容有误，某个控件类型有误（必须为单选框或多选框）", data=False))
            nType = 1 if strType == "单选框" else 2
            if chName in chNameList:
                return jsonify(dict(err=1, msg="表格内容有误，中文名称重复", data=False))
            if enName in enNameList:
                return jsonify(dict(err=1, msg="表格内容有误，英文名称重复", data=False))

            if not is_digit(strGroup):
                return jsonify(dict(err=1, msg="表格内容有误，组编码必须为数字", data=False))

            nGroup = int(float(strGroup))

            dataList.append((tmplId, chName, enName, nType, nGroup, idx, projectId))

            enNameList.append(enName)
            chNameList.append(chName)

        bSuc = BEOPDataAccess.getInstance().addAssetTmplMulti(tmplId, dataList)

        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)

        if bSuc:
            return jsonify(dict(err=0, msg="导入成功", data=True))
        return jsonify(dict(err=1, msg="导入失败", data=False))

    except Exception as e:
        strLog = "ERROR in /equipment/importAssetTmpl: %s" % e.__str__()
        logging.error(strLog)
        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)
        return jsonify(dict(err=1, msg="导入失败: %s" % strLog, data=False))


@bp_equipment.route("/importParamTmpl", methods=["POST"])
def import_param_tmpl():
    saveFilePath = None
    try:
        excelTable = request.files.get("file")
        tmplId = request.form.get("tmplId", None)
        if tmplId is None:
            return jsonify(dict(err=1, msg="模板ID不能为空", data=False))
        if not excelTable:
            return jsonify(dict(err=1, msg="表格不能为空", data=False))
        if not BEOPDataAccess.getInstance().tmplDefIdExists(tmplId):
            return jsonify(dict(err=1, msg="模板ID不存在", data=False))

        fileName = excelTable.filename
        if not fileName.endswith(".xlsx"):
            return jsonify(dict(err=1, msg="表格只支持.xlsx文件", data=False))

        saveFilePath = fetchImportAssetTmplTable(excelTable, fileName)
        if not saveFilePath:
            return jsonify(dict(err=1, msg="获取导入的表格失败", data=False))

        book = xlrd.open_workbook(saveFilePath)
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        if nrows <= 1:
            return jsonify(dict(err=1, msg="表格中无内容", data=False))

        enNameList = []
        chNameList = []
        dataList = []

        for idx in range(nrows):
            if idx < 1:
                continue

            values = sheet.row_values(idx)
            chName = values[0]
            enName = values[1]
            maxValue = values[2]
            minValue = values[3]
            strUnit = values[4]

            if not len(chName) or not len(enName):
                return jsonify(dict(err=1, msg="表格内容有误，某个中文名称或英文名称为空", data=False))

            if chName in chNameList:
                return jsonify(dict(err=1, msg="表格内容有误，中文名称重复", data=False))
            if enName in enNameList:
                return jsonify(dict(err=1, msg="表格内容有误，英文名称重复", data=False))

            if not is_digit(maxValue):
                return jsonify(dict(err=1, msg="表格内容有误，最大值必须为数字", data=False))
            if not is_digit(minValue):
                return jsonify(dict(err=1, msg="表格内容有误，最小值必须为数字", data=False))

            if not len(strUnit):
                return jsonify(dict(err=1, msg="表格内容有误，单位不能为空", data=False))

            dataList.append((tmplId, chName, enName, float(minValue), float(maxValue), strUnit, idx))

            enNameList.append(enName)
            chNameList.append(chName)

        bSuc = BEOPDataAccess.getInstance().addParamTmplMulti(tmplId, dataList)

        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)

        if bSuc:
            return jsonify(dict(err=0, msg="导入成功", data=True))
        return jsonify(dict(err=1, msg="导入失败", data=False))

    except Exception as e:
        strLog = "ERROR in /equipment/importParamTmpl: %s" % e.__str__()
        logging.error(strLog)
        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)
        return jsonify(dict(err=1, msg="导入失败: %s" % strLog, data=False))


@bp_equipment.route("/exportTemplateAsset")
def export_template_asset():
    fileName = "模板_资产信息导入.xlsx"
    filePath = os.path.join(app.static_folder, "files", "asset_template", fileName)
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="模板文件不存在", data=""))
    return jsonify(dict(err=0, msg="", data=fileName))


@bp_equipment.route("/exportTemplateParam")
def export_template_param():
    fileName = "模板_参数信息导入.xlsx"
    filePath = os.path.join(app.static_folder, "files", "asset_template", fileName)
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="模板文件不存在", data=""))
    return jsonify(dict(err=0, msg="", data=fileName))


@bp_equipment.route("/getAssetTemplateFileList")
def get_asset_template_file_list():
    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        return jsonify(dict(err=1, msg="路径不存在", data=[]))

    assetTemplateDir = os.path.join(filesDir, "asset_template")
    if not os.path.exists(assetTemplateDir):
        return jsonify(dict(err=1, msg="路径不存在", data=[]))

    fileNameList = []
    for rootDir, dirs, files in os.walk(assetTemplateDir):
        for file in files:
            if not file.endswith(".xlsx"):
                continue

            if file.find("模板_设备信息导入") == -1:
                continue

            fileNameList.append(file)

    return jsonify(dict(err=0, msg="", data=fileNameList))


@bp_equipment.route("/searchWithRFID", methods=["POST"])
def search_with_rfid():
    rcv = request.get_json()

    projectId = 0
    searchKey = ""
    system_id = ""
    targetPage = 1
    pageSize = 10000

    records, total, flag = BEOPDataAccess.getInstance().searchEquipment(projectId, searchKey, system_id, pageSize,
                                                                     targetPage)

    if flag == False:
        return jsonify(dict(err=0, msg="", data=[]))

    assetCodeList = []
    lData = []
    for record in records:
        assetCode = record.get("online_addr")
        assetCodeList.append(assetCode)
        lData.append(
            dict(id=record["id"], templateId=record["model_id"], assetCode=assetCode, name=record["name"],
                 existingRFIDCodeList=[])
        )

    dRFIDInfo = BEOPDataAccess.getInstance().getRpsRFIDByAssetCodeList(assetCodeList)
    if dRFIDInfo == None:
        return jsonify(dict(err=1, msg="获取RFID码信息失败", data=[]))

    dTemplateIdName = BEOPDataAccess.getInstance().getAssetTemplates(0)

    for i in range(len(lData)):
        assetCode = lData[i].get("assetCode")
        if dRFIDInfo.get(assetCode, None):
            lData[i]["existingRFIDCodeList"] = dRFIDInfo.get(assetCode)

        templateName = dTemplateIdName.get(lData[i]["templateId"], None)
        if templateName != None:
            lData[i].update({"templateName": templateName})

        for j in range(len(lData)-i-1):
            if lData[j]["id"] > lData[j+1]["id"]:
                lData[j], lData[j+1] = lData[j+1], lData[j]

    return jsonify(dict(err=0, msg="", data=lData))


# 根据RFID扫描器id查询所在仓库ID
@bp_equipment.route("/getWarehouseIdOfRFIDReceiver", methods=["POST"])
def get_warehouse_id_of_rfid_receiver():
    rcv = request.get_json()
    receiverId = rcv.get("id", None)

    if receiverId != None:
        if not isinstance(receiverId, int):
            return jsonify(dict(err=0, msg="扫描器ID必须为整数", data={}))

    dData = BEOPDataAccess.getInstance().getWarehouseIdOfRFIDReceiver(receiverId)

    return jsonify(dict(err=0, msg="", data=dData))

@bp_equipment.route("/getAllEquipAssetInfo")
def get_all_equip_asset_info():
    equipList, total, flag = BEOPDataAccess.getInstance().searchEquipment(0, "", "", 500, 1)

    equipIdList = []
    for equip in equipList:
        equipIdList.append(equip.get("id"))

    dRes = BEOPDataAccess.getInstance().getEquipAssetInfo(equipIdList)

    dData = {}
    for strEquipID, dEquipInfo in dRes.items():
        identity = dEquipInfo.get("identity", None)
        if identity == None or identity == "":
            continue

        dData.update({identity: dEquipInfo})

    return jsonify(dict(err=0, msg="", data=dData))
