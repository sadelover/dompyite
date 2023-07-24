
from siteinterface import app
from flask import g, json
from math import floor, ceil
import os, sys
import mysql.connector
from math import floor, ceil
from datetime import datetime,timedelta
import time
import logging

from siteinterface import app
from flask import g, json
from math import floor, ceil
import os, sys
import mysql.connector
from math import floor, ceil
from datetime import datetime,timedelta
import time
import logging
import sqlite3
from os import environ, listdir, path, unlink, remove, makedirs, stat
from siteinterface.BEOPMySqlDBContainer import *
import subprocess
import traceback
import re
import zipfile
import shutil
from siteinterface.utils import zip_folder, isValidDate
import stat

class LogicManager:
    __instance = None


    def __init__(self, ):

        self._mysqlDbContainer = BEOPMySqlDBContainer('LOGIC_MANAGER', 'dompysite')

    @classmethod
    def getInstance(self):
        if(self.__instance == None):
            self.__instance = LogicManager()
        return self.__instance

    #@classmethod
    #def getMySqlContainer(self):

    @classmethod
    def create_queue(cls):

        return None

    @classmethod
    def remove_queue(cls):
        #t ofix
        return None

    @classmethod
    def modify_queue_name(cls, strDBFileName, strOldName, strNewName):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("update list_dllstore set unitproperty04 = '%s' where unitproperty04 = '%s'"%(strNewName, strOldName))
            bSuccess = True
        except Exception as e:
            logging.error("ERROR in modify_queue_name: %s" % e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess


    @classmethod
    def modify_queue_timespan(cls, strLogicName, strLogicNewName):

        return True

    @classmethod # 删除线程
    def del_thread(cls, strDBFileName, threadName):
        cu = None
        con = None
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("delete from  list_dllstore where unitproperty04=:threadName", {"threadName":threadName})
            con.commit()
            bSuccess = True
        except Exception as ee:
            logging.error("ERROR in del_thread of LogicManager: %s" % ee.__str__())
        finally:
           if cu is not None:
            cu.close()
           if con is not None:
            con.close()
        return bSuccess

    @classmethod # 获取列表
    def get_queues_list(cls,strDBFileName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("select DISTINCT(unitproperty04) from list_dllstore")
            #result = cu.execute("select DISTINCT periodicity,runstatus,unitproperty04 from list_dllstore")
            for item in result:
                queueList.append(item[0].decode('gbk'))

        finally:
           if cu is not None:
            cu.close()
           if con is not None:
            con.close()
        return queueList

    @classmethod # 获取详细列表
    def get_queues_detail_list(cls,strDBFileName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()

            result = cu.execute("select unitproperty04, periodicity, runstatus from list_dllstore group by unitproperty04")

            threadNames = ["'{0}'".format(item[0].decode("gbk")) for item in result]

            strQuery = "SELECT unitproperty01, unitproperty02 FROM unit01"

            if len(threadNames):
                strQuery = "SELECT unitproperty01, unitproperty02 FROM unit01 WHERE unitproperty01 in ({0})".format(",".join(threadNames))

            DBM = BEOPMySqlDBContainer()
            dlls = DBM.op_db_query("beopdata", strQuery)

            dllStatusDict = {}
            for dll in dlls:
                dllStatusDict.update({dll[0]: 1 if dll[1] == "1" else 0})

            dllInfo = cu.execute(
                "select unitproperty04, periodicity, runstatus from list_dllstore group by unitproperty04")
            for item in dllInfo:
                queueList.append({
                    'threadName':item[0].decode('gbk'), 
                    'periodicity': item[1].decode('gbk'), 
                    'runstatus': item[2].decode('gbk'),
                    "onoff": dllStatusDict.get(item[0].decode('gbk'), 0)
                })

            return queueList

        except Exception as e:
            logging.error("ERROR in /strategy/getThreadDetailList： %s" % e.__str__())

            return []

    # 获取线程周期
    @classmethod
    def get_queues_timespan(cls,strDBFileName,unitproperty04):
        cu = None
        con = None
        bSuccess = False
        queueList = {}
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("SELECT periodicity,runstatus FROM list_dllstore WHERE unitproperty04='%s' LIMIT 1" %(unitproperty04))
            for item in result:
                queueList={
                    'threadName' : unitproperty04,
                    'periodicity':item[0].decode('gbk'),
                    'runstatus':item[1].decode('gbk')
                }

        finally:
           if cu is not None:
            cu.close()
           if con is not None:
            con.close()
        return queueList

    @classmethod
    def getThreadDetails(cls,):
        return True

    @classmethod
    def move_logic_between_queue(cls, ):
        return True

    @classmethod
    def create_logic(cls, strLogicName):
        return True

    # 获取点列表
    @classmethod
    def get_list_point(cls,strDBFileName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("SELECT name from list_point")
            for item in result:
                queueList.append(item[0].decode('gbk'))

        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return queueList

    # 删除策略
    @classmethod
    def delLogicByDllName(cls,strDBFileName,DllName):
        cu = None
        con = None
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("delete FROM list_dllstore WHERE DllName='%s'" %(DllName))
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess


    # 添加策略
    @classmethod
    def addLogicIntoThread(cls, strDBFileName, threadName, DllName ):
        cu = None
        con = None
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("delete FROM list_dllstore WHERE DllName='%s'" %(DllName))
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    @classmethod
    def enableOrDisableThread(cls,strDBFileName,threadList,runstatus):
        # 支持单个或多个线程同时启用/禁用
        cu = None
        con = None
        bSuccess = False
        try:
            if app.config.get('USE_4DB_FILE_FORMAT'):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + 'file is not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)

            con.text_factory = bytes
            cu = con.cursor()
            for thread in threadList:
                cu.execute('update  list_dllstore SET runstatus="%s" WHERE unitproperty04="%s"' %(runstatus,thread))
            #完全更新后再同步数据库
            bSuccess = con.commit()
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    @classmethod # 更新策略文件
    def update_logic_dll_file(cls,strDBFileName,strDllName,strDllFilePath):
        cu = None   #sqlite的游标实例化使用
        con = None  #sqlite 实例化使用
        bSuccess = {
            "version":False,
            "description":False,
            "binary":False
        }#用于判断写入是否成功
        '''
        确定domlogic.exe的位置
        '''
        domlogicExePath = app.config['CORE_PATH']
        logicExe = os.path.join(domlogicExePath,"domlogic.exe")

        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            '''
            连接SQLite
            '''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes #疑问
            cu = con.cursor()  # 游标

            '''
            需要连接数据库 清除填充位置
            '''
            DBM = BEOPMySqlDBContainer()  # 数据库实例化
            dictDeleteState = DBM.op_db_delete("beopdata",
                                               "DELETE FROM unit01 WHERE unitproperty01=\"tmp_logic_config\";")
            dictDeleteState = DBM.op_db_delete("beopdata",
                                               "DELETE FROM unit01 WHERE unitproperty01=\"tmp_logic_Des\";")

            '''
            将需要的数据使用domlogic.exe存入数据库中
            '''
            shellCom = logicExe +' '+ strDllFilePath #构建命令 中间需要一个空格
            with subprocess.Popen(shellCom,stdout=subprocess.PIPE) as sub:
                outs, errs = sub.communicate(timeout=20)

            '''
                判断返回值
            '''
            strOuts = str(outs, encoding="utf-8")
            if (strOuts.__len__() > 0):
                addr = strOuts.find('yes',0,5)
                if (addr == -1):
                    # 找到"数据库连接失败"字段 直接退出
                    if (strOuts.find('MysqlConnectionNo') != -1):
                        logging.error("Logic Error: Mysql connection fail!")
                        return False
                    # 找到no 代表数据库写入失败
                    elif (strOuts.find('no', 3) != -1):
                        logging.error("Logic Error: Mysql write fail!")
                        return False
                    return False
                # '''连续找到两个yes代表写入成功'''
                elif (addr != -1):#找到yes字段
                    yesAddrs = strOuts.find('yes',addr+3)#再找下一个yes
                    if(yesAddrs == -1):#没有找到yes字段
                        logging.error("Logic Error: Mysql write fail!")
                        return False
                    #else:
                        # 找到yes字段跳出if继续执行
            else:
                return False

            '''
            从mysql取出输入输出参数、版本号、描述
            '''
            strQueryValue_json = None  # 用于从数据库读取json格式的版本号和输入输出参数
            strQueryDes_json = None  # 用于从数据库读取json格式的dll描述

            # DBM = BEOPMySqlDBContainer()  # 数据库操作实例化
            strMsqlQueryCmd = "SELECT unitproperty02 FROM unit01 WHERE unitproperty01=\"tmp_logic_config\""#查询命令
            strQueryValue_json = DBM.op_db_query("beopdata",strMsqlQueryCmd)#获取表中的数据
            strMsqlQueryCmd = "SELECT unitproperty02 FROM unit01 WHERE unitproperty01=\"tmp_logic_Des\""  # 查询命令
            strQueryDes_json = DBM.op_db_query("beopdata", strMsqlQueryCmd)  # 获取描述

            '''
            更新策略版本号
            '''
            dictUpdateData = None  # 存储从数据库中拉的数据 （字典）,是为需要更新进数据库的数据

            if( len(strQueryValue_json[0][0]) > 0 ) :
                dictUpdateData = json.loads(strQueryValue_json[0][0])#将获取的数据转成字典保存
                '''
                "output":{},
                "input":{},
                "version":"",
                '''
                strSqliteCmd = ("update list_dllstore set unitproperty01='%s' where  unitproperty03='%s'")  # 版本号
                cu.execute(strSqliteCmd % (dictUpdateData['version'], strDllName))
                con.commit()  # 提交命令
                bSuccess['version']= True

            '''
                更新策略描述
            '''
            if ( len(strQueryDes_json[0][0]) > 0 ):
                strDesTogb2312 = strQueryDes_json[0][0].encode('gb2312')
                strSqliteCmd = ("update list_dllstore set unitproperty02=? where  unitproperty03='%s'")  # 描述
                cu.execute(strSqliteCmd % (strDllName), (strDesTogb2312,))
                con.commit()  # 提交命令
                bSuccess['description']= True

            '''
            更新策略文件
            '''
            with open(strDllFilePath, 'rb') as f:
                result = sqlite3.Binary(f.read())
                strSqliteCmd = ("update list_dllstore set dllcontent=? where unitproperty03='%s'")#二进制文件
                cu.execute(strSqliteCmd %(strDllName), (result,))
                con.commit()#提交命令
                bSuccess['binary']= True

            '''
            更新策略输入输出参数 （sqlite->list_paramterConfig）
            '''
            # '''从db中的list_dllstore表中取出使用本dll文件的策略'''
            strSqliteCmd = ("select DllName from list_dllstore where unitproperty03='%s'")  # 二进制文件
            cu.execute(strSqliteCmd % (strDllName))
            con.commit()  # 提交命令
            listStrategyNameBytes =cu.fetchall()#获取到使用strDllName的所有策略名
            if listStrategyNameBytes[0].__len__() >0 :
                #策略名 bytes->str
                listStrategyName = []
                for strategyNameBytes in listStrategyNameBytes :
                    listStrategyName.append(str(strategyNameBytes[0], encoding="utf-8"))
                # 策略参数 bytes->str
                for strategyName in listStrategyName :
                    for inOrOut in ("in","out"):
                        '''从db中的list_paramterConfig表中取出所有策略的值'''
                        if (inOrOut == "in"):
                            strSqliteCmd = ("select vname,pname,ptype,vexplain,DllName,INorOut,unitproperty01,unitproperty02 from list_paramterConfig where DllName='%s' and INorOut='0'")
                        elif (inOrOut == "out") :
                            strSqliteCmd = ("select vname,pname,ptype,vexplain,DllName,INorOut,unitproperty01,unitproperty02 from list_paramterConfig where DllName='%s' and INorOut='1'")

                        cu.execute(strSqliteCmd % (strategyName))
                        con.commit()  # 提交命令
                        listTempStrategyParameters_Bytes = cu.fetchall()  # 获取所有的数据
                        listTempStrategyParameters = []
                        for listParameters_Bytes in listTempStrategyParameters_Bytes :#处理所有的bytes数据进入字典
                            tempValue = {
                                'vname':"",
                                'pname':"",
                                'ptype':"",
                                'vexplain':"",
                                'DllName': "",
                                'INorOut': "",
                                'unitproperty01':"",
                                'unitproperty02': ""
                            }
                            tempValue['vname'] = str(listParameters_Bytes[0], encoding="utf-8")
                            tempValue['pname'] = str(listParameters_Bytes[1], encoding="gb2312")
                            tempValue['ptype'] = str(listParameters_Bytes[2], encoding="utf-8")
                            tempValue['vexplain'] = str(listParameters_Bytes[3], encoding="gb2312")
                            tempValue['DllName'] = str(listParameters_Bytes[4], encoding="utf-8")
                            tempValue['INorOut'] = str(listParameters_Bytes[5])
                            tempValue['unitproperty01'] = str(listParameters_Bytes[6], encoding="utf-8")
                            tempValue['unitproperty02'] = str(listParameters_Bytes[7], encoding="utf-8")
                            listTempStrategyParameters.append(tempValue)
                        #end for listValueBytes in listStrategyvalueBytes :
                        if (inOrOut == "in"):
                            listInputParameters = listTempStrategyParameters
                        elif (inOrOut == "out"):
                            listOutputParameters = listTempStrategyParameters
                    #end :: for inOrOut in ("in", "out"):
                    dictPastData = {}
                    dictPastData['input'] = listInputParameters
                    dictPastData['output'] = listOutputParameters


                    for inputOrOutput in ("input","output"):
                        # 更新向老版中寻找 找不到插入
                        if dictPastData[inputOrOutput].__len__() <= 0:
                            break
                        boolFindParameter = False #初始化
                        for dicTemptUpdateParameters in dictUpdateData[inputOrOutput]:
                            for dictTempPastParameters in dictPastData[inputOrOutput]:
                                if (dicTemptUpdateParameters['name'] == dictTempPastParameters['vname']):
                                    boolFindParameter = True
                                    break  # 找到便跳出本次循环
                            if (boolFindParameter == False):
                                strSqliteCmd = (
                                    "insert into list_paramterConfig(vname,pname,ptype,vexplain,DllName,INorOut,unitproperty01,unitproperty02,unitproperty03,unitproperty04,unitproperty05) values(?,?,?,?,?,?,?,?,?,?,?) ")
                                if(inputOrOutput == "input"):
                                    cu.execute(strSqliteCmd, (
                                        dicTemptUpdateParameters['name'],
                                        dicTemptUpdateParameters['value'].encode('gb2312'),
                                        dicTemptUpdateParameters['type'],
                                        dicTemptUpdateParameters['paraphrase'].encode('gb2312'), strategyName, "0", "",
                                        dicTemptUpdateParameters['typeCanModify'],
                                        "", "", ""))
                                if (inputOrOutput == "output"):
                                    cu.execute(strSqliteCmd, (
                                        dicTemptUpdateParameters['name'],
                                        dicTemptUpdateParameters['value'].encode('gb2312'),
                                        dicTemptUpdateParameters['type'],
                                        dicTemptUpdateParameters['paraphrase'].encode('gb2312'), strategyName, "1", dicTemptUpdateParameters['typeCanModify'],
                                        "","", "", ""))
                                con.commit()  # 提交命令
                            boolFindParameter = False  # 复位
                        # 老版向更新中寻找 找不到删除
                        boolFindParameter = False  # 初始化
                        for dictTempPastParameters in dictPastData[inputOrOutput]:
                            for dicTemptUpdateParameters in dictUpdateData[inputOrOutput]:
                                if (dictTempPastParameters['vname'] == dicTemptUpdateParameters['name']):
                                    boolFindParameter = True
                                    break  # 找到便跳出本次循环
                            if (boolFindParameter == False):
                                # 无法删除与数据编码格式有关系 搜不到
                                strSqliteCmd = ("delete from list_paramterConfig where Dllname=? and vname=?;")
                                cu.execute(strSqliteCmd, (strategyName, dictTempPastParameters['vname']))
                                con.commit()  # 提交命令
                            boolFindParameter = False#复位
                #end :: for strategyName in listStrategyName :
            #end :: if listStrategyNameBytes[0].__len__() > 0:
        except Exception as e:
            traceback.print_exc()
            logging.error("Logic Error: "% e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
                '''如果全部成功则返回True'''
            if ( (bSuccess['binary']== True) and (bSuccess['description']== True) and (bSuccess['version']== True) ):
                logging.error("Logic Error: strategy update Success!")
                return True
            else:
                logging.error("Logic Error: strategy update Fial!")
                return False

    def get_logic_file(self, strLogicName, strFilePath):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select dllcontent from list_dllstore where DllName = '%s'" % (strLogicName))
            for item in cu.fetchall():
                resultAll = queueList.append({item[0]})
            with open(strDllFilePath, 'rb') as f:
                 result = sqlite3.Binary(f.read())
            if resultAll == result:
                pass

        except Exception as e:
            print(e.__str__())




    @classmethod
    def modify_logic_name(cls, strDBFileName,strLogicName, strLogicNewName):
        cu = None
        con = None
        bSuccess = False
        flag = 0
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("select DllName from list_dllstore where DllName = '%s' " % (strLogicNewName))
            resultAll = result.fetchall()
            if not resultAll or len(result) == 0:
                flag = 1
            if flag is 1:
                cu.execute("update list_dllstore set DllName = '%s' where  DllName = '%s'" % (strLogicNewName, strLogicName))
                bSuccess = con.commit()
            else:
                print("this name had been used")
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    @classmethod
    def get_logics_list_of_queue(cls, strDBFileName,strQueueName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select id,DllName,importtime,author,periodicity,dllcontent,runstatus,unitproperty01,unitproperty02,unitproperty03,unitproperty04 from list_dllstore  where unitproperty04 = '%s'" % (strQueueName))
            for item in cu.fetchall():
                #print(item[5].decode('gbk','ignore'))
                queueList.append({
                    'id': item[0].decode('gbk') if item[0] != None else 0,
                    'DllName': item[1].decode('gbk') if item[1] != None else '',
                    'importtime': item[2].decode('gbk') if item[2] != None else '',
                    'author': item[3].decode('gbk') if item[3] != None else '',
                    'periodicity': item[4].decode('gbk') if item[4] !=None else '',
                    #'dllcontent': item[5].decode('gbk','ignore') if item[5] != None else '',
                    'runstatus': item[6].decode('gbk') if item[6] != None else '',
                    'unitproperty01': item[7].decode('gbk') if item[7] != None else '',
                    'unitproperty02': item[8].decode('gbk') if item[8] != None else '',
                    'unitproperty03': item[9].decode('gbk') if item[9] != None else '',
                    'unitproperty04': item[10].decode('gbk') if item[10] != None else ''
                })
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return queueList

    def get_log_info(self, searchTime, dllName):
        rv = None
        # 前端处理searchTime字符串
        strSQL = 'SELECT * from '+searchTime+' where loginfo LIKE "['+dllName+']%"'
        print(strSQL)
        data = []
        rv = self._mysqlDbContainer.op_db_query('domlog', strSQL)
        for i in range(len(rv)):
            strInfo = rv[i][1].replace("[{name}]".format(name=dllName), "")
            data.append({'time':rv[i][0].strftime('%Y-%m-%d %H:%M:%S'),'loginfo': strInfo,'_id':i})
        return data

    def get_log_info_from_file(self, dllFilePath, logicCustomNameWithExt):
        with open(dllFilePath, "r") as fileObj:
            strLines = fileObj.readlines()

        if not len(strLines):
            return []

        roundList = [] # 分级整理
        bAddNewRound = False
        for index, strLine in enumerate(strLines):
            try:
                strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", strLine)
                if not len(strTimeList):
                    continue

                strTime = strTimeList[0]
                strLine = strLine.replace(strTime, "")
                strLine = strLine.replace("[{name}]".format(name=logicCustomNameWithExt), "").strip()

                lineSectionName = self.get_section_name(strLine)

                if not len(roundList):
                    roundList.append(dict(round=1, sections=[]))
                elif bAddNewRound:
                    nRdLength = len(roundList)
                    roundList.append(dict(round=nRdLength + 1, sections=[]))
                    bAddNewRound = False

                if not len(roundList[-1]["sections"]):
                    roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                          logList=[{"time": strTime, "loginfo": strLine}]))
                else:
                    if roundList[-1]["sections"][-1].get("sectionName", "") != lineSectionName:
                        roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                              logList=[{"time": strTime, "loginfo": strLine}]))
                    else:
                        roundList[-1]["sections"][-1]["logList"].append(dict(time=strTime, loginfo=strLine))

                if strLine.find("ACT ONCE END") >= 0:
                    bAddNewRound = True

            except Exception as e:
                print(e.__str__())

        return roundList

    def get_log_info_of_one_day_zipped(self, strFolderName, dllFilePath):
        try:
            if not os.path.exists(dllFilePath):
                return []
            fileNameWithExt = os.path.split(dllFilePath)[1]
            fileName = os.path.splitext(fileNameWithExt)[0]
            zipFileName = "{folder}-{file}.zip".format(folder=strFolderName, file=fileName)

            filesDir = os.path.join(app.static_folder, "files")
            if not os.path.exists(filesDir):
                os.mkdir(filesDir)

            tempDir = os.path.join(filesDir, "temp")
            if not os.path.exists(tempDir):
                os.mkdir(tempDir)

            dllDir = os.path.join(tempDir, strFolderName)
            if not os.path.exists(dllDir):
                os.mkdir(dllDir)

            dllPath = os.path.join(dllDir, fileNameWithExt)

            zipFilePath = os.path.join(tempDir, zipFileName)

            if os.path.exists(dllPath):
                os.remove(dllPath)

            if os.path.exists(zipFilePath):
                os.remove(zipFilePath)

            shutil.copyfile(dllFilePath, dllPath)

            zipObj = zipfile.ZipFile(zipFilePath, 'w', zipfile.ZIP_DEFLATED)

            bSucZip = zip_folder(dllDir, zipObj)

            shutil.rmtree(os.path.join(tempDir, strFolderName))

            if bSucZip:
                return os.path.join("static", "files", "temp", zipFileName)
            return None
        except Exception as e:
            logging.error("ERROR in get_log_info_of_one_day_zipped: %s" % e.__str__())
            return None

    def strategy_zip_one_day_log_of_very_date(self, strDate, logFilePath, strategyNameWithExt):
        try:
            if not len(logFilePath):
                return "", "未找到日志文件"

            zipFileName = "{strategy}-log-{date}.zip".format(strategy=strategyNameWithExt, date=strDate)

            filesDir = os.path.join(app.static_folder, "files")
            if not os.path.exists(filesDir):
                os.mkdir(filesDir)

            tempDir = os.path.join(filesDir, "temp")
            if not os.path.exists(tempDir):
                os.mkdir(tempDir)

            zipFilePath = os.path.join(tempDir, zipFileName)
            if os.path.exists(zipFilePath):
                os.remove(zipFilePath)

            dstZipDir = os.path.join(tempDir, "{strategy}-log-{date}".format(strategy=strategyNameWithExt, date=strDate))
            if not os.path.exists(dstZipDir):
                os.mkdir(dstZipDir)

            dstZipPath = os.path.join(dstZipDir, strategyNameWithExt)

            shutil.copyfile(logFilePath, dstZipPath)

            zipObj = zipfile.ZipFile(zipFilePath, "w", zipfile.ZIP_DEFLATED)
            bSucZip = zip_folder(dstZipDir, zipObj)

            shutil.rmtree(dstZipDir)

            if bSucZip:
                return zipFileName, ""
            return "", "压缩失败"
        except Exception as e:
            strLog = "ERROR in zip_process_log: %s" % e.__str__()
            logging.error(strLog)
            return "", strLog

    def get_critical_log(self, strTimeFrom, strTimeTo):
        logDir = os.path.join(app.config["CORE_PATH"], "log")
        if not os.path.exists(logDir):
            return [], "log文件夹不存在"

        filePath = os.path.join(logDir, "CRITICAL.txt")
        if not os.path.exists(filePath):
            return [], "CRITICAL.txt不存在"

        tFrom = datetime.strptime(strTimeFrom, "%Y-%m-%d %H:%M:%S")
        tTo = datetime.strptime(strTimeTo, "%Y-%m-%d %H:%M:%S")

        if tFrom > tTo:
            return [], "起始时间不能大于终止时间"

        with open(filePath, "r", encoding="gbk", errors="ignore") as fo:
            allLines = fo.readlines()

        allLines.reverse()
        logList = []

        for line in allLines:
            if not len(line):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")

            if tTime >= tFrom and tTime <= tTo:
                content = line.replace(strTime, "").replace("\n", "").replace("\r", "").strip()
                logList.append(dict(time=strTime, loginfo=content))

        return logList, ""


    """
    查询目标时间前后5分钟范围内的日志
    """
    def strategy_get_log_near_time_V2(self, tTargetTime, dllFilePath, logicCustomNameWitExt):
        tTimeEnd = tTargetTime + timedelta(minutes=5)
        tTimeBegin = tTargetTime - timedelta(minutes=5)

        try:
            with open(dllFilePath, "r", encoding="gbk", errors="ignore") as fo:
                allLines = fo.readlines()
        except Exception as ecp:
            if isinstance(ecp, MemoryError):
                strLog = "由于日志文件过大，读取时因内存不足而报错退出，请下载log文件后查看策略日志"
            else:
                strLog = "日志文件读取错误，原因:%s" % ecp.__str__()

            return None, strLog

        roundList = []  # 分级整理结果
        tCurLogTime = None
        bAddNewRound = False
        for line in allLines:
            if not len(line):
                continue

            sLine = line.replace("\n", "")
            if not len(sLine):
                continue

            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)

            if len(timeList):
                strTime = timeList[0]
                tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
                tCurLogTime = tTime

            if isinstance(tCurLogTime, datetime):
                if tCurLogTime >= tTimeBegin and tCurLogTime <= tTimeEnd:
                    content = line.replace(tCurLogTime.strftime("%Y-%m-%d %H:%M:%S"), "").replace("\n", "").replace("\r", "").strip()
                    content = content.replace("[{name}.dll]".format(name=logicCustomNameWitExt), "").strip()

                    strCurLogTime = tCurLogTime.strftime("%Y-%m-%d %H:%M:%S")
                    lineSectionName = self.get_section_name(content)
                    if not len(roundList):
                        roundList.append(dict(round=None, sections=[], beginTime="", endTime="", seconds=None))
                    elif bAddNewRound:
                        roundList.append(dict(round=None, sections=[], beginTime="", endTime="", seconds=None))
                        bAddNewRound = False

                    if not len(roundList[-1]["sections"]):
                        roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                              logList=[{"time": strCurLogTime, "loginfo": content}],
                                                              beginTime="",
                                                              endTime="",
                                                              seconds=None))
                    else:
                        if roundList[-1]["sections"][-1].get("sectionName", "") != lineSectionName:
                            roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                                  logList=[{"time": strCurLogTime, "loginfo": content}],
                                                                  beginTime="",
                                                                  endTime="",
                                                                  seconds=None))
                        else:
                            roundList[-1]["sections"][-1]["logList"].append(dict(time=strCurLogTime, loginfo=content))

                    if content.find("ACT ONCE END") >= 0:
                        bAddNewRound = True

        for oneRound in roundList:
            roundBeginTime = ""
            roundEndTime = ""
            strRoundNum = ""
            nRdSecsCsm = None
            if isinstance(oneRound.get("sections"), list):
                if len(oneRound.get("sections")):
                    firstSection = oneRound["sections"][0]
                    lastSection = oneRound["sections"][-1]

                    if isinstance(firstSection.get("logList"), list):
                        if len(firstSection.get("logList")):
                            roundBeginTime = firstSection["logList"][0].get("time", "")
                            if isinstance(firstSection["logList"][0].get("loginfo"), str):
                                if firstSection["logList"][0].get("loginfo"):
                                    strBeginLog = firstSection["logList"][0].get("loginfo")
                                    nIdxCount = strBeginLog.find("COUNT")
                                    nIdxActOnceBegin = strBeginLog.find("ACT ONCE BEGIN")
                                    if nIdxCount >= 0 and nIdxActOnceBegin >= 0:
                                        strRoundNum = strBeginLog[(nIdxCount+5):nIdxActOnceBegin]
                                        strRoundNum = strRoundNum.replace(")", "").strip()

                    if isinstance(lastSection.get("logList"), list):
                        if len(lastSection.get("logList")):
                            roundEndTime = lastSection["logList"][-1].get("time", "")

                    for oneSection in oneRound.get("sections"):
                        sectionBeginTime = ""
                        sectionEndTime = ""
                        nSctSecsCsm = None
                        if isinstance(oneSection.get("logList"), list):
                            if len(oneSection.get("logList")):
                                sectionBeginTime = oneSection["logList"][0].get("time")
                                sectionEndTime = oneSection["logList"][-1].get("time")

                        if isValidDate(sectionBeginTime, "%Y-%m-%d %H:%M:%S") and isValidDate(sectionEndTime, "%Y-%m-%d %H:%M:%S"):
                            nSctSecsCsm = (datetime.strptime(sectionEndTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(sectionBeginTime, "%Y-%m-%d %H:%M:%S")).total_seconds()

                        oneSection.update(dict(beginTime=sectionBeginTime, endTime=sectionEndTime, seconds=nSctSecsCsm))

            if isValidDate(roundBeginTime, "%Y-%m-%d %H:%M:%S") and isValidDate(roundEndTime, "%Y-%m-%d %H:%M:%S"):
                nRdSecsCsm = (datetime.strptime(roundEndTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(roundBeginTime, "%Y-%m-%d %H:%M:%S")).total_seconds()

            oneRound.update(dict(beginTime=roundBeginTime, endTime=roundEndTime, seconds=nRdSecsCsm, round=strRoundNum))

        return roundList, ""

    """
    找从目标时间开始往后5分钟的日志，若目标时间附近没有找到日志
    则在目标时间前后查询10秒，以找到起点，然后往后查5分钟
    """
    def strategy_get_log_near_time(self, tTargetTime, dllFilePath, dllFileName, upwardSecs=1, downwardSecs=5*60):
        with open(dllFilePath, "rb") as fileObj:
            strAllLog = fileObj.read().decode('gbk', "ignore")

        strAllLog = strAllLog.replace("\r", "")
        nIndex = -1  # 目标时间所在的索引
        nDeltaSec = 0
        while nDeltaSec < 10:
            try:
                tTar = tTargetTime + timedelta(seconds=nDeltaSec)
                strTimeKeyword = tTar.strftime("%Y-%m-%d %H:%M:%S")
                nIndex = strAllLog.find(strTimeKeyword)
                if nIndex != -1:
                    break

                tTar = tTargetTime - timedelta(seconds=nDeltaSec)
                strTimeKeyword = tTar.strftime("%Y-%m-%d %H:%M:%S")
                nIndex = strAllLog.find(strTimeKeyword)
                if nIndex != -1:
                    break
            except:
                pass
            finally:
                nDeltaSec += 1

        if nIndex == -1:
            return [], "未找到指定时间附近的日志"

        strUpperHalf = strAllLog[nIndex::-1]  # 日志的上半部分
        upperHalfLineList = strUpperHalf.split("\n")

        strStartTimeKey = None
        for line in upperHalfLineList:
            strTimeList = re.findall(r"[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{2}-[0-9]{2}-[0-9]{4}", line)
            if not len(strTimeList):
                continue

            strTimeReverse = strTimeList[0]
            strTime = strTimeReverse[::-1]
            tLineTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")

            if (tTargetTime - tLineTime).total_seconds() >= upwardSecs:
                strStartTimeKey = strTime
                break

        if strStartTimeKey:
            nStartIndex = strAllLog.find(strStartTimeKey)
        else:
            nStartIndex = 0

        strBottomHalf = strAllLog[nIndex:]
        bottomHalfLineList = strBottomHalf.split("\n")

        strStopTimeKey = None
        for line in bottomHalfLineList:
            strTimeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)
            if not len(strTimeList):
                continue

            strTime = strTimeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")

            if (tTime - tTargetTime).total_seconds() > downwardSecs:
                strStopTimeKey = strTime
                break

        if strStopTimeKey:
            nStopIndex = strAllLog.find(strStopTimeKey)
        else:
            nStopIndex = len(strAllLog) - 1

        # 切片获取目标日志内容
        strLogValid = strAllLog[nStartIndex:nStopIndex]

        logList = []
        lineList = strLogValid.split("\n")
        for line in lineList:
            strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)
            if not len(strTimeList):
                continue

            strLineTime = None
            if isinstance(strTimeList, list) and len(strTimeList):
                strLineTime = strTimeList[0]

            if not strLineTime:
                continue

            strLinePro = line.replace("[{dllFileName}]".format(dllFileName=dllFileName), "")
            strLinePro = strLinePro.replace("\n", "").replace("\r", "")
            strLinePro = strLinePro.replace(strLineTime, "").strip()
            logList.append(dict(loginfo=strLinePro, time=strLineTime))

        # 补齐遗失的时间
        for idx, log in enumerate(logList):
            if not log.get("time"):
                srcTime = None
                for item in logList[idx + 1:]:
                    if item.get("time"):
                        srcTime = item.get("time")
                        break
                if srcTime:
                    log.update(dict(time=srcTime))

        return logList, ""

    def strategy_get_one_round_log_of_very_time(self, tTargetTime, dllFilePath, dllFileName):
        with open(dllFilePath, "rb") as fileObj:
            strAllLog = fileObj.read().decode('gbk', "ignore")

        strAllLog = strAllLog.replace("\r", "")

        nIndex = -1  # 目标时间所在的索引
        nDeltaSec = 0
        while nDeltaSec < 10:
            try:
                tTar = tTargetTime + timedelta(seconds=nDeltaSec)
                strTimeKeyword = tTar.strftime("%Y-%m-%d %H:%M:%S")
                nIndex = strAllLog.find(strTimeKeyword)
                if nIndex != -1:
                    break

                tTar = tTargetTime - timedelta(seconds=nDeltaSec)
                strTimeKeyword = tTar.strftime("%Y-%m-%d %H:%M:%S")
                nIndex = strAllLog.find(strTimeKeyword)
                if nIndex != -1:
                    break
            except:
                pass
            finally:
                nDeltaSec += 1

        if nIndex == -1:
            return [], "未找到指定时间附近的日志"

        # 首先从目标时间所在行检查是否有ACT ONCE BEGIN存在（目标时间即本轮日志起始处）
        nIndexBegin = -1  # 偏移量
        bDirection = False  # 偏移方向
        strAllLogStartFromnIndex = strAllLog[nIndex:]
        nIndexEndOfLine = strAllLogStartFromnIndex.find("\n")
        if nIndexEndOfLine != -1:
            strPossibleStartContent = strAllLog[nIndex:(nIndex+nIndexEndOfLine)]
            if strPossibleStartContent.find("ACT ONCE BEGIN") != -1:
                nIndexBegin = strAllLogStartFromnIndex.find("ACT ONCE BEGIN")
                bDirection = True

        # 如果目标时间所在行不是本路日志起始处，则往上寻找最近的本轮日志起始处
        if nIndexBegin == -1:
            frontSuspect = strAllLog[nIndex::-1]  # 本轮日志的上半部分
            nIndexBegin = frontSuspect.find('NIGEB ECNO TCA')
            bDirection = False

        # 如果找不到本轮日志起始标志字符串（ACT ONCE BEGINE) 则返回查询失败
        if nIndexBegin == -1:
            return [], "未找到指定时间附近的日志开始关键词ACT ONCE BEGIN"

        if bDirection:
            nValidStart = nIndex + nIndexBegin
        else:
            nValidStart = nIndex - nIndexBegin

        # 往前偏移20个字符
        if nValidStart - 20 > 0:
            nValidStart -= 20

        # 目标时间索引往后的日志部分（本轮日志的下半部分）
        laterSuspect = strAllLog[nIndex:]

        nIndexEnd = laterSuspect.find("ACT ONCE END")
        if nIndexEnd == -1:
            return [], "未找到指定时间附近的日志结束关键词ACT ONCE END"

        nValidEnd = nIndex + nIndexEnd # 从目标时间所在索引向下偏移nIndexEnd个字符

        # 在向下偏移20个字符
        if nValidEnd + 20 <= len(strAllLog) - 1:
            nValidEnd += 20
        else:
            nValidEnd = len(strAllLog) - 1

        # 切片获取目标日志内容（目标轮）
        strLogValid = strAllLog[nValidStart:nValidEnd]

        bFoundBegin = False
        logList = []
        lineList = strLogValid.split("\n")
        for line in lineList:
            strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", line)
            if not len(strTimeList) and not re.match(".*ACT ONCE BEGIN.*", line):
                continue

            strLineTime = ""
            if isinstance(strTimeList, list) and len(strTimeList):
                strLineTime = strTimeList[0]

            if re.match(".*ACT ONCE BEGIN.*", line):
                bFoundBegin = True

            if bFoundBegin:
                strLinePro = line.replace("[{dllFileName}]".format(dllFileName=dllFileName), "")
                strLinePro = strLinePro.replace("\n", "").replace("\r", "")
                strLinePro = strLinePro.replace(strLineTime, "").strip()
                logList.append(dict(loginfo=strLinePro, time=strLineTime))

            if bFoundBegin and re.match(".*ACT ONCE END.*", line):
                break

        # 补齐遗失的时间
        for idx, log in enumerate(logList):
            if not log.get("time"):
                srcTime = None
                for item in logList[idx+1:]:
                    if item.get("time"):
                        srcTime = item.get("time")
                        break
                if srcTime:
                    log.update(dict(time=srcTime))

        return logList, ""


    def get_latest_one_round_log_from_file(self, dllFilePath, logicCustomNameWithExt):
        if not os.path.exists(dllFilePath):
            return [], "日志文件不存在"

        try:
            with open(dllFilePath, "r") as fileObj:
                strLines = fileObj.readlines()
        except Exception as ept:
            if isinstance(ept, MemoryError):
                strLog = "由于日志文件过大，读取时因内存不足而报错退出，请下载log文件后查看策略日志"
            else:
                strLog = "日志文件读取错误，原因:%s" % ept.__str__()
            return None, strLog

        if not len(strLines):
            return [], "日志文件为空"

        strLines.reverse()

        roundList = []  # 分级整理
        strEndLogCur = None
        strBeginLogCur = None
        strBeginLogLastRound = None

        strCurLogTime = None
        bAddNewRound = False
        for index, strLine in enumerate(strLines):
            try:
                if not len(strLine):
                    continue

                sLine = strLine.replace("\n", "")
                if not len(sLine):
                    continue

                strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", strLine)
                if len(strTimeList):
                    strTime = strTimeList[0]
                    strCurLogTime = strTime

                if not isinstance(strCurLogTime, str):
                    continue

                if strEndLogCur == None:
                    if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}.*$", strLine):
                        strEndLogCur = strLine
                else:
                    if re.match(".*ACT ONCE END.*", strLine):
                        strEndLogLastRound = strLine

                if not strEndLogCur:
                    continue

                if strBeginLogCur == None:
                    if re.match(".*ACT ONCE BEGIN.*", strLine):
                        strBeginLogCur = strLine
                else:
                    if re.match(".*ACT ONCE BEGIN.*", strLine):
                        strBeginLogLastRound = strLine

                strLinePro = strLine.replace(strCurLogTime, "")
                strLinePro = strLinePro.replace("[{name}]".format(name=logicCustomNameWithExt), "").strip()

                lineSectionName = self.get_section_name(strLinePro)

                # 若达到终止标签则下一行日志新建一个round
                if strLinePro.find("ACT ONCE END") >= 0 or not len(roundList):
                    bAddNewRound = True

                if bAddNewRound:
                    roundList.append(dict(sections=[]))
                    bAddNewRound = False

                if not len(roundList[-1]["sections"]):
                    roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                         logList=[{"time": strCurLogTime, "loginfo": strLinePro}],
                                                         beginTime="",
                                                         endTime="",
                                                         seconds=None))
                else:
                    if roundList[-1]["sections"][-1].get("sectionName", "") != lineSectionName:
                        roundList[-1]["sections"].append(dict(sectionName=lineSectionName,
                                                             logList=[{"time": strCurLogTime, "loginfo": strLinePro}],
                                                             beginTime="",
                                                             endTime="",
                                                             seconds=None))
                    else:
                        roundList[-1]["sections"][-1]["logList"].append(dict(time=strCurLogTime, loginfo=strLinePro))

                if strBeginLogLastRound:
                    break

            except Exception as e:
                print(e.__str__())

        # round 倒序
        roundList.reverse()

        for nRdIdx, round in enumerate(roundList):
            roundBeginTime = ""
            roundEndTime = ""
            strRoundNum = ""
            nRdSecsCsm = None

            if len(round.get("sections", [])):
                round["sections"].reverse()
                for section in round["sections"]:
                    if len(section.get("logList", [])):
                        section["logList"].reverse()
                        nSctSecsCsm = None
                        sectionBeginTime = section["logList"][0].get("time")
                        sectionEndTime = section["logList"][-1].get("time")
                        if isValidDate(sectionBeginTime, "%Y-%m-%d %H:%M:%S") and isValidDate(sectionEndTime, "%Y-%m-%d %H:%M:%S"):
                            nSctSecsCsm = (datetime.strptime(sectionEndTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(sectionBeginTime, "%Y-%m-%d %H:%M:%S")).total_seconds()

                        section.update(dict(beginTime=sectionBeginTime, endTime=sectionEndTime, seconds=nSctSecsCsm))

                firstSection = round["sections"][0]
                lastSection = round["sections"][-1]

                if isinstance(firstSection.get("logList"), list):
                    if len(firstSection.get("logList")):
                        roundBeginTime = firstSection["logList"][0].get("time", "")
                        if isinstance(firstSection["logList"][0].get("loginfo"), str):
                            if firstSection["logList"][0].get("loginfo"):
                                strBeginLog = firstSection["logList"][0].get("loginfo")
                                nIdxCount = strBeginLog.find("COUNT")
                                nIdxActOnceBegin = strBeginLog.find("ACT ONCE BEGIN")
                                if nIdxCount >= 0 and nIdxActOnceBegin >= 0:
                                    strRoundNum = strBeginLog[(nIdxCount + 5):nIdxActOnceBegin]
                                    strRoundNum = strRoundNum.replace(")", "").strip()

                if isinstance(lastSection.get("logList"), list):
                    if len(lastSection.get("logList")):
                        roundEndTime = lastSection["logList"][-1].get("time", "")

                if isValidDate(roundBeginTime, "%Y-%m-%d %H:%M:%S") and isValidDate(roundEndTime, "%Y-%m-%d %H:%M:%S"):
                    nRdSecsCsm = (datetime.strptime(roundEndTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(roundBeginTime,"%Y-%m-%d %H:%M:%S")).total_seconds()

                round.update(dict(beginTime=roundBeginTime, endTime=roundEndTime, seconds=nRdSecsCsm, round=strRoundNum))

        return roundList, ""

    @classmethod # 根据策略名称获取策略配置
    def get_logic_parameters(cls, strDBFileName,strLogicName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select vname,pname,ptype,vexplain,DllName,INorOut,unitproperty01 from list_paramterConfig  where DllName = '%s'" % (strLogicName))
            for item in cu.fetchall():
             queueList.append({'vname': item[0].decode('gbk') if item[0] != None else 0,
                              'pname': item[1].decode('gbk') if item[1] != None else '',
                              'ptype': item[2].decode('gbk') if item[2] != None else '',
                              'vexplain': item[3].decode('gbk') if item[3] != None else '',
                              'DllName': item[4].decode('gbk') if item[4] != None else '',
                              'INorOut': item[5] if item[5] != None else 0,
                              'outputCondition': item[6].decode('gbk') if item[6] != None else '',
                            })

        finally:
            if cu is not None:
               cu.close()
            if con is not None:
             con.close()
        return queueList

    @classmethod #更新策略配置
    def modify_logic_parameters(cls, strDBFileName,strLogicName,inputParameterList, outputParameterList):
        cu = None
        con = None
        bSuccess = False
        flag = 0
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("select vname from list_paramterConfig where DllName = '%s' and vname= '%s'" % (strLogicName,outputParameterList))
            resultAll  = result.fetchall()
            if not resultAll or len(result)==0:
                flag = 1
            if flag is 1:
                    cu.execute("update list_paramterConfig set vname = '%s' where vname = '%s' and DllName = '%s'"%(outputParameterList, inputParameterList, strLogicName))
                    bSuccess = con.commit()
            else:
                 print("this name had been used")
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    # 更新策略设置 DllName为策略唯一标识符，vname为策略中的配置参数标识符 ,pname参数值，ptype类型，unitproperty01是否启用
    @classmethod
    def modify_logic_parameter(cls,strDBFileName,DllName,vname,pname,ptype,unitproperty01):
        cu = None
        con = None
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            strSQLite = 'UPDATE list_paramterConfig set  pname="%s", ptype="%s",unitproperty01="%s" WHERE DllName="%s" AND vname="%s"' %(pname,ptype,unitproperty01,DllName,vname)

            result = cu.execute(strSQLite)
            resultAll  = result.fetchall()
            if not resultAll or len(result)==0:
                con.commit()
                bSuccess = True
            else :
                print('failed')
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess


    @classmethod
    def modify_logic_parameter_input_one(cls, strDBFileName,strLogicName,inputParameterName,inputtype,outputdate):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            # pname,ptype,vexplain
            state = cu.execute("select INorOut from list_paramterConfig  where vname = '%s' and DllName = '%s'"%(inputParameterName,strLogicName))
            for item in state:
                if item[0] == 0:
                    if inputtype is "pname":
                        cu.execute("update list_paramterConfig set pname = '%s' where vname = '%s' and DllName = '%s'"%(outputdate, inputParameterName, strLogicName))
                    elif inputtype is "ptype":
                        cu.execute("update list_paramterConfig set ptype = '%s' where vname = '%s' and DllName = '%s'"%(outputdate, inputParameterName, strLogicName))
                    elif inputtype is "vexplain":
                        cu.execute("update list_paramterConfig set ptype = '%s' where vname = '%s' and DllName = '%s'" % (outputdate, inputParameterName, strLogicName))
            bSuccess = con.commit()
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess



    @classmethod
    def modify_logic_parameter_output_one(cls,strDBFileName,strLogicName,inputParameterName,inputtype,outputdate):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            # pname,ptype,vexplain
            state = cu.execute("select INorOut from list_paramterConfig  where vname = '%s' and DllName = '%s'" % (
            inputParameterName, strLogicName))
            for item in state:
                if item[0] == 1:
                    if inputtype is "pname":
                        cu.execute("update list_paramterConfig set pname = '%s' where vname = '%s' and DllName = '%s'" % (outputdate, inputParameterName, strLogicName))
                    elif inputtype is "ptype":
                        cu.execute("update list_paramterConfig set ptype = '%s' where vname = '%s' and DllName = '%s'" % (outputdate, inputParameterName, strLogicName))
                    elif inputtype is "vexplain":
                        cu.execute("update list_paramterConfig set ptype = '%s' where vname = '%s' and DllName = '%s'" % (outputdate, inputParameterName, strLogicName))
            bSuccess = con.commit()
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    @classmethod
    def get_groups_of_thread(cls, strThreadName):
        cu = None
        con = None
        bSuccess = False
        queueList = []
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select threadname,threadtimetype,threadtimedefine from list_dllthread  where threadname = '%s'" % (strThreadName))
            for item in cu.fetchall():
                queueList.append({'threadname': item[0].decode("gbk"),'threadtimetype': item[1].decode('gbk') if item[1] != None else '','threadtimedefine': item[2].decode('gbk') if item[2] != None else '' })
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return queueList

    def modify_groups_of_thread(cls,strDBFileName, strnewThreadName,stroldThreadName):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("select threadname from list_dllthread where threadname = '%s' " % (strnewThreadName))
            resultAll = result.fetchall()
            if not resultAll or len(result) == 0:
                flag = 1
            if flag is 1:
                cu.execute("update list_dllthread set threadname ='%s'  where threadname = '%s'" % (strnewThreadName, stroldThreadName))
                bSuccess = con.commit()
            else:
                print("this name had been used")
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    @classmethod
    def add_groups_of_thread(cls,strDBFileName,strThreadName,strThreadtimetype,strThreadtimedefine):
        cu = None
        con = None
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            result = cu.execute("select threadname from list_dllthread where threadname = '%s' " % (strThreadName))
            resultAll = result.fetchall()
            if not resultAll or len(result) == 0:
                flag = 1
            if flag is 1:
                cu.execute('insert into list_dllthread (threadname,threadtimetype,threadtimedefine) values( "%s","%s","%s")'% (strThreadName,strThreadtimetype, strThreadtimedefine))
                bSuccess = con.commit()
            else:
                print("this name had been used")

        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    #获取策略列表
    @classmethod
    def get_logics_of_group(cls,strDBFileName, groupId):
        cu = None
        con = None
        bSuccess = False
        flag = 0
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = sqlite3.connect(dbfileDec)
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), strDBFileName)
                dbfileDec = '{}'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                    con = sqlite3.connect(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select count(*) from list_dllstore where unitproperty05=(?);", (groupId,))
            total = cur.fetchone()
            print("the number of total is %s", total)
            # result=cu.execute( "select DllName,importtime,author,periodicity,dllcontent,runstatus,unitproperty01,unitproperty02,unitproperty03,unirproperity04 from list_dllstore group by unitproperty05 ")
            # for item in cu.fetchall():
            #     queueList.append({'DllName': item[0].decode('gdk') if item[0] != None else '',
            #                   'importtime': item[1].decode('gbk') if item[1] != None else '',
            #                   'author': item[2].decode('gbk') if item[2] != None else '',
            #                   'periodicity': item[3].decode('gbk') if item[3] != None else '',
            #                   'dllcontent': item[4].decode('gbk') if item[4] != None else '',
            #                   'runstatus': item[5].decode('gdk') if item[5] != None else '',
            #                   'unitproperty01': item[6].decode('gbk'),'unitproperty02': item[7].decode('gbk') ,
            #                    'unitproperty03': item[8].decode('gbk') ,'dllcontent':item[9].decode('gbk') ,})

        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return true

    @classmethod
    def link_logic(cls, fromLogicName, fromLogicOutputName, toLogicName, toLogicInputName):
        pass

    def find_all_indexes_of_char_from_string(self, string, char):
        indexList = []
        nCur = -1
        while True:
            nCur = string.find(char, nCur + 1)
            if nCur == -1:
                break

            indexList.append(nCur)
        return indexList


    def get_operation_record_output(self, pointName, tTimeFrom, tTimeTo, opRecordDir):
        tFrom = datetime.now()

        errList = []
        nTimeLength = 20
        patTime = "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"
        patPoint = r"^" + pointName + "\.txt$"
        patSource = r"^Source_.*\.txt$"

        recordList = []  # 旧版操作记录容器
        dNewRecordNormal = {}  # 新版操作记录容器
        dNewRecordAbnormal = {}  # 新版操作记录容器（当读文件内存溢出时）

        for root, dirs, strFileNames in os.walk(opRecordDir):
            for strFileName in strFileNames:
                if not strFileName.endswith(".txt"):
                    continue

                # 新版操作记录
                if re.match(patSource, strFileName):
                    source = strFileName.replace("Source_", "").replace(".txt", "")

                    bSliceUp = True
                    fullString = ""
                    try:
                        with open(os.path.join(opRecordDir, strFileName), "rb") as fileObj:
                            fullString = fileObj.read().decode('gbk', "ignore")
                    except:
                        bSliceUp = False

                    if bSliceUp:  # 若内存不溢出

                        idxList = self.find_all_indexes_of_char_from_string(fullString, pointName)
                        if not len(idxList):
                            continue

                        for nIdx in idxList:
                            try:
                                chunk = fullString[nIdx-nTimeLength:nIdx]
                                strTimeList = re.findall(patTime, chunk)
                                if not len(strTimeList):
                                    continue

                                tTime = datetime.strptime(strTimeList[0], "%Y-%m-%d %H:%M:%S")
                                if tTime < tTimeFrom or tTime > tTimeTo:
                                    continue

                                nValueIdxStart = nIdx + len(pointName)

                                strObj = fullString[nValueIdxStart]

                                # 用于屏蔽如下情况，点名为Plant01RealtimeEfficiency，
                                # 但该nIdx定位到的点名是Plant01RealtimeEfficiencyMA15，此时需要将该nIdx过滤掉
                                # 操作记录中点名之后的第一个字符一定是一个\t
                                if strObj != "\t":
                                    continue

                                strValue = ""
                                while strObj != "\n":
                                    strValue += strObj

                                    if re.findall(r"\n[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", strValue):
                                        break

                                    if re.findall(patTime, strValue):
                                        break

                                    if len(strValue) > 100:
                                        break

                                    if strObj == "\r":
                                        break

                                    nValueIdxStart += 1
                                    strObj = fullString[nValueIdxStart]

                                strValue = strValue.replace("\t", "").replace("\n", "").replace("\r", "").strip()

                                if not strValue:
                                    continue

                                if source not in dNewRecordNormal.keys():
                                    dNewRecordNormal.update({source: []})

                                dNewRecordNormal[source].append(dict(time=strTimeList[0], logicName=source, pointName=pointName, value=strValue, tTime=tTime))

                                # rtList.append(dict(time=strTimeList[0], logicName=source, pointName=pointName, value=strValue, tTime=tTime))
                            except Exception as err:
                                errList.append(err.__str__())

                    else: # 内存溢出则使用旧版读法

                        with open(os.path.join(opRecordDir, strFileName), "r", encoding="UTF8", errors="ignore") as fo:
                            lines = fo.readlines()
                        for line in lines:
                            if line == "\n":
                                continue

                            if not line:
                                continue

                            try:
                                items = line.replace("\n", "").split("\t")
                                validObjectList = [obj for obj in items if len(obj)]
                                if len(validObjectList) < 3:
                                    continue

                                strTime = validObjectList[0].strip()
                                linePointName = validObjectList[1].strip()
                                value = validObjectList[2].strip()

                                tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")

                                if linePointName != pointName:
                                    continue

                                if tTime < tTimeFrom or tTime > tTimeTo:
                                    continue

                                if source not in dNewRecordAbnormal.keys():
                                    dNewRecordAbnormal.update({source: []})

                                dNewRecordAbnormal[source].append(dict(time=strTime, logicName=source, pointName=linePointName, value=value, tTime=tTime))

                                # rtList.append(
                                #     dict(time=strTime, logicName=source, pointName=linePointName, value=value, tTime=tTime))

                            except:
                                pass

                # 旧版操作记录
                elif re.match(patPoint, strFileName):

                    with open(os.path.join(opRecordDir, strFileName), "r", encoding="UTF8", errors="ignore") as fo:
                        lines = fo.readlines()
                    for line in lines:
                        if line == "\n":
                            continue

                        if not line:
                            continue

                        try:
                            items = line.replace("\n", "").split("\t")
                            validObjectList = [obj for obj in items if len(obj)]
                            if len(validObjectList) < 3:
                                continue

                            strTime = validObjectList[0].strip()
                            operator = validObjectList[1].strip()
                            value = validObjectList[2].strip()

                            tTime = datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
                            if tTime >= tTimeFrom and tTime <= tTimeTo:
                                recordList.append(dict(time=strTime, logicName=operator, pointName=pointName, value=value, tTime=tTime))

                        except:
                            pass

                    recordList.reverse()

        tDelta = (datetime.now() - tFrom).total_seconds()
        logging.error("operation/logicRecordOutput读耗时: %s" % tDelta)

        tFrom = datetime.now()

        rtList = []
        if dNewRecordNormal:
            for src, itemList in dNewRecordNormal.items():
                itemList.reverse()
                rtList.append(itemList)

        if dNewRecordAbnormal:
            for src, itemList in dNewRecordAbnormal.items():
                itemList.reverse()
                rtList.append(itemList)

        rtList.append(recordList)

        for i in range(len(rtList)):
            for j in range(len(rtList)-i-1):
                if len(rtList[j]) and len(rtList[j+1]):
                    if rtList[j][0].get("tTime") < rtList[j+1][0].get("tTime"):
                        rtList[j], rtList[j+1] = rtList[j+1], rtList[j]

        tDelta = (datetime.now() - tFrom).total_seconds()
        logging.error("operation/logicRecordOutput排序耗时: %s" % tDelta)

        return dict(code=0, msg=";".join(errList), data=rtList)

    def get_section_name(self, strTar):
        unknown = "空段名"
        if strTar.find("ACT ONCE BEGIN") >= 0:
            return "起始标签"
        if strTar.find("ACT ONCE END") >= 0:
            return "终止标签"

        try:
            if not strTar.startswith("["):
                return unknown
            nIdxEnd = strTar.find("]")
            if nIdxEnd == -1:
                return unknown
            if nIdxEnd <= 0:
                return unknown
            name = strTar[0:nIdxEnd].replace("[", "")
            if len(name):
                return name
            return unknown
        except Exception as e:
            print(e.__str__())
            return unknown

    def get_latest_round_log_of_test_failure(self, strDllFilePath, customLogicNameWithExt, keyword):
        strLog = ""
        if not os.path.exists(strDllFilePath):
            return []

        with open(strDllFilePath, "r") as fo:
            strLines = fo.readlines()

        if not len(strLines):
            return []

        strLines.reverse()

        logList = []
        strEndLogCur = None
        bFoundKeyword = False  # 当在一轮中发现关键词（失败）时则认为此轮为需要寻找的日志
        nCount = 0
        for idx, strLine in enumerate(strLines):
            if not len(strLine):
                continue

            strLine = strLine.replace("\n", "")
            if not len(strLine):
                continue

            strTimeList = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", strLine)
            if not len(strTimeList):
                continue

            if strEndLogCur == None:
                if strLine.find("ACT ONCE END") >= 0:
                    strEndLogCur = strLine

            if strEndLogCur == None:
                continue

            if strLine.find(keyword) >= 0:
                bFoundKeyword = True

            strLinePro = strLine.replace("[{name}]".format(name=customLogicNameWithExt), "").strip()
            logList.append("<p>{content}</p>".format(content=strLinePro))

            if strLine.find("ACT ONCE BEGIN") >= 0:
                if bFoundKeyword:
                    break
                else:
                    logList.clear()
                    strEndLogCur = None
                    if nCount >= 400:
                        strLog = "已寻找最近的400轮日志，未发现'失败'关键字，退出"
                        break
                    nCount += 1

        if len(logList):
            if bFoundKeyword:
                logList.reverse()
                return logList, strLog
            else:
                logList.clear()
        return logList, strLog












