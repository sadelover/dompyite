
import os
from siteinterface.utils import log_info_to_file
from datetime import datetime
import ctypes
import re
from siteinterface.commonUtils import convert_version
from siteinterface import app
from siteinterface.OSSTool import OSSTool
import json


def get_logic_sort_no(threadName):
    les = threadName.split("_")
    nNo = -1
    if len(les):
        try:
            nNo = int(les[0])
        except:
            pass
    return nNo


def get_dll_file_info(domlogicParserPath, dllFilePath, jsonFilePath):
    strCmd = "{dllFilePath} {jsonFilePath}".format(dllFilePath=dllFilePath, jsonFilePath=jsonFilePath)
    try:
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW(0, "runas", domlogicParserPath, strCmd, os.path.dirname(domlogicParserPath), 0)
        return True, ""
    except Exception as e:
        strLog = "ERROR in get_dll_file_info (dllFile:{dllFile}): {err}".format(dllFile=dllFilePath, err=e.__str__())
        log_info_to_file('get_dll_file_info_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        return False, e.__str__()

def get_dll_depend_points(domlogicParserPath, domdbPath, logicNameWithExt, jsonFilePath):
    strCmd = "{domdbPath} {logicNameWithExt} {jsonFilePath}".format(domdbPath=domdbPath, logicNameWithExt=logicNameWithExt, jsonFilePath=jsonFilePath)
    try:
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW(0, "runas", domlogicParserPath, strCmd, os.path.dirname(domlogicParserPath), 0)
        return True, ""
    except Exception as e:
        strLog = "ERROR in get_dll_depend_points (logicName:{logicName}): {err}".format(logicName=logicNameWithExt, err=e.__str__())
        log_info_to_file('get_dll_depend_points_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        return False, e.__str__()

def get_logic_process_name_to_restart(logicName):
    if not isinstance(logicName, list):
        nameList = [logicName]
    else:
        nameList = logicName

    toRestartLogicProcessNumList = []
    for strName in nameList:
        matchList = re.findall(r"Process[0-9]{1}_", strName)
        if not len(matchList):
            toRestartLogicProcessNumList.append(0)
        else:
            for match in matchList:
                strNum = match.replace("Process", "").replace("_", "")
                try:
                    toRestartLogicProcessNumList.append(int(strNum))
                except:
                    pass
            toRestartLogicProcessNumList.append(0)

    return toRestartLogicProcessNumList

"""
新建或更新策略时发现dll版本高于OSS记录的策略版本
则将OSS记录的策略版本跟更新一次
"""
def update_cloud_logic_version_when_manual_update(strDllVersion, dllFileNameWitoutExt):
    nDllVersion = convert_version(strDllVersion)
    if not isinstance(nDllVersion, int):
        return

    tempDir = os.path.join(app.static_folder, "temp")
    timeTag = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
    localFilePath = os.path.join(tempDir, "update_{timeTag}.json".format(timeTag=timeTag))

    tool = OSSTool()
    bSucDownload = tool.download("update/update.json", localFilePath)
    if bSucDownload:
        with open(localFilePath, "r", encoding="UTF8", errors="ignore") as fo:
            try:
                dJson = json.load(fo)
            except:
                dJson = {}

    dCloudVersion = dJson.get("logic_version", {})
    strCloudVersion = dCloudVersion.get(dllFileNameWitoutExt, "")
    nCloudVersion = convert_version(strCloudVersion)

    bNeedUploadCloudVersion = False
    if isinstance(nCloudVersion, int):
        if nDllVersion > nCloudVersion:
            if "logic_version" not in dJson.keys():
                dJson.update({"logic_version": {}})
            dJson["logic_version"].update({dllFileNameWitoutExt: strDllVersion})
            bNeedUploadCloudVersion = True
    elif nCloudVersion == None:
        if "logic_version" not in dJson.keys():
            dJson.update({"logic_version": {}})
        dJson["logic_version"].update({dllFileNameWitoutExt: strDllVersion})
        bNeedUploadCloudVersion = True

    if bNeedUploadCloudVersion and bSucDownload:
        with open(localFilePath, "w", encoding="UTF8", errors="ignore") as fo:
            json.dump(dJson, fo)

        tool.upload(localFilePath, "update/update.json")

    try:
        os.remove(localFilePath)
    except:
        pass

def get_cloud_version_of_dll(dllFileNameWithoutExt):
    tool = OSSTool()
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    localFilePath = os.path.join(tempDir, "update_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(localFilePath):
        try:
            os.remove(localFilePath)
        except:
            pass

    strVersion = None
    bSuc = tool.download("update/update.json", localFilePath)
    if bSuc and os.path.exists(localFilePath):
        dJson = None
        with open(localFilePath, "r", encoding="UTF8", errors="ignore") as fo:
            try:
                dJson = json.load(fo)
            except:
                pass

        if isinstance(dJson, dict):
            try:
                strVersion = dJson.get("logic_version", {}).get(dllFileNameWithoutExt, None)
            except:
                pass

    try:
        os.remove(localFilePath)
    except:
        pass

    return strVersion




