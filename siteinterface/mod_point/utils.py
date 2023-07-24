
import logging
import re
import os
from datetime import datetime
from siteinterface.OSSTool import OSSTool
from siteinterface import app
import json


def log_info_to_file(strLogFileName, strLogInfo):
    strCorePath = os.path.dirname(os.getcwd())
    strLogPath = os.path.join(strCorePath, 'dompysite')
    strLogPath = os.path.join(strLogPath, 'log')
    strLogFilePath = os.path.join(strLogPath, strLogFileName)

    tNow = datetime.now()
    with open(strLogFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S')+ '    ' + strLogInfo + '\n')


def is_int(listCount):
    res = True
    for obj in listCount:
        if not isinstance(obj, int):
            res = False
            break
    return res

def is_str(listName):
    res = True
    for obj in listName:
        if not isinstance(obj, str):
            res = False
            break
    return res

def is_digit(strTar):
    try:
        n = float(strTar)
        return True
    except:
        return False

# 采集单元
class DeepLogicUnit:
    def __init__(self, unitId, protocal):
        self._nUnitId = unitId
        self._strProtocal = protocal
        self._dSystem = {}

    def is_ip(self, strTar):
        if re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
                 strTar):
            return True
        return False

    def fill_net_param_for_system(self, strNetParam, systemId):
        oSystem = self._dSystem.get(systemId, None)
        if oSystem == None:
            return

        if oSystem._strProtocal == "bacnet":
            paramList = strNetParam.split(",")
            if not self.is_ip(paramList[0]):
                strErr = "采集设备::ip格式有误: {tar}".format(tar=strNetParam)
                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                return

            ip = paramList[0]
            port = paramList[1]
            snet = paramList[2]
            sadr = paramList[3]

            self._dSystem.get(systemId)._dNetParam.update(dict(ip=ip,
                                                               port=int(float(port)),
                                                               snet=snet,
                                                               sadr=sadr))

        elif oSystem._strProtocal == "modbus":
            if oSystem._strProtocalType == "ModbusTCP":
                paramList = strNetParam.split(",")
                if not self.is_ip(paramList[1]):
                    strErr = "采集设备::ip格式有误: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[0]) or not is_digit(paramList[2]):
                    strErr = "采集设备::modbus网络信息相关参数必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                nSlaveId = int(float(paramList[0].strip()))
                nPort = int(float(paramList[2].strip()))
                strIP = paramList[1].strip()

                self._dSystem.get(systemId)._dNetParam.update(dict(slaveId=nSlaveId,
                                                                   port=nPort,
                                                                   ip=strIP))

            elif oSystem._strProtocalType == "ModbusRTU":
                paramList = strNetParam.split(",")
                if len(paramList) < 6:
                    strErr = "采集设备::所含信息长度应不小于6: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[0]):
                    strErr = "采集设备::站号必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[1]):
                    strErr = "采集设备::com口号必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[2]):
                    strErr = "采集设备::波特率必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[3]):
                    strErr = "采集设备::字长度必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[4]):
                    strErr = "采集设备::停止位必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                if not is_digit(paramList[5]):
                    strErr = "采集设备::校验必须为数字: {tar}".format(tar=strNetParam)
                    log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                    return

                nSlaveId = int(float(paramList[0]))
                nCom = int(float(paramList[1]))
                nBaud = int(float(paramList[2]))
                nBitLength = int(float(paramList[3]))
                nStop = int(float(paramList[4]))
                nVerify = int(float(paramList[5]))   #  0-无校验；1-奇校验；2-偶校验

                self._dSystem.get(systemId)._dNetParam.update(dict(slaveId=nSlaveId,
                                                                   com=nCom,
                                                                   baud=nBaud,
                                                                   bitLength=nBitLength,
                                                                   stop=nStop,
                                                                   verify=nVerify))




    def collect_system(self, systemId, strProtocalType):
        if systemId in self._dSystem.keys():
            return

        oSystem = DeepLogicSystem(systemId, self._strProtocal, strProtocalType)
        self._dSystem.update({systemId: oSystem})

    def collect_equip_for_system(self, systemId, equipId, strNetParam, bacnetDeviceId):
        if systemId not in self._dSystem.keys():
            return False

        self.fill_net_param_for_system(strNetParam, systemId)
        oEquip = DeepLogicEquip(equipId, self._strProtocal, bacnetDeviceId)
        self._dSystem.get(systemId)._dEquip.update({equipId: oEquip})
        return True

def get_source_type_list():
    tool = OSSTool()
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    lfPath = os.path.join(tempDir, "PointSourceTypeMap_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(lfPath):
        try:
            os.remove(lfPath)
        except:
            pass

    originalSourceTypeList = [{"name": "phoenix370", "id": 1},{"name": "simense1200", "id": 2},{"name": "simense300", "id": 3},{"name": "simense1200TCP", "id": 4},
                              {"name": "simense300TCP", "id": 5},{"name": "ab300", "id": 6},{"name": "honeywellebi", "id": 7},
                              {"name": "modbus", "id": 8},{"name": "ModbusDirecctReadInServer", "id": 9},{"name": "wireless", "id": 10},
                              {"name": "vpoint", "id": 11},{"name": "bacnet", "id": 12},{"name": "protocol104", "id": 13},{"name": "lonworks", "id": 14},
                              {"name": "DB-Access", "id": 15},{"name": "DB-SQLServer", "id": 16},{"name": "DB-Oracle", "id": 17},{"name": "DB-MySQL", "id": 18},{"name": "custom1", "id": 19},
                              {"name": "custom2", "id": 20},{"name": "custom3", "id": 21},{"name": "custom4", "id": 22},{"name": "custom5", "id": 23},
                              {"name": "dateTime", "id": 24},{"name": "DanfossFCProtocol", "id": 25},{"name": "Insight", "id": 26},{"name": "WinCC1", "id": 27},
                              {"name": "KingView1", "id": 28},{"name": "ArchestrA3", "id": 29},{"name": "KEPware4", "id": 30},{"name": "ABBScada", "id": 31},
                              {"name": "OPC", "id": 32},{"name": "ModbusEquipment", "id": 33},{"name": "ThirdParty", "id": 34},{"name": "PersagyController", "id": 35},
                              {"name": "bacnet-mstp", "id": 36},{"name": "OPCUA", "id": 37},{"name": "bacnet-py", "id": 38},{"name": "obix", "id": 39},{"name": "logix", "id": 40},
                              {"name": "MoxaTCPServer", "id": 41},{"name": "CoreStation", "id": 42},{"name": "KNX", "id": 43},{"name": "DLT645", "id": 44},{"name": "ABSLC", "id": 45},{"name": "DCIM", "id": 46}]

    bSuc = tool.download("update/dbwizard/PointSourceTypeMap.json", lfPath)
    if not bSuc or not os.path.exists(lfPath):
        return originalSourceTypeList

    with open(lfPath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except Exception as e:
            print(e.__str__())
            dJson = {}

    try:
        os.remove(lfPath)
    except:
        pass

    if isinstance(dJson, dict):
        dSourceType = dJson.get("data", {})

        sourceList = []
        for source, dInfo in dSourceType.items():
            sourceList.append(dict(name=source, id=dInfo.get("id")))

        for i in range(len(sourceList)):
            for j in range(len(sourceList)-i-1):
                if sourceList[j]["id"] > sourceList[j+1]["id"]:
                    sourceList[j], sourceList[j+1] = sourceList[j+1], sourceList[j]

        return sourceList

    return originalSourceTypeList


# 采集系统
class DeepLogicSystem:
    def __init__(self, systemId, protocal, strProtocalType):
        self._nSystemId = systemId
        self._strProtocal = protocal
        self._strProtocalType = strProtocalType
        self._dNetParam = {}
        self._dEquip = {}

# 采集设备
class DeepLogicEquip:
    def __init__(self, equipId, protocal, bacnetDeviceId):
        self._nEquipId = equipId
        self._strProtocal = protocal
        self._nBacnetDeviceId = bacnetDeviceId
        self._dPoint = {}


class SinglePoint:
    def __init__(self, strPointName, strRW, strDescription, strUnit, strHigh, strLow, strBacnetDataType=None, nBacnetAddress=None,
                 nBacnetDeviceId=None, nMbsRegister=None, nMbsFunctionCode=None, nMbsDataType=None, nMbsRegisterLength=None):
        self._strPointName = strPointName
        self._strBacnetDataType = strBacnetDataType
        self._nBacnetAddress = nBacnetAddress
        self._strRW = strRW
        self._strDescription = strDescription
        self._strUnit = strUnit
        self._strHigh = strHigh
        self._strLow = strLow
        self._nBacnetDeviceId = nBacnetDeviceId
        self._nMbsRegister = nMbsRegister
        self._nMbsFunctionCode = nMbsFunctionCode
        self._nMbsDataType = nMbsDataType
        self._nMbsRegisterLength = nMbsRegisterLength


class DeepLogicPointTool:
    def __init__(self):
        self._dUnit = {}
        self._lErr = []
        self._lBacnetPoint = []
        self._lModbusPoint = []
        self._lAllPointName = []

    def is_deeplogic_point_table(self, workbook):
        sheetNameList = workbook._sheet_names
        if len(sheetNameList) >= 2 and "采集点位" in sheetNameList and "采集设备" in sheetNameList and "采集系统" in sheetNameList:
            return True
        return False

    def get_bacnet_datatype_and_bacnetaddress(self, strTar):
        if not strTar:
            return None, None, None
        try:
            tarList = strTar.split(";")
            addrList = tarList[1].split("@")
            strDataType = addrList[0]
            nAddress = int(float(addrList[1]))
            writable = addrList[2]
            rw = "R" if writable == "PV" else "W"
            return strDataType, nAddress, rw
        except:
            return None, None, None

    def process_unit_id(self, tar):
        try:
            nTar = int(float(tar))
            return nTar
        except:
            return None

    def process_system_id(self, tar):
        try:
            nTar = int(float(tar))
            return nTar
        except:
            return None

    def get_bacnet_device_id(self, values):
        try:
            nId = int(float(values[4]))
            return nId
        except:
            return None

    """设备ID为调试人员人为定义的升序虚拟编号"""
    def process_equip_id(self, tar):
        try:
            nTar = int(float(tar))
            return nTar
        except:
            return None

    """新增协议时需增加"""
    def get_protocal_type(self, strTar):
        strType = ""
        if strTar.lower() == "tcp":
            strType = "ModbusTCP"
        elif strTar.lower() == "rtu":
            strType = "ModbusRTU"
        return strType

    """新增协议时需增加"""
    def get_protocal_name(self, strTar):
        strName = None
        if strTar.lower() == "bacnet":
            strName = "bacnet"
        elif strTar.lower() == "modbus":
            strName = "modbus"
        return strName

    """处理采集系统sheet"""
    def process_system_sheet(self, workbook):
        sheet = workbook.sheet_by_name("采集系统")

        if sheet.nrows < 1:
            strErr = "采集系统::采集系统sheet为空"
            self._lErr.append(strErr)
            return

        for idx in range(0, sheet.nrows):
            if idx == 0:
                continue

            values = sheet.row_values(idx)
            tar = values[5]
            unitId = self.process_unit_id(tar)
            if unitId is None:
                strErr = "采集系统::采集单元号有误: {tar}".format(tar=tar)
                self._lErr.append(strErr)
                continue

            tar = values[0]
            systemId = self.process_system_id(tar)
            if systemId is None:
                strErr = "采集系统::采集系统ID有误: {tar}".format(tar=tar)
                self._lErr.append(strErr)
                continue

            strProtocalType = self.get_protocal_type(values[3])

            if unitId not in self._dUnit.keys():
                strProtocalName = self.get_protocal_name(values[2])
                if strProtocalName is None:
                    self._lErr.append("采集系统::[warning!]采集系统ID为{systemId}的系统由于协议名称解析失败或其协议暂未列入解析范围，故舍弃".format(systemId=systemId))
                    continue

                oUnit = DeepLogicUnit(unitId, strProtocalName)
                self._dUnit.update({unitId: oUnit})

            oUnit = self._dUnit.get(unitId)
            oUnit.collect_system(systemId, strProtocalType)

    """处理采集设备sheet"""
    def process_equip_sheet(self, workbook):
        sheet = workbook.sheet_by_name("采集设备")
        if sheet.nrows < 1:
            strErr = "采集设备::采集设备sheet为空"
            self._lErr.append(strErr)
            return

        for idx in range(0, sheet.nrows):
            if idx == 0:
                continue

            values = sheet.row_values(idx)
            tar = values[3]
            systemId = self.process_system_id(tar)
            if systemId is None:
                strErr = "采集设备::系统ID有误: {tar}".format(tar=tar)
                self._lErr.append(strErr)
                continue

            tar = values[0]
            equipId = self.process_equip_id(tar)
            if equipId is None:
                strErr = "采集设备::设备ID有误: {tar}".format(tar=tar)
                self._lErr.append(strErr)
                continue

            bacnetDeviceId = self.get_bacnet_device_id(values)

            strNetParam = values[2]
            bSettle = False
            for oUnit in self._dUnit.values():
                bSettle = oUnit.collect_equip_for_system(systemId, equipId, strNetParam, bacnetDeviceId)
                if bSettle:
                    break

            if not bSettle:
                strErr = "采集设备::[设备ID:{equipId}-系统ID:{systemId}]在采集系统中未发现系统ID:{systemId}".format(equipId=equipId, systemId=systemId)
                self._lErr.append(strErr)

    """处理采集点位sheet"""
    def process_point_sheet(self, workbook):
        sheet = workbook.sheet_by_name("采集点位")
        if sheet.nrows < 1:
            strErr = "采集点位::采集点位sheet为空"
            self._lErr.append(strErr)
            return

        rawDict = {}
        for idx in range(0, sheet.nrows):
            if idx == 0:
                continue

            values = sheet.row_values(idx)
            equipId = None
            try:
                equipId = int(float(values[13]))
            except:
                pass

            if equipId is None or (isinstance(equipId, str) and not len(equipId)):
                continue

            if equipId not in rawDict.keys():
                rawDict.update({equipId: []})

            rawDict.get(equipId).append(values)

        for unitId, oUnit in self._dUnit.items():

            for systemId, oSystem in oUnit._dSystem.items():
                for equipId, oEquip in oSystem._dEquip.items():
                    if equipId not in rawDict.keys():
                        continue

                    if oUnit._strProtocal == "bacnet":
                        pointsOfEquip = rawDict.get(equipId)
                        for lInfo in pointsOfEquip:
                            if len(lInfo) < 11:
                                strErr = "采集点位::经逗号分割后信息长度不能少于11: {info}".format(info=lInfo)
                                self._lErr.append(strErr)
                                continue

                            pointName = lInfo[0]
                            description = lInfo[1]
                            strAddressInfo = lInfo[4]
                            strUnit = lInfo[10]
                            strHigh = lInfo[9]
                            strLow = lInfo[8]
                            strBacnetDataType, nBacnetAddress, strRW = self.get_bacnet_datatype_and_bacnetaddress(strAddressInfo)
                            if strBacnetDataType == None or nBacnetAddress == None or strRW == None:
                                self._lErr.append("采集点位::bacnet点地址信息解析失败，因为信息有误(采集设备ID: {equipId})".format(equipId=equipId))
                                continue

                            if not oEquip._nBacnetDeviceId:
                                self._lErr.append("采集点位::bacnet device id为空(采集设备ID: {equipId})".format(equipId=equipId))
                                continue

                            oPoint = SinglePoint(pointName, strRW, description, strUnit, strHigh, strLow,
                                                 strBacnetDataType=strBacnetDataType,
                                                 nBacnetAddress=nBacnetAddress,
                                                 nBacnetDeviceId=oEquip._nBacnetDeviceId)

                            oEquip._dPoint.update({pointName: oPoint})

                    elif oUnit._strProtocal == "modbus":
                        pointsOfEquip = rawDict.get(equipId)
                        for lInfo in pointsOfEquip:
                            if len(lInfo) < 11:
                                strErr = "采集点位::经逗号分割后信息长度不能少于11: {info}".format(info=lInfo)
                                self._lErr.append(strErr)
                                continue

                            pointName = lInfo[0]
                            description = lInfo[1]
                            strAddressInfo = lInfo[4]
                            strUnit = lInfo[10]
                            strHigh = lInfo[9]
                            strLow = lInfo[8]

                            paramList = strAddressInfo.split(",")
                            if len(paramList) < 4:
                                self._lErr.append("采集点位::modbus点地址信息有误，单元格内容:{address}".format(address=strAddressInfo))
                                continue

                            if not is_digit(paramList[0]):
                                self._lErr.append("采集点位::寄存器地址应为一个数字，单元格内容:{address}".format(address=strAddressInfo))
                                continue

                            if not is_digit(paramList[1]):
                                self._lErr.append("采集点位::数据长度应为一个数字，单元格内容:{address}".format(address=strAddressInfo))
                                continue

                            if not is_digit(paramList[2]):
                                self._lErr.append("采集点位::功能码应该为数字，单元格内容:{address}".format(address=strAddressInfo))
                                continue

                            nRegister = int(float(paramList[0].strip())) + 1
                            nDataLength = int(float(paramList[1].strip()))    # 位情况下 这是位号
                            nFunctionCode = int(float(paramList[2].strip()))
                            strDataType = paramList[3].strip()

                            nDataType = None
                            nRegisterLength = None
                            if strDataType == "bit":
                                nDataType = 2
                                nRegisterLength = nDataLength
                            elif strDataType == "int2_r":
                                nDataType = 0
                                nRegisterLength = 1
                            elif strDataType == "int2":
                                nDataType = 1
                                nRegisterLength = 1
                            elif strDataType == "int4":
                                nDataType = 3
                                nRegisterLength = 2
                            elif strDataType == "int4_r":
                                nDataType = 4
                                nRegisterLength = 2
                            elif strDataType == "float":
                                nDataType = 5
                                nRegisterLength = 2
                            elif strDataType == "float_r":
                                nDataType = 6
                                nRegisterLength = 2

                            if nDataType == None or nRegisterLength == None:
                                self._lErr.append("采集点位::modbus数据类型有误，或者寄存器长度有误，单元格内容:{address}".format(address=strAddressInfo))
                                continue

                            strRW = "R"

                            oPoint = SinglePoint(pointName, strRW, description, strUnit, strHigh, strLow, nMbsRegister=nRegister,
                                                 nMbsFunctionCode=nFunctionCode,
                                                 nMbsDataType=nDataType,
                                                 nMbsRegisterLength=nRegisterLength)

                            oEquip._dPoint.update({pointName: oPoint})


    def get_modbus_network_info(self, strProtocalType, dNetParam):
        if strProtocalType == "ModbusTCP":
            if dNetParam.get("port", None) == None or dNetParam.get("ip", None) == None:
                return ""

            result = dNetParam.get("ip")
            if dNetParam.get("port") != 502:
                result = "{ip}/{port}".format(ip=dNetParam.get("ip"), port=dNetParam.get("port"))
            return result

        else:
            if dNetParam.get("com", None) == None or dNetParam.get("baud", None) == None:
                return ""

            result = "{com}/{baud}".format(com=dNetParam.get("com"), baud=dNetParam.get("baud"))
            return result


    """准备modbus 点( 用于domcore.exe)"""
    def prepare_modbus_point_list(self):
        try:
            idx = 1
            for unitId, oUnit in self._dUnit.items():
                if oUnit._strProtocal.lower() != "modbus":
                    continue

                for systemId, oSystem in oUnit._dSystem.items():
                    for equipId, oEquip in oSystem._dEquip.items():
                        for oPoint in oEquip._dPoint.values():
                            strNetWorkInfo = self.get_modbus_network_info(oSystem._strProtocalType, oSystem._dNetParam)
                            if not strNetWorkInfo:
                                continue

                            strPointName = oPoint._strPointName
                            strSourceType = "modbus"
                            strDescription = oPoint._strDescription
                            strUnit = oPoint._strUnit
                            strRW = oPoint._strRW
                            nSlaveId = oSystem._dNetParam.get("slaveId")
                            nRegisterAddress = oPoint._nMbsRegister
                            nFunctionCode = oPoint._nMbsFunctionCode
                            nMulti = 1
                            nDataType = oPoint._nMbsDataType
                            nRegisterLength = oPoint._nMbsRegisterLength
                            strParam8 = ""
                            strParam9 = ""
                            strParam10 = ""
                            str3rdPartAuth = "0"
                            storecycle = "2"
                            ptCustomName = ""
                            ptSystem = ""
                            ptDevice = ""
                            ptType = ""

                            strReserve01 = ""
                            strReserve02 = ""

                            if strPointName in self._lAllPointName:
                                strErr = "点名重复: %s" % strPointName
                                self._lErr.append(strErr)
                                continue

                            onePointList = [idx, strPointName, strSourceType, strDescription,
                                            strUnit, strRW, nSlaveId, nRegisterAddress, nFunctionCode, nMulti,
                                            strNetWorkInfo, nDataType,
                                            nRegisterLength, strParam8, strParam9, strParam10, oPoint._strHigh,
                                            oPoint._strLow,
                                            str3rdPartAuth,
                                            storecycle, ptCustomName, ptSystem, ptDevice, ptType, strReserve01,
                                            strReserve02]

                            self._lModbusPoint.append(onePointList)
                            self._lAllPointName.append(strPointName)

                            idx += 1
        except Exception as e:
            strErr = "ERROR in prepare_modbus_point_list: %s" % e.__str__()
            self._lErr.append(strErr)


    """准备bacnet点（用于domcore.exe）"""
    def prepare_bacnet_point_list(self):
        try:
            idx = 1
            for unitId, oUnit in self._dUnit.items():
                if oUnit._strProtocal.lower() != "bacnet":
                    continue

                for systemId, oSystem in oUnit._dSystem.items():
                    for equipId, oEquip in oSystem._dEquip.items():
                        for oPoint in oEquip._dPoint.values():

                            strBacnetAddr = str(oPoint._nBacnetAddress)
                            strDeviceId = str(oPoint._nBacnetDeviceId)
                            strPointName = oPoint._strPointName
                            strDataType = oPoint._strBacnetDataType

                            strNetwork = ""

                            strIpPort = ""
                            strParam7 = ""
                            strParam8 = ""
                            strParam9 = ""
                            strParam10 = ""
                            strSourceType = "bacnet"
                            str3rdPartAuth = "0"
                            storecycle = "2"
                            ptCustomName = ""
                            ptSystem = ""
                            ptDevice = ""
                            ptType = ""
                            strMulti = "1"
                            strReserve01 = ""
                            strReserve02 = ""

                            if not len(strPointName):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_point_list] 发现空点名")
                                continue

                            if not len(strDeviceId):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_point_list] deviceId 为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strDataType):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_point_list] 点位类型为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strBacnetAddr):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_point_list] bacnet地址为空(pointName:%s)" % strPointName)
                                continue

                            if strPointName in self._lAllPointName:
                                strErr = "duplicated pointname found: %s" % strPointName
                                self._lErr.append(strErr)
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"), strErr)
                                continue

                            onePointList = [idx, strPointName, strSourceType, oPoint._strDescription,
                                            oPoint._strUnit,
                                            oPoint._strRW, strDeviceId, strDataType, strBacnetAddr, strMulti,
                                            strNetwork, strIpPort,
                                            strParam7, strParam8, strParam9, strParam10, oPoint._strHigh,
                                            oPoint._strLow,
                                            str3rdPartAuth,
                                            storecycle, ptCustomName, ptSystem, ptDevice, ptType, strReserve01, strReserve02]

                            self._lBacnetPoint.append(onePointList)
                            self._lAllPointName.append(strPointName)

                            idx += 1

        except Exception as e:
            strErr = "ERROR in prepare_bacnet_point_list: %s" % e.__str__()
            self._lErr.append(strErr)


    """准备bacnet-py点（用于domBacnetCore.exe)"""
    def prepare_bacnet_py_point_list(self):
        try:

            idx = 1
            for unitId, oUnit in self._dUnit.items():
                if oUnit._strProtocal.lower() != "bacnet":
                    continue

                for systemId, oSystem in oUnit._dSystem.items():
                    for equipId, oEquip in oSystem._dEquip.items():
                        for oPoint in oEquip._dPoint.values():

                            strBacnetAddr = str(oPoint._nBacnetAddress)
                            strIp = oSystem._dNetParam.get("ip")
                            nPort = oSystem._dNetParam.get("port")
                            strSnet = oSystem._dNetParam.get("snet")
                            strSadr = oSystem._dNetParam.get("sadr")
                            strDeviceId = str(oPoint._nBacnetDeviceId)
                            strPointName = oPoint._strPointName
                            strDataType = oPoint._strBacnetDataType

                            strNetwork = strIp
                            if strSnet != "-1" and strSadr != "-1":
                                strNetwork = "{snet}:{sadr}".format(snet=strSnet, sadr=strSadr)

                            strIpPort = "{ip}:{port}".format(ip=strIp, port=nPort)
                            strParam7 = ""
                            strParam8 = ""
                            strParam9 = ""
                            strParam10 = ""
                            strSourceType = "bacnet-py"
                            str3rdPartAuth = "0"
                            storecycle = "2"
                            ptCustomName = ""
                            ptSystem = ""
                            ptDevice = ""
                            ptType = ""
                            strMulti = ""
                            strReserve01 = ""
                            strReserve02 = ""

                            if not len(strPointName):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list] 发现空点名")
                                continue

                            if not len(strDeviceId):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list] deviceId 为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strDataType):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list] 点位类型为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strBacnetAddr):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list] bacnet地址为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strNetwork):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list]param5为空(pointName:%s)" % strPointName)
                                continue

                            if not len(strIpPort):
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),
                                                 "[prepare_bacnet_py_point_list]param6为空(pointName:%s)" % strPointName)
                                continue

                            if strPointName in self._lAllPointName:
                                strErr = "duplicated pointname found: %s" % strPointName
                                self._lErr.append(strErr)
                                log_info_to_file("deeplogic_point_%s.log" % datetime.now().strftime("%Y-%m-%d"),strErr)
                                continue

                            onePointList = [idx, strPointName, strSourceType, oPoint._strDescription,
                                            oPoint._strUnit,
                                            oPoint._strRW, strDeviceId, strDataType, strBacnetAddr, strMulti,
                                            strNetwork, strIpPort,
                                            strParam7, strParam8, strParam9, strParam10, oPoint._strHigh, oPoint._strLow,
                                            str3rdPartAuth,
                                            storecycle, ptCustomName, ptSystem, ptDevice, ptType, strReserve01, strReserve02]

                            self._lBacnetPoint.append(onePointList)
                            self._lAllPointName.append(strPointName)

                            idx += 1

        except Exception as e:
            strErr = "ERROR in prepare_bacnet_py_point_list: %s" % e.__str__()
            self._lErr.append(strErr)

