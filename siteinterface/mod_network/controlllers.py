# -*- coding: utf-8 -*-
from siteinterface.mod_network import bp_network
from flask import request, jsonify
from .utils import *
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
from siteinterface.commonUtils import find_ip_list, is_ip, get_server_adapters, analysis_energy_management_structure, is_time_string
from siteinterface.utils import get_standard_modbus_equipment_define_from_cloud, get_equipment_attr, get_modbus_equip_type_en, get_modbus_equip_type_ch
from siteinterface.BEOPDataAccess import BEOPDataAccess
from datetime import datetime

from ping3 import ping, verbose_ping

"""
网络节点ID格式：

1- {ip}                      bacnet网关/西门子plc     192.168.10.10          192_168_10_10_heart_beat_time
2- {ip}_{port}               modbusTCP网关           192.168.1.105_502       modbusTCP_192_168_1_105_502_heart_beat_time
3- {ip}_{port}_{deviceId}    modbusRTU设备           192.168.1.105_502_13    modbusTCP_192_168_1_105_502_13_heart_beat_time
4- {gatewayId}               ZLAN8308                E_2F_05                 E_2F_05_heart_beat_time
5- {gatewayId}_{meterId}     ZLAN8308 的rtu设备      E_2F_05_2               E_2F_05_2_heart_beat_time
"""
@bp_network.route("/get")
def get_network():
    errList = []
    dAdapters = get_server_adapters()
    if not dAdapters:
        return jsonify(dict(err=1, msg="获取网卡信息失败", data=[]))

    # 初始化各网络的根节点，各网络的根节点为路由器（尽管有的是虚拟的）
    allNodeList = []

    for adapterIp, dAdapterInfo in dAdapters.items():
        segment = get_network_segment(adapterIp)   # 网段 10.0.0
        dServer = dict(device="server",
                       segment=segment,
                       name="core服务器网口\n({adapter})\n{ip}".format(adapter=dAdapterInfo["adapterName"], ip=adapterIp),
                       ip=adapterIp,
                       id=adapterIp,
                       networkType="tcp/ip",
                       detail=dAdapterInfo["adapterName"],
                       remark="",
                       deviceId="",
                       networkName="",
                       subnetwork=[],
                       legal=True)

        remark = ""
        if dAdapterInfo["routerIp"].find(".8.1") >= 0:
            remark = "可能为外网"

        # 路由器节点
        allNodeList.append(dict(
            device="router",
            segment=segment,
            name="",
            ip=dAdapterInfo["routerIp"],
            id=dAdapterInfo["routerIp"],
            networkType="tcp/ip",
            detail="",
            remark=remark,
            deviceId="",
            subnetwork=[dServer],
            networkName="",
            legal=True
        ))

    # 分析modbus equipment配置
    bSucGetJson, dModbusEquipmentPointDefine = get_standard_modbus_equipment_define_from_cloud()
    if not bSucGetJson:
        return jsonify(dict(err=1, msg="从云端获取标准ModBUS设备定义失败", data=[]))

    dData = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfigMul(["modbusclientconfig"])
    dModbusConfig = dData.get("modbusclientconfig", {})
    for modbusTCPKey, dModbusInfo in dModbusConfig.items():
        gatewayIpList = find_ip_list(modbusTCPKey)

        if not len(gatewayIpList):
            continue

        nPort = None
        try:
            nPort = int(float(dModbusInfo.get("port", 502)))
        except:
            pass

        if not isinstance(nPort, int):
            continue

        gatewayIp = gatewayIpList[0]
        dRouterNode = find_node_with_same_network_segment(allNodeList, gatewayIp)   # 路由器网络节点

        # 若在服务器网段中未发现该网关则认为是某个独立的网络，新增一个独立的路由器节点
        if dRouterNode == None:
            unknownSegment = get_network_segment(gatewayIp)
            allNodeList.append(dict(
                device="router",
                segment=unknownSegment,
                name="",
                ip="\n",
                id="",
                networkType="tcp/ip",
                detail="",
                remark="自控系统内网中未发现与设备(ip:{ip})在同一个网段的路由器节点，可能为某独立网络，故增加一个独立的路由器节点".format(ip=gatewayIp),
                deviceId="",
                subnetwork=[],
                networkName="",
                legal=False    # True: 属于自控系统服务器内网网段；False: 不属于自控系统服务器内网网段
            ))
            dRouterNode = find_node_with_same_network_segment(allNodeList, gatewayIp)  # 路由器网络节点

        # dGatewayNode = find_node_with_same_ip(dRouterNode["subnetwork"], gatewayIp)  # 找到位于路由器子网中的网关节点
        dGatewayNode = find_node_with_same_ip_and_port(dRouterNode["subnetwork"], gatewayIp, nPort)  # 找到位于路由器子网中的网关节点
        if dGatewayNode == None:
            dRouterNode["subnetwork"].append(dict(device="ModbusGateway",
                                                  segment=get_network_segment(gatewayIp),
                                                  name="ModBUS网关\n{ip}".format(ip=gatewayIp),
                                                  ip=gatewayIp,
                                                  port=nPort,
                                                  id="{ip}_{port}".format(ip=gatewayIp, port=nPort),
                                                  deviceId="",
                                                  networkType="modbusTCP",
                                                  remark="",
                                                  networkName="",
                                                  detail="",
                                                  subnetwork=[],
                                                  legal=True))

            # dGatewayNode = find_node_with_same_ip(dRouterNode["subnetwork"], gatewayIp)  # 网关节点
            dGatewayNode = find_node_with_same_ip_and_port(dRouterNode["subnetwork"], gatewayIp, nPort)  # 网关节点

        if not modbusTCPKey.startswith("modbusTCP"):
            continue

        dStations = dModbusInfo.get("stations", {})

        for strDeviceId, dStationInfo in dStations.items():
            nDeviceId = None
            try:
                nDeviceId = int(float(strDeviceId))
            except:
                pass

            if not isinstance(nDeviceId, int):
                continue

            equipAttr = get_equipment_attr(dStationInfo.get("pointPrefix", ""))
            equipTypeEn = get_modbus_equip_type_en(dModbusEquipmentPointDefine, dStationInfo.get("type", ""))
            equipTypeCh = get_modbus_equip_type_ch(dModbusEquipmentPointDefine, dStationInfo.get("type", ""))
            strNo = dStationInfo.get("Number", "")

            strName = "未知设备名称"
            if strNo and equipTypeEn:
                if equipTypeEn == "VSD":
                    if equipAttr:
                        strName = "{no}号{attr}\n站号:{deviceId}".format(no=strNo, attr=equipAttr, deviceId=nDeviceId)
                elif equipTypeEn == "PowerMeter":
                    if equipAttr:
                        strName = "{no}号{attr}电表\n站号:{deviceId}".format(no=strNo, attr=equipAttr, deviceId=nDeviceId)
                    else:
                        strName = "{no}号某设备电表\n站号:{deviceId}".format(no=strNo, deviceId=nDeviceId)
                else:
                    strName = "{no}号{type}\n站号:{deviceId}".format(no=strNo, type=equipTypeCh, deviceId=nDeviceId)

            dGatewayNode["subnetwork"].append(dict(device=equipTypeEn,
                                                   segment="",
                                                   name=strName,
                                                   ip="",
                                                   id="{ip}_{port}_{deviceId}".format(ip=gatewayIp, port=nPort, deviceId=nDeviceId),
                                                   deviceId=nDeviceId,
                                                   networkType="modbusRTU",
                                                   remark="",
                                                   networkName="",
                                                   detail="",
                                                   subnetwork=[],
                                                   legal=True))

    # 分析点表
    siemensPlcIpList = []
    bacnetGatewayIpList = []
    dAllPoint = BEOPSqliteAccess.getInstance().getPointInfoFromS3db([])
    for pointName, dPointInfo in dAllPoint.items():
        if dPointInfo.get("sourceType") == "simense1200TCP":
            plcIp = dPointInfo.get("param3", None)
            if plcIp == None:
                continue

            if plcIp not in siemensPlcIpList:
                siemensPlcIpList.append(plcIp)

        elif dPointInfo.get("sourceType") == "bacnet":
            bacnetGatewayIp = dPointInfo.get("addr", None)
            if bacnetGatewayIp == None:
                continue

            if is_ip(bacnetGatewayIp):
                if bacnetGatewayIp not in bacnetGatewayIpList:
                    bacnetGatewayIpList.append(bacnetGatewayIp)

        elif dPointInfo.get("sourceType") == "bacnet-py":
            param5 = dPointInfo.get("param5", None)
            param6 = dPointInfo.get("param6", None)

            bacnetGatewayIp = None
            ipListParam5 = []
            ipListParam6 = []

            if param5 != None:
                ipListParam5 = find_ip_list(param5)
            if param6 != None:
                ipListParam6 = find_ip_list(param6)

            if len(ipListParam5):
                bacnetGatewayIp = ipListParam5[0]
            elif len(ipListParam6):
                bacnetGatewayIp = ipListParam6[0]

            if bacnetGatewayIp != None:
                if bacnetGatewayIp not in bacnetGatewayIpList:
                    bacnetGatewayIpList.append(bacnetGatewayIp)

    for siemensPlcIp in siemensPlcIpList:
        dRouterNode = find_node_with_same_network_segment(allNodeList, siemensPlcIp)   # 路由器网络节点
        if dRouterNode == None:
            errList.append("未发现与西门子PLC(ip:{ip})在同一个网段的路由器节点".format(ip=siemensPlcIp))
            continue

        dRouterNode["subnetwork"].append(dict(device="SiemensPLC",
                                              segment=get_network_segment(siemensPlcIp),
                                              name="西门子PLC\n{ip}".format(ip=siemensPlcIp),
                                              ip=siemensPlcIp,
                                              id=siemensPlcIp,
                                              deviceId="",
                                              networkType="tcp/ip",
                                              remark="",
                                              networkName="",
                                              detail="",
                                              subnetwork=[],
                                              legal=True))

    for bacnetGatewayIp in bacnetGatewayIpList:
        dRouterNode = find_node_with_same_network_segment(allNodeList, bacnetGatewayIp)   # 路由器网络节点
        if dRouterNode == None:
            errList.append("未发现与BACnet网关(ip:{ip})在同一个网段的路由器节点".format(ip=bacnetGatewayIp))
            continue

        dRouterNode["subnetwork"].append(dict(device="BACnetGateway",
                                              segment=get_network_segment(bacnetGatewayIp),
                                              name="BACnet网关\n{ip}".format(ip=bacnetGatewayIp),
                                              ip=bacnetGatewayIp,
                                              id=bacnetGatewayIp,
                                              deviceId="",
                                              networkType="tcp/ip",
                                              remark="",
                                              networkName="",
                                              detail="",
                                              subnetwork=[],
                                              legal=True))

    # 分析能源管理结构
    dEMDefine = {}
    strEMDefine = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig("energy_management_define")
    try:
        dEMDefine = json.loads(strEMDefine)
    except Exception as e:
        print(e.__str__())

    dDistribution = dEMDefine.get("distributionGroupList", {})
    dEMStruct = analysis_energy_management_structure(dDistribution)
    if dEMStruct:
        dEMNode = dict(
                device="router",
                segment="",
                name="dom云平台",
                ip="",
                id="",
                networkType="MQTT",
                detail="",
                remark="dom云平台",
                deviceId="",
                subnetwork=[],
                networkName="dom云平台",
                legal=True
            )

        for gatewayId, dGatewayStruct in dEMStruct.items():
            meterNodeList = []
            for meterId, dMeterStruc in dGatewayStruct.items():
                dEMMeterNode = dict(device="PowerMeter",
                                   segment="",
                                   name=dMeterStruc.get("name", ""),
                                   ip="",
                                   id="{gatewayId}_{meterId}".format(gatewayId=gatewayId, meterId=meterId),
                                   deviceId=meterId,
                                   networkType="modbusRTU",
                                   remark="",
                                   networkName="",
                                   detail="",
                                   subnetwork=[],
                                   legal=True)
                meterNodeList.append(dEMMeterNode)

            dEMGatewayNode = dict(device="ModbusGateway",
                                 segment="",
                                 name="ModBUS网关({gatewayId})".format(gatewayId=gatewayId),
                                 ip="",
                                 id=gatewayId,
                                 deviceId="",
                                 networkType="MQTT",
                                 remark="",
                                 networkName="",
                                 detail="",
                                 subnetwork=meterNodeList,
                                 legal=True)

            dEMNode["subnetwork"].append(dEMGatewayNode)

        allNodeList.append(dEMNode)

    # 排序
    sort_node_via_ip(allNodeList)
    name_router_nodes(allNodeList)
    assign_name_for_router_nodes(allNodeList)

    strErr = ""
    if len(errList):
        strErr += ";".join(errList)

    return jsonify(dict(err=0, msg=strErr, data=allNodeList))


@bp_network.route("/queryHistoryOnlineStatus", methods=["POST"])
def query_history_online_status():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    timeBegin = rcv.get("timeBegin", None)
    timeEnd =rcv.get("timeEnd", None)
    nodeId = rcv.get("id", None)
    if not isinstance(timeBegin, str):
        return jsonify(dict(err=1, msg="开始时间必须为字符串", data=[]))
    if not isinstance(timeEnd, str):
        return jsonify(dict(err=1, msg="结束时间必须为字符串", data=[]))
    if not len(timeBegin) or not len(timeEnd):
        return jsonify(dict(err=1, msg="开始时间或结束时间不能为空", data=[]))
    if not is_time_string(timeBegin, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="开始时间格式有误", data=[]))
    if not is_time_string(timeEnd, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="结束时间格式有误", data=[]))

    if not isinstance(nodeId, str):
        return jsonify(dict(err=1, msg="节点ID必须为字符串", data=[]))
    if not len(nodeId):
        return jsonify(dict(err=1, msg="节点ID不能为空", data=[]))

    pointNameHeartBeart = None
    if is_ip(nodeId): # bacnet网关/西门子plc
        pointNameHeartBeart = "{id}_heart_beat_time".format(id=nodeId.replace(".", "_"))
    elif re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)_[0-9]*$", nodeId): # modbusTCP网关
        pointNameHeartBeart = "modbusTCP_{id}_heart_beat_time".format(id=nodeId.replace(".", "_"))
    elif re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)_[0-9]*_[0-9]*$", nodeId):  # modbusRTU设备
        splitList = nodeId.split("_")
        if len(splitList) == 3:
            pointNameHeartBeart = "modbusTCP_{ip}_{port}_{deviceId}_heart_beat_time".format(ip=splitList[0].replace(".", "_"), port=splitList[1], deviceId=splitList[2])
    elif re.match(r"^[a-zA-Z0-9]*$", nodeId):  # ZLAN8308 及其RTU设备
        pointNameHeartBeart = "{id}_heart_beat_time".format(id=nodeId)

    if pointNameHeartBeart == None:
        return jsonify(dict(err=1, msg="根据节点id({id})未找到格式匹配的心跳包点名".format(id=nodeId), data=[]))

    dHisData = BEOPDataAccess.getInstance().get_history_data_padded([pointNameHeartBeart], timeBegin, timeEnd, "m1")

    if not isinstance(dHisData, dict):
        return jsonify(dict(err=1, msg="历史数据获取失败", data=[]))

    if not isinstance(dHisData.get("map", {}), dict):
        return jsonify(dict(err=1, msg="历史数据获取失败", data=[]))

    if not dHisData.get("map", {}):
        return jsonify(dict(err=1, msg="获取到的历史数据为空", data=[]))

    if not isinstance(dHisData.get("map", {}).get(pointNameHeartBeart, []), list):
        return jsonify(dict(err=1, msg="获取到的历史数据为空", data=[]))

    if not len(dHisData.get("map", {}).get(pointNameHeartBeart, [])):
        return jsonify(dict(err=1, msg="获取到的历史数据为空", data=[]))

    if not isinstance(dHisData.get("time", []), list):
        return jsonify(dict(err=1, msg="所获时间数组有误", data=[]))

    if not len(dHisData.get("time", [])):
        return jsonify(dict(err=1, msg="所获时间数组有误", data=[]))

    dataList = dHisData.get("map", {}).get(pointNameHeartBeart, [])
    timeList = dHisData.get("time", [])

    if len(dataList) != len(timeList):
        return jsonify(dict(err=1, msg="时间列表长度与值列表长度不相等", data=[]))

    resList = []
    for idx, strThen in enumerate(timeList):
        try:
            strTimeValue = dataList[idx]
        except:
            strTimeValue = ""

        tThen = None
        if is_time_string(strThen, "%Y-%m-%d %H:%M:%S"):
            tThen = datetime.strptime(strThen, "%Y-%m-%d %H:%M:%S")

        tTimeValue = None
        if is_time_string(strTimeValue, "%Y-%m-%d %H:%M:%S"):
            tTimeValue = datetime.strptime(strTimeValue, "%Y-%m-%d %H:%M:%S")

        if isinstance(tThen, datetime) and isinstance(tTimeValue, datetime):
            nDelayMins = round((tThen - tTimeValue).total_seconds() / 60, 2)
            if nDelayMins < 0:
                nDelayMins = 0.0

            resList.append(
                dict(time=strThen,
                     delayMins=nDelayMins)
            )

    return jsonify(dict(err=0, msg="", data=resList))


@bp_network.route("/ping", methods=["POST"])
def network_ping():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    strIP = rcv.get("server", None)
    nTimeOut =rcv.get("timeout", 5)
    if isinstance(nTimeOut, str):
        nTimeOut = int(float(nTimeOut))
    nCount = rcv.get("count", 1)

    nResult = -1
    strMsg = ""

    if strIP is None:
        return jsonify(dict(err=1, msg="server param lost", data=-1))

    try:
        nTestCount = 0
        while nTestCount<nCount:
            aa = ping(strIP, timeout=nTimeOut)  # Returns delay in seconds.
            if aa is None:
                nResult = 0
            elif isinstance(aa, bool):
                nResult = 1 if aa else 0
            elif isinstance(aa, float):
                nResult = 1
            else:
                try:
                    strMsg = 'Unhandeled ping return data: %s'%(str(aa))
                except:
                    pass

            if nResult==1:
                break #只要一次成功就返回ok

            nTestCount+=1
    except Exception as e:
        return jsonify(dict(err=1, msg= e.__str__(), data=-1))
    return jsonify(dict(err=0, msg= strMsg, data=nResult))