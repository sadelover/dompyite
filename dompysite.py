import sys
import os
import logging
import copy
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, json, jsonify
import mysql.connector
from datetime import datetime, timedelta
from math import ceil
from math import floor
from siteinterface import app
from siteinterface.BEOPDataAccess import *
from siteinterface.BEOPMySqlDBContainer import *
from siteinterface.DataSaveThread import *
from siteinterface.views import *
from siteinterface.observer import *
from siteinterface.user import *
from siteinterface.SiteTool import SiteTool
from siteinterface.mod_logic import bp_logic
from siteinterface.mod_env import bp_env
from siteinterface.mod_mode import bp_mode
from siteinterface.mod_calendar import bp_calendar
from siteinterface.mode_fix import bp_fix
from siteinterface.mod_fdd import bp_fdd
from siteinterface.mod_system import bp_system
from siteinterface.mod_equipment import bp_equipment
from siteinterface.mod_deviceManage import bp_deviceManage
from siteinterface.mod_care import bp_care
from siteinterface.mod_rps import bp_rps
from siteinterface.mod_network import bp_network
from siteinterface.mod_wizard import bp_wizard
from siteinterface.mod_modscan import bp_modscan
from siteinterface.mod_page import bp_page

from siteinterface.mod_fdd.utils import inspect_work_order_on_time

from win32event import CreateMutex
from win32api import CloseHandle, GetLastError, ShellExecute
from winerror import ERROR_ALREADY_EXISTS
from version import siteVersion
from siteinterface.RedisManager import RedisManager
from configobj import ConfigObj
import zipfile
import calendar

from logic.Utils import *
from logic.LogOperator import LogOperator
from logic.LogicDefine import LogicBase
from logic.Timer import CronTab
from logic.Config import *
from logic.SocketOperator import SocketOperator
from logic.SQLiteOperator import SQLiteOperator
import requests
import win32file  # 导入方法模块

from siteinterface.utils import is_timer_trigger_hour, is_timer_trigger_weekday, is_timer_trigger_monthly, inspect_domhost, update_startup_time

import winreg
from siteinterface.config import config
import sys, os
from logging.handlers import TimedRotatingFileHandler
import logging

from siteinterface.UtilNetSpeed import *
import shutil
import subprocess
import win32api
import psutil
import os
import logging
import subprocess
import win32api, win32con
from siteinterface.BEOPMySqlDBContainer import g_mysql_last_pool_exhaust_time


g_calculation_points_lock = threading.Lock()
g_vpointCalculationList = dict()

g_report_first_run = True
g_report_last_loop = datetime.now()

g_calculation_realtimedata = {}
g_calculation_threads_num = 6 #60个无法支撑，用15个



app.register_blueprint(bp_project)
app.register_blueprint(bp_point)
app.register_blueprint(bp_logic)
app.register_blueprint(bp_env)
app.register_blueprint(bp_mode)
app.register_blueprint(bp_calendar)
app.register_blueprint(bp_fix)
app.register_blueprint(bp_fdd)
app.register_blueprint(bp_system)
app.register_blueprint(bp_equipment)
app.register_blueprint(bp_deviceManage)
app.register_blueprint(bp_care)
app.register_blueprint(bp_rps)
app.register_blueprint(bp_network)
app.register_blueprint(bp_wizard)
app.register_blueprint(bp_modscan)
app.register_blueprint(bp_page)




@app.route('/calc_module_interface', methods=['POST'])
def my_post():
    text = ''
    mydata = request.form
    dict = mydata.to_dict()
    for key in dict:
        text = key
        break

    strContent = '# -*- encoding=utf-8 -*-\n' \
                 'from logic.MySQLOperator import MySQLOperator as mysql\n\n' \
                 'from logic.API import *\n\n'
    strContent += text

    dtNow = datetime.now()
    start = dtNow.strftime('%m%d%H%M%S%f')
    name = 'temp_' + start
    try:
        result = LogicBase.makeFileAndRun(name, strContent)
    except Exception as e:
        print('calc_module_interface ERROR: ' + e.__str__())
    if result == None:
        result = ''
    else:
        result = str(result)
    return result


class singleinstance:
    """ Limits application to single instance """

    def __init__(self):
        self.mutexname = heartbeat_config.get('cmd')
        if app.config['RUN_PORT'] not in [5000,5432]:
            self.mutexname += str(app.config['RUN_PORT'])

        self.mutex = CreateMutex(None, False, self.mutexname)
        self.lasterror = GetLastError()

    def aleradyrunning(self):
        return (self.lasterror == ERROR_ALREADY_EXISTS)

    def __del__(self):
        if self.mutex:
            CloseHandle(self.mutex)


class ProcessManager:
    __instance = None

    def __init__(self):
        pass

    @classmethod
    def getInstance(self):
        if (self.__instance == None):
            self.__instance = ProcessManager()
        return self.__instance

    def findProcess(self, strProcessName):
        pid = []
        self.pidNotHandle = list(psutil.process_iter())  # 获取当前计算机的pid
        for each in self.pidNotHandle:
            a = str(each)  # each 是class 类型 ，可用type（each） 查看类型
            # a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
            if each.name() == strProcessName:
                return each

        return None

    def findProcessWithMemoryBigFirst(self, strProcessName):
        self.pidNotHandle = list(psutil.process_iter())  # 获取当前计算机的pid
        fMemoryMax = 0
        rtProcess = None
        for each in self.pidNotHandle:
            a = str(each)  # each 是class 类型 ，可用type（each） 查看类型
            # a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
            if each.name() == strProcessName:
                fMemoryMB = each.memory_info().rss / 1024.0 / 1024.0
                if fMemoryMB > fMemoryMax:
                    rtProcess = each
                    fMemoryMax = fMemoryMB

        return rtProcess

    def startProcess(self, processExeName, workPath):
        try:
            # 需要添加两个不同的执行路径，modbusServer 和 modbusClient
            proeceePath = os.path.join(workPath, processExeName)
            # print(proeceePath)
            if os.path.exists(workPath) == False:
                logging.error("domhost寻找不到可执行文件目录，期望为 %s 目录，本次运行监护对象失败", workPath)
                return False
            else:
                if os.path.exists(proeceePath) == False:
                    logging.error("domhost寻找不到监护对象可执行文件，期望为 %s 目录 %s 文件 ，本次运行监护对象失败", workPath, processExeName)
                    return False
                else:
                    win32api.ShellExecute(0, 'open', proeceePath, '', self._strProcessWorkPath, 1)
                    return True

        except Exception as e:
            logging.error(e.__str__())

        return True

    def restartOS(self):
        try:
            os.popen("shutdown -r -f -t 0")
        except Exception as e:
            logging.error('ERROR in ProcessManager::RestartOS():' + e.__str__())
            return False

        return True


# 心跳包线程
def startThreadHeartBeat():
    try:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + '心跳包任务启动', False)
        thread = CronTab("ThreadHeartBeat", SocketOperator.sendHeartbeat, (), heartbeat_config.get('period', 60))
        thread.setDaemon(True)
        thread.start()
    except Exception as e:
        LogOperator().writeLog('RunMain startThreadHeartBeat error, %s:' % (get_current_func_name()) + e.__str__())


# 策略、任务线程
def startThreadTask():
    try:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + '定时任务启动', False)
        thread = CronTab("ThreadSyncTask", LogicBase.actLogic, (), task_config.get('period'))
        thread.setDaemon(False)
        thread.start()
    except Exception as e:
        LogOperator().writeLog('RunMain startThreadTask error, %s:' % (get_current_func_name()) + e.__str__())


def startThreadUpdate(period):
    try:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + '定时任务启动', False)
        thread = CronTab("ThreadSyncUpdate_%d" % (period), LogicBase.actLogic, str(period), period)
        thread.setDaemon(False)
        thread.start()
    except Exception as e:
        LogOperator().writeLog('RunMain startThreadUpdate error, %s:' % (get_current_func_name()) + e.__str__())


def startThreadUpdateEx(name, period):
    try:
        name = str(name)
        period = int(period)
        LogOperator().writeLog('%s:' % (get_current_func_name()) + '定时任务启动', False)
        thread = CronTab("ThreadSyncUpdate_%s_%d" % (name, period), LogicBase.actLogic, [name, period], period)
        thread.setDaemon(False)
        thread.start()
    except Exception as e:
        LogOperator().writeLog('RunMain startThreadUpdateEx error, %s:' % (get_current_func_name()) + e.__str__())


g_last_op = {}
g_last_realtime_data = {}
g_last_realtime_data_send_time = None


def getIndex(a, array):
    for i in range(len(array)):
        if a[0] == array[i][0] and a[1] == array[i][1] and a[2] == array[i][2]:
            return i
    return -1


def postDataToServer(dataAllList, strProjName, strServerURL, strTimeHappen):
    if dataAllList:
        headers = {'content-type': 'application/json'}

        nCurIndex = 0
        pointList = []
        valueList = []

        for item in dataAllList:
            nCurIndex += 1
            pointList.append(item[1])
            valueList.append(item[2])
            if nCurIndex >= 3000:
                post_data = {}
                post_data.update({'projName': strProjName,
                                  'point': pointList,
                                  'value': valueList,
                                  'time': strTimeHappen
                                  })
                # 插入测试数据
                r = requests.post('http://%s/set_realtimedata_from_site' % (strServerURL), data=json.dumps(post_data),
                                  headers=headers, timeout=300)
                nCurIndex = 0
                pointList = []
                valueList = []

        if pointList:
            post_data = {}
            post_data.update({'projName': strProjName,
                              'point': pointList,
                              'value': valueList,
                              'time': strTimeHappen
                              })
            # 插入测试数据
            try:
                r = requests.post('http://%s/set_realtimedata_from_site' % (strServerURL), data=json.dumps(post_data),
                                  headers=headers, timeout=300)
            except Exception as e:
                logging.error('ERROR when data upload to server:' + e.__str__())


def execute_command(cmd):
    print('start executing cmd...')
    try:
        s = subprocess.Popen(str(cmd), stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        stderrinfo, stdoutinfo = s.communicate()
        print('stderrinfo is -------> %s and stdoutinfo is -------> %s' % (stderrinfo, stdoutinfo))
        print('finish executing cmd....')
        return s.returncode
    except Exception as e:
        logging.error('ERROR in execute_command: ' + e.__str__())

    return 0


def autoGenPointDataReportForDownload(args):
    tLastGen = datetime.now() - timedelta(days=30)
    lastConfig = None
    while True:

        now_time = datetime.now()
        nDeltaMinutes = (now_time - tLastGen).total_seconds() / 60.0

        try:
            systemConfig = BEOPSqliteAccess.getInstance('autoGenPointDataReportForDownload').getValueByKeyInLocalConfig('globalconfig')
            if systemConfig:
                jsonSystem = json.loads(systemConfig)
                allconfig = jsonSystem.get('dataExportReportConfig')
                if allconfig != lastConfig or (
                        allconfig == lastConfig and nDeltaMinutes > 12 * 60 and now_time.hour == 1):
                    lastConfig = allconfig  # record
                    ptList = allconfig.get('pointList')
                    strStartTime = allconfig.get('timeStart')
                    tEndLastDay = now_time.replace(hour=23, minute=59, second=59)
                    tEndLastDay = tEndLastDay - timedelta(days=1)
                    strEndTime = tEndLastDay.strftime('%Y-%m-%d %H:%M:%S')
                    strReportName = allconfig.get('reportName')
                    strPeriod = allconfig.get('timeFormat')

                    if ptList:
                        generate_report_for_points(ptList, strStartTime, strEndTime, strReportName, strPeriod)


        except Exception as e:
            logging.error('ERROR in read globalconfig : its not json! %s' % (e.__str__()))
            time.sleep(600)
            continue

        tLastGen = now_time

        time.sleep(60)


def remove_dir(strDir):
    res = False
    count = 0
    while count < 5:
        if os.path.exists(strDir):
            try:
                shutil.rmtree(strDir)
                res = True
            except:
                count += 1
                time.sleep(1)
        else:
            res = True
            break
    return res


"""
获取下个月的第一天
"""


def get_date_of_next_month(curDate):
    res = None
    try:
        if not isinstance(curDate, datetime):
            return None

        tNextMonth = curDate.replace(day=28) + timedelta(days=4)
        res = tNextMonth.replace(day=1)
    except:
        pass
    finally:
        return res


"""
判断表是否存在
"""


def table_exists(dbm, strDbname, strTableName):
    res = False
    try:
        strQuery = """SELECT * FROM %s LIMIT 1""" % strTableName
        sql_arr = dbm.op_db_query(strDbname, strQuery)
        if len(sql_arr):
            res = True
    except:
        pass
    finally:
        return res


"""
需要在dompysite\config.ini里面的mysql下配置：
backupto = yyyy_mm_dd    #上次备份截止日期，首次需要添加
mysqlBackupExecuteHour = 2    #备份执行小时，若不配置则程序中默认2时
mysqldumpToolDir    # mysqldump.exe的绝对路径
"""


def backupMySQL(args):
    succeedToBackupInThisHour = False
    while True:
        try:
            cwd = os.getcwd()
            strCoreDir = os.path.dirname(cwd)
            strDompysiteDir = os.path.join(strCoreDir, "dompysite")
            strConfigPath = os.path.join(strDompysiteDir, "config.ini")
            config = ConfigObj(strConfigPath, encoding="UTF8")

            mysqlBackupExecuteHour = 2
            if config.get("mysql"):
                if config.get("mysql").get("mysqlBackupExecuteHour"):
                    try:
                        mysqlBackupExecuteHour = int(config.get("mysql").get("mysqlBackupExecuteHour"))
                    except:
                        pass

            else:
                strError = "mysql config not found in config.ini"
                print(strError)
                logging.error(strError)
                time.sleep(60 * 10)
                continue

            # 判断是否到备份时间
            if datetime.now().hour != mysqlBackupExecuteHour:
                succeedToBackupInThisHour = False
                time.sleep(60 * 10)
                continue

            # 判断这个小时内是否已经备份过
            if succeedToBackupInThisHour == True:
                time.sleep(60 * 10)
                continue

            strProcessName = "domBackupMysql.exe"
            try:
                pInfo = ProcessManager.getInstance().findProcess(strProcessName)
                if not pInfo:
                    logging.error("{0} process doesn't exist, starting...".format(strProcessName))
                    print("{0} process doesn't exist, starting...".format(strProcessName))

                    strExeDir = os.path.join(strCoreDir, "domBackupMysql")
                    strExeFile = os.path.join(strExeDir, "domBackupMysql.exe")

                    if not os.path.exists(strExeFile):
                        strError = 'ERROR in ProcessExistHost start process but not found:  %s' % (strProcessName)
                        logging.error(strError)
                        print(strError)
                        return False

                    win32api.ShellExecute(0, "open", strExeFile, "", strExeDir, 1)
                    logging.error("{0} restarted successfully".format(strProcessName))
                    print("{0} restarted successfully".format(strProcessName))
                    succeedToBackupInThisHour = True
                else:
                    logging.error('{0} is now in process list, it is working.'.format(strProcessName))
            except:
                logging.error('ERROR in backupMysql: %s' % (e.__str__()))
                time.sleep(60)
                continue

        except Exception as e:
            logging.error('ERROR in backupMysql: %s' % (e.__str__()))
            print('ERROR in backupMysql: %s' % (e.__str__()))

        time.sleep(60 * 10)


def getDBFileModifiedTime():
    if app.config.get("USE_4DB_FILE_FORMAT"):
        dbfile = app.config.get("USE_4DB_NAME")

        if not os.path.exists(dbfile):
            return None

        return time.localtime(os.stat(dbfile).st_mtime)
    else:
        dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
        dbfileDec = '{}.dec'.format(dbfile)

        if not os.path.exists(dbfileDec):
            return None

        return time.localtime(os.stat(dbfile).st_mtime)

    return None


def regenCalculationList():
    rv = BEOPSqliteAccess.getInstance('regenCalculationList').GetVPointCalculationList()

    g_calculation_points_lock.acquire()
    g_vpointCalculationList.clear()
    for item in rv:
        nPeriod = g_calculation_threads_num
        try:
            nPeriod = int(float(item.get('period'))/5)
            if nPeriod > g_calculation_threads_num:
                nPeriod = g_calculation_threads_num
            elif nPeriod <= 0:
                nPeriod = 1
        except:
            nPeriod = g_calculation_threads_num

        #过滤，凡是有get_开头的都纳入60S，凡是没有的都纳入16及以下
        strExpression = item.get('expression')
        if strExpression:
            if 'get_' in strExpression or 'accum_' in strExpression:
                if nPeriod<g_calculation_threads_num:
                    nPeriod = g_calculation_threads_num #random.randint(14,16)
            else:
                if nPeriod>=g_calculation_threads_num:
                    nPeriod = random.randint(1,g_calculation_threads_num-1)


        if not g_vpointCalculationList.get(nPeriod):
            g_vpointCalculationList[nPeriod] = []

        g_vpointCalculationList[nPeriod].append(item)
    g_calculation_points_lock.release()


def vpointUpdate(args):
    global g_vpointCalculationList
    global g_calculation_points_lock, g_calculation_realtimedata
    tdbFileModifiedTime = getDBFileModifiedTime()
    g_vpointCalculationList
    regenCalculationList()
    while True:
        try:
            tdbFileModifiedTime_New = getDBFileModifiedTime()
            if tdbFileModifiedTime != tdbFileModifiedTime_New:
                regenCalculationList()
                tdbFileModifiedTime = tdbFileModifiedTime_New

            tempReal = BEOPDataAccess.getInstance().getInputTable(None)[0]
            g_calculation_points_lock.acquire()
            g_calculation_realtimedata = copy.deepcopy(tempReal)
            g_calculation_points_lock.release()

        except Exception as e:
            pass

        time.sleep(5)


def vpointCalculation(args):
    tLastRecord = datetime.now()
    while True:
        try:

            myCalculationList = []

            g_calculation_points_lock.acquire()
            if g_vpointCalculationList.get(args):
                myCalculationList = copy.deepcopy(g_vpointCalculationList.get(args))

            if len(myCalculationList) == 0:
                g_calculation_points_lock.release()
                time.sleep(60)
                continue

            myRealtimeAll = copy.deepcopy(g_calculation_realtimedata)
            g_calculation_points_lock.release()

            if not myRealtimeAll:
                time.sleep(15)
                continue
            strLogCalFileName = 'dompysite_calculation_%s_%s.log'%(str(args),datetime.now().strftime('%Y_%m_%d'))
            log_info_to_file(strLogCalFileName,  'Start Calculation Virtual Points Updated Count' )
            pnameList = []
            pvalueList = []
            tStart = datetime.now()
            calInfoAll = {}
            for pp in myCalculationList:
                try:
                    tEvaStart = datetime.now()
                    strEvaResult = eval_string_expression_strict(pp.get('expression'), '1', '', myRealtimeAll)
                    tDelta = (datetime.now()-tEvaStart).total_seconds()
                    calInfoAll[pp.get('name')] = '%.1f'%(tDelta)
                    if tDelta>=30:
                        strError = 'SLOW CALCULATION in vpointCalculation pool(%s) point define(%s) :cost %d seconds' % (
                            str(args), str(pp), int(tDelta))
                        logging.error(strError)
                        print(strError)
                    if strEvaResult is not None:
                        pnameList.append(pp.get('name'))
                        pvalueList.append(strEvaResult)
                    else:
                        pass
                except Exception as e2:
                    strError = 'ERROR in vpointCalculation pool(%s) point define(%s) :%s' % (
                        str(args), str(pp), e2.__str__())
                    logging.error(strError)
                    print(strError)

            tNow = datetime.now()

            if len(pnameList) > 0:
                BEOPDataAccess.getInstance().setRealtimeData(pnameList, pvalueList)
                if (tNow - tLastRecord).total_seconds() >= 60 * 5:
                    BEOPDataAccess.getInstance().addLogicOutputRecordMul(tNow.strftime('%Y-%m-%d %H:%M:%S'), pnameList,
                                                                         pvalueList, 'SYS_VPOINT_CAL')
                    tLastRecord = tNow
            tDelta = (datetime.now() - tStart).total_seconds()

            log_info_to_file(strLogCalFileName, str(calInfoAll))
            log_info_to_file(strLogCalFileName,
                    'Finish Calculation(Thread:%d) Virtual Points Updated Count:%d,Spent: %.1f seconds\r\n\r\n' % (args, len(pnameList), tDelta))


        except Exception as e:
            strError = 'ERROR in vpointCalculation pool(%s) :%s' % (str(args), e.__str__())
            logging.error(strError)
            print(strError)
        time.sleep(args*4)

'''
启动时自动存储本月起点、本日起点
跨天时自动存储
'''
def updateRedis(args):
    tActLast = datetime.now() - timedelta(days=1)

    #启动时准备小时缓存
    if not RedisManager.is_alive():
        app.config['REDIS_ALIVE'] = False
    else:
        app.config['REDIS_ALIVE'] = True
        #prepare this day begin and month begin
        logging.error('[REDIS_Data_Prepare] Start 1')

        BEOPDataAccess.getInstance().updateRedisDataHoursOfMonth(tActLast)
        logging.error('[REDIS_Data_Prepare] Start 2')
        #tTodayBegin = tActLast.replace(hour=0, minute=0, second=0)
        #BEOPDataAccess.getInstance().updateRedisData(tTodayBegin.strftime("%Y-%m-%d %H:%M:%S"), 'h1')
        #tThisMonthBegin = tActLast.replace(day=1, hour=0, minute=0, second=0)
        #BEOPDataAccess.getInstance().updateRedisData(tThisMonthBegin.strftime("%Y-%m-%d %H:%M:%S"), 'h1')
        #tCur = tTodayBegin
        #while tCur> tThisMonthBegin:
        #    tCur = tCur - timedelta(days=1)
        #    BEOPDataAccess.getInstance().updateRedisData(tCur.strftime("%Y-%m-%d %H:%M:%S"), 'h1')

        logging.error('REDIS Data Prepare Finish')

    #启动时准备之前三天的分钟缓存
    logging.error('[REDIS_Data_Prepare] Start updateRedisDataMinutesOfDay day0')
    BEOPDataAccess.getInstance().updateRedisDataMinutesOfDay(tActLast)
    logging.error('[REDIS_Data_Prepare] Start updateRedisDataMinutesOfDay day1')
    BEOPDataAccess.getInstance().updateRedisDataMinutesOfDay((tActLast-timedelta(days=1)))
    logging.error('[REDIS_Data_Prepare] Start updateRedisDataMinutesOfDay day2')
    BEOPDataAccess.getInstance().updateRedisDataMinutesOfDay((tActLast-timedelta(days=2)))
    logging.error('[REDIS_Data_Prepare] Start updateRedisDataMinutesOfDay day3')
    BEOPDataAccess.getInstance().updateRedisDataMinutesOfDay((tActLast-timedelta(days=3)))
    logging.error('[REDIS_Data_Prepare] Finish updateRedisDataMinutesOfDay ')

    while True:
        tNow = datetime.now()
        try:
            if not RedisManager.is_alive():
                app.config['REDIS_ALIVE'] = False
                time.sleep(60)
                tActLast = tNow
                continue

            app.config['REDIS_ALIVE'] = True

            if tActLast.day != tNow.day:  # 跨天时检查过期删除redis key
                try:
                    RedisManager.del_history_data_minutes_keys((tNow-timedelta(days=60)), tNow-timedelta(days=4))
                except:
                    pass

        except Exception as e:
            print('ERROR in udpateRedis:' + e.__str__())

        time.sleep(5)
        tActLast = tNow


def warningScan(args):
    tLastCheck = datetime.now()
    # init
    # check warning_config

    bIDChecked = False
    while True:
        try:
            allWarningConfigList = BEOPDataAccess.getInstance().getAllWarningConfig()
            ruleConfigList = []
            for item in allWarningConfigList:
                if not bIDChecked:  # only check once
                    if item.get('id') is None or item.get('id') < 0:
                        nNewId = BEOPDataAccess.getInstance().getMaxIdInTable('warning_config') + 1
                        if BEOPDataAccess.getInstance().updateWarningConfigId(item.get('pointname'), item.get('type'),
                                                                              item.get('script'), nNewId):
                            item['id'] = nNewId
                        else:
                            print('ERROR in update warning config id')
                if item.get('type') == 3:  # rule
                    strScript = item.get('script')
                    if strScript:
                        ruleConfigList.append(item)

            bIDChecked = True

            if len(ruleConfigList) > 0:

                rvRequest = BEOPDataAccess.getInstance().getInputTable(pointList=None)
                dj = rvRequest[0]
                PV = rvRequest[1]
                for item in ruleConfigList:
                    scriptList = item.get('script')
                    scriptsResult = False
                    if scriptList:
                        func_def = '\n '.join(scriptList.split('\n'))
                        strFuncName = 'func_rule_%s' % (str(item.get('id')))
                        func_str = 'def %s():\n ' % (strFuncName) + func_def
                        try:
                            func_str_new = replace_string_expression_strict_by_map(func_str, PV)
                            rr = exec(func_str_new)
                            scriptsResult = eval('%s()' % (strFuncName))
                        except Exception as e:
                            strError = 'ERROR in warningScan: eval warning rule:%s, error info: %s' % (
                                scriptList, e.__str__())
                            print(strError)
                            # logging.error(strError)
                            continue

                        if scriptsResult and scriptsResult == True:  # warning is true
                            strInfo = 'Rule Warning Happen, expression: %s, trans to:%s ruleID: %s, PointValueMap Record: 【%s】， DJ:【%s】' % (
                                func_str, func_str_new, str(item.get('id')), str(PV), str(dj))
                            # print(strInfo)
                            # logging.error(strInfo)

                            strInfoDetailScript = item.get('infoDetail')
                            strInfoDetailResult = ''
                            if strInfoDetailScript:
                                strInfoDetailResult = replace_string_expression_strict(strInfoDetailScript, dj)

                            strGoodRange = ''
                            strBindPointName = item.get('pointname', '')
                            if strBindPointName:
                                strBindPointValue = PV.get(strBindPointName, '')
                            bSuccess = BEOPDataAccess.getInstance().insertWarningRecord(item.get('boolWarningInfo', ''),
                                                                                        item.get('boolWarningLevel'),
                                                                                        item.get('pointname', ''),
                                                                                        item.get('id'),
                                                                                        item.get('ofPosition', ''),
                                                                                        item.get('ofSystem', ''),
                                                                                        item.get('ofDepartment', ''),
                                                                                        item.get('ofGroup', ''),
                                                                                        item.get('tag', ''),
                                                                                        strInfoDetailResult,
                                                                                        strGoodRange, strBindPointValue,
                                                                                        item.get('unitproperty03', ''),
                                                                                        item.get('unitproperty04', ''),
                                                                                        item.get('unitproperty05', ''))
                            if not bSuccess:
                                strError = 'ERROR in insertWarningRecord'
                                print(strError)
                                logging.error(strError)

        except Exception as e:
            strError = 'ERROR in warningScan :%s' % (e.__str__())
            logging.error(strError)
            print(strError)
        time.sleep(15)


def clean_dom_log():
    cwd = os.getcwd()
    strCoreDir = os.path.dirname(cwd)
    strProcessName = "domSpaceClean.exe"
    try:
        pInfo = ProcessManager.getInstance().findProcess(strProcessName)
        if not pInfo:
            logging.error("{0} process doesn't exist, starting...".format(strProcessName))
            print("{0} process doesn't exist, starting...".format(strProcessName))

            strExeDir = os.path.join(strCoreDir, "domSpaceClean")
            strExeFile = os.path.join(strExeDir, "domSpaceClean.exe")

            if not os.path.exists(strExeFile):
                strError = 'ERROR in ProcessExistHost start process but not found:  %s' % (strProcessName)
                logging.error(strError)
                print(strError)
                return False

            win32api.ShellExecute(0, "open", strExeFile, "", strExeDir, 0)
            logging.error("{0} started successfully".format(strProcessName))
            print("{0} started successfully".format(strProcessName))
        else:
            logging.error('{0} is now in process list, it is working.'.format(strProcessName))
    except Exception as e:
        logging.error('ERROR in clean_dom_log: %s' % (e.__str__()))
        time.sleep(60)
        return False


def updatePointPageRelation(args):
    tLastLoop = datetime.now()
    bFirstRun = True
    while True:
        tNow = datetime.now()

        nDeltaMinutes = (tNow - tLastLoop).total_seconds() / 3600

        try:
            pointPageMap = BEOPSqliteAccess.getInstance('updatePointPageRelation').getPointPageMap()
            RedisManager.set_point_used_page_list(pointPageMap)
        except Exception as e:
            strError = 'ERROR in updatePointPageRelation:  %s' % (e.__str__())
            logging.error(strError)
            print(strError)
            time.sleep(60)

        # time.sleep(60*60*24)
        return


def gen_report(finfo):
    tNow = datetime.now()

    strInfo = 'autoGenReportOnTime start to generate the report %s' % (finfo.get('file_name'))
    print(strInfo)
    log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)

    strFileName = finfo.get('file_name')
    try:
        strFileNamePrefix = os.path.splitext(strFileName)[0]
        strFileNamePostfix = os.path.splitext(strFileName)[1]
    except:
        strError = 'ERROR in autoGenReportOnTime: template filename(%s) not valid.' % (strFileName)
        log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)
        print(strError)
        return False

    if not strFileNamePostfix in ['.docx', '.xlsx']:
        strError = 'ERROR in autoGenReportOnTime: template filename(%s) format not support.' % (strFileName)
        log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)
        print(strError)
        return False

    strReportName = '%s_%s%s' % (strFileNamePrefix, tNow.strftime('%Y%m%d%H%M%S'), strFileNamePostfix)
    strReportPath = os.path.join(app.static_folder, 'projectReports')
    strReportPath = os.path.join(strReportPath, '0')
    if not os.path.exists(strReportPath):
        os.makedirs(strReportPath)
    strReportFilePath = os.path.join(strReportPath, strReportName)
    BEOPSqliteAccess.getInstance('autoGenReportOnTime').getTemplateFileFrom4DB(finfo.get('file_name'),
                                                                               strReportFilePath)

    #添加Redis记录
    if strFileNamePostfix == '.docx':
        report = ReportTool(strFileName, strReportFilePath)
        bSuccess = report.fillAllTables(tNow.strftime('%Y-%m-%d %H:%M:%S'), strFileName)
        strInfo = 'autoGenReportOnTime generate the report %s, result:%d' % (
            finfo.get('file_name'), 1 if bSuccess else 0)
        print(strInfo)
        log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)

    elif strFileNamePostfix == '.xlsx':
        report = ReportTool(strFileName, strReportFilePath)
        bSuccess = report.fillAllTablesInExcel(tNow.strftime('%Y-%m-%d %H:%M:%S'), strFileName)

        strInfo = 'autoGenReportOnTime generate the report %s, result:%d' % (
            finfo.get('file_name'), 1 if bSuccess else 0)
        print(strInfo)
        log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)

    nFileSize = 200000
    nRetryCount = 5
    res = None
    while res is None and nRetryCount > 0:
        res = BEOPDataAccess.getInstance().insertReportHistory(finfo.get('file_name'),
                                                               finfo.get('file_description'),
                                                               tNow.strftime('%Y-%m-%d %H:%M:%S'),
                                                               nFileSize, 'system', strReportName,
                                                               tNow.strftime('%Y-%m-%d %H:%M:%S'),
                                                               tNow.strftime('%Y-%m-%d %H:%M:%S'), 2)
        nRetryCount -= 1
        time.sleep(1)

    strInsertDBResult = 'Success'
    if res is None:
        strInsertDBResult = 'Failed'

    strInfo = 'autoGenReportOnTime finish generate the report %s, cal time:%s, result:%s' % (
        finfo.get('file_name'), tNow.strftime('%Y-%m-%d %H:%M:%S'), strInsertDBResult)
    print(strInfo)
    log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)
    return True

def runOnceThreadGenReport(args):
    finfo = args
    gen_report(finfo)
    return True

def autoGenReportOnTime(args):
    tLastLoop = datetime.now()
    g_report_first_run = True
    while True:
        tNow = datetime.now()

        nDeltaMinutes = (tNow - tLastLoop).total_seconds() / 3600

        try:

            fileInfoList = BEOPSqliteAccess.getInstance('autoGenReportOnTime').getAutoReportTemplateIdListFileFrom4DB()
            reportThreadList = []
            for finfo in fileInfoList:
                if finfo.get('fileType') != AttachFileType.ReportFile:
                    continue

                nReportTimeType = finfo.get('fileTimeType')
                bNeedGen = False
                if g_report_first_run:
                    nRegen = app.config.get('REGEN_REPORT_WHEN_RESTART', 1)
                    bNeedGen = (nRegen == 1)
                elif nReportTimeType == AttachReportFileTimeType.DailyReport:
                    strTimeConfig = finfo.get('fileTimeConfig')
                    hoursList = strTimeConfig.split(',')
                    bNeedGen = is_timer_trigger_hour(g_report_last_loop, tNow, hoursList)
                elif nReportTimeType == AttachReportFileTimeType.WeeklyReport:
                    strTimeConfig = finfo.get('fileTimeConfig')
                    weekdayList = strTimeConfig.split(',')
                    bNeedGen = is_timer_trigger_weekday(g_report_last_loop, tNow, weekdayList)
                elif nReportTimeType == AttachReportFileTimeType.MonthlyReport:
                    strTimeConfig = finfo.get('fileTimeConfig')
                    dayList = strTimeConfig.split(',')
                    bNeedGen = is_timer_trigger_monthly(g_report_last_loop, tNow, dayList)

                if not bNeedGen:
                    continue

                try:
                    t2 = threading.Thread(target=runOnceThreadGenReport, args=(finfo,))
                    t2.setDaemon(False)
                    reportThreadList.append(t2)
                    t2.start()
                except Exception as e:
                    LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())

            for item in reportThreadList:
                item.join()

            g_report_first_run = False
            g_report_last_loop = tNow
            if len(reportThreadList)>0:
                log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), "Reports gereration finished")

        except Exception as e:
            strError = 'ERROR in autoGenReportOnTime:  %s' % (e.__str__())
            log_info_to_file('dompysite_report_log_%s.log' % (tNow.strftime('%Y_%m')), strInfo)
            print(strError)
            time.sleep(60)

            continue

        tLastLoop = tNow

        time.sleep(60)


def filter_same_warning_by_id(wList, bufferList):
    newWList = []
    for item in wList:
        bExist = False
        for bufferitem in bufferList:
            if item.get('id') == bufferitem.get('id'):
                bExist = True
                break
        if not bExist:
            newWList.append(item)

    return newWList


def startThreadCalculating():
    try:
        tempPath = os.getcwd() + '/Temp'
        res = os.path.exists(tempPath)
        if res is not True:
            os.makedirs(tempPath)

        arr = SQLiteOperator.get_formula_group()
        for item in arr:
            startThreadUpdateEx(item[0], item[1])

    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadUpdatePointPageRelation():
    try:
        t2 = threading.Thread(target=updatePointPageRelation, args=('name',))
        t2.setDaemon(False)
        t2.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadAutoGenReport():
    try:
        t2 = threading.Thread(target=autoGenReportOnTime, args=('name',))
        t2.setDaemon(False)
        t2.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def cleanDOMDisk(args):
    tLastCheck = datetime.now()
    # init
    bFirstStart = True

    while True:
        try:
            tNow = datetime.now()
            tspan = tNow - tLastCheck
            if not bFirstStart:
                if tNow.day!= tLastCheck.day:
                    # clean redis of 7 days before
                    for indexDay in [4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]:
                        RedisManager.del_history_data_minutes_keys_of_date(tNow - timedelta(days=indexDay))
                if tspan.total_seconds() < 60 * 60 * 6 or tNow.hour >= 1:
                    time.sleep(60)
                    continue

            bFirstStart = False

            tLastCheck = tNow  # record time

            try:
                clean_dom_log()

            except:
                pass

        except:
            pass
        time.sleep(60 * 15)


def startThreadCleanDOMDisk():
    try:
        t2 = threading.Thread(target=cleanDOMDisk, args=('name',))
        t2.setDaemon(False)
        t2.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadCheckWarningRule():
    try:
        threadWarningScan = threading.Thread(target=warningScan, args=('warningScan',))
        threadWarningScan.setDaemon(False)
        threadWarningScan.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadUpdateRedis():
    try:
        threadUpdateRedis = threading.Thread(target=updateRedis, args=('',))
        threadUpdateRedis.setDaemon(False)
        threadUpdateRedis.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())

def inspectDomhost():
    while True:
        try:
            inspect_domhost()
        except:
            pass
        finally:
            time.sleep(60)

def inspectWorkOrder():
    while True:
        try:
            inspect_work_order_on_time()
        except:
            pass
        finally:
            time.sleep(60)

def startThreadInspectDomhost():
    try:
        threadInspectDomhost = threading.Thread(target=inspectDomhost, args=())
        threadInspectDomhost.setDaemon(False)
        threadInspectDomhost.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())

def startThreadInspectWorkOrder():
    try:
        threadInspectDomhost = threading.Thread(target=inspectWorkOrder, args=())
        threadInspectDomhost.setDaemon(False)
        threadInspectDomhost.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())

def checkHealthLive(args):
    while True:
        try:
            if g_mysql_last_pool_exhaust_time.get("last", None):
                if (datetime.now() - g_mysql_last_pool_exhaust_time.get("last")).total_seconds() <= 60:
                    continue

            BEOPDataAccess.getInstance().updateProcessStatus('dompysite')
        except:
            pass
        finally:
            time.sleep(60)


def startThreadCheckLiveHealth():
    try:
        threadcheckHealthLive = threading.Thread(target=checkHealthLive, args=('healthLive',))
        threadcheckHealthLive.setDaemon(False)
        threadcheckHealthLive.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadVPointCalculation():
    strDisabled = BEOPDataAccess.getInstance().getUnit01('realtime_vpoint_calculation_disabled')
    if strDisabled == '1':
        strLog = 'realtime_vpoint_calculation_disabled option is 1, so disable vpoint calculation in realtime'
        logging.error(strLog)
        print(strLog)
        return
    try:
        threadVPointCalculation = threading.Thread(target=vpointUpdate, args=('',))
        threadVPointCalculation.setDaemon(False)
        threadVPointCalculation.start()

        time.sleep(5)

        for i in range(g_calculation_threads_num):
            threadVPointCalculation = threading.Thread(target=vpointCalculation, args=(i + 1,))
            threadVPointCalculation.setDaemon(False)
            threadVPointCalculation.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


def startThreadBackupMySQL():
    try:
        t2 = threading.Thread(target=backupMySQL, args=('name',))
        t2.setDaemon(False)
        t2.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())
        print(e.__str__())


def startThreadAutoGenPointDataReportForDownload():
    try:
        t2 = threading.Thread(target=autoGenPointDataReportForDownload, args=('name',))
        t2.setDaemon(False)
        t2.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())


# read port
try:
    cf = ConfigObj('config.ini', encoding='UTF8')
    try:
        nRunPort = int(cf['host']['port'])

        print('Server Run at port: %d'%(nRunPort))
        app.config.update(dict(RUN_PORT=nRunPort))
    except:
        pass
except:
    pass

myapp = singleinstance()


def callback(ch, method, properties, body):
    projId = None

    try:

        msgb = body.decode(encoding='utf-8')
        msg = json.loads(msgb)
        if msg:
            # bCalculatedJustNow =False
            # bNewProject = False
            projId = int(msg.get('projId'))

        # tCostAll =  (datetime.now()-t0).total_seconds()
        logging.error('==================%d消息消费完毕:成功' % (projId))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return True

    except Exception as e:
        if projId is not None:
            logging.error('项目%s意外错误:' % (projId) + e.__str__())
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return True


def runConsume():
    while True:
        try:
            logging.error('消息处理进程启动')
            credentials = pika.PlainCredentials(app.config['MQ_USERNAME'], app.config['MQ_PASSWORD'])
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=app.config['MQ_ADDRESS'], credentials=credentials))
            channel = connection.channel()
            channel.queue_declare(queue=app.config['MQ_RECEIVE_DIAGNOSIS_NAME'], durable=True)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(callback, queue=app.config['MQ_RECEIVE_DIAGNOSIS_NAME'])
            channel.start_consuming()
        except Exception as e:
            logging.error('消息处理进程runConsume意外中止error:' + e.__str__())
            time.sleep(15)


def setRegeditOptionNoPromtWhenCrash():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Classes\CLSID\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\shell\Manage\command", 0,
                             winreg.KEY_ALL_ACCESS)
        i = 0

        newKey = winreg.CreateKey(key, "MyNewkey")
        winreg.SetValue(newKey, "ValueName", 0, "ValueContent")

        while True:
            name, value, type = winreg.EnumValue(key, i)

            # value, type = winreg.QueryValueEx(key, "")
            if value == '%SystemRoot%\system32\CompMgmtLauncher.exe':
                # 给新创建的键添加键值
                winreg.SetValue(key, name, winreg.REG_SZ, "mmc compmgmt.msc")
    except Exception as e:
        strInfo = 'ERROR in setRegeditOptionNoPromtWhenCrash: ' + e.__str__()
        print(strInfo)
        logging.error(strInfo)


def loadDatabaseInfoFromCoreIni():
    strCorePath = os.path.dirname(os.getcwd())
    strCoreIniFilePath = os.path.join(strCorePath, 'domcore.ini')
    try:
        cf = ConfigObj(strCoreIniFilePath, encoding='UTF8')
        if cf.get('core') and cf.get('core').get('dbpassword'):
            app.config.update(dict(PASSWORD=cf.get('core').get('dbpassword')))

    except Exception as e:
        print('ERROR in pase domcore.ini: ' + e.__str__())


def initCheckLoadConfigIni():
    try:
        bNeedWrite = False

        cf = ConfigObj('config.ini', encoding='UTF8')
        if cf.get('mysql') is None:
            cf['mysql'] = dict(dbip='127.0.0.1')
            bNeedWrite = True
        elif cf.get('mysql').get('dbip') is None:
            cf['mysql']['dbip'] = '127.0.0.1'
            bNeedWrite = True

        try:
            str = cf.get('mysql').get('INIT_CONNECTIONS_POOL')
            if str:
                app.config.update(dict(INIT_CONNECTIONS_POOL=int(float(str))))
        except:
            pass
        try:
            str = cf.get('mysql').get('USERNAME')
            if str:
                app.config.update(dict(USERNAME=str))
        except:
            pass
        try:
            str = cf.get('mysql').get('PASSWORD')
            if str:
                app.config.update(dict(PASSWORD=str))
        except:
            pass

        try:
            str = cf.get('data').get('regenReportWhenStart')
            if str=='1':
                app.config.update(dict(REGEN_REPORT_WHEN_RESTART=1))
            else:
                app.config.update(dict(REGEN_REPORT_WHEN_RESTART=0))
        except:
            pass

        if cf.get('data') is None:
            cf['data'] = dict(decimal=2)
            bNeedWrite = True
        elif cf.get('data').get('decimal') is None:
            cf['data']['decimal'] = 2
            bNeedWrite = True

        if cf.get('projectdb') is None:
            cf['projectdb'] = dict(dbFileName='domdb.4db')
            bNeedWrite = True
        elif cf.get('projectdb').get('dbfilename') is not None:
            cf['projectdb']['dbFileName'] = cf.get('projectdb').get('dbfilename')
            del cf['projectdb']['dbfilename']
            bNeedWrite = True
        elif cf.get('projectdb').get('dbFileName') is None:
            cf['projectdb']['dbFileName'] = 'domdb.4db'
            bNeedWrite = True

        if cf.get('cloud') is None:
            cf['cloud'] = dict(projectname=get_machine_code())
            bNeedWrite = True
        elif cf.get('cloud').get('projectname') is None:
            cf['cloud']['projectname'] = get_machine_code()
            bNeedWrite = True

        if cf.get('cloud').get('fileUploadServer') is None:
            cf['cloud']['fileUploadServer'] = 'dom.inwhile.com'
            bNeedWrite = True

        if cf.get('mysql') and cf.get('mysql').get('dbip'):
            app.config.update(dict(HOST=cf.get('mysql').get('dbip')))
        if cf.get('data') and cf.get('data').get('decimal'):
            app.config.update(dict(DECIMAL=int(cf.get('data').get('decimal'))))
        if cf.get('projectdb') and cf.get('projectdb').get('dbFileName'):
            app.config.update(dict(DB_FILE_NAME=cf.get('projectdb').get('dbFileName')))
        if cf.get('cloud') and cf.get('cloud').get('fileUploadServer'):
            app.config.update(dict(FILE_UPLOAD_SERVER=cf.get('cloud').get('fileUploadServer')))

        app.config.update(dict(MONITOR=[]))
        if cf.get("host"):
            if cf.get("host").get("domhost", None) == "1":
                app.config.get("MONITOR").append("domhost")

        logLevel = "ERROR"
        if cf.get("log"):
            if cf.get("log").get("level"):
                logLevel = cf["log"]["level"]
        else:
            cf["log"] = dict(level="CRITICAL")
            bNeedWrite = True

        if bNeedWrite:
            cf.write()
        return logLevel
    except Exception as e:
        strError = 'ERROR in pase config.ini: ' + e.__str__()
        print(strError)
        logging.error(strError)


# 在每一次请求前执行
@app.before_request
def log_each_request():
    try:
        params = request.args if request.args is None else ''
        print(request.base_url+ '  ' + str(request.remote_addr))
    except Exception as e:
        strError = 'ERROR in log_each_request: ' + e.__str__()
        print(strError)
        logging.error(strError)
        pass

def initTemplateFiles(args):
    BEOPSqliteAccess.getInstance('initTemplateFiles').initTemplateImagesFiles(app.config.get('USE_4DB_NAME'))


if __name__ == '__main__':

    strLogPath = os.path.join(os.getcwd(), 'log')
    if not os.path.exists(strLogPath):
        os.makedirs(strLogPath)

    now = datetime.now()
    logFileName = './log/errorlog_dompysite_%s.txt' % now.strftime('%Y-%m-%d')

    strLogFile = os.path.join(strLogPath, 'dompysite_log')
    strWhen = 'midnight'  # 'W0'
    logHandler = TimedRotatingFileHandler(strLogFile, when=strWhen, interval=1, backupCount=200)
    logFormatter = logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s')
    logHandler.setFormatter(logFormatter)
    g_logger = logging.getLogger('')
    g_logger.addHandler(logHandler)

    strLogLevel = initCheckLoadConfigIni()
    if strLogLevel == "ERROR":
        g_logger.setLevel(logging.ERROR)
    elif strLogLevel == "WARNING":
        g_logger.setLevel(logging.WARNING)
    elif strLogLevel == "CRITICAL":
        g_logger.setLevel(logging.CRITICAL)
    elif strLogLevel == "INFO":
        g_logger.setLevel(logging.INFO)
    elif strLogLevel == "DEBUG":
        g_logger.setLevel(logging.DEBUG)
    else:
        g_logger.setLevel(logging.ERROR)

    strInfo = '============dompysite(Version:%s) process started==============\r\n' % (siteVersion.getCurrentVersion())
    logging.critical(strInfo)
    print(strInfo)

    # setRegeditOptionNoPromtWhenCrash()
    if myapp.aleradyrunning() and  app.config.get('RUN_PORT')  in [5000,5432]:#5000是独立运行端口, 5432是nginx增强环境端口
        LogOperator().writeLog("Another instance of this program is already running\r\n")
        sys.exit()

    if not RedisManager.is_alive():
        app.config['REDIS_ALIVE'] = False
    else:
        app.config['REDIS_ALIVE'] = True


    strCorePath = os.path.dirname(os.getcwd())
    strDomJobPath = os.path.join(strCorePath, 'domJobs')
    strDomJobFile = os.path.join(strDomJobPath, 'domJobs.exe')
    if os.path.exists(strDomJobFile):
        app.config['ONLY_RUN_AS_SERVICE'] = True
    else:
        app.config['ONLY_RUN_AS_SERVICE'] = False

    loadDatabaseInfoFromCoreIni()

    logging.error('Start to read config.ini of dompysite')


    BEOPDataAccess.getInstance().updateProcessStatus('dompysite')

    update_startup_time()

    logging.error('Start to check MySQL db and version')

    # prepare directory
    strPath = app.static_folder
    strTempPath = os.path.join(strPath, 'files')
    strTempPath = os.path.join(strTempPath, 'temp')
    if not os.path.exists(strTempPath):
        os.makedirs(strTempPath)

    strWarningSoundFilePath = os.path.join(app.static_folder, '警报音.mp3')
    if not os.path.exists(strWarningSoundFilePath):
        strSrcPath = os.path.join(os.getcwd(), 'sound')
        strSrcPath = os.path.join(strSrcPath, 'default')
        strSrcPath = os.path.join(strSrcPath, '警报音.mp3')
        if os.path.exists(strSrcPath):
            try:
                shutil.copy(strSrcPath, strWarningSoundFilePath)
            except:
                pass

    strInfo = 'Start to load project db file: %s' % (app.config.get('DB_FILE_NAME'))
    print(strInfo)
    logging.error(strInfo)

    # 从domdb.4db 、模板文件中解压出图片
    while not BEOPSqliteAccess.getInstance('MAIN Startup').initAutoLoadDBFile(app.config.get('DB_FILE_NAME')):
        strError = 'ERROR in read db file, please check whether 4db file exist or file size is good, will re check after 10 seconds'
        print(strError)
        logging.error(strError)
        time.sleep(10)

    #如果domdb被设置为只读则修改为正常
    try:
        fattrs = win32api.GetFileAttributes(app.config.get('USE_4DB_NAME'))
        bIsFileReadOnly = bool(fattrs & win32con.FILE_ATTRIBUTE_READONLY)
        if bIsFileReadOnly:
            win32api.SetFileAttributes(app.config.get('USE_4DB_NAME'), win32con.FILE_ATTRIBUTE_NORMAL)
    except Exception as e_file_attr:
        strLog = 'ERROR in win32api.Get Set FileAttributes:%s'%(e_file_attr.__str__())
        logging.error(strLog)

    BEOPSqliteAccess.getInstance('MAIN Startup').initTemplate4dbFile()
    BEOPSqliteAccess.getInstance('MAIN Startup').addHideScriptToDomdb()
    BEOPSqliteAccess.getInstance('MAIN Startup').addHideScriptToTemplate4db()
    BEOPSqliteAccess.getInstance('MAIN Startup').addSourceTypeToListButtonTable()
    BEOPSqliteAccess.getInstance('MAIN Startup').prepareStandardButtonImages()

    # BEOPSqliteAccess.getInstance('MAIN Startup').initAllPageInfoIntoRedis_DebugTool()  # 2023-07-7 为了加速dompysite启动，暂时不将页面内容存入debugtool专用缓存

    #解压图片需要放在dompysite而不是domJobs
    try:
        threadTemplate = threading.Thread(target=initTemplateFiles, args=('name',))
        threadTemplate.setDaemon(False)
        threadTemplate.start()
    except Exception as e:
        LogOperator().writeLog('%s:' % (get_current_func_name()) + e.__str__())

    BEOPSqliteAccess.getInstance('MAIN Startup').UpdateFaultPointsToRedis()
    BEOPSqliteAccess.getInstance('MAIN Startup').UpdateFaultViewInfoToRedis()
    BEOPSqliteAccess.getInstance('MAIN Startup').UpdateFaultAuthInfoToRedis()
    BEOPSqliteAccess.getInstance('MAIN Startup').updateAllPointInfoIntoRedis()
    BEOPSqliteAccess.getInstance('MAIN Startup').updateFireModeScriptIntoMemory()

    ProjectdbSettingParam = BEOPSqliteAccess.getInstance('MAIN Startup').ReadRealDBparam()
    if ProjectdbSettingParam.get('RealtimeDBName'):
        app.config.update(dict(DATABASE=ProjectdbSettingParam.get('RealtimeDBName')))

    # check mysql
    strDBVersion = BEOPDataAccess.getInstance().getDBVersion()
    LogOperator().writeLog("Check MySQL Database(%s) Version, Current: %s" % (app.config["DATABASE"], strDBVersion))

    if float(strDBVersion) < 3:
        bSuccess = BEOPDataAccess.getInstance().createRealtimeinputTablesIfNotExist()
        bSuccess = bSuccess and BEOPDataAccess.getInstance().createRealtimeOutputTablesIfNotExist()
        if bSuccess:
            LogOperator().writeLog("Update MySQL Database Version to 3")
            BEOPDataAccess.getInstance().updateDBVersion('3')

    # 将mysql版本号记录在全局变量
    strDBVersion = BEOPDataAccess.getInstance().getDBVersion()
    app.config.update(
        dict(DATABASE_VERSION={ProjectdbSettingParam.get('RealtimeDBName'): float(strDBVersion)})
    )
    
    # 记录版本号、重启次数、重启时间记录
    BEOPDataAccess.getInstance().saveDoubleKeyInUnit01('dompysite', 'version', siteVersion.getCurrentVersion())
    strRestartCount = BEOPDataAccess.getInstance().getDoubleKeyInUnit01('dompysite', 'restartCount')
    nRestartCount = 0
    if strRestartCount:
        try:
            nRestartCount = int(float(strRestartCount))
        except:
            nRestartCount = 0
    nRestartCount += 1
    BEOPDataAccess.getInstance().saveDoubleKeyInUnit01('dompysite', 'restartCount', str(nRestartCount))

    strRestartTimeList = BEOPDataAccess.getInstance().getDoubleKeyInUnit01('dompysite', 'restartTimeList')
    ttList = []
    if strRestartTimeList:
        try:
            ttList = strRestartTimeList.split(',')
            if len(ttList) >= 100:
                del ttList[0]
        except:
            pass
    ttList.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    BEOPDataAccess.getInstance().saveDoubleKeyInUnit01('dompysite', 'restartTimeList', ','.join(str(i) for i in ttList))

    # init logo and logo_small
    BEOPSqliteAccess.getInstance('MAIN Startup').InitLogoFiles()
    BEOPSqliteAccess.getInstance('MAIN Startup').InitModbusServerFileComparingTime()

    # create the sample database
    BEOPDataAccess.getInstance().checkBuildIOSampleDB()
    BEOPDataAccess.getInstance().checkBuildFDDDB()
    BEOPDataAccess.getInstance().checkCreateIfNotExistFDDTable(datetime.now())
    BEOPDataAccess.getInstance().checkCreateIfNotExistFddDataErrorTable()

    BEOPDataAccess.getInstance().checkAndAutoInitAssetTmplDef()


    updateMailSetting()
    initFirewall()

    try:
        if app.config['ONLY_RUN_AS_SERVICE']==False:
            startThreadUpdatePointPageRelation()

            startThreadBackupMySQL()

            startThreadCheckWarningRule()

            if app.config['RUN_PORT'] in [5000,5432]:
                startThreadCleanDOMDisk()
                startThreadCalculating()
                startThreadAutoGenReport()
                startThreadVPointCalculation()
                startThreadAutoGenPointDataReportForDownload()

            startThreadUpdateRedis()

            startThreadInspectDomhost()

            startThreadInspectWorkOrder()

        strLog = 'db images prepared, Start calc and web server( port:%d ) success.' % (app.config['RUN_PORT'])
        logging.error(strLog)
        print(strLog)

        startThreadCheckLiveHealth()

        app.run(host='0.0.0.0', port=app.config['RUN_PORT'], use_reloader=False, threaded=True)

    except Exception as e:
        strLog = 'app run exception: %s \r\n !!!!请注意计算机名(当前名:%s)不能含中文!!!!\r\n' % (e.__str__(), socket.gethostname())
        LogOperator().writeLog(strLog)
