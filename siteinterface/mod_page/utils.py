
from siteinterface.RedisManager import RedisManager
from datetime import datetime
import requests
import json
import os
from siteinterface import app
import re
import shutil
import time


# 页面编辑超时限制分钟数
nPageEditMinsTimeOut = 5

strPageEditLockKey = "page_edit_lock"


def get_current_locked_page_map():
    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict):
        dEditLock = {}

    if not dEditLock:
        return {}

    dLockedPage = {}
    for strPageId, dPageEditLock in dEditLock.items():
        if not isinstance(dPageEditLock, dict):
            continue

        if dPageEditLock.get("lock", 0) == 1:
            tActiveTime = None
            try:
                tActiveTime = datetime.strptime(dPageEditLock.get("activeTime"), "%Y-%m-%d %H:%M:%S")
            except:
                pass

            if isinstance(tActiveTime, datetime):
                if (datetime.now() - tActiveTime).total_seconds() < nPageEditMinsTimeOut * 60:
                    dLockedPage.update({str(strPageId): dict(pageId=strPageId,
                                                    userId=dPageEditLock.get("userId"),
                                                    userName=dPageEditLock.get("userName"))})

    return dLockedPage

def search_template_by_point_keyword_from_cloud(keyword):
    headers = {"Content-Type": "application/json"}
    postData = {"keyword": keyword}
    rsp = None
    try:
        rsp = requests.post("http://47.100.17.99/api/s3dbFileManage/searchTemplateByPointNameKeyword", data=json.dumps(postData), headers=headers, timeout=30)
    except Exception as e:
        return {}, e.__str__()

    if rsp == None:
        return {}, ""

    if rsp.status_code != 200:
        return {}, "status_code 不等于200"

    try:
        dResult = json.loads(rsp.text)
    except:
        dResult = {}

    if not dResult:
        return {}, ""

    dData = dResult.get("data", {})
    return dData, ""

def get_domdb_backup_time_list():
    dbFileVerDir = os.path.join(app.config["CORE_PATH"], "DBFileVersion")
    if not os.path.exists(dbFileVerDir):
        return []

    tTimeList = []
    for root, dirs, fileNames in os.walk(dbFileVerDir):
        for fileName in fileNames:
            if not fileName.endswith(".4db"):
                continue

            if fileName.find("domdb_autosave") == -1:
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", fileName)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = None
            try:
                tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")
            except:
                pass

            if isinstance(tTime, datetime):
                tTimeList.append(tTime)

    tTimeList.sort(reverse=True)
    return tTimeList

def backup_domdb():
    dbFileVerDir = os.path.join(app.config["CORE_PATH"], "DBFileVersion")
    domdbPath = os.path.join(app.config["CORE_PATH"], "domdb.4db")
    try:
        shutil.copyfile(domdbPath,
                        os.path.join(dbFileVerDir, "domdb_autosave_{time}.4db".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))))
        return True, ""
    except Exception as e:
        strLog = "备份domdb.4db出错:%s" % e.__str__()
        return False, strLog

def execute_backup_domdb():
    bSucBackup = True
    errMsg = ""

    dbFileVerDir = os.path.join(app.config["CORE_PATH"], "DBFileVersion")
    if not os.path.exists(dbFileVerDir):
        os.mkdir(dbFileVerDir)

    domdbPath = os.path.join(app.config["CORE_PATH"], "domdb.4db")
    if not os.path.exists(domdbPath):
        return

    tTimeList = get_domdb_backup_time_list()

    tLatestBackup = None
    if len(tTimeList):
        tLatestBackup = tTimeList[0]

    tOutdateList = []
    if len(tTimeList) > 20:
        tOutdateList = tTimeList[20:]

    if tLatestBackup == None:
        bSuc, msg = backup_domdb()
        return bSuc, msg

    stTime = time.localtime(os.stat(domdbPath).st_mtime)
    tDomdbLatestEditTime = datetime.now().replace(year=stTime.tm_year, month=stTime.tm_mon, day=stTime.tm_mday,
                                                  hour=stTime.tm_hour, minute=stTime.tm_min, second=stTime.tm_sec, microsecond=0)

    if (tDomdbLatestEditTime - tLatestBackup).total_seconds() > 3600:
        bSucBackup, errMsg = backup_domdb()

    if len(tOutdateList):
        for tOutdate in tOutdateList:
            filePath = os.path.join(dbFileVerDir, "domdb_autosave_{time}.4db".format(time=tOutdate.strftime("%Y-%m-%d-%H-%M-%S")))
            try:
                os.remove(filePath)
            except:
                pass

    return bSucBackup, errMsg
