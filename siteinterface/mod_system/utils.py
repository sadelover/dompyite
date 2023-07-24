
from siteinterface.processManager import ProcessManager
from datetime import datetime
import re
import shutil
import os
from configparser import ConfigParser
from siteinterface import app
import json
import collections
from siteinterface.commonUtils import is_int_digit, get_all_process_name_list
import subprocess
import pythoncom
import wmi
import pathlib
import time


def partition(les):
    pi = les[0]
    lo = [item for item in les[1:] if item["percent"] < pi["percent"]]
    hi = [item for item in les[1:] if item["percent"] >= pi["percent"]]
    return lo, pi, hi

def quick_sort(les):
    if len(les) <= 1:
        return les

    lo, pi, hi = partition(les)
    return quick_sort(lo) + [pi] + quick_sort(hi)


class ServerDiagnosis:
    def __init__(self, criticalFilePath):
        self.patProcessExeName = r"[\u4e00-\u9fa5_a-zA-Z0-9]+\.exe"
        self.dMonitorService = {"mysqldom": "mysqld.exe", "Redis": "redis-server.exe"}
        self.criticalFilePath = criticalFilePath
        self.nCriticalLimit = 5   # 重启多少次则认为是故障
        self.nHoursMonitor = 1    # 监测的最近多少小时内的CRITICAL.txt内容

    def read_critical_file_latest_lines(self, filePath):
        with open(filePath, "rb") as fileObj:
            fileObj.seek(0, 2)
            end = fileObj.tell()

            if end > 100000:
                fileObj.seek(-100000, 1)
            else:
                fileObj.seek(0)

            char = fileObj.read().decode('gbk', "ignore")
            char = char.replace("\r", "")
            lineList = char.split("\n")

        return lineList

    def detect_frequent_restart_process(self, strOneLineCriticalDetail):
        exeNameList = re.findall(self.patProcessExeName, strOneLineCriticalDetail)
        if not len(exeNameList):
            return None

        if (strOneLineCriticalDetail.find("关闭") >= 0 or strOneLineCriticalDetail.find("重启") >= 0) and strOneLineCriticalDetail.find("Menu Restart") == -1:
            return exeNameList[0]
        return None

    def detect_frequent_restart_service(self, strOneLineCriticalDetail):
        faultServiceName = None
        for name, process in self.dMonitorService.items():
            if strOneLineCriticalDetail.find(name) >= 0:
                faultServiceName = name
                break

        if faultServiceName == None:
            return None

        if strOneLineCriticalDetail.find("服务进程不存在") >= 0 or strOneLineCriticalDetail.find("导致启动") >= 0 or strOneLineCriticalDetail.find("失败") >= 0 or strOneLineCriticalDetail.find("重启") >= 0:
            return faultServiceName

        return None

    def analysis_critical_file(self):

        dFrequentRestartProcess = {}
        dFrequentRestartService = {}

        lineList = self.read_critical_file_latest_lines(self.criticalFilePath)

        reversedLineList = reversed(lineList)

        for line in reversedLineList:
            strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)
            if not len(strTimeList):
                continue

            tTime = datetime.strptime(strTimeList[0], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - tTime).total_seconds() > 3600 * self.nHoursMonitor:
                break

            recordList = []
            for idx, strTime in enumerate(strTimeList):
                nPosBegin = line.find(strTime)
                if idx + 1 <= len(strTimeList) - 1:
                    nPosEnd = line.find(strTimeList[idx + 1])
                else:
                    nPosEnd = len(line)

                detail = line[nPosBegin:nPosEnd]
                detail = detail.replace(strTime, "")
                recordList.append(
                    (strTime, detail)
                )

            for record in recordList:
                faultExeName = self.detect_frequent_restart_process(record[1])
                if faultExeName != None:
                    if faultExeName not in dFrequentRestartProcess.keys():
                        dFrequentRestartProcess.update({faultExeName: 0})
                    dFrequentRestartProcess[faultExeName] += 1

                faultServiceName = self.detect_frequent_restart_service(record[1])
                if faultServiceName != None:
                    if faultServiceName not in dFrequentRestartService.keys():
                        dFrequentRestartService.update({faultServiceName: 0})
                    dFrequentRestartService[faultServiceName] += 1

        return dFrequentRestartProcess, dFrequentRestartService

    def detect_stopped_service(self):
        faultServiceNameList = []
        for name, process in self.dMonitorService.items():
            handler = ProcessManager.getInstance().findProcess(process)
            if not handler:
                faultServiceNameList.append(name)
        return faultServiceNameList

    def diagnose(self):
        faultInfoList = []
        stoppedServiceNameList = self.detect_stopped_service()
        if len(stoppedServiceNameList):
            for sName in stoppedServiceNameList:
                faultInfoList.append(dict(title="%s服务已停止" % sName, detail="%s未在运行" % sName))

        dFrequentRestartProcess, dFrequentRestartService = self.analysis_critical_file()
        if dFrequentRestartProcess:
            for exeName, nCount in dFrequentRestartProcess.items():
                if nCount >= self.nCriticalLimit:
                    faultInfoList.append(dict(title="%s频繁重启" % exeName, detail="%s在过去的%s小时内重启%s次，异常" % (exeName, self.nHoursMonitor, nCount)))

        if dFrequentRestartService:
            for serviceName, nCount in dFrequentRestartService.items():
                if nCount >= self.nCriticalLimit:
                    faultInfoList.append(dict(title="%s频繁重启" % serviceName, detail="%s在过去的%s小时内重启%s次，异常" % (serviceName, self.nHoursMonitor, nCount)))
        return faultInfoList


"""
zipFilePath: the file.zip path
toUnzipDir: example:   file.zip ->  .\a\b\file\   toUnzipDir is .\a\b
"""
def unzip_file(zipFilePath, toUnzipDir):
    try:
        shutil.unpack_archive(zipFilePath, toUnzipDir)
        return True
    except Exception as e:
        return False

def get_exe_file_name(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".exe"):
                return file
    return None

def find_out_true_src_dir(directory, procName):
    try:
        while not os.path.exists(os.path.join(directory, "{proc}.exe".format(proc=procName))):
            directory = os.path.join(directory, procName)
            if not os.path.exists(directory):
                return None
        return directory
    except Exception as e:
        return None


def copy_tree(src, dst):
    if not os.path.exists(dst):
        print("{dir} doesn't exist, making it...".format(dir=dst))
        os.mkdir(dst)
    try:
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    os.mkdir(d)
                copy_tree(s, d)
            else:
                if os.path.exists(d):
                    os.remove(d)
                shutil.copy2(s, d)
        return True
    except Exception as e:
        return False

class MyConf(ConfigParser):
    def __init__(self):
        ConfigParser.__init__(self, defaults=None)

    def optionxform(self, strOption):
        return strOption


def get_options_as_dict_of_section(conf, strSectionKey):
    options = conf.options(strSectionKey)
    dOptions = {}
    for option in options:
        optionValue = conf[strSectionKey][option]
        dOptions.update({option: optionValue})
    return dOptions

"""
在编辑frpc.ini之后将即有的projid暂存一下
"""
def temporary_save_last_proj_id(strProjId):
    jsonFileName = "proj_id_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
    tempDir = os.path.join(app.config["CORE_PATH"], "domfrpc", "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    for root, dirs, fileNames in os.walk(tempDir):
        for fileName in fileNames:
            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", fileName)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            if (datetime.now() - tTime).total_seconds() > 5 * 60:
                try:
                    os.remove(os.path.join(root, fileName))
                except:
                    pass

    jsonFilePath = os.path.join(tempDir, jsonFileName)
    if os.path.exists(jsonFilePath):
        try:
            os.remove(jsonFilePath)
        except:
            pass

    with open(jsonFilePath, "w", encoding="UTF8", errors="ignore") as fo:
        json.dump({"projId": strProjId}, fo)

    return jsonFileName

def get_last_proj_id(jsonFileName):
    jsonFilePath = os.path.join(app.config["CORE_PATH"], "domfrpc", "temp", jsonFileName)
    if not os.path.exists(jsonFilePath):
        return None

    with open(jsonFilePath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            dJson = {}

    if not isinstance(dJson, dict):
        return None

    return dJson.get("projId", None)


def set_proj_id_to_rdpdom(dOptions, strProjId):
    dOptions.update({"remote_port": "7{projId}".format(projId=strProjId)})

def set_proj_id_to_rdpdesktop(dOptions, strProjId):
    dOptions.update({"remote_port": "8{projId}".format(projId=strProjId)})

def remove_temporary_json_file(jsonFileName):
    jsonFilePath = os.path.join(app.config["CORE_PATH"], "domfrpc", "temp", jsonFileName)
    try:
        os.remove(jsonFilePath)
    except:
        pass


def get_config_from_frpc_ini(strConfiginiFilePath):
    conf = MyConf()
    conf.read(strConfiginiFilePath)

    projIdRdpDom = None
    projIdDesktop = None

    try:
        for sectionKey in conf.sections():
            if sectionKey.find("RDPDOM") >= 0:
                natchList = re.findall(r"[0-9]*", sectionKey)
                if len(natchList):
                    for item in natchList:
                        if is_int_digit(item):
                            projIdRdpDom = item
                            break

            elif sectionKey.find("RDPDesktop") >= 0:
                natchList = re.findall(r"[0-9]*", sectionKey)
                if len(natchList):
                    for item in natchList:
                        if is_int_digit(item):
                            projIdDesktop = item
                            break
    except:
        pass

    if projIdRdpDom and projIdDesktop:
        if projIdRdpDom == projIdDesktop:
            return {"projId": projIdRdpDom}, ""
        else:
            return {"projId": None}, "当前配置有误"
    else:
        return {"projId": None}, "当前无配置"


def edit_frpc_config_file(strConfiginiFilePath, strLogFilePath, strProjId):
    if not os.path.exists(strConfiginiFilePath):
        return False, "frpc.ini文件不存在", None

    conf = MyConf()
    conf.read(strConfiginiFilePath)
    temporayFileName = None

    try:
        for sectionKey in conf.sections():
            if sectionKey.find("RDPDOM") >= 0:

                natchList = re.findall(r"[0-9]*", sectionKey)
                if len(natchList):
                    origProjId = None
                    for item in natchList:
                        if is_int_digit(item):
                            origProjId = item
                            break

                    if origProjId != None:
                        temporayFileName = temporary_save_last_proj_id(origProjId)

                dOptions = get_options_as_dict_of_section(conf, sectionKey)
                newSectionKey = "RDPDOM_{projId}".format(projId=strProjId)
                del conf[sectionKey]
                set_proj_id_to_rdpdom(dOptions, strProjId)
                conf.update({newSectionKey: dOptions})

            elif sectionKey.find("RDPDesktop") >= 0:
                dOptions = get_options_as_dict_of_section(conf, sectionKey)
                newSectionKey = "RDPDesktop_{projId}".format(projId=strProjId)
                del conf[sectionKey]
                set_proj_id_to_rdpdesktop(dOptions, strProjId)
                conf.update({newSectionKey: dOptions})

            elif sectionKey == "common":
                conf["common"].update(dict(log_level="info",
                                           log_max_days="2",
                                           log_file=strLogFilePath))

        with open(strConfiginiFilePath, "w") as fo:
            conf.write(fo)

        return True, "", temporayFileName

    except Exception as e:
        strLog = "编辑服务器远程设置失败:%s" % e.__str__()
        return False, strLog, None



def analysis_if_domfrpc_is_normally_running(strProjId, logFilePath):
    if not os.path.exists(logFilePath):
        return False

    nCode = -1  # 1-正常  2-端口已被其他服务器占用   -1 -不明
    strInfo = "不明"
    nCount = 0

    bConclusive = False
    while nCount < 10:
        try:
            lineList = collections.deque()
            for line in open(logFilePath, "r", encoding="UTF8", errors="ignore"):
                lineList.appendleft(line)
                if len(lineList) > 5:
                    lineList.pop()

            linList = list(lineList)

            linList.reverse()

            for lin in linList:
                if lin.find(strProjId) >= 0 and lin.find("start proxy success") >= 0:
                    nCode = 1
                    strInfo = "运行正常"
                    bConclusive = True
                    break

                if lin.find(strProjId) >= 0 and (lin.find("port already used") >= 0 or lin.find("start error") >= 0):
                    nCode = 2
                    strInfo = "ID({id})已被其他服务器占用".format(id=strProjId)
                    bConclusive = True
                    break

            if bConclusive:
                break

        except Exception as e:
            print(e.__str__())
        finally:
            nCount += 1
            time.sleep(3)

    return nCode, strInfo


def make_bat_and_run(strCmd):
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    batFileName = "bat_{time}.bat".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f"))
    batFilePath = os.path.join(tempDir, batFileName)
    with open(batFilePath, "w", encoding="UTF8", errors="ignore") as fo:
        fo.write(strCmd)

    if not os.path.exists(batFilePath):
        return False

    subprocess.call([batFilePath])

    try:
        os.remove(batFilePath)
    except:
        pass

    return True


def get_drive_info():
    dDriveInfo = {}
    pythoncom.CoInitialize()
    c = wmi.WMI()
    for physical_disk in c.Win32_DiskDrive():
        for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
            for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                name = logical_disk.Caption
                name = name.replace("/", "").replace("\\", "").replace(":", "").lower()
                if name not in dDriveInfo.keys():
                    dDriveInfo.update({name: {}})

                dDriveInfo[name].update(dict(total=round(int(logical_disk.Size) / 1024 / 1024 / 1024, 1),
                                             used=round((int(logical_disk.Size) - int(
                                                 logical_disk.FreeSpace)) / 1024 / 1024 / 1024, 1),
                                             free=round(int(logical_disk.FreeSpace) / 1024 / 1024 / 1024, 1),
                                             usedPercent=round(
                                                 float(100.0 * (int(logical_disk.Size) - int(
                                                     logical_disk.FreeSpace)) / int(logical_disk.Size)), 1)))
    return dDriveInfo

def str_to_raw(s):
    raw_map = {8:r'\b', 7:r'\a', 12:r'\f', 10:r'\n', 13:r'\r', 9:r'\t', 11:r'\v'}
    return r''.join(i if ord(i) > 32 else raw_map.get(ord(i), i) for i in s)

def analysis_directory(strInput):
    strInput = str_to_raw(strInput)
    strInput = strInput.replace("\\", "\\\\")
    try:
        directory = pathlib.Path(strInput)
    except Exception as e:
        return None, None, "分析存储路径失败:%s" % e.__str__()

    dDriveInfo = get_drive_info()

    itemList = []
    for part in directory.parts:
        itemList.append(part.replace(":", "").replace("\\", "").replace("/", "").strip().lower())

    if not len(itemList):
        return None, None, "分析存储路径失败"

    if itemList[0] not in dDriveInfo.keys():
        return None, None, "服务器磁盘无该盘符: {n}".format(n=itemList[0])

    driveName = itemList[0]
    strDirectory = "{drive}:\\".format(drive=driveName)

    if len(itemList) > 1:
        for item in itemList[1:]:
            strDirectory = os.path.join(strDirectory, item)

    if re.match(r"^[a-z]:\\$", strDirectory):
        bOnlyDrive = True
    else:
        bOnlyDrive = False

    return strDirectory, bOnlyDrive, ""


def get_process_name_with_capital(procNameWithoutExt):
    continuousProcessNameList, discontinousProcessNameList = get_all_process_name_list()
    dContinuous = {}
    for name in continuousProcessNameList:
        dContinuous.update({name.lower(): name})

    nameWithCapital = dContinuous.get(procNameWithoutExt, None)
    if nameWithCapital == None:
        nameWithCapital = procNameWithoutExt
    return nameWithCapital


