# -*- coding: utf-8 -*-
from siteinterface.mod_system import bp_system
from flask import request, jsonify
from siteinterface.BEOPSqliteAccess import *
import logging
import re
from winreg import OpenKey, KEY_READ, HKEY_LOCAL_MACHINE, KEY_WRITE
from winreg import QueryValueEx, REG_SZ, SetValueEx, CloseKey
import psutil
import wmi
import pythoncom
from siteinterface.mod_system.utils import quick_sort, ServerDiagnosis, unzip_file, get_exe_file_name, find_out_true_src_dir, copy_tree, \
    edit_frpc_config_file, get_last_proj_id, analysis_if_domfrpc_is_normally_running, remove_temporary_json_file, make_bat_and_run, \
    get_config_from_frpc_ini, analysis_directory, get_drive_info
from siteinterface.processManager import ProcessManager
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface.utils import process_restart_domfrpc
from siteinterface.RedisManager import RedisManager
import pathlib
from siteinterface.commonUtils import MyConf
import os
from siteinterface.mod_system.utils import *
from version import siteVersion


def clear_path(strDir):
    try:
        delList = os.listdir(strDir)
        for item in delList:
            strPath = os.path.join(strDir, item)
            if os.path.isfile(strPath):
                os.remove(strPath)
            elif os.path.isdir(strPath):
                shutil.rmtree(strPath)
        return True
    except Exception as e:
        logging.error("ERROR in bp_system clear_path: %s" % e.__str__())
        return False


@bp_system.route("/restartOS")
def restart_os():
    try:
        os.popen("shutdown -r -f -t 0")
        return jsonify(dict(err=0, msg="重启成功", data=True))
    except Exception as e:
        logging.error("ERROR in /system/restartOS: %s" % e.__str__())
        return jsonify(dict(err=1, msg="重启失败", data=False))


@bp_system.route("/clearLog")
def clear_log():
    try:
        coreDir = os.path.dirname(os.getcwd())
        if not os.path.exists(coreDir):
            return jsonify(dict(err=1, msg="core目录不存在", data=False))

        logDir = os.path.join(coreDir, "log")
        if not os.path.exists(logDir):
            return jsonify(dict(err=1, msg="core log目录不存在", data=False))

        rt = clear_path(logDir)
        return jsonify(dict(err=0, msg="", data=rt))
    except Exception as e:
        logging.error("ERROR in /system/clearLog: %s" % e.__str__())
        return jsonify(dict(err=1, msg="", data=False))

@bp_system.route("/startTaskManager")
def start_task_manager():
    try:
        os.popen("taskmgr")
        return jsonify(dict(err=0, msg="succeed to start task manager", data=True))
    except Exception as e:
        logging.error("ERROR in /system/startTaskManager: %s" % e.__str__())
        return jsonify(dict(err=1, msg="fail to start task manager", data=False))

@bp_system.route("/startCMD")
def start_cmd():
    try:
        os.popen("start cmd.exe")
        return jsonify(dict(err=0, msg="succeed to start cmd", data=True))
    except Exception as e:
        logging.error("ERROR in /system/startCMD: %s" % e.__str__())
        return jsonify(dict(err=1, msg="fail to start cmd", data=False))

@bp_system.route("/startExplorer")
def start_explorer():
    try:
        os.popen("start cmd.exe /c explorer.exe")
        return jsonify(dict(err=0, msg="succeed to start explorer", data=True))
    except Exception as e:
        logging.error("ERROR in /system/startCMD: %s" % e.__str__())
        return jsonify(dict(err=1, msg="fail to start explorer", data=False))

@bp_system.route("/getBACNET_IFACE")
def get_bacnet_iface():
    strR = ""
    try:
        strKey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
        rKey = OpenKey(HKEY_LOCAL_MACHINE, strKey, 0, KEY_READ)
        rs = QueryValueEx(rKey, "BACNET_IFACE")
        if len(rs):
            strR = rs[0]
        CloseKey(rKey)
        return jsonify(dict(err=0, msg="", data=strR))
    except:
        return jsonify(dict(err=0, msg="", data=""))


@bp_system.route("/setBACNET_IFACE", methods=["POST"])
def set_bacnet_iface():
    try:
        rcv = request.get_json()
        ip = rcv.get("ip", None)
        if not isinstance(ip, str):
            return jsonify(dict(err=1, msg="IP必须为字符串", data=False))
        if not re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", ip):
            return jsonify(dict(err=1, msg="IP格式有误", data=False))

        strKey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
        rKey = OpenKey(HKEY_LOCAL_MACHINE, strKey, 0, KEY_WRITE)
        SetValueEx(rKey, "BACNET_IFACE", 0, REG_SZ, ip)
        CloseKey(rKey)

        return jsonify(dict(err=0, msg="设置成功", data=True))
    except Exception as e:
        return jsonify(dict(err=1, msg="设置失败: %s" % e.__str__(), data=False))


@bp_system.route("/monitorResources")
def monitor_resources():
    dInfo = {}
    strMsg = ""

    # 读取当前资源
    memopct = psutil.virtual_memory().percent
    cpupct = psutil.cpu_percent()
    dInfo.update(dict(memoryUsedPercent=memopct, cpuUsedPercent=cpupct))
    driveT = None
    for drive in ["C:\\", "D:\\", "E:\\"]:
        domDir = os.path.join(drive, "dom")
        if os.path.exists(domDir):
            if os.path.exists(os.path.join(domDir, "core", "domcore.exe")):
                driveT = drive
                break

    if driveT != None:
        tmpdict = {}

        pythoncom.CoInitialize()
        c = wmi.WMI()
        for physical_disk in c.Win32_DiskDrive():
            for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                    strDiskName = logical_disk.Caption
                    if strDiskName == driveT.replace("\\", ""):
                        tmpdict["disk"] = logical_disk.Caption
                        tmpdict["total"] = int(logical_disk.Size) / 1024 / 1024 / 1024
                        tmpdict["used"] = (int(logical_disk.Size) - int(logical_disk.FreeSpace)) / 1024 / 1024 / 1024
                        tmpdict["free"] = int(logical_disk.FreeSpace) / 1024 / 1024 / 1024
                        tmpdict["usedPercent"] = round(float(100.0 * (int(logical_disk.Size) - int(logical_disk.FreeSpace)) / int(logical_disk.Size)), 1)
                        break

        dInfo.update(domDriveUsedPercent=tmpdict["usedPercent"], domDriveName=tmpdict["disk"])
    else:
        dInfo.update(domDriveUsedPercent=None, domDriveName=None)
        strMsg += "未发现dom软件安装盘符"

    # 读取进程内存、CPU使用量
    pidNotHandle = list(psutil.process_iter())
    memoInfoList = []
    cpuInfoList = []
    for ps in pidNotHandle:
        name = None
        memopct = None
        cpupct = None
        try:
            name = ps.name()
            memopct = ps.memory_percent()
            cpupct = ps.cpu_percent()
        except Exception as e:
            strMsg += "ERROR in get memopct, cpupct: %s" % e.__str__()

        if name == None:
            continue

        if memopct != None:
            memoInfoList.append(dict(name=name, percent=memopct))

        if cpupct != None:
            cpuInfoList.append(dict(name=name, percent=cpupct))

    lmemo = quick_sort(memoInfoList)
    lcpu = quick_sort(cpuInfoList)

    processMemoPercentList = []
    i = 1
    for item in reversed(lmemo):
        processMemoPercentList.append({"percent": round(item["percent"], 2), "name": item["name"]})
        if i >= 10:
            break
        i += 1

    processCpuPercentList = []
    i = 1
    for item in reversed(lcpu):
        processCpuPercentList.append({"percent": round(item["percent"], 4), "name": item["name"]})
        if i >= 10:
            break
        i += 1

    dInfo.update({"processMemoPercentList": processMemoPercentList, "processCpuPercentList": processCpuPercentList})

    return jsonify(dict(err=0, msg=strMsg, data=dInfo))


@bp_system.route("/diagnosis")
def diagnosis():
    dInfo = {}
    strMsg = ""

    # 读取当前资源
    memopct = psutil.virtual_memory().percent
    cpupct = psutil.cpu_percent()
    dInfo.update(dict(memoryUsedPercent=memopct, cpuUsedPercent=cpupct))
    driveT = None
    for drive in ["C:\\", "D:\\", "E:\\"]:
        domDir = os.path.join(drive, "dom")
        if os.path.exists(domDir):
            if os.path.exists(os.path.join(domDir, "core", "domcore.exe")):
                driveT = drive
                break

    if driveT != None:
        tmpdict = {}

        pythoncom.CoInitialize()
        c = wmi.WMI()
        for physical_disk in c.Win32_DiskDrive():
            for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                    strDiskName = logical_disk.Caption
                    if strDiskName == driveT.replace("\\", ""):
                        tmpdict["disk"] = logical_disk.Caption
                        tmpdict["total"] = int(logical_disk.Size) / 1024 / 1024 / 1024
                        tmpdict["used"] = (int(logical_disk.Size) - int(logical_disk.FreeSpace)) / 1024 / 1024 / 1024
                        tmpdict["free"] = int(logical_disk.FreeSpace) / 1024 / 1024 / 1024
                        tmpdict["usedPercent"] = round(float(100.0 * (int(logical_disk.Size) - int(logical_disk.FreeSpace)) / int(logical_disk.Size)), 1)
                        break

        dInfo.update(domDriveUsedPercent=tmpdict["usedPercent"], domDriveName=tmpdict["disk"])
    else:
        dInfo.update(domDriveUsedPercent=None, domDriveName=None)
        strMsg += "未发现dom软件安装盘符"

    # 读取进程内存、CPU使用量
    pidNotHandle = list(psutil.process_iter())
    memoInfoList = []
    cpuInfoList = []
    for ps in pidNotHandle:
        name = None
        memopct = None
        cpupct = None
        try:
            name = ps.name()
            memopct = ps.memory_percent()
            cpupct = ps.cpu_percent()
        except Exception as e:
            strMsg += "ERROR in get memopct, cpupct: %s" % e.__str__()

        if name == None:
            continue

        if memopct != None:
            memoInfoList.append(dict(name=name, percent=memopct))

        if cpupct != None:
            cpuInfoList.append(dict(name=name, percent=cpupct))

    lmemo = quick_sort(memoInfoList)
    lcpu = quick_sort(cpuInfoList)

    processMemoPercentList = []
    i = 1
    for item in reversed(lmemo):
        processMemoPercentList.append({"percent": round(item["percent"], 2), "name": item["name"]})
        if i >= 10:
            break
        i += 1

    processCpuPercentList = []
    i = 1
    for item in reversed(lcpu):
        processCpuPercentList.append({"percent": round(item["percent"], 4), "name": item["name"]})
        if i >= 10:
            break
        i += 1

    dInfo.update({"processMemoPercentList": processMemoPercentList, "processCpuPercentList": processCpuPercentList})

    faultInfoList = []

    # 进程频繁重启诊断
    criticalFilePath = os.path.join(app.config["CORE_PATH"], "log", "CRITICAL.txt")
    if os.path.exists(criticalFilePath):
        diag = ServerDiagnosis(criticalFilePath)
        faultInfoList.extend(diag.diagnose())

    # dom所在磁盘使用量诊断
    if isinstance(dInfo.get("domDriveUsedPercent"), float) or isinstance(dInfo.get("domDriveUsedPercent"), int):
        if dInfo.get("domDriveUsedPercent") > 90:
            faultInfoList.append(dict(title="dom所在磁盘已被占用90%以上", detail="dom所在磁盘已被占用{n}%".format(n=dInfo.get("domDriveUsedPercent"))))

    # 进程升级问题诊断
    updateErrPath = os.path.join(app.config["CORE_PATH"], "domUpdate", "err.json")
    if os.path.exists(updateErrPath):
        with open(updateErrPath, encoding="UTF8", errors="ignore") as fo:
            try:
                dJson = json.load(fo)
            except:
                dJson = {}

            if isinstance(dJson, dict):
                for procName, dUpdateErrDetail in dJson.items():
                    for strTime, dErrDetail in dUpdateErrDetail.items():
                        faultInfoList.append(dict(title="{procName}在{time}执行升级时出现问题".format(procName=procName, time=datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")),
                                                  detail=dErrDetail.get("err", "")))

    # dompysite和domModbusClientCore版本不匹配诊断
    nDompysiteVersion = convert_version(siteVersion.getCurrentVersion())
    nDomModbusClientCoreVersion = convert_version(RedisManager.get("VersionDomModbusClientCore"))

    if isinstance(nDompysiteVersion, int) and isinstance(nDomModbusClientCoreVersion, int):
        if nDompysiteVersion >= convert_version("0.13.9") and nDomModbusClientCoreVersion < convert_version("0.3.14"):
            faultInfoList.append(dict(title="domModbusClientCore版本过低",
                                      detail="domModbusClientCore需要升级以适配最新的通讯类设备读取机制"))

    return jsonify(dict(err=1 if len(strMsg) else 0, msg=strMsg, data=faultInfoList))


@bp_system.route("/uploadModuleZip", methods=["POST"])
def upload_module_zip():
    file = request.files.get("file")

    try:
        if file == None:
            return jsonify(dict(err=1, msg="zip文件不能为空", data=False))

        if not file.filename.endswith(".zip"):
            return jsonify(dict(err=1, msg="只支持.zip格式文件", data=False))

        tempDir = os.path.join(app.static_folder, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        # 暂存
        fileNameWithExt = file.filename
        fileName = os.path.splitext(fileNameWithExt)[0]
        tempSaveFilePath = os.path.join(tempDir, fileNameWithExt)
        if os.path.exists(tempSaveFilePath):
            try:
                os.remove(tempSaveFilePath)
                shutil.rmtree(os.path.join(tempDir, fileName))
            except:
                jsonify(dict(err=1, msg="内部错误：删除过期文件%s失败" % fileNameWithExt, data=False))
        file.save(tempSaveFilePath)

        # 解压
        unzipDestDir = os.path.join(tempDir, fileName)
        if os.path.exists(unzipDestDir):
            try:
                shutil.rmtree(unzipDestDir)
            except:
                jsonify(dict(err=1, msg="内部错误：删除过期文件夹失败", data=False))
        os.mkdir(unzipDestDir)
        unzip_file(tempSaveFilePath, tempDir)

        # 寻找exe文件
        exeFileNameWithExt = get_exe_file_name(unzipDestDir)
        exeFileName = os.path.splitext(exeFileNameWithExt)[0]
        if exeFileNameWithExt == None:
            return jsonify(dict(err=1, msg="上传的zip包中未发现exe文件，停止部署", data=False))

        # 设置暂缓
        dAll = RedisManager.get("pause_host_config")
        if not isinstance(dAll, dict):
            dAll = {}

        processName = exeFileNameWithExt.replace(".exe", "")
        dProcessInfo = dAll.get(processName, {})
        if not isinstance(dProcessInfo, dict):
            dProcessInfo = {}

        tPauseTo = datetime.now() + timedelta(hours=1)
        strPauseToTime = tPauseTo.strftime("%Y-%m-%d %H:%M:%S")
        dProcessInfo.update({"pauseTo": strPauseToTime})

        dAll.update({processName: dProcessInfo})
        RedisManager.set("pause_host_config", dAll)

        # 停止在运行的进程（如果在运行）
        bKilled = False
        nCount = 0
        while nCount <= 5:
            if ProcessManager.getInstance().findProcess(exeFileNameWithExt):
                ProcessManager.getInstance().killProcess(exeFileNameWithExt)
            else:
                bKilled = True
                break
            time.sleep(1)
            nCount += 1

        if not bKilled:
            return jsonify(dict(err=1, msg="kill正在运行的进程:%s 失败" % exeFileNameWithExt, data=False))

        # 覆盖进程文件夹
        existingExeFolderDir = os.path.join(app.config["CORE_PATH"], exeFileName)
        if os.path.exists(existingExeFolderDir):
            try:
                shutil.rmtree(existingExeFolderDir)
            except Exception as e:
                jsonify(dict(err=1, msg="删除core目录下既有的进程文件夹(%s)失败: %s" % (existingExeFolderDir, e.__str__())))

        # os.mkdir(existingExeFolderDir)

        trueSourceDir = find_out_true_src_dir(unzipDestDir, exeFileName)
        if trueSourceDir == None:
            jsonify(dict(err=1, msg="进程待复制根目录寻找失败", data=False))

        bSucCopy = copy_tree(trueSourceDir, existingExeFolderDir)
        if not bSucCopy:
            jsonify(dict(err=1, msg="复制进程文件夹工程失败", data=False))

        # 去除暂缓
        dAll = RedisManager.get("pause_host_config")
        if not isinstance(dAll, dict):
            dAll = {}

        if processName in dAll.keys():
            del dAll[processName]

        RedisManager.set("pause_host_config", dAll)

        # 添加驻守并启动
        BEOPDataAccess.getInstance().addProcessByName(exeFileName, exeFileNameWithExt, "hostprocess", "")
        ProcessManager.getInstance().startProcess(exeFileNameWithExt, os.path.join(app.config["CORE_PATH"], exeFileName))

        try:
            shutil.rmtree(unzipDestDir)
            os.remove(tempSaveFilePath)
        except:
            pass

        return jsonify(dict(err=0, msg="上传成功", data=True))

    except Exception as e:
        return jsonify(dict(err=1, msg="ERROR in /system/uploadModuleZip: %s" % e.__str__(), data=False))



@bp_system.route("/configRemoteAccess", methods=["POST"])
def config_remove_access():
    rcv = request.get_json()
    if rcv == None:
        rcv = {}

    projId = rcv.get("projId", None)
    nOnOffSetting = rcv.get("OnOffSetting", 1)   # 0-关  1-开

    if not isinstance(projId, str):
        return jsonify(dict(err=1, msg="项目ID必须为字符串", data=False))

    if not len(projId):
        return jsonify(dict(err=1, msg="项目ID不能为空", data=False))

    if not is_int_digit(nOnOffSetting):
        nOnOffSetting = 1
    else:
        nOnOffSetting = int(nOnOffSetting)

    if nOnOffSetting not in [0, 1]:
        nOnOffSetting = 1

    domFRPCDir = os.path.join(app.config["CORE_PATH"], "domFRPC")
    if not os.path.exists(domFRPCDir):
        return jsonify(dict(err=1, msg="domFRPC不存在于core文件夹下", data=False))

    frpcLogFilePath = os.path.join(app.config["CORE_PATH"], "domfrpc", "frpc.log")
    frpcIniFilePath = os.path.join(app.config["CORE_PATH"], "domfrpc", "frpc.ini")
    frpcLogFilePath = frpcLogFilePath.replace("\\", "\\\\")

    # 若指令为关闭则传入###
    obj = projId if nOnOffSetting == 1 else "###"
    bSuc, msg, origProjIdTempFileName = edit_frpc_config_file(frpcIniFilePath, frpcLogFilePath, obj)
    if not bSuc:
        return jsonify(dict(err=1, msg=msg, data=False))

    if nOnOffSetting == 1:
        process_restart_domfrpc()
    else:
        kill_domfrpc()

    nCount = 0
    bStarted = False
    while nCount <= 10:
        try:
            if nOnOffSetting == 1:
                if ProcessManager.getInstance().findProcess("domFRPC.exe"):
                    bStarted = True
                    break
            elif nOnOffSetting == 0:
                if not ProcessManager.getInstance().findProcess("domFRPC.exe"):
                    break
        except:
            pass

        nCount += 1
        time.sleep(0.2)

    # 若指令为开启domFRPC且domFRPC没有在正常运行
    if not bStarted and nOnOffSetting == 1:
        if origProjIdTempFileName != None:
            lastProjId = get_last_proj_id(origProjIdTempFileName)
            if lastProjId != None and isinstance(lastProjId, str) and len(lastProjId):
                edit_frpc_config_file(frpcIniFilePath, frpcLogFilePath, lastProjId)
                process_restart_domfrpc()
                return jsonify(dict(err=1, msg="项目ID修改为{id}后domfrpc.exe未启动，已恢复原来的设置({originalId})".format(id=projId, originalId=lastProjId), data=False))

        return jsonify(dict(err=1, msg="项目ID修改为{id}后domfrpc.exe未启动，因修改前domfrpc中未配置任何有效项目id，则没有执行恢复操作".format(id=projId), data=False))


    if nOnOffSetting == 1:
        nStatusCode, strInfo = analysis_if_domfrpc_is_normally_running(projId, frpcLogFilePath)

        if nStatusCode != 1:
            lastProjId = get_last_proj_id(origProjIdTempFileName)
            if lastProjId != None and isinstance(lastProjId, str) and len(lastProjId):
                edit_frpc_config_file(frpcIniFilePath, frpcLogFilePath, lastProjId)
                process_restart_domfrpc()
                return jsonify(dict(err=1, msg="项目ID修改为{id}后检测到domfrpc.exe运行不正常，原因:{strInfo}。已恢复原来的设置({originalId})".format(id=projId, originalId=lastProjId, strInfo=strInfo), data=False))
            return jsonify(dict(err=1, msg="项目ID修改为{id}后检测到domfrpc.exe运行不正常，原因:{strInfo}。因修改前domfrpc中未配置任何有效项目id，则没有执行恢复操作".format(id=projId, strInfo=strInfo), data=False))

    if origProjIdTempFileName:
        remove_temporary_json_file(origProjIdTempFileName)

    # 打开远程桌面
    make_bat_and_run('@echo off\nreg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f')

    # 开启防火墙
    make_bat_and_run("@echo off\nnetsh advfirewall set allprofiles state on\n")

    # 入站规则加入5000端口   需要先检查入站规则池中是否已存在该设置
    # make_bat_and_run("@echo off\nnetsh advfirewall firewall add rule name='dompysite' dir=in action=allow protocol=tcp localport=5000\n")

    return jsonify(dict(err=0, msg="设置成功", data=True))


@bp_system.route("/getDomFrpcCurrentConfig")
def get_domfrpc_current_config():
    domFrpcDir = os.path.join(app.config["CORE_PATH"], "domFRPC")
    if not os.path.exists(domFrpcDir):
        return jsonify(dict(err=1, msg="domFRPC路径不存在", data={}))

    frpcIniFilePath = os.path.join(domFrpcDir, "frpc.ini")
    if not os.path.exists(frpcIniFilePath):
        return jsonify(dict(err=1, msg="frpc.ini不存在", data={}))

    dRes, msg = get_config_from_frpc_ini(frpcIniFilePath)

    bIsRunning = False
    if ProcessManager.getInstance().findProcess("domFRPC.exe"):
        bIsRunning = True

    dRes.update({"running": bIsRunning})

    return jsonify(dict(err=0, msg=msg, data=dRes))


@bp_system.route("/pauseProcess", methods=["POST"])
def pause_process():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}
    processName = rcv.get("processName", None)
    strPauseToTime = rcv.get("pauseToTime", None)

    if not isinstance(processName, str):
        return jsonify(dict(err=1, msg="进程名称不能为空", data=False))
    if not len(processName):
        return jsonify(dict(err=1, msg="进程名称不能为空", data=False))
    if processName.endswith(".exe"):
        processName = processName.replace(".exe", "")

    if not isinstance(strPauseToTime, str):
        return jsonify(dict(err=1, msg="暂缓至时间不能为空", data=False))
    if not len(strPauseToTime):
        return jsonify(dict(err=1, msg="暂缓至时间不能为空", data=False))
    if not is_time_string(strPauseToTime, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="暂缓至时间格式有误(yyyy-mm-dd HH:MM:SS)", data=False))

    if datetime.strptime(strPauseToTime, "%Y-%m-%d %H:%M:%S") <= datetime.now():
        return jsonify(dict(err=1, msg="暂缓至时间不能小于当前时间", data=False))

    dAll = RedisManager.get("pause_host_config")
    if not isinstance(dAll, dict):
        dAll = {}

    dProcessInfo = dAll.get(processName, {})
    if not isinstance(dProcessInfo, dict):
        dProcessInfo = {}

    dProcessInfo.update({"pauseTo": strPauseToTime})

    dAll.update({processName: dProcessInfo})
    RedisManager.set("pause_host_config", dAll)

    nCount = 0
    bKilled = False
    while nCount < 5:
        ProcessManager.getInstance().killProcess("{proc}.exe".format(proc=processName))
        time.sleep(0.5)
        if not ProcessManager.getInstance().findProcess("{proc}.exe".format(proc=processName)):
            bKilled = True
            break

        nCount += 1
        time.sleep(0.5)

    if bKilled:
        return jsonify(dict(err=0, msg="暂缓{processName}成功".format(processName=processName), data=True))
    return jsonify(dict(err=1, msg="暂缓{processName}失败".format(processName=processName), data=False))

@bp_system.route("/removeProcessPause", methods=["POST"])
def remove_process_pause():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}
    processName = rcv.get("processName", None)

    if not isinstance(processName, str):
        return jsonify(dict(err=1, msg="进程名称不能为空", data=False))
    if not len(processName):
        return jsonify(dict(err=1, msg="进程名称不能为空", data=False))
    if processName.endswith(".exe"):
        processName = processName.replace(".exe", "")

    dAll = RedisManager.get("pause_host_config")
    if not isinstance(dAll, dict):
        dAll = {}

    if processName in dAll.keys():
        del dAll[processName]

    RedisManager.set("pause_host_config", dAll)

    return jsonify(dict(err=0, msg="清除成功", data=True))


@bp_system.route("/getBacnetCoreConfig", methods=["POST"])
def get_bacnetcore_config():
    dMap = {0: "domBacnetCore",
            1: "domBacnetCore1",
            2: "domBacnetCore2",
            3: "domBacnetCore3",
            4: "domBacnetCore4",
            5: "domBacnetCore5"}

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nProcNum = rcv.get("num", None)
    if nProcNum not in [0, 1, 2, 3, 4, 5]:
        return jsonify(dict(err=1, msg="进程序号必须为整数且为0,1,2,3,4,5中的一个", data=""))

    procName = dMap.get(nProcNum)

    procDir = os.path.join(app.config["CORE_PATH"], procName)
    if not os.path.exists(procDir):
        tempDir = os.path.join(app.static_folder, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        osstool = OSSTool()
        lfPath = os.path.join(tempDir, "{procName}_{time}.zip".format(procName=procName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
        if os.path.exists(lfPath):
            try:
                os.remove(lfPath)
            except:
                pass

        bSuc = osstool.download("update/domBacnetCore.zip", lfPath)
        if not bSuc or not os.path.exists(lfPath):
            return jsonify(dict(err=1, msg="{procName}在本地磁盘不存在，从云端下载失败".format(procName=procName)))

        unzipDestDir = os.path.join(tempDir, "domBacnetCore")
        if os.path.exists(unzipDestDir):
            try:
                shutil.rmtree(unzipDestDir)
            except:
                return jsonify(dict(err=1, msg="服务器磁盘上无{procName}，清除之前的下载残留失败".format(procName=procName), data=""))

        os.mkdir(unzipDestDir)

        unzip_file(lfPath, unzipDestDir)

        try:
            os.remove(lfPath)
        except:
            pass

        targetDir = os.path.join(unzipDestDir, "domBacnetCore")
        targetExePath = os.path.join(targetDir, "domBacnetCore.exe")
        if not os.path.exists(targetExePath):
            return jsonify(dict(err=1, msg="下载解压后的进程文件夹中未发现domBacnetCore.exe", data=""))

        os.rename(os.path.join(targetDir, "domBacnetCore.exe"),
                  os.path.join(targetDir, "{name}.exe".format(name=procName)))
        os.rename(targetDir, os.path.join(unzipDestDir, procName))

        copy_tree(os.path.join(unzipDestDir, procName),
                  os.path.join(app.config["CORE_PATH"], procName))

        try:
            shutil.rmtree(unzipDestDir)
        except:
            pass

    configIniPath = os.path.join(procDir, "config.ini")
    if not os.path.exists(configIniPath):
        strContent = "[mysql]\ndbip = 127.0.0.1\n\n[bacnet]\nBacnetMultiRead = 50\nBacnetMultiWrite = 20\nBacnetPoolInterval = 2\n" \
                     "BacnetCmdInterval = 0.3\nBacnetTimeOut = 10\nBacnetRetries = 0\nBacnetPriority = 1\nPointFilterIP=10.209.208.13\n\n" \
                     "[data]\nupdaterealinterval = 2\nupdatewriteinterval = 2\ndecimal = 2\nerrorflag = 10\n"

        with open(configIniPath, "w+", encoding="UTF8", errors="ignore") as fo:
            fo.write(strContent)

        return jsonify(dict(err=0, msg="", data=strContent))

    else:
        with open(configIniPath, "r", encoding="UTF8", errors="ignore") as fo:
            strContent = fo.read()
            return jsonify(dict(err=0, msg="", data=strContent))


@bp_system.route("/setBacnetCoreConfig", methods=["POST"])
def set_bacnetcore_config():
    dMap = {0: "domBacnetCore",
            1: "domBacnetCore1",
            2: "domBacnetCore2",
            3: "domBacnetCore3",
            4: "domBacnetCore4",
            5: "domBacnetCore5"}

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nProcNum = rcv.get("num", None)
    if nProcNum not in [0, 1, 2, 3, 4, 5]:
        return jsonify(dict(err=1, msg="进程序号必须为整数且为0,1,2,3,4,5中的一个", data=""))

    strContent = rcv.get("content", None)
    if not isinstance(strContent, str):
        return jsonify(dict(err=1, msg="输入内容不能为空", data=""))
    if not len(strContent):
        return jsonify(dict(err=1, msg="输入内容不能为空", data=""))

    procName = dMap.get(nProcNum)
    procDir = os.path.join(app.config["CORE_PATH"], procName)
    if not os.path.exists(procDir):
        tempDir = os.path.join(app.static_folder, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        osstool = OSSTool()
        lfPath = os.path.join(tempDir, "{procName}_{time}.zip".format(procName=procName, time=datetime.now().strftime(
            "%Y-%m-%d-%H-%M-%S-%f")))
        if os.path.exists(lfPath):
            try:
                os.remove(lfPath)
            except:
                pass

        bSuc = osstool.download("update/domBacnetCore.zip", lfPath)
        if not bSuc or not os.path.exists(lfPath):
            return jsonify(dict(err=1, msg="{procName}在本地磁盘不存在，从云端下载失败".format(procName=procName)))

        unzipDestDir = os.path.join(tempDir, "domBacnetCore")
        if os.path.exists(unzipDestDir):
            try:
                shutil.rmtree(unzipDestDir)
            except:
                return jsonify(dict(err=1, msg="服务器磁盘上无{procName}，清除之前的下载残留失败".format(procName=procName), data=""))

        os.mkdir(unzipDestDir)

        unzip_file(lfPath, unzipDestDir)

        try:
            os.remove(lfPath)
        except:
            pass

        targetDir = os.path.join(unzipDestDir, "domBacnetCore")
        targetExePath = os.path.join(targetDir, "domBacnetCore.exe")
        if not os.path.exists(targetExePath):
            return jsonify(dict(err=1, msg="下载解压后的进程文件夹中未发现domBacnetCore.exe", data=""))

        os.rename(os.path.join(targetDir, "domBacnetCore.exe"),
                  os.path.join(targetDir, "{name}.exe".format(name=procName)))
        os.rename(targetDir, os.path.join(unzipDestDir, procName))

        copy_tree(os.path.join(unzipDestDir, procName),
                  os.path.join(app.config["CORE_PATH"], procName))

        try:
            shutil.rmtree(unzipDestDir)
        except:
            pass

    configIniPath = os.path.join(app.config["CORE_PATH"], procName, "config.ini")
    if os.path.exists(configIniPath):
        try:
            os.remove(configIniPath)
        except:
            return jsonify(dict(err=1, msg="删除config.ini失败", data=False))

    with open(configIniPath, "w", encoding="UTF8", errors="ignore") as fo:
        fo.write(strContent)

    return jsonify(dict(err=0, msg="设置成功", data=True))

@bp_system.route("/getMysqlBackupConfig")
def get_mysql_backup_config():

    dDriveInfo = get_drive_info()

    # domBackupMysql不存在则建立
    domBackupMysqlDir = os.path.join(app.config["CORE_PATH"], "domBackupMysql")
    if not os.path.exists(domBackupMysqlDir):
        tempDir = os.path.join(app.static_folder, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        osstool = OSSTool()
        lfPath = os.path.join(tempDir, "domBackupMysql_{time}.zip".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
        if os.path.exists(lfPath):
            try:
                os.remove(lfPath)
            except:
                pass

        bSuc = osstool.download("update/domBackupMysql.zip", lfPath)
        if not bSuc or not os.path.exists(lfPath):
            return jsonify(dict(err=1, msg="domBackupMysql在本地磁盘不存在，从云端下载失败", data=False))

        unzipDestDir = os.path.join(tempDir, "domBackupMysql")
        if os.path.exists(unzipDestDir):
            try:
                shutil.rmtree(unzipDestDir)
            except:
                return jsonify(dict(err=1, msg="服务器磁盘上无domBackupMysql，下载前清除之前的下载残留失败", data=False))

        os.mkdir(unzipDestDir)

        unzip_file(lfPath, unzipDestDir)

        try:
            os.remove(lfPath)
        except:
            pass

        targetDir = os.path.join(unzipDestDir, "domBackupMysql")
        targetExePath = os.path.join(targetDir, "domBackupMysql.exe")
        if not os.path.exists(targetExePath):
            return jsonify(dict(err=1, msg="下载解压后的进程文件夹中未发现domBackupMysql.exe", data=False))

        copy_tree(os.path.join(unzipDestDir, "domBackupMysql"),
                  os.path.join(app.config["CORE_PATH"], "domBackupMysql"))

        try:
            shutil.rmtree(unzipDestDir)
        except:
            pass

    configIniPath = os.path.join(app.config["CORE_PATH"], "domBackupMysql", "config.ini")
    conf = MyConf()
    if not os.path.exists(configIniPath):  # 不存在则建立
        with open(configIniPath, "w+", encoding="UTF8", errors="ignore") as oFile:
            conf.write(oFile)

        if not conf.has_section("info"):
            conf.add_section("info")

        conf["info"].update({"enable": "1"})
        conf["info"].update({"cloudenable": "1"})
        conf["info"].update({"localbackup": "1"})
        conf["info"].update({"localbackupdir": os.path.join(app.config["CORE_PATH"], "mysqlLocalBackup")})

        with open(configIniPath, "w", encoding="UTF8", errors="ignore") as oFile:
            conf.write(oFile)

    conf.read(configIniPath)
    if not conf.has_section("info"):
        conf.add_section("info")

    if not conf.has_option("info", "enable"):
        conf["info"].update({"enable": "1"})
    if not conf.has_option("info", "cloudenable"):
        conf["info"].update({"cloudenable": "1"})
    if not conf.has_option("info", "localbackup"):
        conf["info"].update({"localbackup": "1"})
    if not conf.has_option("info", "localbackupdir"):
        conf["info"].update({"localbackupdir": os.path.join(app.config["CORE_PATH"], "mysqlLocalBackup")})

    try:
        nCloudEnable = int(conf["info"]["cloudenable"])
    except:
        nCloudEnable = conf["info"]["cloudenable"]

    try:
        nLocalEnable = int(conf["info"]["localbackup"])
    except:
        nLocalEnable = conf["info"]["localbackup"]

    localBackupDir = conf["info"]["localbackupdir"]

    localBackupDir = localBackupDir.replace("\\\\", "\\")

    return jsonify(dict(err=0, msg="", data={"enableCloudBackup": nCloudEnable,
                                             "enableLocalBackup": nLocalEnable,
                                             "localBackupDirectory": localBackupDir,
                                             "disk": dDriveInfo}))


@bp_system.route("/setMysqlBackupConfig", methods=["POST"])
def set_mysql_backup_config():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nEnableCloudBackup = rcv.get("enableCloudBackup", None)
    nEnableLocalBackuop = rcv.get("enableLocalBackup", None)
    localBackupDirectory = rcv.get("localBackupDirectory", None)

    if nEnableCloudBackup != None:
        if nEnableCloudBackup not in [0, 1]:
            return jsonify(dict(err=1, msg="是否启用mysql云端备份必须为0或1", data=False))

    if nEnableLocalBackuop != None:
        if nEnableLocalBackuop not in [0, 1]:
            return jsonify(dict(err=1, msg="是否启用mysql本地备份必须为0或1", data=False))

    if localBackupDirectory != None:
        if not isinstance(localBackupDirectory, str):
            return jsonify(dict(err=1, msg="mysql本地备份路径必须为字符串", data=False))

    strFullLocalBackupDirectory = None  # 完整的本地备份路径
    if localBackupDirectory != None:
        # 完整的本地备份路径、路径是否只有盘符、报错信息返回
        strFullLocalBackupDirectory, bOnlyDrive, msg = analysis_directory(localBackupDirectory)
        if strFullLocalBackupDirectory == None:
            return jsonify(dict(err=1, msg=msg, data=False))

        if msg:
            return jsonify(dict(err=1, msg=msg, data=False))

        # 如果是只是盘符则加上 mysqlLocalBackup ，补全路径
        if bOnlyDrive:
            strFullLocalBackupDirectory = os.path.join(strFullLocalBackupDirectory, "mysqlLocalBackup")

        # 检查路径是否存在若不存在则建立文件夹
        partList = list(pathlib.Path(strFullLocalBackupDirectory).parts)

        strTempDir = partList[0]
        for idx, part in enumerate(partList):
            if idx == 0:
                continue

            strTempDir = os.path.join(strTempDir, part)
            if not os.path.exists(strTempDir):
                os.mkdir(strTempDir)

    if nEnableCloudBackup == None and nEnableLocalBackuop == None and localBackupDirectory == None:
        return jsonify(dict(err=1, msg="未发现修改项", data=False))

    domBackupMysqlDir = os.path.join(app.config["CORE_PATH"], "domBackupMysql")
    if not os.path.exists(domBackupMysqlDir):
        tempDir = os.path.join(app.static_folder, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        osstool = OSSTool()
        lfPath = os.path.join(tempDir, "domBackupMysql_{time}.zip".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
        if os.path.exists(lfPath):
            try:
                os.remove(lfPath)
            except:
                pass

        bSuc = osstool.download("update/domBackupMysql.zip", lfPath)
        if not bSuc or not os.path.exists(lfPath):
            return jsonify(dict(err=1, msg="domBackupMysql在本地磁盘不存在，从云端下载失败", data=False))

        unzipDestDir = os.path.join(tempDir, "domBackupMysql")
        if os.path.exists(unzipDestDir):
            try:
                shutil.rmtree(unzipDestDir)
            except:
                return jsonify(dict(err=1, msg="服务器磁盘上无domBackupMysql，下载前清除之前的下载残留失败", data=False))

        os.mkdir(unzipDestDir)

        unzip_file(lfPath, unzipDestDir)

        try:
            os.remove(lfPath)
        except:
            pass

        targetDir = os.path.join(unzipDestDir, "domBackupMysql")
        targetExePath = os.path.join(targetDir, "domBackupMysql.exe")
        if not os.path.exists(targetExePath):
            return jsonify(dict(err=1, msg="下载解压后的进程文件夹中未发现domBackupMysql.exe", data=False))

        copy_tree(os.path.join(unzipDestDir, "domBackupMysql"),
                  os.path.join(app.config["CORE_PATH"], "domBackupMysql"))

        try:
            shutil.rmtree(unzipDestDir)
        except:
            pass

    configIniPath = os.path.join(app.config["CORE_PATH"], "domBackupMysql", "config.ini")
    conf = MyConf()
    if not os.path.exists(configIniPath): # 不存在则建立
        with open(configIniPath, "w+", encoding="UTF8", errors="ignore") as oFile:
            conf.write(oFile)

        if not conf.has_section("info"):
            conf.add_section("info")

        conf["info"].update({"cloudenable": str(nEnableCloudBackup) if nEnableCloudBackup != None else "1"})
        conf["info"].update({"localbackup": str(nEnableLocalBackuop) if nEnableLocalBackuop != None else "1"})
        conf["info"].update({"localbackupdir": os.path.join(app.config["CORE_PATH"], "mysqlLocalBackup") if strFullLocalBackupDirectory == None else strFullLocalBackupDirectory})

        with open(configIniPath, "w", encoding="UTF8", errors="ignore") as oFile:
            conf.write(oFile)

    else:
        conf.read(configIniPath)
        if not conf.has_section("info"):
            conf.add_section("info")

        if nEnableCloudBackup != None:
            conf["info"].update({"cloudenable": str(nEnableCloudBackup)})

        if nEnableLocalBackuop != None:
            conf["info"].update({"localbackup": str(nEnableLocalBackuop)})

        if strFullLocalBackupDirectory != None:
            conf["info"].update({"localbackupdir": strFullLocalBackupDirectory})

        with open(configIniPath, "w", encoding="UTF8", errors="ignore") as oFile:
            conf.write(oFile)

    return jsonify(dict(err=0, msg="设置成功", data=True))


@bp_system.route("/getDisplayManage")
def get_display_manage():
    res = BEOPSqliteAccess.getInstance().getDisplayManage()
    return jsonify(res)


@bp_system.route("/setDisplayManage", methods=["POST"])
def set_display_manage():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    enableSecondaryNaviMenu = rcv.get("enableSecondaryNaviMenu", 0)
    rememberPassword = rcv.get("rememberPassword", 0)
    nAutoLogoutTimeout = rcv.get("nAutoLogoutTimeout", 0)

    if not isinstance(nAutoLogoutTimeout, int):
        return jsonify(dict(err=1, msg="超时无操作则自动退出分钟数必须为正整数", data=False))
    if nAutoLogoutTimeout < 0:
        return jsonify(dict(err=1, msg="超时无操作则自动退出分钟数必须为正整数", data=False))

    if enableSecondaryNaviMenu not in [True, False, 1, 0, "0", "1"]:
        return jsonify(dict(err=1, msg="是否启用二级菜单导航必须为True, False 或 0， 1", data=False))

    if rememberPassword not in [True, False, 1, 0, "0", "1"]:
        return jsonify(dict(err=1, msg="是否记住密码必须为True, False 或 0， 1", data=False))

    bEnableNaviSecondryMenu = True if enableSecondaryNaviMenu in [True, 1, "1"] else False
    bRememberPassword = True if rememberPassword in [True, "1", 1] else False

    bSuc = BEOPSqliteAccess.getInstance().setDisplayManage(bEnableNaviSecondryMenu, bRememberPassword, nAutoLogoutTimeout)
    return jsonify(dict(err=0, msg="", data=bSuc))


@bp_system.route("/ProcessLogOnOffSet", methods=["POST"])
def process_log_onoff_set():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    processName = rcv.get("processName", None)
    nOnOffSetOrStrLevel = rcv.get("onoffSetOrLevel", None)
    if not isinstance(processName, str):
        return jsonify(dict(err=1, msg="进程名不能为空", data=False))
    if not len(processName):
        return jsonify(dict(err=1, msg="进程名不能为空", data=False))

    logLevelList = ["ERROR", "WARNING", "CRITICAL", "INFO", "DEBUG"]
    if nOnOffSetOrStrLevel not in [0, 1] and not isinstance(nOnOffSetOrStrLevel, str):
        return jsonify(dict(err=1, msg="log执行动作必须为0或1或代表log设置等级的字符串", data=False))

    if isinstance(nOnOffSetOrStrLevel, str):
        if nOnOffSetOrStrLevel not in logLevelList:
            return jsonify(dict(err=1, msg="log设置等级仅支持：{lvl}".format(lvl=",".join(logLevelList)), data=False))

    if processName.endswith(".exe"):
        processName = processName.replace(".exe", "")

    procDir = os.path.join(app.config["CORE_PATH"], processName.lower())
    if not os.path.exists(procDir):
        return jsonify(dict(err=1, msg="该进程不存在", data=False))

    conf = MyConf()
    configFilePath = os.path.join(procDir, "config.ini")

    strToSetLevel = "ERROR"
    if nOnOffSetOrStrLevel == 0:
        strToSetLevel = "CRITICAL"
    elif nOnOffSetOrStrLevel == 1:
        strToSetLevel = "ERROR"
    elif isinstance(nOnOffSetOrStrLevel, str):
        strToSetLevel = nOnOffSetOrStrLevel

    if not os.path.exists(configFilePath):
        with open(configFilePath, "w+", encoding="UTF8", errors="ignore") as fo:
            conf.write(fo)

    conf.read(configFilePath)
    if not conf.has_section("log"):
        conf.add_section("log")
    if not conf.has_option("log", "level"):
        conf["log"].update({"level": strToSetLevel})

    conf["log"].update({"level": strToSetLevel})
    with open(configFilePath, "w") as file:
        conf.write(file)

    procNameWithCapital = get_process_name_with_capital(processName)

    restart_process(procNameWithCapital)

    return jsonify(dict(err=0, msg="设置成功", data=True))

@bp_system.route("/getProcessLogOnOff", methods=["POST"])
def get_process_log_onoff():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    processName = rcv.get("processName", None)
    if processName != None:
        if not isinstance(processName, str):
            return jsonify(dict(err=1, msg="进程名必须为字符串", data=[]))
        if not len(processName):
            return jsonify(dict(err=1, msg="进程名不能为空", data=[]))

    dAllProc = {}
    for item in allProcList:
        name = item.get("name", "").lower()
        if not name:
            continue

        dAllProc.update({name: {"nameWithCapital": item.get("name"),
                                "logOpType": item.get("logOpType", 0)}})


    if processName:
        conf = MyConf()
        if not dAllProc.get(processName.lower(), None):
            return jsonify(dict(err=1, msg="未知进程名", data=[]))


        nLogType = dAllProc.get(processName.lower()).get("logOpType", 0)
        if nLogType == 0:
            return jsonify(dict(err=1, msg="无法通过控制config.ini操作日志开关状态，故无法判断日志开关状态", data=[]))

        procDir = os.path.join(app.config["CORE_PATH"], dAllProc.get(processName.lower()).get("nameWithCapital", ""))
        if not os.path.exists(procDir):
            return jsonify(dict(err=1, msg="服务器core路径下未发现该进程文件夹", data=[]))

        nLogOnOff = 1
        configPath = os.path.join(procDir, "config.ini")
        if os.path.exists(configPath):
            conf.read(configPath)
            if conf.has_section("log"):
                if conf.has_option("log", "level"):
                    if conf["log"]["level"] == "CRITICAL":
                        nLogOnOff = 0

        return jsonify(dict(err=0, msg="", data=[{"processName": dAllProc.get(processName.lower()).get("nameWithCapital", ""),
                                                  "logOnOff": nLogOnOff}]))


    resList = []
    for nameLower, dProcInfo in dAllProc.items():
        if dProcInfo.get("logOpType", 0) == 0:
            continue

        procDir = os.path.join(app.config["CORE_PATH"], dProcInfo.get("nameWithCapital", ""))
        if not os.path.exists(procDir):
            continue

        conf = MyConf()
        nLogOnOff = 1
        configPath = os.path.join(procDir, "config.ini")
        if os.path.exists(configPath):
            conf.read(configPath)
            if conf.has_section("log"):
                if conf.has_option("log", "level"):
                    if conf["log"]["level"] == "CRITICAL":
                        nLogOnOff = 0

        resList.append(dict(processName=dProcInfo.get("nameWithCapital", ""),
                            logOnOff=nLogOnOff))

    for i in range(len(resList)):
        for j in range(len(resList)-i-1):
            if resList[j]["processName"] > resList[j+1]["processName"]:
                resList[j], resList[j+1] = resList[j+1], resList[j]

    return jsonify(dict(err=0, msg="", data=resList))


@bp_system.route("/turnOffAllLogs")
def turn_off_all_logs():
    dTar = {"outputerrpoint": [False], "debugopc": [False], "outputerrcode": [False], "debugbacnet": [False],
            "debugmodbus": [False], "logic_log_level": [-1], "logic_thread_mode": [False]}
    bSuc, strMsg = BEOPDataAccess.getInstance().updateMultiKeyValueOfUnit01(dTar)
    if not bSuc:
        return jsonify(dict(err=1, msg="调试设置关闭下发失败:{err}".format(err=strMsg), data=False))

    for item in allProcList:
        if item.get("logOpType", 0) == 0:
            continue

        procDir = item.get("name")

        try:
            procDir = os.path.join(app.config["CORE_PATH"], procDir)
            if not os.path.exists(procDir):
                continue

            conf = MyConf()
            configFilePath = os.path.join(procDir, "config.ini")

            if not os.path.exists(configFilePath):
                with open(configFilePath, "w+", encoding="UTF8", errors="ignore") as fo:
                    conf.write(fo)

            conf.read(configFilePath)
            if not conf.has_section("log"):
                conf.add_section("log")
            if not conf.has_option("log", "level"):
                conf["log"].update({"level": "CRITICAL"})

            conf["log"].update({"level": "CRITICAL"})
            with open(configFilePath, "w") as file:
                conf.write(file)

        except Exception as e:
            jsonify(dict(err=1, msg="关闭进程日志失败:{err}".format(err=e.__str__()), data=False))

    RedisManager().check_redis_initial_settings()

    return jsonify(dict(err=0, msg="设置成功", data=True))

@bp_system.route("/getUpdateProgress", methods=["POST"])
def get_update_progress():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nType = rcv.get("type", 0)  # 0-进程 1-组态模板文件
    name = rcv.get("name", None)

    if nType not in [0, 1]:
        return jsonify(dict(err=1, msg="type有误", data={}))

    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="name必须为字符串", data={}))

    if not len(name):
        return jsonify(dict(err=1, msg="name不能为空", data={}))

    dUpdateProgress = None
    nStatus = 0
    if nType == 0:
        if name.endswith(".exe"):
            name = name.replace(".exe", "")

        dUpdateProgress = RedisManager.get("ProcessUpdateProgress")
        dUpdateStatus = RedisManager.get("ProcessUpdateStatus")
        dStatusInfo = dUpdateStatus.get(name, {})
        if isinstance(dStatusInfo, dict):
            for strKeyTime, nStatusValue in dStatusInfo.items():
                if nStatusValue == 1:
                    nStatus = 1
                    break

    elif nType == 1:
        if not name.endswith(".4db"):
            name = "{name}.4db".format(name=name)
        dUpdateProgress = RedisManager.get("TemplateFileUpdateProgress")
        dUpdateStatus = RedisManager.get("TemplateFileUpdateStatus")
        dStatusInfo = dUpdateStatus.get(name, {})
        if isinstance(dStatusInfo, dict):
            for strKeyTime, nStatusValue in dStatusInfo.items():
                if nStatusValue == 1:
                    nStatus = 1
                    break

    if not isinstance(dUpdateProgress, dict):
        return jsonify(dict(err=1, msg="未发现进程或模板文件升级进度信息", data={}))

    dUpdateInfo = dUpdateProgress.get(name, {})
    if not isinstance(dUpdateInfo, dict):
        return jsonify(dict(err=1, msg="未发现{name}对应的升级进度信息".format(name=name), data={}))

    strTime = dUpdateInfo.get("time", "")
    description = dUpdateInfo.get("description", "")
    nProgress = dUpdateInfo.get("progress", None)

    tTime = None
    try:
        tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
    except:
        pass

    if not isinstance(tTime, datetime):
        return jsonify(dict(err=1, msg="进程升级进度指向的时间有误", data={}))

    if (datetime.now() - tTime).total_seconds() > 3600:
        return jsonify(dict(err=1, msg="进程升级进度指向的时间已过期，当前进度无法反应该进程的升级进度", data={}))

    if not isinstance(nProgress, int):
        return jsonify(dict(err=1, msg="进程升级进度格式有误，当前进度无法反应该进程的升级进度", data={}))

    if nProgress > 100 or nProgress < 0:
        return jsonify(dict(err=1, msg="进程升级进度数据有误，当前进度无法反应该进程的升级进度", data={}))

    if nStatus == 1 and nProgress < 100 and nProgress > 0:
        nProgressFinal = nProgress
    elif nStatus == 0:
        nProgressFinal = 0
    else:
        nProgressFinal = 0

    return jsonify(dict(err=0, msg="获取成功", data={"time": strTime,
                                                 "description": description,
                                                 "progress": nProgressFinal}))






