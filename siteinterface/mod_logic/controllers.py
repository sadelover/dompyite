from siteinterface.mod_logic import bp_logic
from flask import request, jsonify
from .. BEOPMySqlDBContainer import BEOPMySqlDBContainer
import traceback
import json
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
from siteinterface.LogicManager import LogicManager
from .config import *
import os       #文件操作
import shutil   #文件操作
import requests
import zipfile
import logging
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface import app
from siteinterface.OSSTool import OSSTool
from .utils import *
import time
import sqlite3
from siteinterface.commonUtils import is_one_number
from siteinterface.processManager import ProcessManager
from siteinterface.utils import process_restart_domlogic
from siteinterface.RedisManager import RedisManager


@bp_logic.route("/getSyslogicParameters", methods=["POST"])
def get_sys_logic_parameters():
    try:
        data = request.get_json()
        logicName = data.get("logic_name")

        if not isinstance(logicName, str):
            return jsonify(dict(err=1, msg="策略名称必须为字符串", data=list()))

        data = BEOPDataAccess.getInstance().getSysLogicParameters(logicName)

        return jsonify(dict(err=0, msg="获取成功", data=data))

    except Exception as e:
        strLog = "获取策略失败: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取策略失败: %s" % e.__str__(), data=""))


@bp_logic.route("/getSyslogicList")
def get_sys_logic_list():
    try:

        dataList = BEOPDataAccess.getInstance().getSysLogicList()

        return jsonify(dict(err=0, msg="获取成功", data=dataList))

    except Exception as e:
        strLog = "ERROR in /logic/getSyslogicList: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取策略列表失败: %s" % e.__str__(), data=list()))


'''
接受参数：
  data.get('path'), 如：d:\dom\factory\syslogic
  
  从https://dom-soft-release.oss-cn-shanghai.aliyuncs.com/syslogic.zip
  下载，解压替换，

 返回：成功的列表，失败的列表。
'''
# import time
def fileFind (objectName,Dir):
    #找到返回True
    for fileName in Dir:
        if objectName == fileName:
            return True
    return False

@bp_logic.route('/update_syslogic_single_with_file', methods=['POST'])
def logci_update_syslogic_single_with_file():
    upload_file = request.files['file']
    filename = upload_file.filename
    strFileNameWithoutExt = os.path.splitext(filename)[0]
    strDompysiteDir = os.getcwd()

    tempPath = os.path.join(strDompysiteDir, 'siteinterface')

    tempPath = os.path.join(tempPath, 'static/files/temp')
    if not os.path.exists(tempPath):
        os.mkdir(tempPath)

    saveFilePath = os.path.join(tempPath, filename)
    try:
        upload_file.save(saveFilePath)
    except Exception as e:
        return jsonify(dict(err=1, data={}, msg= e.__str__()))
    try:
        LogicManager.getInstance().update_logic_dll_file('domdb.4db', strFileNameWithoutExt, saveFilePath)
    except Exception as e:
        return jsonify(dict(err=1, data={}, msg= e.__str__()))

    return jsonify(dict(err=0, msg='success', data={}))

"""
从OSS下载单个dll文件
"""
@bp_logic.route('/update_syslogic_single', methods=['POST'])
def logic_update_syslogic_single():
    # start = time.clock()
    print('logic_update_syslogic_single request recv from factory')
    logging.error('logic_update_syslogic_single request recv from factory')
    data = request.get_json()#从json获取数据
    syslogicPath = data.get("syslogicPath")#获取本地更新地址
    strLogicName = data.get('logicName')
    syslogicDllPath = os.path.join(syslogicPath, strLogicName+'.dll')
    bUpdateIntoProject = data.get('updateIntoProject', False)
    rst = {
        "succeed_to_cover": [],
        "fail_to_cover": [],
        "succeed_to_add": []
    }

    try:
        # downloadStart = time.clock()
        #下载

        # NOTE the stream=True parameter below
        rep = requests.get('https://dom-soft-release.oss-cn-shanghai.aliyuncs.com/syslogic/'+ strLogicName+'.dll', stream=True, timeout=300)
        rep.raise_for_status()
        with open(syslogicDllPath, 'wb') as f:
            for chunk in rep.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        # end = time.clock()-start
        print('logic_update_syslogic_single : 更新成功')
        logging.error('logic_update_syslogic_single : 更新成功')

        if bUpdateIntoProject:
            LogicManager.getInstance().update_logic_dll_file('domdb.4db', strLogicName, syslogicDllPath)

        return json.dumps(dict(err=0, msg='更新成功', data=rst))
    except Exception as e:
        traceback.print_exc()
        print('update_syslogic : 更新失败')
        logging.error('update_syslogic : 更新失败')
        return json.dumps(dict(err=1, msg='更新失败', data=[]))

"""
从OSS下载syslogic.zip
"""
@bp_logic.route('/update_syslogic', methods=['POST'])
def logic_update_syslogic():
    # start = time.clock()
    print('update_syslogic request recv from factory')
    logging.error('update_syslogic request recv from factory')
    data = request.get_json()#从json获取数据
    syslogicPath = data.get("syslogicPath")#获取本地更新地址
    syslogicPath = syslogicPath.strip()# 移除首位空格
    syslogicZIPPath = os.path.join(syslogicPath, 'syslogic.zip')
    unzipPath = os.path.join(syslogicPath, "_unzip_")

    rst = {
        "succeed_to_cover": [],
        "fail_to_cover": [],
        "succeed_to_add": []
    }

    try:
        # downloadStart = time.clock()
        #下载

        # NOTE the stream=True parameter below
        rep = requests.get(region, stream=True, timeout=300)
        rep.raise_for_status()
        with open(syslogicZIPPath, 'wb') as f:
            for chunk in rep.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


        # downloadEnd = time.clock() - downloadStart
        #↓创建缓存文件夹
        if (os.path.exists(unzipPath)) == False:
            os.mkdir(unzipPath)  # 创建目录
        else:
            shutil.rmtree(unzipPath)  # 先删除直接删除文件夹，防止文件夹下存在文件
            os.mkdir(unzipPath)  # 创建目录

        # 解压缩
        # unzipStart = time.clock()

        sZip = zipfile.ZipFile(syslogicZIPPath, 'r')
        sZip.extractall(unzipPath)
        sZip.close()

        # unzipEnd = time.clock() - unzipStart

        # ↓更新文件:
        # updateStart = time.clock()
        syslogicDir = os.listdir(syslogicPath)  # 读取syslogic文件列表
        unzipDir = os.listdir(unzipPath)  # 读取文件列表

        print('update_syslogic :start to write files')
        logging.error('update_syslogic :start to write files')
        for unzipDir_file in unzipDir:
            if fileFind(unzipDir_file, syslogicDir) == False:  # 没有找到文件
                try:
                    shutil.copy(unzipPath + '\\' + unzipDir_file, syslogicPath)  # 复制文件到syslogicDir
                    rst["succeed_to_add"].append(unzipDir_file)
                    # print(unzipDir_file+"   Add Succeed")
                except:
                    traceback.print_exc()
                    rst["fail_to_cover"].append(unzipDir_file)
            else:  # 文件重复
                try:
                    shutil.copyfile(unzipPath + '\\' + unzipDir_file,
                                    syslogicPath + '\\' + unzipDir_file)  # 复制文件到syslogicDir覆盖原文件
                    rst["succeed_to_cover"].append(unzipDir_file)
                except:
                    traceback.print_exc()
                    rst["fail_to_cover"].append(unzipDir_file)
            #end for unzipDir_file in unzipDir:
        # updateEnd = time.clock() - updateStart

        shutil.rmtree(unzipPath)  # 删除临时解压文件夹
        os.remove(syslogicZIPPath)#删除下载的更新文件
        # end = time.clock()-start
        print('update_syslogic : 更新成功')
        logging.error('update_syslogic : 更新成功')
        return json.dumps(dict(err=0, msg='更新成功', data=rst))
    except Exception as e:
        traceback.print_exc()
        shutil.rmtree(unzipPath)  # 删除临时解压文件夹
        os.remove(syslogicZIPPath)#删除下载的更新文件
        print('update_syslogic : 更新失败')
        logging.error('update_syslogic : 更新失败')
        return json.dumps(dict(err=1, msg='更新失败', data=[]))


@bp_logic.route('/updateLogicFileInProject', methods=['POST'])
def logic_Update_LogicFileInProject():
    rst={
        "successed_to_update" : [],
        "fail_to_update" : []
        }
    try:
        data = request.get_json()  # 从json获取数据
        strLogicNameList = data.get('logicFileNameList') # '''["MathAND", "MathOR"]'''
        strLogicFilePath = data.get('LogicFilePath')  #"D:\dom\factory\syslogic"

        for dllName in strLogicNameList:
            dllPath = os.path.join(strLogicFilePath,dllName+'.dll')
            if os.path.exists(dllPath):#判断文件是否存在
                update_flag = LogicManager.update_logic_dll_file(strDBFileName='domdb.4db',strDllName=dllName,strDllFilePath=dllPath)
                if (update_flag == True) :#判断执行是否成功
                    rst["successed_to_update"].append(dllName)
                else:
                    rst["fail_to_update"].append(dllName)
            else:
                rst["fail_to_update"].append(dllName)
        return json.dumps(dict(err=0, msg='更新结果', data=rst))
    except Exception as e:
        strError = 'ERROR Update Logic File In Project : %s' % (e.__str__())
        logging.error(strError)
        traceback.print_exc()
        return json.dumps(dict(err=1, msg='更新失败', data=[]))

@bp_logic.route('/downloadSyslogicFiles', methods=['POST'])
def download_syslogic_files():
    errMsg = ""
    rcv = request.get_json()
    syslogicName = rcv.get("logicName", None)
    if syslogicName != None:
        if not isinstance(syslogicName, str):
            return jsonify(dict(err=1, msg="策略名必须为字符串", data={}))

    sysLogicDir = os.path.join(app.static_folder, "syslogic")
    if not os.path.exists(sysLogicDir):
        os.mkdir(sysLogicDir)

    tool = OSSTool()
    nDownloadCount = 0
    nTotal = 0
    failList = []
    if syslogicName == None:
        dllNameList = tool.iterate_files("syslogic")

        logicNameList = []
        for dllName in dllNameList:
            if dllName.endswith(".dll"):
                logicNameList.append(dllName)

        nTotal = len(logicNameList)

        for logicName in logicNameList:
            bSuc = tool.download("syslogic/{file}".format(file=logicName), os.path.join(sysLogicDir, logicName))
            if bSuc:
                nDownloadCount += 1
            else:
                failList.append(logicName)

        if len(failList):
            errMsg += "存在下载失败的文件"

    else:
        nTotal = 1
        logicName = syslogicName.replace(".dll", "")
        bExists = tool.file_exists("syslogic/{file}.dll".format(file=logicName))
        if not bExists:
            errMsg += ";{file}.dll不存在于OSS".format(file=logicName)
            failList.append("{file}.dll".format(file=logicName))
        else:
            bSuc = tool.download("syslogic/{file}.dll".format(file=logicName),
                                 os.path.join(sysLogicDir, "{logicName}.dll".format(logicName=logicName)))
            if bSuc:
                nDownloadCount += 1
            else:
                failList.append("{file}.dll".format(file=logicName))
                errMsg += "存在下载失败的文件"

    return jsonify(dict(err=1 if len(errMsg) else 0, msg=errMsg, data={"total": nTotal,
                                                                       "succeed": nDownloadCount,
                                                                       "fail": nTotal - nDownloadCount,
                                                                       "failList": failList,
                                                                       "syslogicDir": sysLogicDir}))

@bp_logic.route('/getLogicList')
def get_logic_list():
    dAllLogic = BEOPSqliteAccess.getInstance().getAllLogic()
    if not dAllLogic:
        return jsonify(dict(err=0, msg="", data=[]))

    tool = OSSTool()

    ossPath = "update/update.json"
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    timeTag = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
    localPath = os.path.join(tempDir, "update_{timeTag}.json".format(timeTag=timeTag))

    bSuc = tool.download(ossPath, localPath)
    if bSuc:
        with open(localPath, "r", encoding="UTF8", errors="ignore") as fo:
            try:
                dJson = json.load(fo)
            except:
                dJson = {}

            dCloudLogicVersion = dJson.get("logic_version", {})
            for dllName, dOneLogic in dAllLogic.items():
                strCloudVersion = dCloudLogicVersion.get(dOneLogic.get("dllFileName", ""), "")
                dOneLogic.update({"cloudVersion": strCloudVersion})

        if os.path.exists(localPath):
            try:
                os.remove(localPath)
            except:
                pass

    # dllName: start_chiller.dll
    # logicName: start_chiller
    logicNameList = [name.replace(".dll", "") for name in list(dAllLogic.keys())]
    dLogicOnOff = BEOPDataAccess.getInstance().getMultiKeyValueFromUnit01(logicNameList)

    allLogicList = []
    for dllName, dInfo in dAllLogic.items():
        logicName = dllName.replace(".dll", "")

        nSortNo = get_logic_sort_no(logicName)
        nLogicOnOff = 0
        if isinstance(dLogicOnOff.get(logicName, None), tuple):
            if len(dLogicOnOff.get(logicName)):
                if is_one_number(dLogicOnOff.get(logicName)[0]):
                    nLogicOnOff = int(dLogicOnOff.get(logicName)[0])

        dInfo.update(dict(onoff=nLogicOnOff, sortNo=nSortNo))
        allLogicList.append(dInfo)

    for i in range(len(allLogicList)):
        for j in range(len(allLogicList)-i-1):
            if allLogicList[j]["sortNo"] == -1 and allLogicList[j+1]["sortNo"] != -1:
                allLogicList[j], allLogicList[j + 1] = allLogicList[j + 1], allLogicList[j]
            else:
                if allLogicList[j]["sortNo"] > allLogicList[j + 1]["sortNo"]:
                    allLogicList[j], allLogicList[j + 1] = allLogicList[j + 1], allLogicList[j]

    return jsonify(dict(err=0, msg="", data=allLogicList))

@bp_logic.route('/getConfig', methods=["POST"])
def get_config():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)   # start_chiller   (无.dll)
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=[]))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    paramList = BEOPSqliteAccess.getInstance().getLogicConfig(logicName)

    return jsonify(dict(err=0, msg="", data=[{"groupName": '默认参数组', "paramList": paramList}]))

@bp_logic.route('/editConfig', methods=["POST"])
def edit_config():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)
    editList = rcv.get("editList", [])
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=False))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    if not editList:
        return jsonify(dict(err=1, msg="编辑列表不能为空", data=False))

    bSuc, strErr = BEOPSqliteAccess.getInstance().editLogicConfig(logicName, editList)
    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02EditConfig(logicName, editList)

    return jsonify(dict(err=1 if len(strErr) else 0,
                        msg=strErr,
                        data=True if bSuc and not len(strErr) else False))

@bp_logic.route('/delete', methods=["POST"])
def logic_delete():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=False))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    bSuc1 = BEOPSqliteAccess.getInstance().deleteLogic(logicName)
    bSuc2 = BEOPDataAccess.getInstance().deleteLogic(logicName)
    bSuc = bSuc1 and bSuc2
    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02ForLogic(5, logicName)

    return jsonify(dict(err=1 if not bSuc else 0, msg="", data=bSuc))

@bp_logic.route('/listLogicName')
def list_logic_name():
    tool = OSSTool()
    fileNameList = tool.iterate_files("syslogic")

    # 改为从oss遍历获取dll名称
    logicNameList = []
    for fileName in fileNameList:
        if not fileName.endswith(".dll"):
            continue
        logicNameList.append(fileName.replace(".dll", "").strip())

    return jsonify(dict(err=0, msg="", data=logicNameList))

@bp_logic.route('/add', methods=["POST"])
def add_logic():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)  # 用户自定义的策略名
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=False))

    dllFileName = rcv.get("dllFileName", None)   # syslogic下的dll文件名（不带后缀）
    if dllFileName == None:
        return jsonify(dict(err=1, msg="dll文件名不能为空", data=False))

    period = rcv.get("period", None)
    if period != None:
        if not isinstance(period, int):
            return jsonify(dict(err=1, msg="策略运行周期必须为整数", data=False))

    if dllFileName.find(".dll") >= 0:
        dllFileName = dllFileName.replace(".dll", "")

    domlogicParserPath = os.path.join(os.getcwd(), "domlogicparser", "domlogicparser.exe")
    if not os.path.exists(domlogicParserPath):
        return jsonify(dict(err=1, msg="domlogicParser不存在", data=False))

    dExistingLogic = BEOPSqliteAccess.getInstance().getAllLogic(logicName)
    if dExistingLogic:
        return jsonify(dict(err=1, msg="策略名称{logicName}已存在，无法新建重名策略".format(logicName=logicName), data=False))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    # 从OSS下载
    tool = OSSTool()
    bExists = tool.file_exists("syslogic/{file}.dll".format(file=dllFileName))
    if not bExists:
        return jsonify(dict(err=1, msg="{dllFile}.dll不存在于OSS".format(dllFile=dllFileName), data=False))

    syslogicDir = os.path.join(app.static_folder, "syslogic")
    if not os.path.exists(syslogicDir):
        os.mkdir(syslogicDir)

    dllSrcPath = os.path.join(syslogicDir, "{logicName}.dll".format(logicName=dllFileName))
    bSucDownload = tool.download("syslogic/{file}.dll".format(file=dllFileName), dllSrcPath)
    if not bSucDownload:
        return jsonify(dict(err=1, msg="{dllFile}.dll下载失败".format(dllFile=dllFileName), data=False))

    dllDstPath = os.path.join(tempDir, "{name}_{time}.dll".format(name=dllFileName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(dllDstPath):
        try:
            os.remove(dllDstPath)
        except:
            jsonify(dict(err=1, msg="删除temp文件夹下的既有dll文件失败", data=False))

    shutil.copy(dllSrcPath, dllDstPath)
    if not os.path.exists(dllDstPath):
        jsonify(dict(err=1, msg="dll文件复制失败", data=False))

    jsonFilePath = os.path.join(tempDir, "{dllFileName}_{time}.json".format(dllFileName=dllFileName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(jsonFilePath):
        try:
            os.remove(jsonFilePath)
        except:
            jsonify(dict(err=1, msg="删除{file}失败".format(file=jsonFilePath), data=False))

    bSuc, msg = get_dll_file_info(domlogicParserPath, dllDstPath, jsonFilePath)
    if not bSuc:
        return jsonify(dict(err=1, msg="启动domlogicParser.exe失败:{err}".format(err=msg), data=False))

    nCount = 0
    while nCount < 30:
        if os.path.exists(jsonFilePath):
            break
        nCount += 1
        time.sleep(1)

    if not os.path.exists(jsonFilePath):
        return jsonify(dict(err=1, msg="解析策略文件失败，{jsonFile}未生成".format(jsonFile=jsonFilePath), data=False))

    try:
        with open(jsonFilePath, "r", encoding="gbk", errors="ignore") as fo:
            dJson = json.load(fo)
    except Exception as e:
        return jsonify(dict(err=1, msg="解析{jsonFilePath}失败:{err}".format(jsonFilePath=jsonFilePath, err=e.__str__()), data=False))

    if not isinstance(dJson, dict):
        return jsonify(dict(err=1, msg="由domLogicParser.exe读到的策略信息格式不是字典", data=False))

    dDllData = dJson.get("data", {})
    author = dDllData.get("author", "")
    description = dDllData.get("description", "")
    version = dDllData.get("version", "")
    paramList = dDllData.get("paramList", [])

    version = version.replace("V", "").replace("v", "")

    update_cloud_logic_version_when_manual_update(version, dllFileName)

    with open(dllDstPath, 'rb') as f:
        dllContent = sqlite3.Binary(f.read())

    nMaxId = BEOPSqliteAccess.getInstance().getMaxIdInTable("list_dllstore")
    if isinstance(nMaxId, bytes):
        try:
            nMaxId = nMaxId.decode("gbk")
            nMaxId = int(nMaxId)
        except:
            return jsonify(dict(err=1, msg="获取list_dllstore最大id失败", data=False))

    bSuc, errMsg = BEOPSqliteAccess.getInstance().addLogic(nMaxId+1, logicName, author, period, dllContent, version, description, dllFileName, paramList)
    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02ForLogic(4, logicName)

    try:
        os.remove(dllDstPath)
    except:
        pass

    try:
        os.remove(jsonFilePath)
    except:
        pass

    return jsonify(dict(err=1 if not bSuc else 0, msg=errMsg, data=bSuc))

@bp_logic.route('/editName', methods=["POST"])
def edit_logic_name():
    rcv = request.get_json()
    oldName = rcv.get("oldName", None)
    newName = rcv.get("newName", None)

    if not isinstance(oldName, str):
        return jsonify(dict(err=1, msg="旧名称不能为空", data=False))
    if not isinstance(newName, str):
        return jsonify(dict(err=1, msg="新名称不能为空", data=False))

    if not len(oldName) or not len(newName):
        return jsonify(dict(err=1, msg="新名称或旧名称不能为空", data=False))

    if oldName.find(".dll") >= 0:
        oldName = oldName.replace(".dll", "")

    if newName.find(".dll") >= 0:
        newName = newName.replace(".dll", "")

    dExistingLogic = BEOPSqliteAccess.getInstance().getAllLogic(newName)
    if dExistingLogic:
        return jsonify(dict(err=1, msg="新名称{name}已存在，无法修改".format(name=newName), data=False))

    bSuc, errMsg = BEOPSqliteAccess.getInstance().editLogicName(oldName, newName)
    if bSuc:
        BEOPDataAccess.getInstance().editLogicNameInUnit01(oldName, newName)

        toRestartLogicProcessNumList = get_logic_process_name_to_restart([oldName, newName])
        nNumList = list(set(toRestartLogicProcessNumList))

        for nNum in nNumList:
            if nNum == 0:
                domlogicNameWithExt = "domlogic.exe"
            else:
                domlogicNameWithExt = "domlogic{n:02d}.exe".format(n=nNum)
            process_restart_domlogic(domlogicNameWithExt)
            time.sleep(0.1)

    return jsonify(dict(err=1 if not bSuc else 0, msg=errMsg, data=bSuc))


@bp_logic.route('/editPeriod', methods=["POST"])
def edit_logic_period():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)
    period = rcv.get("period", None)
    if not isinstance(logicName, str):
        return jsonify(dict(err=1, msg="策略名称不能为空", data=False))

    if not isinstance(period, int):
        return jsonify(dict(err=1, msg="策略运行周期必须为整数", data=False))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    bSuc = BEOPSqliteAccess.getInstance().editLogicPeriod(logicName, period)
    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02ForLogic(2, logicName, period=period)
    return jsonify(dict(err=1 if not bSuc else 0, msg="", data=bSuc))

@bp_logic.route('/updateLogic', methods=["POST"])
def update_logic():
    rcv = request.get_json()
    dllFileName = rcv.get("dllFileName", None)  # syslogic下的dll文件名（不带后缀）
    if dllFileName == None:
        return jsonify(dict(err=1, msg="dll文件名不能为空", data=False))

    if dllFileName.find(".dll") >= 0:
        dllFileName = dllFileName.replace(".dll", "")

    domlogicParserPath = os.path.join(os.getcwd(), "domlogicparser", "domlogicparser.exe")
    if not os.path.exists(domlogicParserPath):
        return jsonify(dict(err=1, msg="domlogicParser不存在", data=False))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    # 从OSS下载
    tool = OSSTool()
    bExists = tool.file_exists("syslogic/{file}.dll".format(file=dllFileName))
    if not bExists:
        return jsonify(dict(err=1, msg="{dllFile}.dll不存在于OSS".format(dllFile=dllFileName), data=False))

    syslogicDir = os.path.join(app.static_folder, "syslogic")
    if not os.path.exists(syslogicDir):
        os.mkdir(syslogicDir)

    bSucDownload = tool.download("syslogic/{file}.dll".format(file=dllFileName), os.path.join(syslogicDir, "{logicName}.dll".format(logicName=dllFileName)))
    if not bSucDownload:
        return jsonify(dict(err=1, msg="{dllFile}.dll下载失败".format(dllFile=dllFileName), data=False))

    # 复制到temp文件夹下
    dllSrcPath = os.path.join(app.static_folder, "syslogic", "{name}.dll".format(name=dllFileName))
    if not os.path.exists(dllSrcPath):
        return jsonify(dict(err=1, msg="{name}.dll不存在于syslogic文件夹下".format(name=dllFileName), data=False))

    dllDstPath = os.path.join(tempDir, "{name}_{time}.dll".format(name=dllFileName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(dllDstPath):
        try:
            os.remove(dllDstPath)
        except:
            jsonify(dict(err=1, msg="删除temp文件夹下的既有dll文件失败", data=False))

    shutil.copy(dllSrcPath, dllDstPath)
    if not os.path.exists(dllDstPath):
        jsonify(dict(err=1, msg="dll文件复制失败", data=False))

    jsonFilePath = os.path.join(tempDir, "{dllFileName}_{time}.json".format(dllFileName=dllFileName,time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(jsonFilePath):
        try:
            os.remove(jsonFilePath)
        except:
            jsonify(dict(err=1, msg="删除{file}失败".format(file=jsonFilePath), data=False))

    bSuc, msg = get_dll_file_info(domlogicParserPath, dllDstPath, jsonFilePath)
    if not bSuc:
        return jsonify(dict(err=1, msg="启动domlogicParser.exe失败:{err}".format(err=msg), data=False))

    nCount = 0
    while nCount < 30:
        if os.path.exists(jsonFilePath):
            break
        nCount += 1
        time.sleep(1)

    if not os.path.exists(jsonFilePath):
        return jsonify(dict(err=1, msg="解析策略文件失败，{jsonFile}未生成".format(jsonFile=jsonFilePath), data=False))

    dJson = {}
    try:
        with open(jsonFilePath, "r", encoding="gbk", errors="ignore") as fo:
            dJson = json.load(fo)
    except Exception as e:
        return jsonify(dict(err=1, msg="解析{jsonFilePath}失败:{err}".format(jsonFilePath=jsonFilePath, err=e.__str__()), data=False))

    if not isinstance(dJson, dict):
        return jsonify(dict(err=1, msg="由domLogicParser.exe读到的策略信息格式不是字典", data=False))

    dDllData = dJson.get("data", {})
    author = dDllData.get("author", "")
    description = dDllData.get("description", "")
    version = dDllData.get("version", "")
    configList = dDllData.get("paramList", [])

    version = version.replace("V", "").replace("v", "")

    update_cloud_logic_version_when_manual_update(version, dllFileName)

    with open(dllDstPath, 'rb') as f:
        dllContent = sqlite3.Binary(f.read())

    bSuc, msg, dllNameList = BEOPSqliteAccess.getInstance().updateLogic(dllFileName, author, description, version, dllContent, configList)

    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02UpdateDllFile("{dllFileName}.dll".format(dllFileName=dllFileName))

    try:
        os.remove(dllDstPath)
        os.remove(jsonFilePath)
    except:
        pass

    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_logic.route('/analyseMissingDependPoints', methods=["POST"])
def analyseMissingDependPoints():
    rcv = request.get_json()
    logicName = rcv.get("logicName", None)  # start_chiller   (无.dll)
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=[]))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    domlogicParserPath = os.path.join(os.getcwd(), "domlogicparser", "domlogicparser.exe")
    if not os.path.exists(domlogicParserPath):
        return jsonify(dict(err=1, msg="检测到domlogicParser不存在，请升级调试工具后台", data=False))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    jsonFilePath = os.path.join(tempDir, "{logicName}_{time}.json".format(logicName=logicName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(jsonFilePath):
        try:
            os.remove(jsonFilePath)
        except:
            jsonify(dict(err=1, msg="删除{file}失败".format(file=jsonFilePath), data=False))

    logicNameWithExt = "{logicName}.dll".format(logicName=logicName)
    bSuc, msg = get_dll_depend_points(domlogicParserPath,
                                      os.path.join(app.config["CORE_PATH"], "domdb.4db"),
                                      logicNameWithExt,
                                      jsonFilePath)

    if not bSuc:
        return jsonify(dict(err=1, msg="启动domlogicParser.exe失败:{err}".format(err=msg), data=False))

    nCount = 0
    while nCount < 60:
        if os.path.exists(jsonFilePath):
            break
        nCount += 1
        time.sleep(1)

    if not os.path.exists(jsonFilePath):
        return jsonify(dict(err=1, msg="解析策略文件失败，{jsonFile}未生成".format(jsonFile=jsonFilePath), data=False))

    with open(jsonFilePath, "r", encoding="gbk", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            dJson = {}

    if not isinstance(dJson, dict):
        return jsonify(dict(err=1, msg="由domLogicParser.exe读到的点依赖信息格式不是字典", data=False))

    dDllData = dJson.get("data", {})
    analysisPointList = dDllData.get("pointList", [])
    if not isinstance(analysisPointList, list):
        analysisPointList = []

    curPointList = BEOPSqliteAccess.getInstance().getPointListForExport()
    curPointNameList = []
    for point in curPointList:
        curPointNameList.append(point[1].decode("gbk"))

    toInsertList = []
    toInsertPointNameList = []
    for dOnePoint in analysisPointList:
        if not dOnePoint.get("pointName", ""):
            continue

        if dOnePoint.get("pointName") in curPointNameList:
            continue

        strRW = "W" if dOnePoint.get("pointName").lower().find("setting") >= 0 or dOnePoint.get(
            "pointName").lower().find("setpoint") >= 0 else "R"

        if dOnePoint.get("pointName") in toInsertPointNameList:
            continue

        toInsertList.append(
            dict(name=dOnePoint.get("pointName"),
                 type="vpoint",
                 description=dOnePoint.get("pointDesccription", ""),
                 unit=dOnePoint.get("pointUnit", ""),
                 rw=strRW))
        toInsertPointNameList.append(dOnePoint.get("pointName"))

    try:
        os.remove(jsonFilePath)
    except:
        pass

    strMsg = "预检成功" if len(toInsertList) else "预检成功，无缺失点位"
    return jsonify(dict(err=0, msg=strMsg, data=toInsertList))


@bp_logic.route("/insertMissingDependPoints", methods=["POST"])
def insert_missing_depend_points():
    try:
        rcv = request.get_json()
        pointList = rcv.get("pointList", [])
        strErrMsg = ""
        if not len(pointList):
            return jsonify(dict(err=1, msg="pointList不能为空", data={}))

        curPointList = BEOPSqliteAccess.getInstance().getPointListForExport()
        curMaxIndex = BEOPSqliteAccess.getInstance().getMaxIdInTable("list_point")
        nNum = curMaxIndex + 1

        curPointNameList = []
        for curPoint in curPointList:
            curPointNameList.append(curPoint[1].decode("gbk"))

        toInsertList = []
        toInsertPointNameList = []
        for point in pointList:
            name = point.get("name", None)
            strType = point.get("type", None)
            if name == None or strType == None:
                continue

            if name in curPointNameList:
                continue

            if name in toInsertPointNameList:
                continue

            # id, name, type, description, unit, rw, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, high, highhigh, low, lowlow, param11(存储周期), param15, param16, param17, param18, param19
            toInsertList.append(
                [str(nNum), name, strType, point.get("description", ""), point.get("unit", ""), point.get("rw", "R"),
                 '', '', '', '', '', '', '', '', '', '', '0', '0', '0', '0', '2', '', '', '', '', "2"]
            )

            toInsertPointNameList.append(name)

            nNum += 1

        if not len(toInsertList):
            return jsonify(dict(err=0, msg="未发现需要增加的策略依赖点，或传入的点信息格式有误", data={"addCount": 0}))

        dResult = BEOPSqliteAccess.getInstance().insertPointList(toInsertList)
        if dResult.get("success", False):
            BEOPSqliteAccess.getInstance().updateAllPointInfoIntoRedis()

            nCount = 0
            bSucKill = False
            bSucRestart = False
            while nCount < 3:
                bSucKill = ProcessManager.getInstance().killProcess("domcore.exe")
                if bSucKill:
                    break
                time.sleep(1)
                nCount += 1

            if bSucKill:
                nCount = 0
                while nCount < 3:
                    bSucRestart = ProcessManager.getInstance().startProcess("domcore.exe", app.config['CORE_PATH'])
                    if bSucRestart:
                        break
                    time.sleep(1)
                    nCount += 1

            bCoreRestart = bSucKill and bSucRestart
            bFinalSuc = bCoreRestart
            if not bCoreRestart:
                strErrMsg = "domcore自动重启失败，请手动重启domcore"

            strMsg = "添加成功" if not strErrMsg else strErrMsg
            return jsonify(dict(err=1 if not bFinalSuc else 0, msg=strMsg, data={"addCount": len(toInsertList)}))
        else:
            return jsonify(dict(err=1, msg="插入策略依赖点失败:{msg}".format(msg=dResult.get("msg","")), data={"addCount": 0}))
    except Exception as e:
        return jsonify(dict(err=1, msg="插入策略依赖点失败: %s" % e.__str__(), data={"addCount": 0}))

@bp_logic.route("/startStopLogic", methods=["POST"])
def start_stop_logic():
    rcv = request.get_json()
    onoff = rcv.get("onoff", None)
    logicName = rcv.get("logicName", None)
    if logicName == None:
        return jsonify(dict(err=1, msg="策略名称不能为空", data=[]))

    if logicName.find(".dll") >= 0:
        logicName = logicName.replace(".dll", "")

    if onoff == None:
        return jsonify(dict(err=1, msg="onoff不能为空", data=False))
    if onoff not in [0, 1]:
        return jsonify(dict(err=1, msg="onoff必须为整数的0或1", data=False))

    dAllLogic = BEOPSqliteAccess.getInstance().getAllLogic(logicName)
    if not dAllLogic:
        return jsonify(dict(err=1, msg="策略名称{name}不存在".format(name=logicName), data=False))

    bSuc = BEOPDataAccess.getInstance().startStopLogic(logicName, onoff)

    bSucConsistency, strErrMsg = BEOPSqliteAccess.getInstance().logicConsistencyCheck(logicName)

    if not bSuc:
        strMsg = "策略启停操作失败"
    else:
        if bSucConsistency:
            strMsg = ""
        else:
            strMsg = "策略启停操作成功，但一致性处理失败，原因：" + strErrMsg

    return jsonify(dict(err=1 if not bSuc else 0, msg=strMsg, data=bSuc))


@bp_logic.route("/getEquipCommandLockProtect", methods=["POST"])
def get_equip_command_lock_protect():
    nThresholdMins = 15 # 多久之内的结果认为是有效的
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    point = rcv.get("point", None)
    userName = rcv.get("userName", None)
    if not isinstance(point, str) and not isinstance(point, list):
        return jsonify(dict(err=1, msg="必须传入点名", data={}))

    if not isinstance(userName, str):
        return jsonify(dict(err=1, msg="必须传入userName", data={}))
    if not len(userName):
        return jsonify(dict(err=1, msg="userName不能为空", data={}))

    nUserId = BEOPDataAccess.getInstance().get_user_id_by_name(userName)
    try:
        nUserId = int(float(nUserId))
    except:
        pass

    if nUserId == None or not isinstance(nUserId, int):
        return jsonify(dict(err=1, msg="用户名{userName}对应的用户ID不存在或获取失败".format(userName=userName), data=False))

    pointList = point
    if not isinstance(point, list):
        pointList = [point]

    dCmdLockProtect = RedisManager.get("command_lock_protect")
    if not isinstance(dCmdLockProtect, dict):
        dCmdLockProtect = {}

    dMaintainLockRecord = BEOPDataAccess.getInstance().getMaintainLockRecord()

    dRes = {}
    for strPointName in pointList:
        if dMaintainLockRecord != None:
            if dMaintainLockRecord.get(strPointName, {}):

                if isinstance(dMaintainLockRecord.get(strPointName, {}).get("userId", None), int):
                    if dMaintainLockRecord[strPointName].get("userId") != nUserId:   # 若mysql中挂牌记录中的用户ID与当前访问用户ID不同则返回不允许对该挂牌点写值0

                        if strPointName not in dRes.keys():
                            dRes.update({strPointName: {}})

                        dRes[strPointName].update({"0": dict(permit=False,
                                                           description="所属设备已于{time}被{userName}挂牌，故当前该点不允许被置为0".format(time=dMaintainLockRecord[strPointName]["time"], userName=dMaintainLockRecord[strPointName]["userName"]),
                                                           time=dMaintainLockRecord[strPointName].get("time", ""))})

        dDiag = dCmdLockProtect.get(strPointName, {})
        if not isinstance(dDiag, dict) or not dDiag:
            continue

        for strValue, dDiagDetail in dDiag.items():
            strTime = dDiagDetail.get("time", None)
            try:
                tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
            except:
                tTime = None

            if isinstance(tTime, datetime):
                if (datetime.now() - tTime).total_seconds() <= nThresholdMins * 60:
                    if strPointName not in dRes.keys():
                        dRes.update({strPointName: {}})

                    dRes[strPointName].update({strValue: dict(permit=True if dDiagDetail.get("permit", None) in [1, "1", True] else False,
                                                              description=dDiagDetail.get("description", ""),
                                                              time=dDiagDetail.get("time"))})
    return jsonify(dict(err=0, msg="获取成功", data=dRes))

"""
data: 
0-本地版本已是最新，无需更新；
N-本地版本较旧，已更新至最新版本，N未更新后的版本号；
-1- 本地版本较旧，但更新失败
"""
@bp_logic.route('/updateLogicOfLatestVersion', methods=["POST"])
def update_logic_of_latest_version():
    rcv = request.get_json()
    dllFileName = rcv.get("dllFileName", None)  # syslogic下的dll文件名（不带后缀）
    if dllFileName == None:
        return jsonify(dict(err=1, msg="dll文件名不能为空", data=None))

    if dllFileName.find(".dll") >= 0:
        dllFileName = dllFileName.replace(".dll", "")

    nLocalVersion = rcv.get("localVersion", None)
    if nLocalVersion == None:
        return jsonify(dict(err=1, msg="本地版本不能为空", data=None))

    if not isinstance(nLocalVersion, int):
        return jsonify(dict(err=1, msg="本地版本必须为整数", data=None))

    domlogicParserPath = os.path.join(os.getcwd(), "domlogicparser", "domlogicparser.exe")
    if not os.path.exists(domlogicParserPath):
        return jsonify(dict(err=1, msg="domlogicParser不存在", data=None))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    bNeedUpdate = False

    strCloudVersion = get_cloud_version_of_dll(dllFileName)
    nCloudVersion = -1
    # dLocalVersion = BEOPSqliteAccess.getInstance().getVersionOfDllFile(dllFileName)
    # nLocalVersion = dLocalVersion.get(dllFileName, None)

    if isinstance(strCloudVersion, str):
        nCloudVersion = convert_version(strCloudVersion)
        if isinstance(nCloudVersion, int) and isinstance(nLocalVersion, int):
            if nLocalVersion < nCloudVersion:
                bNeedUpdate = True

    if not bNeedUpdate:
        return jsonify(dict(err=0, msg="经对比策略版本，无需更新", data=0))

    # 从OSS下载
    tool = OSSTool()
    bExists = tool.file_exists("syslogic/{file}.dll".format(file=dllFileName))
    if not bExists:
        return jsonify(dict(err=1, msg="{dllFile}.dll不存在于OSS".format(dllFile=dllFileName), data=None))

    syslogicDir = os.path.join(app.static_folder, "syslogic")
    if not os.path.exists(syslogicDir):
        os.mkdir(syslogicDir)

    bSucDownload = tool.download("syslogic/{file}.dll".format(file=dllFileName), os.path.join(syslogicDir, "{logicName}.dll".format(logicName=dllFileName)))
    if not bSucDownload:
        return jsonify(dict(err=1, msg="{dllFile}.dll下载失败".format(dllFile=dllFileName), data=None))

    # 复制到temp文件夹下
    dllSrcPath = os.path.join(app.static_folder, "syslogic", "{name}.dll".format(name=dllFileName))
    if not os.path.exists(dllSrcPath):
        return jsonify(dict(err=1, msg="{name}.dll不存在于syslogic文件夹下".format(name=dllFileName), data=None))

    dllDstPath = os.path.join(tempDir, "{name}_{time}.dll".format(name=dllFileName, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(dllDstPath):
        try:
            os.remove(dllDstPath)
        except:
            jsonify(dict(err=1, msg="删除temp文件夹下的既有dll文件失败", data=None))

    shutil.copy(dllSrcPath, dllDstPath)
    if not os.path.exists(dllDstPath):
        jsonify(dict(err=1, msg="dll文件复制失败", data=-1))

    jsonFilePath = os.path.join(tempDir, "{dllFileName}_{time}.json".format(dllFileName=dllFileName,time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(jsonFilePath):
        try:
            os.remove(jsonFilePath)
        except:
            jsonify(dict(err=1, msg="删除{file}失败".format(file=jsonFilePath), data=None))

    bSuc, msg = get_dll_file_info(domlogicParserPath, dllDstPath, jsonFilePath)
    if not bSuc:
        return jsonify(dict(err=1, msg="启动domlogicParser.exe失败:{err}".format(err=msg), data=None))

    nCount = 0
    while nCount < 30:
        if os.path.exists(jsonFilePath):
            break
        nCount += 1
        time.sleep(1)

    if not os.path.exists(jsonFilePath):
        return jsonify(dict(err=1, msg="解析策略文件失败，{jsonFile}未生成".format(jsonFile=jsonFilePath), data=None))

    dJson = {}
    try:
        with open(jsonFilePath, "r", encoding="gbk", errors="ignore") as fo:
            dJson = json.load(fo)
    except Exception as e:
        return jsonify(dict(err=1, msg="解析{jsonFilePath}失败:{err}".format(jsonFilePath=jsonFilePath, err=e.__str__()), data=None))

    if not isinstance(dJson, dict):
        return jsonify(dict(err=1, msg="由domLogicParser.exe读到的策略信息格式不是字典", data=None))

    dDllData = dJson.get("data", {})
    author = dDllData.get("author", "")
    description = dDllData.get("description", "")
    version = dDllData.get("version", "")
    configList = dDllData.get("paramList", [])

    version = version.replace("V", "").replace("v", "")

    update_cloud_logic_version_when_manual_update(version, dllFileName)

    with open(dllDstPath, 'rb') as f:
        dllContent = sqlite3.Binary(f.read())

    bSuc, msg, dllNameList = BEOPSqliteAccess.getInstance().updateLogic(dllFileName, author, description, version, dllContent, configList)

    if bSuc:
        BEOPDataAccess.getInstance().operateUnit02UpdateDllFile("{dllFileName}.dll".format(dllFileName=dllFileName))

    try:
        os.remove(dllDstPath)
        os.remove(jsonFilePath)
    except:
        pass

    return jsonify(dict(err=0, msg=msg, data=nCloudVersion if bSuc else -1, strData=strCloudVersion if bSuc else "-1"))


@bp_logic.route('/getLogicVersion', methods=["POST"])
def get_logic_version():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    dllNameList = rcv.get("dllNameList", None)
    if not isinstance(dllNameList, list):
        return jsonify(dict(err=1, msg="logicNameList必须为数组", data={}))

    if not len(dllNameList):
        return jsonify(dict(err=1, msg="logicNameList不能为空", data={}))

    dVersion, dAllStringVersion = BEOPSqliteAccess.getInstance().getVersionOfDllFile(dllNameList)

    return jsonify(dict(err=0, msg="", data=dVersion, strData=dAllStringVersion))


@bp_logic.route('/upgradeSeparateThreads', methods=["POST"])
def upgrade_separate_threads():
    errList = []

    nCountNeedToUpgrade = 0
    nCountUpgraded = 0
    dAllLogic = BEOPSqliteAccess.getInstance().getAllLogic()
    for oldDllName, dLogicInfo in dAllLogic.items():
        oldThreadName = dLogicInfo.get("threadName", "")
        try:
            if oldDllName == oldThreadName + ".dll":
                continue

            nCountNeedToUpgrade += 1

            procPrefixMatchList = re.findall(r"Process[0-9]{1}_", oldThreadName)
            procPrefix = None
            if isinstance(procPrefixMatchList, list):
                if len(procPrefixMatchList):
                    procPrefix = procPrefixMatchList[0]

            newDllName = oldDllName

            bDupDllNameFound = False
            if procPrefix != None and isinstance(procPrefix, str) and len(procPrefix):
                newDllName = "{tag}{dllName}".format(tag=procPrefix, dllName=oldDllName.replace(procPrefix, ""))
                dAllLogic = BEOPSqliteAccess.getInstance().getAllLogic()

                for existingDllName in dAllLogic.keys():
                    if existingDllName == newDllName:
                        errList.append("{dllName}添加前缀{prefix}后与既有的dllName重复，停止执行该策略的单线程化处理".format(dllName=oldDllName, prefix=procPrefix))
                        bDupDllNameFound = True
                        break

            if bDupDllNameFound:
                continue

            newLogicName = newDllName.replace(".dll", "")

            # 更新策略表中的字段
            bSuc, msg = BEOPSqliteAccess.getInstance().upgradeDllNameForSeparateThreads(oldDllName, newDllName)
            if not bSuc:
                errList.append("{oldDllName}修改为{newDllName}时失败，原因:{msg}，停止执行该策略的单线程化处理".format(oldDllName=oldDllName,
                                                                                               newDllName=newDllName, msg=msg))
                continue

            # 获取原有策略运行状态
            originalOnOff = BEOPDataAccess.getInstance().getUnit01(oldThreadName)
            nOnOff = 0
            try:
                nOnOff = int(originalOnOff)
            except:
                pass

            # 设置策略新版运行状态
            bSuc = BEOPDataAccess.getInstance().startStopLogic(newLogicName, nOnOff)
            if not bSuc:
                errList.append("将{newDllName}的策略运行状态(新版)更新进mysql失败".format(newDllName=newDllName))
                continue

            nCountUpgraded += 1

        except Exception as ept:
            errList.append("处理{dllName}时报错:{err}".format(dllName=oldThreadName, err=ept.__str__()))
        finally:
            time.sleep(0.1)

    return jsonify(dict(err=0, msg=";".join(errList), data={"totalNeed": nCountNeedToUpgrade,
                                             "done": nCountUpgraded}))


@bp_logic.route('/listLogicByType')
def list_logic_by_type():
    tool = OSSTool()
    bExists = tool.file_exists("update/syslogicwizard/syslogic.json")
    if not bExists:
        return jsonify(dict(err=1, msg="syslogic.json不存在，无法下载", data=[]))

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    lfilePath = os.path.join(tempDir, "syslogic_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
    if os.path.exists(lfilePath):
        try:
            os.remove(lfilePath)
        except:
            pass

    bSuc = tool.download("update/syslogicwizard/syslogic.json", lfilePath)
    if not bSuc or not os.path.exists(lfilePath):
        try:
            os.remove(lfilePath)
        except:
            pass
        return jsonify(dict(err=1, msg="syslogic.json下载失败", data=[]))

    with open(lfilePath, "r", encoding="UTF-8", errors="ignore") as f:
        try:
            dJson = json.load(f)
        except:
            dJson = {}

    dataList = dJson.get("data", [])
    if not isinstance(dataList, list):
        return jsonify(dict(err=1, msg="云端策略分类信息有误", data=[]))
    if not len(dataList):
        return jsonify(dict(err=1, msg="云端策略分类信息为空", data=[]))

    for dType in dataList:
        if isinstance(dType.get("children"), list):
            if len(dType.get("children")):
                for i in range(len(dType.get("children"))):
                    for j in range(len(dType.get("children"))-i-1):
                        if dType.get("children")[j].get("name") > dType.get("children")[j+1].get("name"):
                            dType.get("children")[j], dType.get("children")[j+1] = dType.get("children")[j+1], dType.get("children")[j]

    for i in range(len(dataList)):
        for j in range(len(dataList)-i-1):
            if isinstance(dataList[j].get("sort"), int) and isinstance(dataList[j+1].get("sort"), int):
                if dataList[j].get("sort") > dataList[j+1].get("sort"):
                    dataList[j], dataList[j+1] = dataList[j+1], dataList[j]

    try:
        os.remove(lfilePath)
    except:
        pass

    return jsonify(dict(err=0, msg="", data=dataList))

