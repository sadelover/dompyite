# -*- encoding=utf-8 -*-
__author__ = 'golding'
import os, sys, imp, time, inspect, re, glob
import pdfkit
from flask import render_template
from datetime import datetime, timedelta, date
import calendar as cal
from subprocess import Popen, PIPE

from flask import current_app
from flask_mail import Mail, Message

import pika
import logging
import json
import paho.mqtt.client as mqtt
import zipfile
from siteinterface import app
import uuid

import subprocess
import traceback
from siteinterface.BEOPDataAccess import BEOPDataAccess
from configobj import ConfigObj
from siteinterface.commonUtils import *
import sqlite3
from siteinterface.processManager import ProcessManager
from siteinterface.RedisManager import RedisManager
import requests
from siteinterface.UtilNetSpeed import test_server_speed
import psutil
import wmi
import win32file
import shutil
import time
from siteinterface.LicenseManage import LicenseManage
import win32api
from siteinterface.OSSTool import OSSTool

g_app_config_database = 'beopdata'
g_work_order_inspect_time = None



def on_publish(mqttc, obj, mid):
    print("MQTT OnPublish, mid: "+str(mid))

def sendEmailByMessageQueue(strMessageQueueAddress, strUserName,strUserPwd, subject, recipients, msgId, sender, html, cc, bcc):
    try:
        credentials = pika.PlainCredentials(strUserName, strUserPwd)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=strMessageQueueAddress,
            credentials = credentials,
            socket_timeout=300
        ))
        channel = connection.channel()
        strQueueName=  'email'
        channel.queue_declare(queue=  strQueueName, durable=True)

        msgValue = {'type': 'email', 'subject': subject, 'recipients': recipients, 'msgId': 1,
                    'sender': sender, 'html': html, 'cc': cc, 'bcc': bcc}

        bSuccess = channel.basic_publish(exchange='',
                              routing_key=strQueueName,
                              body= json.dumps(msgValue),
                              properties=pika.BasicProperties(
                                 delivery_mode = 2,  # make message persistent
                                  ))
        if not bSuccess:
            print('ERROR in channel.sendEmailByMessageQueue')
        else:
            print('%s sendEmailByMessageQueue Success Once' %(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        connection.close()
    except pika.exceptions.ProbableAuthenticationError as e:
        strInfo = 'ERROR in sendEmailByMessageQueue: Failed to send mail ' % ()
        logging.info(strInfo)
        print(strInfo)

    except Exception as e:
        strError = 'ERROR in sendEmailByMessageQueue: %s'%(e.__str__())
        print(strError)
        logging.error(strError)


    return False

def sendDataToMQTT( userName, userPwd, topicName, projName, ptInfoList):
    try:
        mqttc = mqtt.Client()
        mqttc.on_publish = on_publish
        #设置用户名与密码
        mqttc.username_pw_set(userName, userPwd)

        #connect(self, host, port=1883, keepalive=60, bind_address="")
        #host 是你的代理的hostname或者IP
        #port 是你的MQTT服务的端口. 默认是 1883.
        #注意，使用SSL/TLS的默认端口是 8883
        #
        bRv = mqttc.connect(app.config['MQ_ADDRESS'], 1883, 60)
        #mqttc.subscribe(topicName, 0)

        jsonMessage={"error":0, "msg":"", "projId":projName, "pointList":ptInfoList}
        strMessage=json.dumps(jsonMessage, ensure_ascii=False)
        """
        publish(topic, payload=None, qos=0, retain=False)
        topic:你的消息将被发送到的所在的主题
        payload:实际的要发送的消息
        qos:设置服务级别。
        retain:if set to True, the message will be set as the “last known good”/retained message for the topic.
        """
        rv = mqttc.publish(topicName,strMessage, 0, False)
        #_logger.writeLog('mqtt publish return :' + str(rv), True)
        mqttc.disconnect()
        return True
    except Exception as e:
        logging.error('mqtt send ERROR:' + e.__str__())
        return False
    return True


def time_get_day_start(tAct):
    tt = tAct.replace(hour=0, minute=0, second=0)
    return tt


def time_get_day_end(tAct):
    tEnd = tAct.replace(hour=23, minute=59, second=59)
    return tEnd

def time_get_today_start(tAct):
    tStart = tAct.replace(hour=0, minute=0, second=0)
    return tStart


def time_get_next_day_start(tAct):
    tStart = tAct.replace(hour=0, minute=0, second=0)
    tStart = tStart+timedelta(days=1)
    return tStart

def process_restart_domlogic(strProcessName):
    os.popen("taskkill /im %s -f"%(strProcessName))
    time.sleep(5)
    coreDir = app.config['CORE_PATH']
    domLogicPath = os.path.join(coreDir, strProcessName)

    # subprocess.Popen(domLogicPath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=coreDir)
    win32api.ShellExecute(0, 'open', domLogicPath, '', coreDir, 0)
    log_critical_event("Request", strProcessName, "web调试工具执行重启")

def process_stop_all():
    os.popen("taskkill /im domcore.exe -f")
    os.popen("taskkill /im domlogic.exe -f")
    return True

def process_stop_core():
    os.popen("taskkill /im domcore.exe -f")
    return True

def process_run_domShutdown():

    corePath = app.config['CORE_PATH']
    strExeDir = os.path.join(corePath, 'domShutdown')
    strExePath = os.path.join(strExeDir, 'domShutdown.exe')

    # subprocess.Popen(strExePath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=corePath)
    win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 0)

def process_restart_domfrpc():
    coreDir = app.config['CORE_PATH']
    domFRPCPath = os.path.join(coreDir, "domfrpc", 'domfrpc.exe')
    if not os.path.exists(domFRPCPath):
        return False

    os.popen("taskkill /im domfrpc.exe -f")
    time.sleep(1)

    domFrpcDir = os.path.join(coreDir, "domFRPC")
    win32api.ShellExecute(0, 'open', domFRPCPath, '', domFrpcDir, 0)

def kill_domfrpc():
    os.popen("taskkill /im domfrpc.exe -f")
    time.sleep(1)

def process_restart_domcore():
    os.popen("taskkill /im domcore.exe -f")
    time.sleep(1)
    coreDir = app.config['CORE_PATH']
    domcorePath = os.path.join(coreDir, 'domcore.exe')

    # subprocess.Popen(domcorePath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=corePath)
    win32api.ShellExecute(0, 'open', domcorePath, '', coreDir, 0)
    log_critical_event("Request", "domcore.exe", "web调试工具执行重启")

    process_restart_dom_siemensecore_if_running()

def process_restart_dom_siemensecore_if_running():
    if not ProcessManager.getInstance().findProcess("domSiemenseTCPCore.exe"):
        return

    os.popen("taskkill /im domSiemenseTCPCore.exe -f")
    time.sleep(1)
    corePath = app.config['CORE_PATH']
    strDir = os.path.join(corePath, 'domSiemenseTCPCore')
    strPath = os.path.join(strDir, 'domSiemenseTCPCore.exe')

    # subprocess.Popen(strPath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=corePath)
    win32api.ShellExecute(0, 'open', strPath, '', strDir, 0)

    log_critical_event("DebugTool", "domSiemenseTCPCore.exe", "web调试工具执行重启")

def restart_process(processName):
    processNameExe = "{processName}.exe".format(processName=processName)
    coreDir = app.config['CORE_PATH']
    if re.match(r"^domcore$", processName) or re.match(r"^domlogic.*$", processName):
        processDir = coreDir
    else:
        processDir = os.path.join(coreDir, processName)

    processPath = os.path.join(processDir, processNameExe)

    if processName in ["domhost"]:
        os.popen("taskkill /im {processNameExe} -f".format(processNameExe=processNameExe))
        time.sleep(1)
        try:
            # subprocess.Popen(processPath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=processDir)
            win32api.ShellExecute(0, 'open', processPath, '', processDir, 0)
            log_critical_event("Request", processNameExe, "web调试工具执行重启")
            return True
        except:
            return False

    else:

        os.popen("taskkill /im {processNameExe} -f".format(processNameExe=processNameExe))
        time.sleep(1)
        try:
            # subprocess.Popen(processPath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=coreDir)
            win32api.ShellExecute(0, 'open', processPath, '', processDir, 0)
            log_critical_event("Request", processNameExe, "web调试工具执行重启")
            return True
        except Exception as e:
            print(e.__str__())
            return False

def process_restart_domhost():
    os.popen("taskkill /im domhost.exe -f")
    time.sleep(1)
    corePath = app.config['CORE_PATH']
    strDir = os.path.join(corePath, 'domhost')
    strPath = os.path.join(strDir, 'domhost.exe')

    # subprocess.Popen(domLogicPath, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=strDomHostPath)
    win32api.ShellExecute(0, 'open', strPath, '', strDir, 0)

def zip_dir(dirname,zipfilename):
    filelist = []
    if os.path.isfile(dirname):
        filelist.append(dirname)
    else :
        for root, dirs, files in os.walk(dirname):
            for name in files:
                filelist.append(os.path.join(root, name))
    zf = zipfile.ZipFile(zipfilename, "w", zipfile.zlib.DEFLATED)
    for tar in filelist:
        arcname = tar[len(dirname):]
        #print arcname
        zf.write(tar,arcname)
    zf.close()


def send_email(subject, recipients, html, attachment_list=None, cc=None, bcc=None):
    rt = False
    if not current_app:
        app_ctx = app.app_context()
        app_ctx.push()
    try:
        if not isinstance(recipients, (list,)):
            recipients = recipients.split(';')


        sender = app.config['MAIL_DEFAULT_SENDER']
        msg = Message(subject=subject, recipients=recipients, charset='utf-8', html=html,
                      sender=sender, cc=cc, bcc=bcc)
        if attachment_list:
            for attachment_item in attachment_list:
                with app.open_resource(attachment_item.get('filepath')) as fp:
                    msg.attach(attachment_item.get('filename'), attachment_item.get('filetype'), fp.read())

        Mail(app).send(msg)
        print('Mail Sent Once to %s:' % (str(recipients)))
        logging.error('Mail Sent Once to %s:' % (str(recipients)))
        rt = True
    except Exception as e:
        logging.error('send_email error:'+e.__str__())
    return rt



def replace_string_expression_strict_by_map(strExpression, allPointRealtimeDataLMap={}):
    try:
        strExpressionNew = strExpression

        nFound = strExpression.find('<%')
        nFoundClose = strExpression.find('%>', nFound+1)

        strHavePointNameList = []
        while nFound>=0 and nFoundClose>nFound:
            strPointName = strExpression[nFound+2: nFoundClose]
            strHavePointNameList.append(strPointName)
            nFound = strExpression.find('<%', nFoundClose+1)
            nFoundClose = strExpression.find('%>', nFound + 1)

        for item in strHavePointNameList:
            strValue = allPointRealtimeDataLMap.get(item, None)
            if strValue is not None:
                strExpressionNew = strExpressionNew.replace('<%'+ item +'%>', strValue)

        return strExpressionNew



    except Exception as e:
        print('ERROR in replace_string_expression_strict:%s'%(e.__str__()))

    return strExpressionNew

# def tool_replace_string_with_value(strExpression, allPointRealtimeDataLMap):
#     rvDataList= []
#
#     if allPointRealtimeDataLMap is None:
#         return json.dumps(dict(err=1, msg='allPointRealtimeDataList param lost', data=-1), ensure_ascii=False)
#
#     try:
#
#         strExpressionModify = strExpression.replace('<%', '')
#         strExpressionModify = strExpressionModify.replace('%>', '')
#
#         p = re.compile(r'[a-zA-Z]+[a-zA-Z0-9_]+', re.IGNORECASE)
#
#         pointNameList = p.findall(strExpressionModify)
#         for pitem in pointNameList:
#             if pitem in ['and', 'or', 'is' 'None','True', 'False', 'sqrt', 'pow','exp', 'log', 'log10', 'ceil', 'floor',
#                         'fabs' ,'if', 'else' ]:
#                 continue
#             else:
#                 strVV = allPointRealtimeDataLMap.get(pitem)
#                 if strVV is not None:
#                     strExpressionModify = strExpressionModify.replace(pitem, strVV)
#
#         return strExpressionModify
#
#     except Exception as e:
#         strError  = 'ERROR in tool_replace_string_with_value :%s, expression:%s'%(e.__str__(), strExpression)
#         logging.error(strError)
#         return strExpressionModify
#
#     return strExpressionModify




def tool_eval_string_common(strExpression, strConditionExpressionList):
    rv = ''

    try:
        for item in strConditionExpressionList:
            exec(item)
        rv= eval(strExpression)


    except Exception as e:
        strError  = 'ERROR in tool_eval_string_common :%s, expression:%s'%(e.__str__(), strExpression)
        logging.error(strError)


    return rv



def get_mac_address_str():
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:].upper()
    #return '%s:%s:%s:%s:%s:%s' % (mac[0:2],mac[2:4],mac[4:6],mac[6:8],mac[8:10],mac[10:])
    return mac

def get_machine_code():
    nLicenseVersion = BEOPDataAccess.getInstance().getLicenseVersion()
    licenseManage = LicenseManage(nLicenseVersion)
    contentList = licenseManage.getVolumeSerialNumberList()
    volnumber = None
    if contentList and isinstance(contentList, list):
        volnumber = contentList[-1]
        for cc in contentList:
            if cc and len(cc) > len(volnumber):  # choose length more
                volnumber = cc

    else:
        return None

    strVolNumberMD5 = licenseManage.getMD5OfSerialNumber(volnumber)
    strMachineCode = strVolNumberMD5.replace("-", "_")
    return strMachineCode



def is_timer_trigger_hour(tLastLoop, tNow, hoursList):
    for hhitem in hoursList:
        try:
            hhitem_float = float(hhitem)
            hh = int(hhitem_float)
            mm = int(float(hhitem_float - hh)*60)
        except:
            continue
        if hh<0 or hh>=24:
            continue

        tPassPoint = tNow
        tPassPoint = tPassPoint.replace(hour= hh, minute=mm, second=0)
        if tLastLoop<tPassPoint and tNow>=tPassPoint:
            return True

    return False


def is_timer_trigger_weekday(tLastLoop, tNow, weekdayList):
    for dd in weekdayList:
        try:
            dd = int(dd)
        except:
            continue
        if dd <=0 or dd >= 8:
            continue



        if tLastLoop.weekday()!=(dd-1) and tNow.weekday()==(dd-1):
            return True

    return False

def is_timer_trigger_monthly(tLastLoop, tNow, monthdayList):
    for dd in monthdayList:
        try:
            dd = int(dd)
        except:
            continue
        if dd <=0 or dd >= 32:
            continue

        if tLastLoop.day!=dd and tNow.day==dd:
            return True

    return False

def find_vars_in_str(str):
    bFind = True
    allVars = []
    nIndexA = 0
    nIndexB = 0
    while bFind:
        nIndexA = str.find('<%', nIndexB)
        if nIndexA<0:
            break
        nIndexB = str.find('%>',nIndexA)
        if nIndexA>=0 and nIndexB>nIndexA:
            allVars.append(str[nIndexA+2: nIndexB])
        else:
            break

    return allVars

def replace_place_holder(strTarget, dictPlaceHolder):
    try:
        if isinstance(strTarget, str) and isinstance(dictPlaceHolder, dict):
            for key in dictPlaceHolder.keys():
                placeHolder = "{%s}" % key
                strTarget = strTarget.replace(placeHolder, dictPlaceHolder.get(key))
        else:
            strTarget = ""
    except:
        strTarget = ""
    return strTarget

def save_app_config_database():
    global g_app_config_database
    g_app_config_database = app.config['DATABASE']

def restore_app_config_database():
    app.config['DATABASE']  = g_app_config_database

def isValidDate(strDate, strFormat):
    res = False
    try:
        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res

def colorHexToRgb(colorBytes):
    colorRgb = {"r": 0, "g": 0, "b": 0}
    try:
        colorHex = colorBytes.decode("gbk").replace("#", "")
        colorDec = tuple(int(colorHex[i:i + 2], 16) for i in (0, 2, 4))
        colorRgb = dict(r=colorDec[0], g=colorDec[1], b=colorDec[2])

    except Exception as e:
        print(e.__str__())
    finally:
        return colorRgb

def get_multiple_values_for_persagy_controller_points_calc(strMultiple):
    try:
        pieces = strMultiple.split("|")
        jStart = pieces[0].split(":")[0]
        sStart = pieces[0].split(":")[1]
        jEnd = pieces[1].split(":")[0]
        sEnd = pieces[1].split(":")[1]
        return float(jStart), float(sStart), float(jEnd), float(sEnd)
    except:
        return None, None, None, None


def log_info_to_file(strLogFileName, strLogInfo):
    strCorePath = os.path.dirname(os.getcwd())
    strLogPath = os.path.join(strCorePath, 'dompysite')
    strLogPath = os.path.join(strLogPath, 'log')
    strLogFilePath = os.path.join(strLogPath, strLogFileName)

    tNow = datetime.now()
    with open(strLogFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S')+ '    ' + strLogInfo + '\n')

def get_proj_name():
    configPath = os.path.join(app.config["CORE_PATH"], "dompysite", "config.ini")
    name = None
    try:
        cf = ConfigObj(configPath, encoding="UTF8")
        name = cf["cloud"]["projectname"]
    except:
        pass
    return "Unknown" if name is None else name

def log_critical_event(strActor, strObject,  strContent):
    pathCoreLog = os.path.join(app.config["CORE_PATH"], 'log')
    pathDomHostLogFile = os.path.join(pathCoreLog, 'CRITICAL.txt')
    strContent += "\n"
    with open(pathDomHostLogFile, "a+") as f:
        f.write('%s\t%s\t%s\t%s'%(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), strActor, strObject, strContent))

def send_alert_to_cloud_center(strProjectName, strContent):
    try:
        strToken = "fa92187e426443d7a6a4a31677ebcd71b9f949634a174e92aa807030f30056b8"
        headers = {"content-type": "application/json"}

        postData = {
            "content": {
                "text": {
                    "content": "事件通知：{}".format(strContent)
                },
                "msgtype": "text"
            },
            "token": strToken,
            "source": "dompysite (project: {})".format(strProjectName)
        }

        url = "http://dom.inwhile.com/api/dingtalk/sendByCloud"

        rsp = requests.post(url, data=json.dumps(postData), headers=headers, timeout=15)
        rspData = json.loads(rsp.text)

        if isinstance(rspData, dict):
            if rspData.get("data", None):
                if rspData.get("data", {}).get("errcode") == 0:
                    return True

        return False
    except Exception as exp:
        logging.error("ERROR in send_alert_to_cloud_center: %s" % exp.__str__())
        return False

def inspect_domhost():

    if "domhost" not in app.config.get("MONITOR"):
        return True

    try:
        if not ProcessManager.getInstance().findProcess("redis-server.exe"):
            return None

        strTime = RedisManager.get("DomhostHeartBeatTime")
        if strTime is None:
            return None

        tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")

        if (datetime.now() - tTime).total_seconds() > 300:
            os.popen("taskkill /im domhost.exe -f")

            strMsg = "(projectName: {projectName}; CloudSetting: {CloudSetting}) Message from dompysite: It has been more " \
                     "than 5 minutes(currentTime: {currentTime}) after the latest updating of DomhostHeartBeatTime in Redis, " \
                     "executed the kill of domhost.exe".format(projectName=get_proj_name(), CloudSetting=app.config["CloudSetting"], currentTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            log_critical_event('dompysite.exe', "domhost.exe", strMsg)

            send_alert_to_cloud_center(get_proj_name(), strMsg)

            time.sleep(0.2)
            hostDir = os.path.join(app.config['CORE_PATH'], "domhost")
            ProcessManager.getInstance().startProcess("domhost.exe", hostDir)
            time.sleep(600)
            return True
        return None
    except Exception as e:
        logging.error("ERROR in inspect_domhost: %s" % e.__str__())
        return None

def get_mem_cpu_by_pid(pid):
    process = psutil.Process(pid)
    mem = process.memory_info()[0] / 1024 / 1024
    cpu = process.cpu_percent(interval=1) / psutil.cpu_count()
    return round(mem, 2), round(cpu, 2)

def get_pid(procNameList):
    procDict = {}
    for proc in psutil.process_iter():
        pid = proc.pid
        name = proc.name()
        if name in procNameList:
            procDict.update({name: pid})
    return procDict

def getCurrentSystemResource():
    try:
        infoDict = {}

        cpuLoad = psutil.cpu_percent()
        memoryLoad = psutil.virtual_memory().percent

        infoDict.update(dict(cpuLoadPercent=round(cpuLoad, 1), memoryLoadPercent=round(memoryLoad,1)))

        try:
            sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = win32file.GetDiskFreeSpace("C:")
            g_system_disk1_load = (1 - numFreeClusters / totalNumClusters) * 100.0
        except:
            g_system_disk1_load = -1

        try:
            sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = win32file.GetDiskFreeSpace("D:")
            g_system_disk2_load = (1 - numFreeClusters / totalNumClusters) * 100.0
        except:
            g_system_disk2_load = -1

        try:
            sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = win32file.GetDiskFreeSpace("E:")
            g_system_disk3_load = (1 - numFreeClusters / totalNumClusters) * 100.0
        except:
            g_system_disk3_load = -1

        if g_system_disk1_load >= 0:
            infoDict.update(dict(disk1LoadPercent=round(g_system_disk1_load,1)))
        if g_system_disk2_load >= 0:
            infoDict.update(dict(disk2LoadPercent=round(g_system_disk2_load, 1)))
        if g_system_disk3_load >= 0:
            infoDict.update(dict(disk3LoadPercent=round(g_system_disk3_load, 1)))

        infoDict.update(dict(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        dPid = get_pid(["domcore.exe", "domlogic.exe", "domModbusClientCore.exe", "domSiemenseTCPCore.exe",
                        "domBackupMysql.exe", "domCloudSync.exe", "domLogixCore.exe", "domModbusServer.exe",
                        "domMoxaTelnetCore.exe", "domOPCUACore.exe", "dompysite.exe", "domSpaceClean.exe",
                        "domUpload.exe"])

        memCpuInfoList = []
        for procName, pid in dPid.items():
            mem, cpu = get_mem_cpu_by_pid(pid)
            memCpuInfoList.append((procName, mem, cpu))

        memInfoList = cpuInfoList = memCpuInfoList

        # 整理内存信息
        for i in range(len(memInfoList)):
            for j in range(0, len(memInfoList) - i - 1):
                if memInfoList[j][1] < memInfoList[j + 1][1]:
                    memInfoList[j], memInfoList[j + 1] = memInfoList[j + 1], memInfoList[j]

        iMemInfoList = iter(memInfoList)
        memList = []
        idx = 0
        while idx < 5:
            try:
                next = iMemInfoList.__next__()
                memList.append((next[0], next[1]))
            except StopIteration:
                break
            idx += 1

        # 整理cpu信息
        for i in range(len(cpuInfoList)):
            for j in range(0, len(cpuInfoList) - i - 1):
                if cpuInfoList[j][2] < cpuInfoList[j + 1][2]:
                    cpuInfoList[j], cpuInfoList[j + 1] = cpuInfoList[j + 1], cpuInfoList[j]

        iCpuInfoList = iter(cpuInfoList)
        cpuList = []
        idx = 0
        while idx < 5:
            try:
                next = iCpuInfoList.__next__()
                cpuList.append((next[0], next[2]))
            except StopIteration:
                break
            idx += 1

        infoDict.update({"memoryTop": memList})
        infoDict.update({"cpuTop": cpuList})

        return dict(code=0, data=infoDict)

    except Exception as e:
        logging.error("ERROR in getCurrentSystemResource: %s" % e.__str__())
        return dict(code=1, data={})


def zip_folder(strDir, zipf):
    res = False
    try:
        for root, dirs, files in os.walk(strDir):
            for file in files:
                fileFullPath = os.path.join(strDir, file)
                zipf.write(fileFullPath, file)
                time.sleep(0.2)
        res = True
    except:
        pass
    finally:
        return res

"""
获取故障维度的英文名称
"""
def get_fault_view_en_name(viewZh):
    viewEnMap = {"类型": "category", "位置": "position", "介质": "medium"}
    return viewEnMap.get(viewZh, None)

def is_english_word(word):
    bIs = True
    for char in word:
        if (char >= u'\u0041' and char <= u'\u005a') or (char >= u'\u0061' and char <= u'\u007a'):
            bIs = True
        else:
            bIs = False
            break
    return bIs

def find_domcore_or_domlogic_log_of_one_day(strDate, strProcess):
    logFilePathList = []
    try:
        domcoreLogDir = os.path.join(app.config["CORE_PATH"], "log")
        tDate = datetime.strptime(strDate, "%Y-%m-%d")

        pattern = r"^core_err_{strDate}.*.log$".format(strDate=tDate.strftime("%Y_%m_%d"))
        for rootDir, dirs, fileNames in os.walk(domcoreLogDir):
            for fileName in fileNames:
                if re.match(pattern, fileName):
                    logFilePathList.append(
                        os.path.join(app.config["CORE_PATH"], "log", fileName)
                    )

        if strProcess == "domSiemenseTCPCore":
            logDir = os.path.join(app.config["CORE_PATH"], "domSiemenseTCPCore", "log")
            if not os.path.exists(logDir):
                return dict(code=0, msg="目录不存在:%s" % logDir, data=[])

            pattern1 = r"^domSiemenseCore_{strDate}.*.log$".format(strDate=tDate.strftime("%Y_%m_%d"))
            pattern2 = r"^core_err_{strDate}.*.log$".format(strDate=tDate.strftime("%Y_%m_%d"))
            pattern3 = r"^err_{strDate}.*.log$".format(strDate=tDate.strftime("%Y_%m_%d"))
            for rootDir, dirs, fileNames in os.walk(logDir):
                for fileName in fileNames:
                    if re.match(pattern1, fileName) or re.match(pattern2, fileName) or re.match(pattern3, fileName):
                        logFilePathList.append(
                            os.path.join(app.config["CORE_PATH"], "domSiemenseTCPCore", "log", fileName)
                        )

        return dict(code=0, msg="", data=logFilePathList)

    except Exception as e:
        logging.error("ERROR in find_domcore_or_domlogic_log_of_one_day: %s" % e.__str__())
        return dict(code=1, msg="获取失败: %s" % e.__str__(), data=[])


def find_other_process_log_of_one_day(strDate, strProcess):
    try:
        isToday = True if datetime.now().strftime("%Y-%m-%d") == strDate else False
        processDir = os.path.join(app.config["CORE_PATH"], strProcess)

        if not os.path.exists(processDir):
            return dict(code=1, msg="core目录下无{process}".format(process=strProcess), data=[])

        logDir = os.path.join(processDir, "log")
        if not os.path.exists(logDir):
            return dict(code=1, msg="{process}目录下无log目录".format(process=strProcess), data=[])

        filePathList = []
        for root, dirs, files in os.walk(logDir):
            for file in files:
                if isToday:
                    strReg = "^{proc}_log$".format(proc=strProcess)
                    if not re.match(strReg, file):
                        continue
                    filePathList.append(os.path.join(logDir, file))
                else:
                    if file.find(strDate) != -1:
                        filePathList.append(os.path.join(logDir, file))

        return dict(code=0, msg="", data=filePathList)

    except Exception as e:
        logging.error("ERROR in find_other_process_log_of_one_day: %s" % e.__str__())
        return dict(code=1, msg="获取失败: {0}".format(e.__str__()), data=[])

def zip_process_log(date, process, logFilePathList):
    try:
        if not len(logFilePathList):
            return dict(code=1, msg="未找到任何符合查询条件的log文件", data="")

        zipFileName = "{process}-log-{date}.zip".format(process=process, date=date)

        filesDir = os.path.join(app.static_folder, "files")
        if not os.path.exists(filesDir):
            os.mkdir(filesDir)

        tempDir = os.path.join(filesDir, "temp")
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        zipFilePath = os.path.join(tempDir, zipFileName)
        if os.path.exists(zipFilePath):
            os.remove(zipFilePath)

        logZipDir = os.path.join(tempDir, "{process}-log-{date}".format(process=process, date=date))
        if not os.path.exists(logZipDir):
            os.mkdir(logZipDir)

        for filePath in logFilePathList:
            if not os.path.exists(filePath):
                continue

            logFileNameWithExt = os.path.split(filePath)[1]
            logZipFilePath = os.path.join(logZipDir, logFileNameWithExt)

            if os.path.exists(logZipFilePath):
                os.remove(logZipFilePath)

            shutil.copyfile(filePath, logZipFilePath)

        zipObj = zipfile.ZipFile(zipFilePath, "w", zipfile.ZIP_DEFLATED)
        bSucZip = zip_folder(logZipDir, zipObj)

        shutil.rmtree(logZipDir)

        if bSucZip:
            return dict(code=0, msg="", data=os.path.join("static", "files", "temp", zipFileName))
        return dict(code=1, msg="", data="")
    except Exception as e:
        strLog = "ERROR in zip_process_log: %s" % e.__str__()
        logging.error(strLog)
        return dict(code=1, msg=strLog, data="")

def city_name_convertor(strCityId):
    rsp = requests.get('http://dom.inwhile.com/api/s6/weather/getCnCityNameById?CityId=%s' % strCityId, verify=False, timeout=30)
    if rsp.status_code != 200:
        return ""
    dJson = json.loads(rsp.text)
    return dJson.get("data", "")

def api_log_info(strFileName, strLog):
    strLogDir = os.path.join(os.getcwd(), "log")
    if not os.path.exists(strLogDir):
        os.mkdir(strLogDir)

    apiLogDir = os.path.join(strLogDir, "api")
    if not os.path.exists(apiLogDir):
        os.mkdir(apiLogDir)

    logFilePath = os.path.join(apiLogDir, strFileName)

    tNow = datetime.now()
    with open(logFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S')+ '    ' + strLog + '\n')

def find_full_path_of_executable_file(executable, path=None):
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    extlist = ['']
    if os.name == 'os2':
        (base, ext) = os.path.splitext(executable)
        # executable files on OS/2 can have an arbitrary extension, but
        # .exe is automatically appended if no dot is present in the name
        if not ext:
            executable = executable + ".exe"
    elif sys.platform == 'win32':
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in pathext:
            extlist = pathext
        # Windows looks for binaries in current dir first
        paths.insert(0, '')

    for ext in extlist:
        execname = executable + ext
        for p in paths:
            f = os.path.join(p, execname)
            if os.path.isfile(f):
                return f
    else:
        return None


def get_standard_modbus_equipment_define_from_cloud():
    key = "standard_modbus_equipment_define_from_cloud"
    tempDir = os.path.join(app.static_folder, 'temp')
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    localFilePath = os.path.join(tempDir, "StandardModbusEquipmentDefine_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    tool = OSSTool()
    bSuc = tool.download("update/dbwizard/StandardModbusEquipment/StandardModbusEquipmentDefine.json", localFilePath)
    if not bSuc:
        return False, {}

    with open(localFilePath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            return False, {}

    if dJson:
        dCur = dict(updateTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), define=dJson)
        RedisManager.set(key, dCur)

    try:
        os.remove(localFilePath)
    except:
        pass
    return True, dJson

"""
用于频繁获取StandardModbusEquipmentDefine.json
"""
def get_standard_modbus_equipment_define_from_cloud_frequent():
    key = "standard_modbus_equipment_define_from_cloud"
    dCur = RedisManager.get(key)
    if not isinstance(dCur, dict):
        dCur = {}

    strUpdateTime = dCur.get("updateTime", None)
    tUpdateTime = None
    try:
        tUpdateTime = datetime.strptime(strUpdateTime, "%Y-%m-%d %H:%M:%S")
    except:
        pass

    # 若在24小时之内则直接返回redis中的缓存
    if isinstance(tUpdateTime, datetime):
        if (datetime.now() - tUpdateTime).total_seconds() < 3600 * 24:
            dDefine = dCur.get("define", None)
            if isinstance(dDefine, dict) and dDefine:
                return dDefine

    # 否则去oss取新的
    tempDir = os.path.join(app.static_folder, 'temp')
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    localFilePath = os.path.join(tempDir, "StandardModbusEquipmentDefine_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    tool = OSSTool()
    bSuc = tool.download("update/dbwizard/StandardModbusEquipment/StandardModbusEquipmentDefine.json", localFilePath)
    if not bSuc:
        try:
            os.remove(localFilePath)
        except:
            pass
        return {}

    with open(localFilePath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dDefine = json.load(fo)
        except:
            dDefine = {}

    if dDefine:
        dCur = dict(updateTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), define=dDefine)
        RedisManager.set(key, dCur)

    try:
        os.remove(localFilePath)
    except:
        pass
    return dDefine


def get_equipment_attr(tar):
    if tar.find("PriChWP") >= 0:
        return "一次冷冻泵"
    if tar.find("SecChWP") >= 0:
        return "二次冷冻泵"
    if tar.find("AirCompressor") >= 0:
        return "空压机"
    if tar.find("Dryer") >= 0:
        return "干燥机"
    if tar.find("Boiler") >= 0:
        return "锅炉"
    if tar.find("CTFan") >= 0:
        return "冷却塔风机"
    if tar.find("HWP") >= 0:
        return "热水泵"
    if tar.find("CWP") >= 0:
        return "冷却泵"
    if tar.find("CT") >= 0:
        return "冷却塔"
    if tar.find("Ch") >= 0:
        return "冷机"
    return ""

def get_modbus_equip_type_en(dModbusEquipmentPointDefine, strType):
    return dModbusEquipmentPointDefine.get(strType, {}).get("equipTypeEn", "")

def get_modbus_equip_type_ch(dModbusEquipmentPointDefine, strType):
    return dModbusEquipmentPointDefine.get(strType, {}).get("equipTypeCh", "未知设备类型")

def get_modbus_equip_brand(dModbusEquipmentPointDefine, strType):
    return dModbusEquipmentPointDefine.get(strType, {}).get("brand", "未知品牌")

def get_modbus_equip_model(dModbusEquipmentPointDefine, strType):
    return dModbusEquipmentPointDefine.get(strType, {}).get("model", "未知型号")


def get_int_from_rgb(nR, nG, nB):
    nRgb = nB << 16 | nG << 8 | nR
    return nRgb

def get_r_from_int(nInt):
    if not isinstance(nInt, int):
        try:
            nInt = int(nInt)
        except:
            nInt = 0
    return nInt & 255

def get_g_from_int(nInt):
    if not isinstance(nInt, int):
        try:
            nInt = int(nInt)
        except:
            nInt = 0
    return (nInt >> 8) & 255

def get_b_from_int(nInt):
    if not isinstance(nInt, int):
        try:
            nInt = int(nInt)
        except:
            nInt = 0
    return (nInt >> 16) & 255

def get_hex_from_rgb(nR, nG, nB):
    hexr = hex(nR).replace("0x", "").rjust(2, "0")
    hexg = hex(nG).replace("0x", "").rjust(2, "0")
    hexb = hex(nB).replace("0x", "").rjust(2, "0")

    strHex = ""
    strHex += hexr
    strHex += hexg
    strHex += hexb
    return strHex

def update_startup_time():
    try:
        key = "StartupTimeDompysite"
        if not ProcessManager.getInstance().findProcess("redis-server.exe"):
            return

        dCur = RedisManager.get(key)
        if not isinstance(dCur, dict):
            dCur = {}

        dCur.update(dict(startup=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        RedisManager.set(key, dCur)
    except Exception as e:
        logging.error("ERROR in update_startup_time: %s" % e.__str__())




