
import re
import ctypes
from siteinterface.utils import log_info_to_file
import os
from datetime import datetime
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
import requests
import json
from siteinterface.RedisManager import RedisManager
from siteinterface import app
from siteinterface.OSSTool import OSSTool

def is_ip(tar):
    if not isinstance(tar, str):
        return False

    if re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", tar):
        return True
    return False

# 对所有总线按IP排序
def sort_bus_via_ip(nodeList):
    for i in range(len(nodeList)):
        for j in range(len(nodeList)-i-1):
            if not is_ip(nodeList[j]["ip"]) and is_ip(nodeList[j+1]["ip"]):
                nodeList[j], nodeList[j + 1] = nodeList[j + 1], nodeList[j]
            elif is_ip(nodeList[j]["ip"]) and is_ip(nodeList[j+1]["ip"]):
                front = nodeList[j]["ip"].split(".")
                back = nodeList[j+1]["ip"].split(".")

                nFront = int(front[0]) * 1000000000 + int(front[1]) * 1000000 + int(front[2]) * 1000 + int(front[3])
                nBack = int(back[0]) * 1000000000 + int(back[1]) * 1000000 + int(back[2]) * 1000 + int(back[3])

                if nFront > nBack:
                    nodeList[j], nodeList[j+1] = nodeList[j+1], nodeList[j]

def find_obj_via_brand(objList, brand):
    for obj in objList:
        if obj.get("brand", "").lower() == brand.lower():
            return obj
    return None

def find_obj_via_model(objList, model):
    for obj in objList:
        if obj.get("model", "").lower() == model.lower():
            return obj
    return None

def sort_obj_by_first_character(objList):
    try:
        if not len(objList):
            return

        key = None
        if "brand" in objList[0].keys():
            key = "brand"
        elif "model" in objList[0].keys():
            key = "model"
        elif "name" in objList[0].keys():
            key = "name"

        if not key:
            return

        for i in range(len(objList)):
            for j in range(len(objList)-i-1):
                if objList[j].get(key, "") and objList[j+1].get(key, ""):
                    if objList[j][key][0] > objList[j+1][key][0]:
                        objList[j], objList[j+1] = objList[j+1], objList[j]

        for obj in objList:
            if isinstance(obj.get("children", None), list):
                sort_obj_by_first_character(obj["children"])

    except Exception as e:
        print(e.__str__())

def execute_modbus_test(domModbusTestPath, inputFileName, outputFileName):
    strCmd = "-inputFileName {inputFileName} -outputFileName {outputFileName}".format(inputFileName=inputFileName, outputFileName=outputFileName)
    print(strCmd)
    try:
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW(0, "runas", domModbusTestPath, strCmd, os.path.dirname(domModbusTestPath), 0)
        return True, ""
    except Exception as e:
        strLog = "ERROR in execute_modbus_test: {err}".format( err=e.__str__())
        log_info_to_file('execute_modbus_test_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        return False, e.__str__()

def delete_file(filePath):
    if os.path.exists(filePath):
        try:
            os.remove(filePath)
            return True
        except:
            return False

    return True

def clear_json_file_1_hour_ago(strDir):
    for root, dirs, files in os.walk(strDir):
        for file in files:
            if not file.endswith(".json"):
                continue

            timeList = re.findall(r"[0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}", file)
            if len(timeList):
                strTime = timeList[0]
                tTime = datetime.strptime(strTime, "%Y_%m_%d_%H_%M_%S")
                if (datetime.now() - tTime).total_seconds() > 60 * 30:
                    try:
                        os.remove(os.path.join(root, file))
                    except:
                        pass

def get_slot_to_assign(dShuttle, nUsedSlotList):
    nCurSlot = dShuttle.get("current")
    while nCurSlot <= 10000:
        if nCurSlot not in nUsedSlotList:
            dShuttle["decide"] = nCurSlot
            dShuttle["current"] = nCurSlot
            break

        nCurSlot += 1

def get_ip(tar):
    mList = re.findall(r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)", tar)
    if not mList:
        return None

    if not len(mList):
        return None

    return mList[0].strip()



"""
为modbus仪表接口配置的每个bus(ip) 分配slot号
"""
def assignSlotForStandardModbusConfig():
    dData = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfigMul(["modbusclientconfig"])
    dConfig = dData.get("modbusclientconfig", {})
    if not dConfig:
        return

    if not isinstance(dConfig, dict):
        return

    # 整理既有的ip与slot的对应关系
    busList = []
    for key, dInfo in dConfig.items():
        if not key.startswith("modbusTCP"):
            continue

        port = dInfo.get("port", 502)

        ip = get_ip(key)
        if ip == None:
            continue

        if not is_ip(ip):
            continue

        nSlot = None
        if isinstance(dInfo.get("slot", None), int):
            nSlot = dInfo.get("slot")

        busList.append(dict(ip=ip, slot=nSlot, port=port))

    # 按ip、 slot排序
    for i in range(len(busList)):
        for j in range(len(busList) - i - 1):
            if busList[j]["slot"] and busList[j + 1]["slot"]:
                if busList[j]["slot"] > busList[j + 1]["slot"]:
                    busList[j], busList[j + 1] = busList[j + 1], busList[j]
            elif not busList[j]["slot"] and not busList[j + 1]["slot"]:
                front = busList[j]["ip"].split(".")
                back = busList[j + 1]["ip"].split(".")
                nFront = int(front[0]) * 1000000000 + int(front[1]) * 1000000 + int(front[2]) * 1000 + int(front[3])
                nBack = int(back[0]) * 1000000000 + int(back[1]) * 1000000 + int(back[2]) * 1000 + int(back[3])
                if nFront > nBack:
                    busList[j], busList[j + 1] = busList[j + 1], busList[j]
            elif not busList[j]["slot"] and busList[j + 1]["slot"]:
                busList[j], busList[j + 1] = busList[j + 1], busList[j]

    # 为不含有slot的bus分配slot
    nCurSlot = 1
    usedSlotList = []
    task = {}
    for bus in busList:
        if isinstance(bus.get("slot"), int):
            usedSlotList.append(bus["slot"])
        else:

            dShuttle = {"current": nCurSlot}
            get_slot_to_assign(dShuttle, usedSlotList)
            nCurSlot = dShuttle.get("current")

            if dShuttle.get("decide") != None:
                task.update({bus.get("ip"): dShuttle.get("decide")})
                usedSlotList.append(dShuttle.get("decide"))

    # 写入slot
    for key, dInfo in dConfig.items():
        if not key.startswith("modbusTCP"):
            continue

        ip = get_ip(key)
        if not is_ip(ip):
            continue

        port = dInfo.get("port", 502)
        newKey = "modbusTCP:{ip}:{port}".format(ip=ip, port=port)

        if task.get(ip, None):
            dInfo.update(dict(slot=task[ip]))

        if key != newKey:
            del dConfig[key]
            dConfig.update({newKey: dInfo})

    BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', 'modbusclientconfig', dConfig)


"""
walkDir: 遍历路径
patFile: 文件名匹配正则表达式
nSeconds: 多少秒之前
timeFormat: 时间格式 %Y-%m-%d-%H-%M-%S

文件名中的时间格式包含 %Y-%m-%d-%H-%M-%S
"""
def delete_files_specified_seconds_ago(walkDir, patFile, nSeconds):
    for root, dirs, files in os.walk(walkDir):
        for file in files:
            if not re.match(patFile, file):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", file)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")

            if (datetime.now() - tTime).total_seconds() > nSeconds:
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

# 获取云端模板文件信息
def get_template_info(userId=None, templateId=None, templateFileNameList=[]):
    headers = {"Content-Type": "application/json"}
    postData = {"userId": userId, "templateId": templateId, "templateFileNameOrList": templateFileNameList}
    rsp = requests.post("http://47.100.17.99/api/getTemplateInfo", data=json.dumps(postData), headers=headers, timeout=15)
    if rsp.status_code != 200:
        return []

    try:
        dataList = json.loads(rsp.text).get("data", [])
        return True, dataList
    except:
        return False, []

def get_template_update_status(templateName):
    dJson = RedisManager.get("TemplateFileUpdateStatus")
    if not isinstance(dJson, dict):
        dJson = {}

    dUpdateInfo = dJson.get("{name}.4db".format(name=templateName), {})
    if not dUpdateInfo:
        return 0

    for strTime, nStatus in dUpdateInfo.items():
        if (datetime.now() - datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")).total_seconds() > 30 * 60:  # 超过半小时认为上次更新失败，则
            return 0
        else:
            return 1
    return 0

def get_template_update_progress(templateName):
    if not RedisManager.is_alive():
        return -1

    dJson = RedisManager.get("TemplateFileUpdateProgress")
    if not isinstance(dJson, dict):
        dJson = {}

    dCurrent = dJson.get("{name}.4db".format(name=templateName), {})
    if not isinstance(dCurrent, dict):
        return {}
    return dCurrent



def get_template_update_err(templateName):
    domUpdateDir = os.path.join(app.config["CORE_PATH"], "domUpdate")
    if not os.path.exists(domUpdateDir):
        return ""

    errFilePath = os.path.join(domUpdateDir, "err.json")
    if not os.path.exists(errFilePath):
        return ""

    with open(errFilePath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            dJson = {}

    if not isinstance(dJson, dict):
        return ""

    if not dJson.get(templateName, None):
        return ""

    dInfo = dJson.get(templateName)

    tTarget = None
    strErr = ""
    for strTime, dDetail in dInfo.items():
        tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
        if not isinstance(tTarget, datetime):
            tTarget = tTime

        if tTime > tTarget:
            tTarget = tTime
            strErr = dDetail.get("err", "")

    return strErr

def backup_template_file(templateName, lfPath, version):
    nThreshode = 3   # 单个模板文件最多保存几个备份
    tool = OSSTool()
    bSuc = tool.upload(lfPath, "release_history/templateFile/{templateName}/{templateName}_{time}_{version}.4db".format(templateName=templateName,
                                                                                                                      version=version,
                                                                                                                      time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))

    fileNameList = tool.iterate_files("release_history/templateFile/{templateName}".format(templateName=templateName))
    if len(fileNameList) > nThreshode:
        fileInfoList = []
        for fileName in fileNameList:
            if not fileName.endswith(".4db"):
                continue

            infoList = fileName.split("_")
            if len(infoList) < 3:
                continue

            strTime = infoList[1]
            tTime = None
            try:
                tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            except:
                pass

            if not isinstance(tTime, datetime):
                continue

            fileInfoList.append((fileName, tTime))

        for i in range(len(fileInfoList)):
            for j in range(len(fileInfoList)-i-1):
                if fileInfoList[j][1] < fileInfoList[j+1][1]:
                    fileInfoList[j], fileInfoList[j+1] = fileInfoList[j+1], fileInfoList[j]

        toDeleteFileNameList = []
        while len(fileInfoList) > nThreshode:
            name, timi = fileInfoList.pop()
            toDeleteFileNameList.append(name)

        if len(toDeleteFileNameList):
            strFilePathList = ["release_history/templateFile/{templateName}/{fileName}".format(templateName=templateName,fileName=item) for item in toDeleteFileNameList]
            tool.delete_files(strFilePathList)

    return bSuc


def replace_point_prefix(pointPrefix, localDomdbPath):
    bSucFinal = True
    msg = ""
    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_unit19("Plant01", pointPrefix, localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_unit19点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_paramterConfig("Plant01", pointPrefix, localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_paramterConfig点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_local_config("Plant01", pointPrefix, localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "local_config点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_unit13("Plant01", pointPrefix, localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_unit13点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_text("Plant01", pointPrefix,
                                                                                     localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_text点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_point("Plant01", pointPrefix,
                                                                                   localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_point点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_button("Plant01", pointPrefix,
                                                                                    localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_button点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_page_contain_elements("Plant01", pointPrefix,
                                                                                     localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "page_contain_elements点名前缀替换失败:{err};".format(err=errMsg)

    bSuc, errMsg = BEOPSqliteAccess.getInstance().replacePointPrefixFrom_list_line("Plant01", pointPrefix, localDomdbPath)
    if not bSuc:
        bSucFinal = False
        msg += "list_line点名前缀替换失败:{err};".format(err=errMsg)

    return bSucFinal, msg







