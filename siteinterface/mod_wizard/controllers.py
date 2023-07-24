# -*- coding: utf-8 -*-
from siteinterface.mod_wizard import bp_wizard
from flask import request, jsonify
from .utils import *
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
from siteinterface.commonUtils import find_ip_list, is_ip, get_server_adapters, analysis_energy_management_structure, is_digit, \
    shutdown_processes, is_int_digit, update_template_info_to_cloud, cloud_verification, convert_version, update_template_file_to_mainService
from siteinterface.utils import get_standard_modbus_equipment_define_from_cloud_frequent, get_standard_modbus_equipment_define_from_cloud, get_equipment_attr, get_modbus_equip_type_en, get_modbus_equip_type_ch, \
    get_modbus_equip_brand, get_modbus_equip_model, get_proj_name, get_cloud_user_info
import json
import time
import os
from datetime import datetime
from siteinterface.OSSTool import OSSTool
from siteinterface import app
import shutil
import sys
from siteinterface.processManager import ProcessManager
import subprocess
import win32api


@bp_wizard.route("/getStandardModbusConfig")
def get_standard_modbus_config():
    """
    获取本地已有的modbus仪表接口配置内容
    """
    bSucGetJson, dModbusEquipmentPointDefine = get_standard_modbus_equipment_define_from_cloud()
    if not bSucGetJson:
        return jsonify(dict(err=1, msg="从云端获取标准ModBUS设备定义失败", data={}))

    dTypeEnChNameMap = {}
    for driveName, dDrive in dModbusEquipmentPointDefine.items():
        equipTypeEn = dDrive.get("equipTypeEn", None)
        equipTypeCh = dDrive.get("equipTypeCh", None)
        if equipTypeEn not in dTypeEnChNameMap.keys():
            dTypeEnChNameMap.update({equipTypeEn: equipTypeCh})
        else:
            if equipTypeCh > dTypeEnChNameMap[equipTypeEn]:
                dTypeEnChNameMap[equipTypeEn] = equipTypeCh

    assignSlotForStandardModbusConfig()

    dData = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfigMul(["modbusclientconfig"])
    dCurrentConfig = dData.get("modbusclientconfig", {})

    dModbusConfig = dCurrentConfig
    if not isinstance(dCurrentConfig, dict):
        dModbusConfig = {}
        try:
            dModbusConfig = json.loads(dCurrentConfig)
        except:
            pass

        if not dModbusConfig:
            return jsonify(dict(err=0, msg="未发现仪表接口配置", data=[]))

    dResult = {}
    for modbusTCPKey, dModbusInfo in dModbusConfig.items():

        if not modbusTCPKey.startswith("modbusTCP"):
            continue

        busIpList = find_ip_list(modbusTCPKey)

        if not len(busIpList):
            continue

        busIp = busIpList[0]
        port = dModbusInfo.get("port", 502)
        slot = dModbusInfo.get("slot", None)
        if slot == None:
            continue

        dBusNode = dict(
            device="bus",
            name="总线({ip})".format(ip=busIp),
            ip=busIp,
            id=busIp,
            port=port,
            slot=slot,
            networkType="modbustcp",
            detail="",
            remark="",
            deviceId="",
            subnetwork=[],
            type="",
            brand="",
            model=""
        )

        dStations = dModbusInfo.get("stations", {})

        for strDeviceId, dStationInfo in dStations.items():
            strType = dStationInfo.get("type", "")
            equipAttr = get_equipment_attr(dStationInfo.get("pointPrefix", ""))
            equipTypeEn = get_modbus_equip_type_en(dModbusEquipmentPointDefine, strType)
            equipTypeCh = dTypeEnChNameMap.get(equipTypeEn, "未知")                                #get_modbus_equip_type_ch(dModbusEquipmentPointDefine, strType)
            brand = get_modbus_equip_brand(dModbusEquipmentPointDefine, strType)
            model = get_modbus_equip_model(dModbusEquipmentPointDefine, strType)
            strNo = dStationInfo.get("Number", "")
            pointPrefix = dStationInfo.get("pointPrefix", "")

            strName = "未知设备名称"
            if strNo and equipTypeEn:
                if equipTypeEn == "VSD":
                    if equipAttr:
                        strName = "{no}号{attr}\n站号:{deviceId}".format(no=strNo, attr=equipAttr, deviceId=strDeviceId)
                elif equipTypeEn == "PowerMeter":
                    if equipAttr:
                        strName = "{no}号{attr}电表\n站号:{deviceId}".format(no=strNo, attr=equipAttr, deviceId=strDeviceId)
                    else:
                        strName = "{no}号某设备电表\n站号:{deviceId}".format(no=strNo, deviceId=strDeviceId)
                else:
                    strName = "{no}号{type}\n站号:{deviceId}".format(no=strNo, type=equipTypeCh, deviceId=strDeviceId)

            indexing = [equipTypeCh, brand, model, strType]
            dBusNode["subnetwork"].append(dict(device=equipTypeEn,
                                               name=strName,
                                               ip="",
                                               id="{ip}_{deviceId}".format(ip=busIp, deviceId=strDeviceId),
                                               deviceId=strDeviceId,
                                               networkType="modbusrtu",
                                               remark="",
                                               detail="",
                                               subnetwork=[],
                                               type=strType,
                                               brand=brand,
                                               model=model,
                                               pointPrefix=pointPrefix,
                                               Number=strNo,
                                               indexing=indexing))

        dResult.update({slot: dBusNode})

    return jsonify(dict(err=0, msg="", data=dResult))


@bp_wizard.route("/getAllStandardModbusEquipmentDefine")
def get_all_standard_modbus_equipment_define():
    """
    从OSS获取现有已支持的所有modbus 标注设备（按类型、品牌、型号分类）
    """
    try:
        bSucGetJson, dCloudDefine = get_standard_modbus_equipment_define_from_cloud()
        if not bSucGetJson:
            return jsonify(dict(err=1, msg="从云端获取标准ModBUS设备定义失败", data={}))

        dAll = {}

        for driveName, dDrive in dCloudDefine.items():
            equipTypeEn = dDrive.get("equipTypeEn", None)
            equipTypeCh = dDrive.get("equipTypeCh", None)
            brand = dDrive.get("brand", None)
            model = dDrive.get("model", None)
            if equipTypeEn in [None, ""] or equipTypeCh in [None, ""] or brand in [None, ""] or model in [None, ""]:
                continue

            if equipTypeEn not in dAll.keys():
                dAll.update({equipTypeEn: dict(name=equipTypeCh, children=[])})
            else:
                if equipTypeCh > dAll[equipTypeEn]["name"]:
                    dAll[equipTypeEn]["name"] = equipTypeCh

            objOfBrand = find_obj_via_brand(dAll[equipTypeEn]["children"], brand)
            if objOfBrand == None:
                dAll[equipTypeEn]["children"].append(dict(brand=brand, children=[]))

            objOfBrand = find_obj_via_brand(dAll[equipTypeEn]["children"], brand)

            objOfModel = find_obj_via_model(objOfBrand["children"], model)
            if objOfModel == None:
                objOfBrand["children"].append(dict(model=model, children=[]))

            objOfModel = find_obj_via_model(objOfBrand["children"], model)

            objOfModel["children"].append(dict(name=driveName, description="", manual=""))

        for value in dAll.values():
            sort_obj_by_first_character(value["children"])

        return jsonify(dict(err=0, msg="", data=dAll))

    except Exception as e:
        return jsonify(dict(err=1, msg="获取失败:%s" % e.__str__(), data={}))


@bp_wizard.route("/saveModbusEquipmentOfBus", methods=["POST"])
def save_modbus_equipment_of_bus():
    try:
        rcv = request.get_json()
        ip = rcv.get("ip", None)
        slot = rcv.get("slot", None)
        port = rcv.get("port", None)
        stationList = rcv.get("stationList", [])

        if not isinstance(slot, int):
            return jsonify(dict(err=1, msg="slot不能为空且必须为整数", data=False))

        if ip != None:
            if not isinstance(ip, str):
                return jsonify(dict(err=1, msg="ip必须为字符串", data=False))
            if not is_ip(ip):
                return jsonify(dict(err=1, msg="ip格式有误", data=False))

        if port != None:
            if not isinstance(port, int):
                return jsonify(dict(err=1, msg="port必须为整数", data=False))

        current = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig('modbusclientconfig', )
        if current == None or not isinstance(current, str):
            current = "{}"
        dModbusClientConfig = json.loads(current)

        dCurrentConfig = dModbusClientConfig
        if not isinstance(dModbusClientConfig, dict):
            try:
                dCurrentConfig = json.loads(dModbusClientConfig)
            except:
                dCurrentConfig = {}

        dEquipPrefixSuffix = {}
        for key, dInfo in dCurrentConfig.items():
            dStationsOfBus = dInfo.get("stations", {})
            if not dStationsOfBus:
                continue

            strBusIp = get_ip(key)
            if not is_ip(strBusIp):
                continue

            nBusSlot = dInfo.get("slot", None)
            if nBusSlot == None:
                continue

            nBusPort = dInfo.get("port", 502)

            if strBusIp == ip and port == nBusPort:    # 跳过本ip + port，因为该ip+port指向的这个总线为正在修改的目标总线
                continue

            # 将其他总线的前后缀+驱动名称组合存入equipPrefixSuffixList以供后面的重复检查
            for strDeviceId, dDeviceInfo in dStationsOfBus.items():
                combination = "{prefix}_{suffix}_{strType}".format(prefix=dDeviceInfo.get("pointPrefix", ""),
                                                         suffix=dDeviceInfo.get("Number", ""),
                                                         strType=dDeviceInfo.get("type", ""))

                dEquipPrefixSuffix.update({combination: nBusSlot})

        stations = []
        nDeviceIdList = []

        for station in stationList:
            number = station.get("Number", "")
            if not is_digit(station.get("deviceId", None)):
                continue

            if not isinstance(station.get("type", None), str) or not station.get("type", ""):
                continue

            if not isinstance(station.get("pointPrefix", None), str) or not station.get("pointPrefix", ""):
                continue

            if not isinstance(number, str):
                if is_int_digit(number):
                    number = "{number:02d}".format(number=number)
                else:
                    number = ""

            if int(station.get("deviceId")) in nDeviceIdList:
                return jsonify(dict(err=1, msg="输入参数中发现重复的站号: %s" % station.get("deviceId"), data=False))

            combination = "{prefix}_{suffix}_{strType}".format(prefix=station["pointPrefix"],
                                                               suffix=number,
                                                               strType=station["type"])

            if dEquipPrefixSuffix.get(combination, None):
                if dEquipPrefixSuffix.get(combination) != slot:
                    return jsonify(dict(err=1, msg="前缀为{prefix}，后缀为{suffix}、驱动名为{strType}的配置已存在于其他总线中，保存失败".format(
                        prefix=station["pointPrefix"],
                        suffix=number, strType=station["type"]), data=False))

            nDeviceIdList.append(int(station.get("deviceId")))

            stations.append(dict(deviceId=str(station["deviceId"]),
                                 type=station["type"],
                                 pointPrefix=station["pointPrefix"],
                                 Number=number))

        if not len(stations) and ip == None and port == None:
            return jsonify(dict(err=1, msg="未发现需要修改的信息", data=False))

        strTargetIp = None   # 找到slot指向的那个ip
        nTargetPort = None   # 找到slot指向的那个port
        dTargetInfo = None   # 找到slot指向的key对应的键
        existingIpPortList = []  # 准备既有的ip_port组合列表
        for key, dInfo in dCurrentConfig.items():
            if not key.startswith("modbusTCP"):
                continue

            strBusIp = get_ip(key)
            if not is_ip(strBusIp):
                continue

            nBusPort = dInfo.get("port", 502)

            existingIpPortList.append("{ip}_{port}".format(ip=strBusIp, port=nBusPort))

            nBusSlot = dInfo.get("slot", None)

            if dTargetInfo == None:
                if nBusSlot == slot:
                    strTargetIp = strBusIp
                    nTargetPort = nBusPort
                    dTargetInfo = dInfo

        strSaveType = "edit"
        if strTargetIp == None or dTargetInfo == None:
            strSaveType = "new"
            if ip == None:
                return jsonify(dict(err=1, msg="仪表接口配置中未发现slot为{slot}的总线，则认为是新建，但传入的ip为空".format(slot=slot), data=False))

            if "{ip}_{port}".format(ip=ip, port=port) in existingIpPortList:
                return jsonify(dict(err=1, msg="仪表接口配置中未发现slot为{slot}的总线，则认为是新建，但传入的ip+port组合({ip}、{port})已存在于当前仪表接口配置中".format(slot=slot, ip=ip, port=port), data=False))

            if port == None:
                return jsonify(dict(err=1, msg="仪表接口配置中未发现slot为{slot}的总线，则认为是新建，但传入的port为空".format(slot=slot), data=False))

            if not len(stations):
                return jsonify(dict(err=1, msg="仪表接口配置中未发现slot为{slot}的总线，则认为是新建，但传入的子站为空".format(slot=slot), data=False))

        if strSaveType == "edit":
            if ip != None:
                if strTargetIp != ip or nTargetPort != port:  # 代表目标总线的ip或者port要被修改
                    if "{ip}_{port}".format(ip=ip, port=port) in existingIpPortList:  # 代表ip_port组合已存在于既有仪表接口配置中
                        return jsonify(dict(err=1, msg="要修改ip或port，但{ip}_{port}已存在于当前仪表接口中，无法修改".format(ip=ip, port=port), data=False))

                    strCurKey = "modbusTCP:{ip}:{port}".format(ip=strTargetIp, port=nTargetPort) # 当前的key
                    if strCurKey in dCurrentConfig.keys():
                        del dCurrentConfig[strCurKey]  # 删除当前的key，因为ip或port要被改变


            strNewKey = "modbusTCP:{ip}:{port}".format(ip=ip if ip != None else strTargetIp,
                                                       port=port if port != None else nTargetPort)

            if port != None:
                dTargetInfo.update(dict(port=port))

            # 修改即有stations (前端会全部传入，这里直接替换）
            if len(stations):
                dTargetInfo.update(dict(stations={}))
                for station in stations:
                    dTargetInfo["stations"].update({station["deviceId"]: dict(type=station.get("type"),
                                                                              pointPrefix=station.get("pointPrefix"),
                                                                              Number=station.get("Number"))})

                dCurrentConfig.update({strNewKey: dTargetInfo})
            else:  # 由于stations为空，则代表所有子站都被清空了，则该总线将被直接移除
                toDeleteKey = None
                for key, dConfig in dCurrentConfig.items():
                    if dConfig.get("slot") == slot:
                        toDeleteKey = key
                        break

                if toDeleteKey:
                    del dCurrentConfig[toDeleteKey]

        else:  # 增加一个新的总线
            if ip == None:
                return jsonify(dict(err=1, msg="新增一个总线，IP不能为空", data=False))
            if port == None:
                return jsonify(dict(err=1, msg="新增一个总线，port不能为空", data=False))
            if not len(stations):
                return jsonify(dict(err=1, msg="新增一个总线，子站列表不能为空", data=False))

            dModbusStations = {}
            for station in stations:
                dModbusStations.update({station["deviceId"]: dict(type=station.get("type"),
                                                                      pointPrefix=station.get("pointPrefix"),
                                                                      Number=station.get("Number"))})

            dCurrentConfig.update({"modbusTCP:{ip}:{port}".format(ip=ip, port=port): dict(interval=1,
                                                                                          port=port,
                                                                                          slot=slot,
                                                                                          stations=dModbusStations)})

        bSuc = BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', 'modbusclientconfig', dCurrentConfig)
        return jsonify(dict(err=1 if not bSuc else 0, msg="", data=bSuc))

    except Exception as e:
        return jsonify(dict(err=1, msg="保存失败:%s" % e.__str__(), data=False))

@bp_wizard.route("/testModbusConn", methods=["POST"])
def test_modbus_conn():

    errMsgList = []

    testerDir = os.path.join(os.getcwd(), "domModbusTest")
    testerPath = os.path.join(testerDir, "domModbusTest.exe")

    if not os.path.exists(testerDir) or not os.path.exists(testerPath):
        return jsonify(dict(err=1, msg="domModbusTest.exe不存在于dompysite文件夹下，请升级dompysite", data={}))

    clear_json_file_1_hour_ago(testerDir)

    rcv = request.get_json()
    ip = rcv.get("ip", None)
    port = rcv.get("port", None)
    deviceList = rcv.get("deviceList", None)

    """
    deviceList: [{"deviceId": 1, "type": "ABB_ACS510"}, {"deviceId": 2, "type": "ABB_ACS510"}]
    """
    if not isinstance(ip, str):
        return jsonify(dict(err=1, msg="ip必须为字符串", data={}))
    if not is_ip(ip):
        return jsonify(dict(err=1, msg="ip格式有误", data={}))
    if not isinstance(port, int):
        return jsonify(dict(err=1, msg="port必须为整数", data={}))

    if not isinstance(deviceList, list):
        return jsonify(dict(err=1, msg="设备列表必须为一个数组", data={}))

    nIdList = []
    equipList = []
    bSucGetJson, dStdModbusEquip = get_standard_modbus_equipment_define_from_cloud()
    if not bSucGetJson:
        return jsonify(dict(err=1, msg="从云端获取标准ModBUS设备定义失败", data=[]))

    for device in deviceList:
        if not device.get("deviceId", None):
            return jsonify(dict(err=1, msg="输入信息中存在站号未传入的设备", data={}))

        if not is_digit(device.get("deviceId")):
            return jsonify(dict(err=1, msg="输入信息中存在站号为非数字的设备", data={}))

        nDeviceId = int(device.get("deviceId"))

        if nDeviceId in nIdList:
            return jsonify(dict(err=1, msg="输入信息中存在重复的站号:{id}".format(id=nDeviceId), data={}))

        nIdList.append(nDeviceId)

        strType = device.get("type", None)
        if not strType:
            return jsonify(dict(err=1, msg="输入信息中存在非字符串的驱动名称:{s}".format(s=strType), data={}))

        if strType not in dStdModbusEquip.keys():
            return jsonify(dict(err=1, msg="输入信息中存在非法驱动名称:{s}".format(s=strType), data={}))

        equipList.append(dict(type=strType, deviceId=nDeviceId))

    dJson = dict(ip=ip, port=port, deviceList=[])
    for dEquip in equipList:
        strType = dEquip.get("type")   # 驱动名

        dTestPoint = dStdModbusEquip.get(strType).get("debugToolTestPoint", {})
        if not dTestPoint:
            errMsgList.append("驱动({strType})中未发现测点信息".format(strType=strType))
            continue

        script = dTestPoint.get("script", "")
        multi = dTestPoint.get("multi", 1)
        register = dTestPoint.get("register", None)
        registerCount = dTestPoint.get("registerCount", None)
        functionCode = dTestPoint.get("functionCode", None)
        description = dTestPoint.get("description", "")
        dataType = dTestPoint.get("dataType", None)
        pointName = dTestPoint.get("pointName", None)

        if register == None or registerCount == None or functionCode == None or dataType == None or pointName == None:
            errMsgList.append("驱动({strType})的测点信息有误，请联系开发检查domModbusClientCore".format(strType=strType))
            continue

        dJson["deviceList"].append({
            "deviceId": dEquip.get("deviceId"),
            "driveName": strType,
            "testPoint": {
                "description": description,
                "register": register,
                "registerCount": registerCount,
                "pointName": pointName,
                "multi": multi,
                "functionCode": functionCode,
                "script": script,
                "dataType": dataType
            }
        })

    timeTag = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")

    inputFileName = "input_{timeTag}.json".format(timeTag=timeTag)
    outputFileName = "output_{timeTag}.json".format(timeTag=timeTag)

    inputFilePath = os.path.join(testerDir, inputFileName)
    outputFilePath = os.path.join(testerDir, outputFileName)

    if os.path.exists(inputFilePath):
        bSucDel = delete_file(inputFilePath)
        if not bSucDel:
            return jsonify(dict(err=1, msg="删除上次残存的文件{file}失败".format(file=inputFilePath), data={}))

    if os.path.exists(outputFilePath):
        bSucDel = delete_file(outputFilePath)
        if not bSucDel:
            return jsonify(dict(err=1, msg="删除上次残存的文件{file}失败".format(file=outputFilePath), data={}))

    with open(inputFilePath, "w", encoding="UTF8", errors="ignore") as fo:
        json.dump(dJson, fo)

    if not os.path.exists(inputFilePath):
        return jsonify(dict(err=1, msg="生成domModbusTest.exe的输入文件{file}失败".format(file=inputFilePath), data={}))

    bSuc, sMsg = execute_modbus_test(testerPath, inputFileName, outputFileName)

    if not bSuc:
        strError = ";".join(errMsgList) if len(errMsgList) else ""
        msg = "测试失败:{err}".format(err=sMsg)
        if strError:
            msg += "，另外发现一些其他问题：" + strError

        delete_file(inputFilePath)
        delete_file(outputFilePath)

        return jsonify(dict(err=1, msg=msg, data={}))

    nCount = 0
    bSucGetOutputFile = False
    while nCount <= 60 * 2:   # 等2分钟
        if os.path.exists(outputFilePath):
            bSucGetOutputFile = True
            break
        nCount += 1
        time.sleep(1)

    if not bSucGetOutputFile:
        delete_file(inputFilePath)
        delete_file(outputFilePath)
        return jsonify(dict(err=1, msg="等待超时，domModbusTest.exe执行后未生成输出文件{file}".format(file=outputFilePath), data={}))

    with open(outputFilePath, "r", encoding="UTF8", errors="ignore") as fo:
        dOutputJson = json.load(fo)

    if not isinstance(dOutputJson, dict):
        delete_file(inputFilePath)
        delete_file(outputFilePath)
        return jsonify(dict(err=1, msg="domModbusTest.exe执行后未生成的输入文件{file}经解析后发现不是字典，有误".format(file=outputFilePath), data={}))

    strConnErr = ""
    if dOutputJson.get("conn_err", []) and isinstance(dOutputJson.get("conn_err"), list):
        if len(dOutputJson.get("conn_err")):
            strConnErr = ";".join(dOutputJson.get("conn_err"))

    dResult = {}
    for nId in nIdList:
        strId = str(nId)
        dInfo = dOutputJson.get(strId, {})
        if not dInfo:
            nErrCode = -1
            strTestMsg = "测试结果：失败。\n\n失败原因：测试结果中未发现站号为{deviceId}的设备的测试结果。".format(deviceId=nId)
            if strConnErr:
                strTestMsg += "（{strConnErr}）".format(strConnErr=strConnErr)
                strTestMsg += "\n\n参考建议：检查该总线的modbusTCP网络，如网关上电、网线接线等是否存在问题。\n\n"
            else:
                strTestMsg += "\n\n参考建议：检查modbus设备的品牌、型号，判断所选驱动是否适用于该设备。\n\n"
        else:
            nErrCode = dInfo.get("err")
            strTestMsg = dInfo.get("msg")

        dResult.update({strId: dict(errCode=nErrCode, msg=strTestMsg)})

    delete_file(inputFilePath)
    delete_file(outputFilePath)

    strMsg = "发现了一些其他的问题: " + ";".join(errMsgList) if len(errMsgList) else ""
    return jsonify(dict(err=0, msg=strMsg, data=dResult))

@bp_wizard.route("/deleteBus", methods=["POST"])
def deleteBus():
    rcv = request.get_json()
    slot = rcv.get("slot", None)

    if not isinstance(slot, int):
        return jsonify(dict(err=1, msg="slot不能为空且必须为整数", data=False))

    current = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig('modbusclientconfig', )
    dCurrentConfig = json.loads(current)

    nTargetSlot = None
    strTargetIp = None
    nTargetPort = None
    for key, dInfo in dCurrentConfig.items():
        if not key.startswith("modbusTCP"):
            continue

        strBusIp = get_ip(key)
        if not is_ip(strBusIp):
            continue

        nBusPort = dInfo.get("port", 502)

        try:
            nBusSlot = int(dInfo.get("slot", None))
        except:
            nBusSlot = None

        if nBusSlot == slot:
            nTargetSlot = nBusSlot
            strTargetIp = strBusIp
            nTargetPort = nBusPort
            break

    if nTargetSlot == None:
        return jsonify(dict(err=1, msg="未发现槽号为{slot}的总线".format(slot=slot), data=False))

    strKey = "modbusTCP:{ip}:{port}".format(ip=strTargetIp, port=nTargetPort)

    if strKey in dCurrentConfig.keys():
        del dCurrentConfig[strKey]

    bSuc = BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', 'modbusclientconfig', dCurrentConfig)

    return jsonify(dict(err=1 if not bSuc else 0, msg="", data=bSuc))


@bp_wizard.route("/downloadStdModbusEquipManual", methods=["POST"])
def download_std_modbus_equip_manual():
    rcv = request.get_json()
    strType = rcv.get("type", None)  # 驱动名称
    if not isinstance(strType, str):
        return jsonify(dict(err=1, msg="驱动名称不能为空", data=""))

    if not len(strType):
        return jsonify(dict(err=1, msg="驱动名称不能为空", data=""))

    fileFolder = os.path.join(app.static_folder, "std_modbus_equip_manual")
    if not os.path.exists(fileFolder):
        os.mkdir(fileFolder)

    localFilePath = os.path.join(fileFolder, "{driveName}.pdf".format(driveName=strType))
    if os.path.exists(localFilePath):
        try:
            os.remove(localFilePath)
        except:
            return jsonify(dict(err=1, msg="删除之前的残留文档失败，请检查服务器上是否有程序正在占用该文档：{file}".format(file=localFilePath), data=""))

    dAllDefine = get_standard_modbus_equipment_define_from_cloud_frequent()

    if strType not in dAllDefine.keys():
        bSucGetJson, dAllDefine = get_standard_modbus_equipment_define_from_cloud()
        if not bSucGetJson:
            return jsonify(dict(err=1, msg="从云端获取标准ModBUS设备定义失败", data=[]))

        if strType not in dAllDefine.keys():
            return jsonify(dict(err=1, msg='未知驱动名称:{name}'.format(name=strType), data=""))

    equipType = dAllDefine.get(strType, {}).get("equipTypeEn", "")
    brand = dAllDefine.get(strType, {}).get("brand", "")
    model = dAllDefine.get(strType, {}).get("model", "")

    if not equipType or not brand or not model:
        return jsonify(dict(err=1, msg='从云端的配置中获取的关于该驱动的设备类型或品牌或型号信息缺失', data=""))

    tool = OSSTool()
    ossFilePath = "update/dbwizard/StandardModbusEquipment/manual/{equipType}/{brand}/{model}/{driveName}.pdf".format(equipType=equipType,
                                                                                                                         brand=brand,
                                                                                                                         model=model,
                                                                                                                         driveName=strType)
    if not tool.file_exists(ossFilePath):
        return jsonify(dict(err=1, msg='云端未发现该驱动的描述文档', data=""))

    bSuc = tool.download(ossFilePath, localFilePath)
    if not bSuc:
        return jsonify(dict(err=1, msg="下载文档失败", data=""))

    if not os.path.exists(localFilePath):
        return jsonify(dict(err=1, msg="下载文档失败，因磁盘中未发现该文件", data=""))
    return jsonify(dict(err=0, msg="", data="{driveName}.pdf".format(driveName=strType)))


@bp_wizard.route("/uploadDomdbFromCoreServer")
def upload_domdb_from_core_server():
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    wizardDir = os.path.join(tempDir, "wizard")
    if not os.path.exists(wizardDir):
        os.mkdir(wizardDir)

    domdbUploadDir = os.path.join(wizardDir, "domdb_upload")
    if not os.path.exists(domdbUploadDir):
        os.mkdir(domdbUploadDir)

    srcPath = os.path.join(app.config["CORE_PATH"], "domdb.4db")

    dstFileName = "domdb_{proj}_{time}.4db".format(proj=get_proj_name(), time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"))
    dstPath = os.path.join(domdbUploadDir, dstFileName)

    if os.path.exists(dstPath):
        try:
            os.remove(dstPath)
        except:
            return jsonify(dict(err=1, msg="删除上次残余文件失败", data=""))

    # 清除之前的文件
    for root, dirs, files in os.walk(domdbUploadDir):
        for file in files:
            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", file)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            if (datetime.now() - tTime).total_seconds() > 60 * 30:    # 删除30分钟之前的文件
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

    shutil.copyfile(srcPath, dstPath)

    nCount = 0
    bExist = False
    while nCount < 5:
        if os.path.exists(dstPath):
            bExist = True
            break

        nCount += 1
        time.sleep(1)

    if not bExist:
        return jsonify(dict(err=1, msg="文件复制失败", data=""))

    fileStat = os.stat(dstPath)
    if fileStat.st_size <= 0:
        return jsonify(dict(err=1, msg="文件复制失败，因文件大小为{size}字节，异常".format(size=fileStat), data=""))

    return jsonify(dict(err=0, msg="", data=dstFileName))


@bp_wizard.route("/downloadDomdbToCoreServer", methods=["POST"])
def download_domdb_to_core_server():
    oFile = request.files.get("file")
    if oFile == None:
        return jsonify(dict(err=1, msg="未发现传入的domdb.4db", data=False))

    fileName = oFile.filename
    if not fileName.endswith(".4db"):
        return jsonify(dict(err=1, msg="文件无效，必须传入后缀为.4db的工程文件", data=False))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    wizardDir = os.path.join(tempDir, "wizard")
    if not os.path.exists(wizardDir):
        os.mkdir(wizardDir)

    domdbDownloadDir = os.path.join(wizardDir, "domdb_download")
    if not os.path.exists(domdbDownloadDir):
        os.mkdir(domdbDownloadDir)

    fileName = "domdb_{time}.4db".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"))
    saveFilePath = os.path.join(domdbDownloadDir, fileName)

    # 若有则清除
    if os.path.exists(saveFilePath):
        try:
            os.remove(saveFilePath)
        except:
            return jsonify(dict(err=1, msg="删除上次残余的文件失败", data=False))

    # 清除之前的文件
    for root, dirs, files in os.walk(domdbDownloadDir):
        for file in files:
            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", file)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            if (datetime.now() - tTime).total_seconds() > 60 * 30:  # 删除30分钟之前的文件
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

    # 保存文件
    oFile.save(saveFilePath)

    nCount = 0
    bExist = False
    while nCount < 5:
        if os.path.exists(saveFilePath):
            bExist = True
            break

        nCount += 1
        time.sleep(1)

    if not bExist:
        return jsonify(dict(err=1, msg="下载文件失败，core服务器上未发现传入的工程文件", data=False))

    # 替换前缀

    # 备份core服务器上的 domdb.4db
    backupDir = os.path.join(app.config["CORE_PATH"], "backup")
    if not os.path.exists(backupDir):
        os.mkdir(backupDir)

    coreServerDomdbPath = os.path.join(app.config["CORE_PATH"], "domdb.4db")
    if os.path.exists(coreServerDomdbPath):
        domdbBackupDir = os.path.join(backupDir, "domdbBackup")
        if not os.path.exists(domdbBackupDir):
            os.mkdir(domdbBackupDir)

        backupDstFileName = "domdb_{time}.4db".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        backupDstFilePath = os.path.join(domdbBackupDir, backupDstFileName)
        if os.path.exists(backupDstFilePath):
            os.remove(backupDstFilePath)

        shutil.copyfile(coreServerDomdbPath, backupDstFilePath)

    # 将文件复制到core路径下
    try:
        shutil.copyfile(saveFilePath, coreServerDomdbPath)
    except Exception as e:
        return jsonify(dict(err=1, msg="下载文件失败，因可能domdb.4db当前处于被占用状态(err:{err})".format(err=e.__str__()), data=False))

    nCount = 0
    bSucCopy = False
    while nCount < 5:
        if os.path.exists(coreServerDomdbPath):
            bSucCopy = True
            break

        nCount += 1
        time.sleep(1)

    if not bSucCopy:
        return jsonify(dict(err=1, msg="将文件复制到core路径下失败", data=False))

    fileStat = os.stat(coreServerDomdbPath)
    if fileStat.st_size <= 0:
        return jsonify(dict(err=1, msg="文件复制失败，因文件大小为{size}字节，异常".format(size=fileStat), data=""))

    shutdown_processes(["redis", "domhost", "dompysite", "omsite"])

    os.popen("taskkill /im dompysite.exe -f")

    return jsonify(dict(err=0, msg="下载成功，正在重启后台进程", data=True))

@bp_wizard.route("/getAllDomdbTemplateFromCloud")
def get_all_domdb_template_from_cloud():
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    wizardDir = os.path.join(tempDir, "wizard")
    if not os.path.exists(wizardDir):
        os.mkdir(wizardDir)

    projectGuideDir = os.path.join(wizardDir, "project_guide")
    if not os.path.exists(projectGuideDir):
        os.mkdir(projectGuideDir)

    tool = OSSTool()
    jsonFileNameLocal = "CloudTemplate_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"))
    jsonFilePathLocal = os.path.join(projectGuideDir, jsonFileNameLocal)
    if os.path.exists(jsonFilePathLocal):
        try:
            os.remove(jsonFilePathLocal)
        except:
            pass

    jsonFilePathOss = "update/dbwizard/CloudTemplate.json"
    if not tool.file_exists(jsonFilePathOss):
        return jsonify(dict(err=1, msg="云端未发现json文件: CloudTemplate.json"))

    bSuc = tool.download(jsonFilePathOss, jsonFilePathLocal)
    if not bSuc or not os.path.exists(jsonFilePathLocal):
        return jsonify(dict(err=1, msg="下载CloudTemplate.json失败"))

    with open(jsonFilePathLocal, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            dJson = {}

    plantList = dJson.get("data", [])
    if not isinstance(plantList, list):
        return jsonify(dict(err=1, msg="云端CloudTemplate.json格式有误"))

    dGroupClassify = {}
    for dPlant in plantList:
        if dPlant.get("CloudTemplateGroup", None) == None:
            continue
        if not isinstance(dPlant.get("CloudTemplateGroup", ""), str):
            continue
        if not len(dPlant.get("CloudTemplateGroup", "")):
            continue

        if dPlant.get("CloudTemplateID", None) == None:
            continue
        if not isinstance(dPlant.get("CloudTemplateID", ""), str):
            continue
        if not len(dPlant.get("CloudTemplateID", "")):
            continue

        if dPlant.get("CloudTemplateName", None) == None:
            continue
        if not isinstance(dPlant.get("CloudTemplateName", ""), str):
            continue
        if not len(dPlant.get("CloudTemplateName", "")):
            continue

        groupName = dPlant.get("CloudTemplateGroup")
        templateId = dPlant.get("CloudTemplateID")
        templateName = dPlant.get("CloudTemplateName")

        if groupName not in dGroupClassify.keys():
            dGroupClassify.update({groupName: []})

        dGroupClassify[groupName].append(dict(id=templateId, name="{name}({id})".format(name=templateName,
                                                                                        id=templateId)))

    return jsonify(dict(err=0, msg="", data=dGroupClassify))


@bp_wizard.route("/getTemplatePlantImg", methods=["POST"])
def get_template_plant_img():
    rcv = request.get_json()
    templateId = rcv.get("templateId", None)
    if templateId == None:
        return jsonify(dict(err=1, msg="模板ID不能为空", data=""))

    if not isinstance(templateId, str):
        return jsonify(dict(err=1, msg="模板ID必须为字符串", data=""))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    wizardDir = os.path.join(tempDir, "wizard")
    if not os.path.exists(wizardDir):
        os.mkdir(wizardDir)

    projectGuideDir = os.path.join(wizardDir, "project_guide")
    if not os.path.exists(projectGuideDir):
        os.mkdir(projectGuideDir)

    # 删除一天以前的文件
    for root, dirs, files in os.walk(projectGuideDir):
        for file in files:
            if not re.match(r"^room_[0-9]*_[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]*\.png$", file):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", file)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            if (datetime.now() - tTime).total_seconds() > 3600 * 24:
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

    tool = OSSTool()
    if not tool.file_exists("update/dbwizard/{id}/".format(id=templateId)):
        return jsonify(dict(err=1, msg="模板ID:{id}不存在".format(id=templateId), data=""))

    imgNameLocal = "room_{id}_{time}.png".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"), id=templateId)
    imgPathLocal = os.path.join(projectGuideDir, imgNameLocal)
    if os.path.exists(imgPathLocal):  # 存在则直接返回
        return jsonify(dict(err=0, msg="", data=imgNameLocal))

    ossImgPath = "update/dbwizard/{id}/room.png".format(id=templateId)
    if not tool.file_exists(ossImgPath):
        return jsonify(dict(err=1, msg="该模板({id})下不存在机房示例图片".format(id=templateId), data=""))

    bSuc = tool.download(ossImgPath, imgPathLocal)
    if not bSuc or not os.path.exists(imgPathLocal):
        return jsonify(dict(err=1, msg="机房示例图片下载失败", data=""))

    return jsonify(dict(err=0, msg="", data=imgNameLocal))



@bp_wizard.route("/downloadDomdbToCoreServerFromCloud", methods=["POST"])
def download_domdb_to_core_server_from_cloud():
    rcv = request.get_json()
    errMsg = ""

    templateId = rcv.get("templateId", None)
    if templateId == None:
        return jsonify(dict(err=1, msg="模板ID不能为空", data=""))
    if not isinstance(templateId, str):
        return jsonify(dict(err=1, msg="模板ID必须为字符串", data=""))

    pointPrefix = rcv.get("pointPrefix", None)
    if pointPrefix != None:
        if not isinstance(pointPrefix, str):
            return jsonify(dict(err=1, msg="需替换为的点名前缀必须为字符串", data=""))
        if not len(pointPrefix):
            return jsonify(dict(err=1, msg="需替换为的点名前缀不能为空", data=""))
        if re.match(r"^[0-9]{1}$", pointPrefix[0]):
            return jsonify(dict(err=1, msg="需替换为的点名前缀不能以数字开头", data=""))
        if pointPrefix.find(" ") >= 0:
            return jsonify(dict(err=1, msg="需替换为的点名前缀不能包含空格", data=""))
        if not re.match(r"^[a-zA-Z0-9_]*$", pointPrefix):
            return jsonify(dict(err=1, msg="需替换为的点名前缀不能包含特殊字符", data=""))

    tool = OSSTool()
    if not tool.file_exists("update/dbwizard/{id}/".format(id=templateId)):
        return jsonify(dict(err=1, msg="模板ID:{id}不存在".format(id=templateId), data=""))

    ossDomdbPath = "update/dbwizard/{id}/domdb.4db".format(id=templateId)
    if not tool.file_exists(ossDomdbPath):
        return jsonify(dict(err=1, msg="该模板({id})下不存在工程文件".format(id=templateId), data=""))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    wizardDir = os.path.join(tempDir, "wizard")
    if not os.path.exists(wizardDir):
        os.mkdir(wizardDir)

    projectGuideDir = os.path.join(wizardDir, "project_guide")
    if not os.path.exists(projectGuideDir):
        os.mkdir(projectGuideDir)

    # 删除一段时间之前的domdb.4db
    delete_files_specified_seconds_ago(projectGuideDir, r"^domdb_[0-9]*_[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]*\.4db$", 60*30)

    localDomdbName = "domdb_{id}_{time}.4db".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"), id=templateId)
    localDomdbPath = os.path.join(projectGuideDir, localDomdbName)
    if os.path.exists(localDomdbPath):
        try:
            os.remove(localDomdbPath)
        except:
            pass

    bSuc = tool.download(ossDomdbPath, localDomdbPath)
    if not bSuc or not os.path.exists(localDomdbPath):
        return jsonify(dict(err=1, msg="从云端下载工程文件失败", data=""))

    # 替换点名前缀
    if pointPrefix != None:
        bSucReplacePrefix, strReplaceErrMsg = replace_point_prefix(pointPrefix, localDomdbPath)
        if not bSucReplacePrefix:
            errMsg += strReplaceErrMsg

    # 将文件复制到core路径下
    coreServerDomdbPath = os.path.join(app.config["CORE_PATH"], "domdb.4db")
    try:
        shutil.copyfile(localDomdbPath, coreServerDomdbPath)
    except Exception as e:
        return jsonify(
            dict(err=1, msg="覆盖文件失败，因可能domdb.4db当前处于被占用状态(err:{err})".format(err=e.__str__()), data=False))

    nCount = 0
    bSucCopy = False
    while nCount < 5:
        if os.path.exists(coreServerDomdbPath):
            bSucCopy = True
            break

        nCount += 1
        time.sleep(1)

    if not bSucCopy:
        return jsonify(dict(err=1, msg="将文件复制到core路径下失败", data=False))

    fileStat = os.stat(coreServerDomdbPath)
    if fileStat.st_size <= 0:
        return jsonify(dict(err=1, msg="文件覆盖失败，因文件大小为{size}字节，异常".format(size=fileStat), data=""))

    shutdown_processes(["redis", "omsite", "domcore", "domModbusClientCore", "domOPCUACore", "domDLT645Core", "domObixCore",
                        "domLogixCore", "domSiemenseTCPCore", "domCloudSync", "domKNXMonitor", "domKNXCore", "domJobs", "domBacnetCore",
                        "domBacnetCore1", "domBacnetCore2", "domBacnetCore3", "domBacnetCore4", "domBacnetCore5", "domDCIMDataDriver",
                        "domABSLCCore", "domModbusServer", "domlogic", "domlogic01", "domlogic02", "domlogic03", "domlogic04", "domlogic05"])

    os.popen("taskkill /im dompysite.exe -f")

    return jsonify(dict(err=0, msg=errMsg, data=True))


@bp_wizard.route("/downloadPeriodicUpdateManualByKey", methods=["POST"])
def download_periodic_update_manual():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    key = rcv.get("key", None)
    nUpdatePeriodHour = rcv.get("period", 24)
    if not isinstance(key, str):
        return jsonify(dict(err=1, msg="key必须为字符串", data=""))
    if not len(key):
        return jsonify(dict(err=1, msg="key不能为空", data=""))
    if not isinstance(nUpdatePeriodHour, int):
        return jsonify(dict(err=1, msg="更新周期(小时)必须为整数", data=""))
    if nUpdatePeriodHour < 1:
        return jsonify(dict(err=1, msg="更新周期(小时)不能小于1", data=""))

    splitList = key.split("/")
    if not len(splitList):
        return jsonify(dict(err=1, msg="传入的key有误", data=""))

    fileNameWithExt = splitList[len(splitList)-1]
    fileSplit = os.path.splitext(fileNameWithExt)
    if not len(fileSplit[1]):
        return jsonify(dict(err=1, msg="传入的key应为包含文件名的完整路径，即key的末尾应为带有后缀的文件名", data=""))

    if not fileSplit[1].startswith("."):
        return jsonify(dict(err=1, msg="传入的key应为包含文件名的完整路径，即key的末尾应为带有后缀的文件名", data=""))

    tarFileName = fileSplit[0]
    extension = fileSplit[1]

    periodicUpdateManualDir = os.path.join(app.static_folder, "periodic_update_manual")
    if not os.path.exists(periodicUpdateManualDir):
        os.mkdir(periodicUpdateManualDir)

    existingFileNameList = []
    for root, dirs, strFileNames in os.walk(periodicUpdateManualDir):
        for strFileName in strFileNames:
            pat = r"^" + tarFileName + "_[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{6}" + extension + "$"
            if not re.match(pat, strFileName):
                continue

            existingFileNameList.append(strFileName)

    tTarget = None
    fileNameTarget = None
    for fileName in existingFileNameList:
        strTimeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{6}", fileName)
        if not len(strTimeList):
            continue

        strTime = strTimeList[0]
        tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S-%f")
        if not isinstance(tTarget, datetime):
            tTarget = tTime
            fileNameTarget = fileName
        else:
            if tTime > tTarget:
                tTarget = tTime
                fileNameTarget = fileName

    bNeedDownload = False
    if not fileNameTarget:  # 若本地没有则直接下载
        bNeedDownload = True
    else:   # 本地存在
        if (datetime.now() - tTarget).total_seconds() / 3600 > nUpdatePeriodHour:  # 超时则需要下载并将所有已存在的该文件的历史文件都删掉
            for fileName in existingFileNameList:
                try:
                    os.remove(os.path.join(periodicUpdateManualDir, fileName))
                except:
                    pass
            bNeedDownload = True
        else:  # 未超时则保留时间最近的一个文件并将其余的删除
            for fileName in existingFileNameList:
                if fileName == fileNameTarget:
                    continue
                try:
                    os.remove(os.path.join(periodicUpdateManualDir, fileName))
                except:
                    pass

    if bNeedDownload:
        tool = OSSTool()
        localFileName = "{tarFileName}_{time}{ext}".format(tarFileName=tarFileName,
                                                           time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"),
                                                           ext=extension)
        localFilePath = os.path.join(periodicUpdateManualDir, localFileName)
        if os.path.exists(localFilePath):
            try:
                os.remove(localFilePath)
            except:
                pass
        bSucDownload = tool.download(key, localFilePath)
        if not bSucDownload:
            if not tool.file_exists(key):
                return jsonify(dict(err=1, msg="key指向的文件不存在:{key}".format(key=key), data=""))
            return jsonify(dict(err=1, msg="key指向的文件下载失败:{key}".format(key=key), data=""))

        return jsonify(dict(err=0, msg="下载成功", data=localFileName))

    return jsonify(dict(err=0, msg="之前下载的文件未超时可直接使用", data=fileNameTarget))

"""OSS文档下载通用接口"""
@bp_wizard.route("/downloadManual/<key>")
def download_manual(key=None):
    if key == None:
        return jsonify(dict(err=1, msg="key不能为空", data={}))

    if not isinstance(key, str):
        return jsonify(dict(err=1, msg="key必须为字符串", data={}))

    if not len(key):
        return jsonify(dict(err=1, msg="key不能为空", data={}))

    if key == "PointTable":
        fileName = "PointNameStandardIntro.pdf"
        folderName = "guidance_manual"
        localDir = os.path.join(app.static_folder, folderName)
        ossPath = "update/dbwizard/Guidance/Configuration/{fileName}".format(fileName=fileName)
        if not os.path.exists(localDir):
            os.mkdir(localDir)

    elif key == "Gateway":
        fileName = "ZLAN5243A_5143D.pdf"
        folderName = "gateway_manual"
        localDir = os.path.join(app.static_folder, folderName)
        ossPath = "update/dbwizard/Gateway/{fileName}".format(fileName=fileName)
        if not os.path.exists(localDir):
            os.mkdir(localDir)

    else:
        fileName = "{key}.pdf".format(key=key)
        folderName = "guidance_manual"
        localDir = os.path.join(app.static_folder, folderName)
        ossPath = "update/dbwizard/Guidance/Configuration/{fileName}".format(fileName=fileName)
        if not os.path.exists(localDir):
            os.mkdir(localDir)

    localPath = os.path.join(localDir, fileName)
    if os.path.exists(localPath):
        try:
            os.remove(localPath)
        except:
            return jsonify(dict(err=1, msg="删除之前的残留文档失败，请检查服务器上是否有程序正在占用该文档：{file}".format(file=localPath), data={}))

    if ossPath == None:
        return jsonify(dict(err=1, msg="云端暂无该key对应的文档", data={}))

    tool = OSSTool()
    if not tool.file_exists(ossPath):
        return jsonify(dict(err=1, msg="云端未发现该文档", data={}))

    bSuc = tool.download(ossPath, localPath)

    if not bSuc or not os.path.exists(localPath):
        return jsonify(dict(err=1, msg="文档下载失败", data={}))

    return jsonify(dict(err=0, msg="文档下载成功", data={"folder": folderName,
                                                   "name": fileName}))


"""
上传模板文件，包括更新和新建
"""
@bp_wizard.route("/uploadTemplateFile", methods=["POST"])
def upload_template_file():
    oFile = request.files.get("file", None)  # 文件对象
    templateName = request.form.get("templateName", None)  # 模板名称
    cloudUserName = request.form.get("cloudUserName", None)   # 云端用户名
    cloudUserPassword = request.form.get("cloudUserPassword", None)   # 云端用户密码
    description = request.form.get("description", None)   # 模板描述

    if oFile == None:
        return jsonify(dict(err=1, msg="文件对象不能为空", data=False))

    strFileName = oFile.filename
    if not strFileName.endswith(".4db"):
        return jsonify(dict(err=1, msg="模板文件必须为.4db文件", data=False))

    if templateName != None:
        if not isinstance(templateName, str):
            return jsonify(dict(err=1, msg="模板名称有误", data=False))
        if not len(templateName):
            return jsonify(dict(err=1, msg="模板名称有误", data=False))
    else:
        templateName = oFile.filename.replace(".4db", "")

    if not isinstance(cloudUserName, str):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))
    if not len(cloudUserName):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))

    if not isinstance(cloudUserPassword, str):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))
    if not len(cloudUserPassword):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))

    bSucVer, dUserInfo = cloud_verification(cloudUserName, cloudUserPassword)
    if not bSucVer:
        return jsonify(dict(err=1, msg="云端验证失败", data=False))

    nUserId = dUserInfo.get("id", None)
    if not isinstance(nUserId, int):
        return jsonify(dict(err=1, msg="用户ID获取失败", data=False))

    templateName = templateName.replace(".4db", "").lower()
    templateNameWithExt = "{name}.4db".format(name=templateName)

    bSucGet, templateInfoList = get_template_info()
    if not bSucGet:
        return jsonify(dict(err=1, msg="从云端获取模板信息列表失败", data=False))

    bTemplateExists = False
    ownerUserId = None
    ownerUserFullName = ""
    strCloudVersion = ""
    for item in templateInfoList:
        if item.get("fileName").lower() == templateNameWithExt:
            bTemplateExists = True
            ownerUserId = item.get("userId")
            ownerUserFullName = item.get("userFullName")
            strCloudVersion = item.get("version")
            break

    # nType  0-更新；1-新增
    if bTemplateExists:
        if ownerUserId != nUserId:
            return jsonify(dict(err=1, msg="当前用户无权限编辑{template}，该模板文件的编辑权限属于{name}(userId:{userId})".format(template=templateNameWithExt,
                                                                                                           name=ownerUserFullName, userId=ownerUserId), data=False))
        nType = 0
    else:
        for item in templateInfoList:
            if item.get("fileName").lower() == templateNameWithExt:
                return jsonify(dict(err=1, msg="检测到新增模板文件指令，但模板名称({name})已存在，请重新定一个模板名称".format(name=templateNameWithExt.replace(".4db", "")), data=False))
        nType = 1

    if nType == 1:  # 只有新增模板才必须传入description
        if not isinstance(description, str):
            return jsonify(dict(err=1, msg="模板描述不能为空", data=False))
        if not len(description):
            return jsonify(dict(err=1, msg="模板描述不能为空", data=False))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    lfPath = os.path.join(tempDir, "{templateName}_{time}.4db".format(templateName=templateName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(lfPath):
        try:
            os.remove(lfPath)
        except:
            pass

    try:
        oFile.save(lfPath)
        if not os.path.exists(lfPath):
            return jsonify(dict(err=1, msg="上传的文件有误，暂存失败", data=False))
    except:
        return jsonify(dict(err=1, msg="上传的文件有误，暂存失败", data=False))

    bSucGetVersion, strErrMsg, dTemplateInfo = BEOPSqliteAccess.getInstance().getTemplateFileInfo(lfPath)
    if not bSucGetVersion:
        try:
            os.remove(lfPath)
        except:
            pass
        return jsonify(dict(err=1, msg=strErrMsg, data=False))

    version = dTemplateInfo.get("version")  # 待上传文件的版本号

    # 版本检查
    nVersion = convert_version(version)
    nCloudVersion = convert_version(strCloudVersion)

    if nVersion == None:
        return jsonify(dict(err=1, msg="上传的模板文件版本号有误", data=False))

    if nCloudVersion != None:
        if nVersion == nCloudVersion:
            return jsonify(dict(err=1, msg="{templateName}.4db的云端版本为{strCloudVersion}，与想要上传的模板文件版本号({strVersion})相同，无需上传".format(templateName=templateName,
                                                                                                                                        strCloudVersion=strCloudVersion,
                                                                                                                                        strVersion=version), data=False))
        if nVersion < nCloudVersion:
            return jsonify(dict(err=1, msg="想要上传的模板文件{templateName}.4db版本号为{strVersion}，低于云端版本号({strCloudVersion})，请先将云端版本同步至本机，修改并更新版本号后再上传".format(
                templateName=templateName,
                strCloudVersion=strCloudVersion,
                strVersion=version), data=False))

    tool = OSSTool()
    bSuc = tool.upload(lfPath, "update/templatewizard/{name}".format(name=templateNameWithExt))
    if not bSuc:
        try:
            os.remove(lfPath)
        except:
            pass
        return jsonify(dict(err=1, msg="上传至oss失败", data=False))

    strMsg = "上传成功"
    bSucBackup = backup_template_file(templateName, lfPath, version)
    if not bSucBackup:
        strMsg += ",但备份失败"

    bSucUpdateCloudInfo = update_template_info_to_cloud(templateNameWithExt, version, nType, nUserId, description)
    if not bSucUpdateCloudInfo:
        try:
            os.remove(lfPath)
        except:
            pass
        return jsonify(dict(err=1, msg="模板文件云端信息更新失败", data=False))

    # 更新组态模板文件至mainService
    update_template_file_to_mainService(templateName)

    try:
        os.remove(lfPath)
    except:
        pass
    return jsonify(dict(err=0, msg=strMsg, data=True))


@bp_wizard.route("/getAllTemplateInfo", methods=["POST"])
def get_all_template_info():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}
    userId = rcv.get("userId", None)
    templateId = rcv.get("templateId", None)

    if userId != None:
        if not is_int_digit(userId):
            return jsonify(dict(err=1, msg="用户ID有误", data=[]))

    if templateId != None:
        if not is_int_digit(templateId):
            return jsonify(dict(err=1, msg="模板ID有误", data=[]))

    bSucGet, templateInfoList = get_template_info(userId=userId, templateId=templateId)
    if not bSucGet:
        return jsonify(dict(err=1, msg="获取模板文件信息失败", data=[]))

    return jsonify(dict(err=0, msg="", data=templateInfoList))


@bp_wizard.route("/updateTemplate/<templateName>")
def update_template(templateName=None):
    nWaitStartMins = 1  # 等待更新启动的分钟数
    nWaitFinishMins = 20  # 等待更新结束的分钟数

    if templateName == None:
        return jsonify(dict(err=1, msg="模板名称不能为空", data=False))

    if not isinstance(templateName, str):
        return jsonify(dict(err=1, msg="模板名称必须为字符串", data=False))

    if templateName.endswith(".4db"):
        templateName = templateName.replace(".4db", "")

    if not len(templateName):
        return jsonify(dict(err=1, msg="模板名称不能为空", data=False))

    if ProcessManager.getInstance().findProcess("domUpdate.exe"):
        return jsonify(dict(err=1, msg="domUpdate.exe在运行，本次更新放弃", data=False))

    nStatus = get_template_update_status(templateName)
    if nStatus:
        return jsonify(dict(err=1, msg="模板{name}现在处于正在更新状态，放弃本次更新".format(name=templateName), data=False))

    filePath = os.path.join(app.config["CORE_PATH"], "domUpdate", "domUpdate.exe")
    fileDir = os.path.join(app.config["CORE_PATH"], "domUpdate")
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="domUpdate.exe不存在，本次更新放弃", data=False))

    try:
        strCmd = "-name {templateName} -objectType 1".format(templateName=templateName)
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW(0, "runas", filePath, strCmd, fileDir, 0)
    except Exception as e:
        return jsonify(dict(err=1, msg="domUpdate启动失败: {err}".format(err=e.__str__()), data=False))

    nCount = 0
    bStarted = False
    while nCount <= nWaitStartMins * 60:
        dCurrProgress = get_template_update_progress(templateName)
        if dCurrProgress == -1:
            return jsonify(dict(err=0, msg="Redis未在运行，请10分钟后自行检查模板升级结果", data=True))

        if dCurrProgress.get("progress", 0) > 0 and (datetime.now() - datetime.strptime(dCurrProgress["time"], "%Y-%m-%d %H:%M:%S")).total_seconds() <= 20:
            bStarted = True
            break

        time.sleep(1)
        nCount += 1

    if not bStarted:
        return jsonify(dict(err=1, msg="{name}更新动作未启动成功".format(name=templateName), data=False))

    nCount = 0
    bFinished = False
    errMsg = ""
    while nCount <= 60 * nWaitFinishMins:
        dCurrProgress = get_template_update_progress(templateName)
        if dCurrProgress == -1:
            return jsonify(dict(err=0, msg="Redis未在运行，请10分钟后自行检查模板升级结果", data=True))

        if dCurrProgress.get("progress", 0) == 100 and (datetime.now() - datetime.strptime(dCurrProgress["time"], "%Y-%m-%d %H:%M:%S")).total_seconds() <= 20:
            bFinished = True
            errMsg = get_template_update_err(templateName)
            break

    if not bFinished:
        msg = "等待{min}分钟后未等到{name}升级成功的结果，请自行检查升级结果".format(min=nWaitFinishMins, name=templateName)
        if errMsg:
            msg += "(另外出现了一些其它问题：{errMsg})".format(errMsg=errMsg)
        return jsonify(dict(err=1, msg=msg, data=False))

    if not errMsg:
        msg = "模板{name}升级成功".format(name=templateName)

        # 解压图片
        strTemplateDir = os.path.join(app.static_folder, "template")
        templateFileList = []
        for subdir, dirs, fileNames in os.walk(strTemplateDir):
            for strFileName in fileNames:
                if strFileName.endswith(".4db"):
                    if strFileName == "{templateName}.4db".format(templateName=templateName):
                        templateFileList.append(os.path.join(strTemplateDir, strFileName))

        BEOPSqliteAccess.getInstance().prepareTemplateResouceFrom4db(templateFileList)
    else:
        msg = errMsg

    return jsonify(dict(err=1 if errMsg else 0, msg=msg, data=False if errMsg else True))


@bp_wizard.route("/deleteTemplateFile", methods=["POST"])
def delete_template_file():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    templateName = rcv.get("templateName", None)
    if not isinstance(templateName, str):
        return jsonify(dict(err=1, msg="模板名称必须为字符串", data=False))

    if templateName.endswith(".4db"):
        templateName = templateName.replace(".4db", "")

    if not len(templateName):
        return jsonify(dict(err=1, msg="模板名称不能为空", data=False))

    cloudUserName = rcv.get("cloudUserName", None)  # 云端用户名
    cloudUserPassword = rcv.get("cloudUserPassword", None)  # 云端用户密码

    if not isinstance(cloudUserName, str):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))
    if not len(cloudUserName):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))

    if not isinstance(cloudUserPassword, str):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))
    if not len(cloudUserPassword):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))

    bSucVer, dUserInfo = cloud_verification(cloudUserName, cloudUserPassword)
    if not bSucVer:
        return jsonify(dict(err=1, msg="云端验证失败", data=False))

    tool = OSSTool()
    bSuc = tool.delete_files(["update/templatewizard/{name}.4db".format(name=templateName)])
    if not bSuc:
        return jsonify(dict(err=1, msg="从云端删除{name}.4db失败".format(name=templateName), data=False))

    bSuc = update_template_info_to_cloud("{name}.4db".format(name=templateName), None, 2, None, None)
    if not bSuc:
        return jsonify(dict(err=1, msg="模板云端信息更新失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))


@bp_wizard.route("/getLocalTemplateFileList")
def get_local_template_file_list():
    templateDir = os.path.join(app.static_folder, "template")
    if not os.path.exists(templateDir):
        return jsonify(dict(err=1, msg="后台模板文件夹不存在", data=[]))

    dAllLocalTemplate = {}
    templateFileNameList = []
    for root, dirs, fileNames in os.walk(templateDir):
        for fileName in fileNames:
            if not fileName.endswith(".4db"):
                continue

            templateFileNameList.append(fileName)
            dInfo = {fileName: {}}
            bSucGetVersion, strErrMsg, dTemplateInfo = BEOPSqliteAccess.getInstance().getTemplateFileInfo(os.path.join(root, fileName))
            if bSucGetVersion:
                """
                type: 0- 云端有本地没有 1-云端有本地也有 2-本地有云端没有
                """
                dInfo[fileName].update({"localVersion": dTemplateInfo.get("version", ""),
                                        "templateId": "",
                                        "userFullName": "",
                                        "userId": "",
                                        "cloudVersion": "",
                                        "fileName": fileName,
                                        "description": "",
                                        "type": 2,
                                        "updateTime": "",
                                        "remark": strErrMsg})

            dAllLocalTemplate.update(dInfo)

    bSucGet, templateInfoList = get_template_info()
    if bSucGet:
        for item in templateInfoList:
            cloudTemplateFileName = item.get("fileName", None)
            if not cloudTemplateFileName:
                continue

            # 若云端有该模板则将该本地模板信息更新掉
            if dAllLocalTemplate.get(cloudTemplateFileName):
                dAllLocalTemplate[cloudTemplateFileName].update(dict(templateId=item["id"],
                                                          updateTime=item["updateTime"],
                                                          userFullName=item["userFullName"],
                                                          userId=item["userId"],
                                                          cloudVersion=item["version"],
                                                          description=item["description"],
                                                          type=1))
            # 若本地没有则将该模板直接加入
            else:
                dAllLocalTemplate.update({cloudTemplateFileName: dict(templateId=item["id"],
                                                          updateTime=item["updateTime"],
                                                          userFullName=item["userFullName"],
                                                          userId=item["userId"],
                                                          cloudVersion=item["version"],
                                                          description=item["description"],
                                                          type=0,
                                                          localVersion="",
                                                          fileName=cloudTemplateFileName,
                                                          remark="")})

    resList = [item for item in dAllLocalTemplate.values() if item]

    for i in range(len(resList)):
        for j in range(len(resList)-i-1):
            nTemplateIdFst = None
            try:
                nTemplateIdFst = int(resList[j]["templateId"])
            except:
                pass

            nTemplateIdScd = None
            try:
                nTemplateIdScd = int(resList[j + 1]["templateId"])
            except:
                pass

            if nTemplateIdFst == None and nTemplateIdScd != None:
                resList[j], resList[j + 1] = resList[j + 1], resList[j]
            elif nTemplateIdFst != None and nTemplateIdScd != None:
                if nTemplateIdFst > nTemplateIdScd:
                    resList[j], resList[j+1] = resList[j+1], resList[j]

    return jsonify(dict(err=0, msg="", data=resList))


@bp_wizard.route("/updateTemplateInfo", methods=["POST"])
def update_template_info():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    templateName = rcv.get("templateName", None)
    if not isinstance(templateName, str):
        return jsonify(dict(err=1, msg="模板名称必须为字符串", data=False))

    if templateName.endswith(".4db"):
        templateName = templateName.replace(".4db", "")

    if not len(templateName):
        return jsonify(dict(err=1, msg="模板名称不能为空", data=False))

    userId = rcv.get("userId", None)
    if userId != None:
        if not is_int_digit(userId):
            return jsonify(dict(err=1, msg="用户ID必须为整数", data=False))

        itemList = get_cloud_user_info(userId)
        if not len(itemList):
            return jsonify(dict(err=1, msg="用户ID不存在", data=False))

    description = rcv.get("description", None)
    if description != None:
        if not isinstance(description, str):
            return jsonify(dict(err=1, msg="模板描述必须为字符串", data=False))
        if not len(description):
            return jsonify(dict(err=1, msg="模板描述不能为空", data=False))

    cloudUserName = rcv.get("cloudUserName", None)  # 云端用户名
    cloudUserPassword = rcv.get("cloudUserPassword", None)  # 云端用户密码

    if not isinstance(cloudUserName, str):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))
    if not len(cloudUserName):
        return jsonify(dict(err=1, msg="云端用户名有误", data=False))

    if not isinstance(cloudUserPassword, str):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))
    if not len(cloudUserPassword):
        return jsonify(dict(err=1, msg="云端用户密码有误", data=False))

    bSucVer, dUserInfo = cloud_verification(cloudUserName, cloudUserPassword)
    if not bSucVer:
        return jsonify(dict(err=1, msg="云端验证失败", data=False))

    nVerifyUserId = dUserInfo.get("id", None)

    bSucGetTemplateInfo, infoList = get_template_info(templateFileNameList=["{name}.4db".format(name=templateName)])
    if not bSucGetTemplateInfo:
        return jsonify(dict(err=1, msg="获取云端模板信息失败", data=False))

    if not len(infoList):
        return jsonify(dict(err=1, msg="云端无该模板", data=False))

    nUserIdBelong = infoList[0].get("userId", None)
    if nUserIdBelong == None:
        return jsonify(dict(err=1, msg="获取模板归属用户ID失败", data=False))

    if nUserIdBelong != nVerifyUserId:
        return jsonify(dict(err=1, msg="当前用户无该模板的编辑权限（模板归属用户ID：{id}）".format(id=nUserIdBelong), data=False))

    if userId == None and description == None:
        return jsonify(dict(err=1, msg="未发现修改项", data=False))

    bSucUpdateCloudInfo = update_template_info_to_cloud("{name}.4db".format(name=templateName), None, 0, userId, description)
    if not bSucUpdateCloudInfo:
        return jsonify(dict(err=1, msg="更新失败", data=False))
    return jsonify(dict(err=0, msg="更新成功", data=True))

# 将模板文件下载至core服务器的静态路径：\static\files\templateFileLocal
# 供调试工具将模板文件传至本机做修改
@bp_wizard.route("/syncTemplateFileToLocal", methods=["POST"])
def sync_template_file_to_local():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}
    templateName = rcv.get("templateName", None)
    if not isinstance(templateName, str):
        return jsonify(dict(err=1, msg="模板名称必须为字符串", data=""))
    if not len(templateName):
        return jsonify(dict(err=1, msg="模板名称不能为空", data=""))
    if templateName.endswith(".4db"):
        templateName = templateName.replace(".4db", "")

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    templateFileLocalDir = os.path.join(filesDir, "templateFileLocal")
    if not os.path.exists(templateFileLocalDir):
        os.mkdir(templateFileLocalDir)

    lfName = "{templateName}_{time}.4db".format(templateName=templateName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"))
    lfPath = os.path.join(templateFileLocalDir, lfName)
    if os.path.exists(lfPath):
        try:
            os.remove(lfPath)
        except:
            pass

    for root, dirs, strFileNames in os.walk(templateFileLocalDir):
        for strFileName in strFileNames:
            if not strFileName.endswith(".4db"):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{6}", strFileName)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S-%f")
            if (datetime.now() - tTime).total_seconds() > 3600:
                try:
                    os.remove(os.path.join(root, strFileName))
                except:
                    pass

    tool = OSSTool()
    bSuc = tool.download("update/templatewizard/{templateName}.4db".format(templateName=templateName), lfPath)
    if not bSuc:
        if not tool.file_exists("update/templatewizard/{templateName}.4db".format(templateName=templateName)):
            return jsonify(dict(err=1, msg="云端不存在该模板文件{templateName}.4db".format(templateName=templateName), data=""))
        return jsonify(dict(err=1, msg="{templateName}.4db下载失败".format(templateName=templateName), data=""))

    return jsonify(dict(err=0, msg="下载成功", data=lfName))


@bp_wizard.route("/downloadOMZip")
def download_om_zip():
    tool = OSSTool()

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    for root, dirs, fileNames in os.walk(tempDir):
        for fileName in fileNames:
            if not fileName.endswith(".zip"):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", fileName)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            if (datetime.now() - tTime).total_seconds() > 3600 * 3:
                try:
                    os.remove(os.path.join(root, fileName))
                except:
                    pass

    zipFileName = "omsite_{time}.zip".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
    zipFilePath = os.path.join(tempDir, zipFileName)
    bSuc = tool.download("update/omsite.zip", zipFilePath)
    if not bSuc:
        return jsonify(dict(err=1, msg="omsite.zip下载失败", data=""))

    if not os.path.exists(zipFilePath):
        return jsonify(dict(err=1, msg="omsite.zip下载失败", data=""))

    return jsonify(dict(err=0, msg="omsite.zip下载成功", data="/temp/{fileName}".format(fileName=zipFileName)))



