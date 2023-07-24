# -*- coding: utf-8 -*-

"""
Routes and views for the flask application.
"""
import xlwt
import xlrd

from siteinterface import app
from flask import g, json
from math import floor, ceil
import os, sys
import mysql.connector
from math import floor, ceil
from datetime import datetime, timedelta
import time
import logging
import sqlite3
from os import environ, listdir, path, unlink, remove, makedirs, stat
import shutil
from sqlite3 import InternalError,DataError,IntegrityError,InterfaceError,NotSupportedError,OperationalError

from win32event import CreateMutex
from win32api import CloseHandle, GetLastError, ShellExecute
from winerror import ERROR_ALREADY_EXISTS
from version import siteVersion
from siteinterface.utils import *
from enum import IntEnum
import traceback
from .sqlite_manager import SqliteManager
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface.commonUtils import numericItemToInt, check_encoding, is_int_digit, check_bytes_encoding
from siteinterface.RedisManager import RedisManager
import chardet


class AttachFileType(IntEnum):
    SystemFile = 0,
    UserFile = 1,
    ReportFile = 2


class AttachReportFileTimeType(IntEnum):
    DailyReport = 0,
    WeeklyReport = 1,
    MonthlyReport = 2


class BEOPSqliteAccess:
    __instance = None

    def __init__(self):
        pass

    @classmethod
    def getInstance(self, strSource=''):
        if (self.__instance == None):
            self.__instance = BEOPSqliteAccess()

        print('SqliteAccess Acquire...'+ strSource)
        return self.__instance

    @classmethod
    def get_db(self, dbname):
        db = None
        return db

    '''
    根据项目编号，获取数据连接。如果项目编号为0则打开默认数据库文件，只支持4db格式，3db不进行多项目处理
    '''

    def get_con(self, projId=0):
        dbfile = app.config.get("USE_4DB_NAME")

        if projId > 0:
            dbfile = os.path.join(app.config.get('CORE_PATH'), 'domdb%03d.4db' % projId)
        if not os.path.exists(dbfile):
            raise Exception('未找到项目4db文件 %s' % dbfile)

        con = self.connect_readonly(dbfile)
        return con

    def release_db(self, db, cur):
        if cur is not None:
            cur.close()
        if db is not None:
            db.close()

    def getFaultPointListFromS3db_With_Redis(self):

        result = []
        record = [0]
        condition = None
        try:
            if RedisManager.is_alive():
                pointData = RedisManager.get_4db_points_info()
            else:
                pointData = self.getPointInfoFromS3db(None)

            if pointData is None:
                return None

            for k, v in pointData.items():
                if v.get('param2')=='fault':
                    result.append(v)

        except Exception as err:
            print(str(err))
        return {
            'pointList': result,
            'total': len(result)
        }
            
    def getPointListFromS3db_With_Redis(self, page_index, page_size, keyword, projId=0):
        
        result = []
        record = [0]
        condition = None
        try:
            pointDataInRedis = RedisManager.get_4db_points_info()
            if pointDataInRedis is None:
                return self.getPointListFromS3db( page_index, page_size, keyword, projId)

            for k,v in pointDataInRedis.items():
                if keyword:
                    if k.find(keyword)>=0:
                        result.append(v)
                else:
                    result.append(v)


        except Exception as err:
            print(str(err))
        return {
            'pointList': result,
            'total': len(result)
        }

    '''
    获取项目点表。项目编号为0则打开默认项目
    '''

    def getPointListFromS3db(self, page_index, page_size, keyword, projId=0):
        cur = None
        con = None
        result = []
        record = [0]
        condition = None
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return None

            # con = self.connect_readonly(dbfileDec)

            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                con = self.get_con(projId)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            start_index = (page_index - 1) * page_size
            if keyword:
                keyword = '%%%s%%' % keyword
                sql = 'select name, ch_description, SourceType, Param1, highhigh as highLimit, low as lowLimit from list_point where name like ? ' \
                      'or ch_description like ? order by id limit ?, ?'
                cur.execute(sql, (keyword, keyword, start_index, page_size))
                data = cur.fetchall()
                cur.execute('SELECT count(id) FROM list_point where name like ? or ch_description like ?',
                            (keyword, keyword))
                record = cur.fetchone()
            else:
                sql = 'select name, ch_description, SourceType, Param1, highhigh as highLimit, low as lowLimit from list_point order by id limit ?, ?'
                cur.execute(sql, (start_index, page_size))
                data = cur.fetchall()
                cur.execute('SELECT count(id) FROM list_point')
                record = cur.fetchone()

            for item in data:
                dTemp = {
                    'name': item[0].decode('gbk'),
                    'description': item[1].decode('gbk'),
                    'sourceType': item[2].decode('gbk'),
                    'addr': item[3].decode('gbk')
                }

                try:
                    if item[4] or item[5]:

                        dTemp.update({
                            "pointInfo": dict()
                        })

                        if item[4] and (isinstance(item[4], float) or isinstance(item[4], int)):
                            dTemp["pointInfo"].update({
                                "hight": item[4]
                            })

                        if item[5] and (isinstance(item[5], float) or isinstance(item[5], int)):
                            dTemp["pointInfo"].update({
                                "low": item[5]
                            })

                except:
                    traceback.print_exc()

                result.append(dTemp)

        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return {
            'pointList': result,
            'total': record[0]
        }

    '''
    删除点表
    '''

    def deletePoint(self, pointList, projId=0):
        cur = None
        con = None
        bSuccess = False
        if not len(pointList):
            return {"success": True, "recc": None}

        try:
            dbFilePath = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbFilePath):
                logging.error("ERROR in BEOPSqliteAccess::insertPointList: %s doesn't exist" % dbFilePath)
                return False

            con = sqlite3.connect(dbFilePath)
            con.text_factory = bytes
            cur = con.cursor()
            sql = 'delete from list_point where name in(%s)' % ','.join('?' * len(pointList))
            recc = cur.execute(sql, pointList).rowcount
            con.commit()
            bSuccess = True

        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return {
            'success': bSuccess,
            "recc": None
        }

    def clearPointList(self, projId=0):
        cur = None
        con = None
        bSuccess = False
        try:

            dbFile = app.config.get("USE_4DB_NAME")
            con = sqlite3.connect(dbFile)
            con.text_factory = bytes
            cur = con.cursor()
            sql = 'delete from list_point'
            cur.execute(sql)
            con.commit()
            bSuccess = True

        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return bSuccess

    """补充点表，即只增加点表中不存在的点"""
    def supplementPoints(self, pointNameListToDeleteFromExisting, toAddPointList):
        cur = None
        con = None
        bSuccess = False
        strArrsystem = ["None", "HVAC", "Power", "Lighting", "CRAC"]
        strArrdevice = ["None", "Chiller", "Pump", "CT", "AHU", "VAV", "System"]
        strArrtype = ["None", "Power meter", "Thermal meter", "Tmperature", "Flow rate", "Pressure", "Amps", "Power",
                      "Frequency", "OnOff", "Alarm"]

        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            return False, "domdb.4db不存在"

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strDel = "DELETE FROM list_point WHERE name in (" + ",".join(['"{name}"'.format(name=item) for item in pointNameListToDeleteFromExisting]) + ")"

            insertSQL = 'INSERT INTO list_point(id,name,storetable,storeid,updatetable,updateid,type,unit,ch_description,en_description,R_W,`group`,calc_method,Source,Param1,Param2,Param3,Param4,Param5,Param6,Param7,Param8,Param9,Param10,SourceType,high,highhigh,low,lowlow,Param11,Param12,Param13,Param14,Param15,Param16,Param17,Param18, Param19) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
            params = []
            for index in range(len(toAddPointList)):
                onePoint = toAddPointList[index]
                if (onePoint[5] == 'R' or onePoint[5] == "0"):
                    onePoint[5] = '0'
                else:
                    onePoint[5] = '1'
                for i in range(len(strArrsystem)):
                    if (onePoint[22] == strArrsystem[i]):
                        onePoint[22] = i + 1
                        break
                for j in range(len(strArrdevice)):
                    if (onePoint[23] == strArrdevice[j]):
                        onePoint[23] = j + 1
                        break
                for k in range(len(strArrtype)):
                    if (onePoint[24] == strArrtype[k]):
                        onePoint[24] = k + 1
                        break
                if onePoint[16] == '':
                    onePoint[16] = -9999.0

                try:
                    strChDescription = onePoint[3].encode('gbk')
                except:
                    strChDescription = ""

                strUnit = ""
                try:
                    strUnit = onePoint[4].encode("gbk")
                except:
                    try:
                        strUnit = onePoint[4].encode("utf8")
                    except:
                        pass

                strDecimal = "2"
                if len(onePoint) >= 26:
                    strDecimal = onePoint[25]

                params.append((
                    int(onePoint[0]), onePoint[1], '', '', '', '', '0', strUnit, strChDescription, '',
                    int(onePoint[5]), 0, '', '12', onePoint[6], onePoint[7], onePoint[8],
                    onePoint[9], onePoint[10], onePoint[11], onePoint[12], onePoint[13], onePoint[14], onePoint[15],
                    onePoint[2], onePoint[16], onePoint[17], onePoint[18],
                    onePoint[19], onePoint[20], '', '', '', onePoint[21], onePoint[22], onePoint[23], onePoint[24],
                    strDecimal))

            cur.execute(strDel)
            cur.executemany(insertSQL, tuple(params))
            con.commit()
            bSuccess = True
            return True, ""
        except Exception as err:
            return False, "补充点表失败:{err}".format(err=err.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def insertPointList(self, pointList, nProjSrc=0):
        strLogProfix = "[DOM]"
        if nProjSrc == 1:
            strLogProfix = "[DEEPLOGIC]"
        cur = None
        con = None
        bSuccess = False
        errList = []
        record = [0]
        strArrsystem = ["None", "HVAC", "Power", "Lighting", "CRAC"]
        strArrdevice = ["None", "Chiller", "Pump", "CT", "AHU", "VAV", "System"]
        strArrtype = ["None", "Power meter", "Thermal meter", "Tmperature", "Flow rate", "Pressure", "Amps", "Power",
                      "Frequency", "OnOff", "Alarm"]
        try:

            dbFilePath = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbFilePath):
                logging.error("ERROR in BEOPSqliteAccess::insertPointList: %s doesn't exist" % dbFilePath)
                return {"msg": "domdb.4db不存在", "success": False}

            con = sqlite3.connect(dbFilePath)
            con.text_factory = bytes
            cur = con.cursor()

            insertSQL = 'INSERT INTO list_point(id,name,storetable,storeid,updatetable,updateid,type,unit,ch_description,en_description,R_W,`group`,calc_method,Source,Param1,Param2,Param3,Param4,Param5,Param6,Param7,Param8,Param9,Param10,SourceType,high,highhigh,low,lowlow,Param11,Param12,Param13,Param14,Param15,Param16,Param17,Param18, Param19) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'

            params = []
            for index in range(len(pointList)):
                onePoint = pointList[index]
                if (onePoint[5] == 'R' or onePoint[5]== "0"):
                    onePoint[5] = '0'
                else:
                    onePoint[5] = '1'
                for i in range(len(strArrsystem)):
                    if (onePoint[22] == strArrsystem[i]):
                        onePoint[22] = i + 1
                        break
                for j in range(len(strArrdevice)):
                    if (onePoint[23] == strArrdevice[j]):
                        onePoint[23] = j + 1
                        break
                for k in range(len(strArrtype)):
                    if (onePoint[24] == strArrtype[k]):
                        onePoint[24] = k + 1
                        break
                if onePoint[16] == '':
                    onePoint[16] = -9999.0

                try:
                    strChDescription = onePoint[3].encode('gbk')
                except Exception as descErr:
                    strChDescription = ""

                strUnit = ""
                try:
                    strUnit = onePoint[4].encode("gbk")
                except:
                    try:
                        strUnit = onePoint[4].encode("utf8")
                    except:
                        pass

                strDecimal = "2"
                if len(onePoint) >= 26:
                    strDecimal = onePoint[25]

                params.append((
                    int(onePoint[0]), onePoint[1], '', '', '', '', '0', strUnit, strChDescription, '',
                    int(onePoint[5]), 0, '', '12', onePoint[6], onePoint[7], onePoint[8],
                    onePoint[9], onePoint[10], onePoint[11], onePoint[12], onePoint[13], onePoint[14], onePoint[15],
                    onePoint[2], onePoint[16], onePoint[17], onePoint[18],
                    onePoint[19], onePoint[20], '', '', '', onePoint[21], onePoint[22], onePoint[23], onePoint[24], strDecimal))

            cur.executemany(insertSQL, tuple(params))
            con.commit()
            bSuccess = True
            return dict(msg="", success=True)

        except Exception as err:
            return dict(msg="替换点表失败:{err}".format(err=err.__str__()), success=False)
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()



    def getPointInfoFromS3db(self, pointList, sourceType=None):
        cur = None
        con = None
        result = {}
        record = [0]
        try:

            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            if pointList is None or not len(pointList):
                if sourceType and isinstance(sourceType, str):
                    sql = 'select name, ch_description, SourceType, Param1,high,highhigh,low,lowlow,Param2,Param3,Param4,Param5,Param6, unit, R_W, Param7, Param8, Param9, Param10, Param11, Param15, Param16, Param17, Param18, id from list_point where SourceType = "%s"' % (
                    sourceType)
                else:
                    sql = 'select name, ch_description, SourceType, Param1,high,highhigh,low,lowlow,Param2,Param3,Param4,Param5,Param6, unit, R_W, Param7, Param8, Param9, Param10, Param11, Param15, Param16, Param17, Param18, id from list_point'
            else:
                if sourceType and isinstance(sourceType, str):
                    sql = 'select name, ch_description, SourceType, Param1,high,highhigh,low,lowlow,Param2,Param3,Param4,Param5,Param6, unit, R_W, Param7, Param8, Param9, Param10, Param11, Param15, Param16, Param17, Param18, id from list_point where SourceType = "%s" and name in ("' % (sourceType)
                else:
                    sql = 'select name, ch_description, SourceType, Param1,high,highhigh,low,lowlow,Param2,Param3,Param4,Param5,Param6, unit, R_W, Param7, Param8, Param9, Param10, Param11, Param15, Param16, Param17, Param18, id from list_point where name in ("'
                nIndex = 0
                for pt in pointList:
                    sql += pt
                    sql += '"'
                    if nIndex < len(pointList) - 1:
                        sql += ',"'
                    else:
                        sql += ')'
                    nIndex += 1

            sql += " order by id"
            cur.execute(sql)
            data = cur.fetchall()

            for item in data:
                try:
                    it4 = item[4]
                    it5 = item[5]
                    it6 = item[6]
                    it7 = item[7]
                    param2 = item[8]
                    param3 = item[9]
                    param4 = item[10]
                    param5 = item[11]
                    param6 = item[12]
                    unit = item[13]
                    RW = item[14]
                    param7 = item[15]
                    param8 = item[16]
                    param9 = item[17]
                    param10 = item[18]
                    storecycle = item[19]
                    customName = item[20]
                    strSystem = item[21]
                    strDevice = item[22]
                    strType = item[23]
                    nId = item[24]

                    if isinstance(item[4], bytes):
                        it4 = item[4].decode('gbk')

                    if isinstance(item[5], bytes):
                        it5 = item[5].decode('gbk')

                    if isinstance(item[6], bytes):
                        it6 = item[6].decode('gbk')

                    if isinstance(item[7], bytes):
                        it7 = item[7].decode('gbk')

                    if isinstance(item[8], bytes):
                        param2 = item[8].decode('gbk')

                    if isinstance(item[9], bytes):
                        try:
                            param3 = item[9].decode('gbk')
                        except:
                            param3 = item[9].decode("utf8")

                    if isinstance(item[10], bytes):
                        param4 = item[10].decode('gbk')

                    if isinstance(item[11], bytes):
                        param5 = item[11].decode('gbk')

                    if isinstance(item[12], bytes):
                        param6 = item[12].decode('gbk')

                    if isinstance(item[13], bytes):
                        unit = ""
                        nCheck = check_bytes_encoding(item[13])
                        if nCheck == 0:
                            try:
                                unit = item[13].decode("utf8")
                            except:
                                pass

                        elif nCheck == 1:
                            try:
                                unit = item[13].decode('gbk')
                            except:
                                pass
                        else:
                            try:
                                unit = item[13].decode('gbk')
                            except:
                                pass

                    if isinstance(item[14], bytes):
                        RW = item[14].decode('gbk')

                    if isinstance(item[15], bytes):
                        param7 = item[15].decode('gbk')

                    if isinstance(item[16], bytes):
                        param8 = item[16].decode('gbk')

                    if isinstance(item[17], bytes):
                        param9 = item[17].decode('gbk')

                    if isinstance(item[18], bytes):
                        param10 = item[18].decode('gbk')

                    if isinstance(item[19], bytes):
                        storecycle = item[19].decode('gbk')

                    if isinstance(item[20], bytes):
                        customName = item[20].decode('gbk')

                    if isinstance(item[21], bytes):
                        strSystem = item[21].decode('gbk')

                    if isinstance(item[22], bytes):
                        strDevice = item[22].decode('gbk')

                    if isinstance(item[23], bytes):
                        strType = item[23].decode('gbk')

                    pointInfo = dict()
                    if isinstance(it5, float) or isinstance(it5, int):
                        pointInfo.update({
                            "hight": it5
                        })

                    if isinstance(it6, float) or isinstance(it6, int):
                        pointInfo.update({
                            "low": it6
                        })

                    strDescription = ''
                    try:
                        strDescription = item[1].decode('gbk')
                    except:
                        pass

                    dOutput = {
                        'name': item[0].decode('gbk'),
                        'description': strDescription,
                        'sourceType': item[2].decode('gbk'),
                        'addr': item[3].decode('gbk'),
                        'high': it4,
                        'highhigh': it5,
                        'low': it6,
                        'lowlow': it7,
                        'param2': param2,
                        'param3': param3,
                        'param4': param4,
                        'param5': param5,
                        'param6': param6,
                        "unit": unit,
                        "RW": RW,
                        "param7": param7,
                        "param8": param8,
                        "param9": param9,
                        "param10": param10,
                        "storecycle": storecycle,
                        "customName": customName,
                        "system": strSystem,
                        "device": strDevice,
                        "type": strType,
                        "id": nId
                    }

                    if pointInfo:
                        dOutput.update({"pointInfo": pointInfo})

                    result[item[0].decode('gbk')] = dOutput

                except:
                    continue
        except Exception as err:
            logging.error("ERROR in BEOPSqliteAccess::getPointInfoFromS3db:%s" % err.__str__())
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return result
    '''
    获取点名清单
    pointList给None表示获取全部
    '''

    def getPointInfoFromS3db_WithRedis(self, pointList, sourceType=None):
        result = {}
        try:
            allPointInfo = RedisManager.get_4db_points_info()

            if pointList:
                for k,v in allPointInfo.items():

                    if sourceType is not None:
                        if v.get('sourceType','')!=sourceType:
                            continue

                    if k in pointList:
                        result[k] = v
            else:
                result = allPointInfo

        except Exception as err:
            print(str(err))

        if not result:
            return self.getPointInfoFromS3db(pointList)

        return result

    def findPointListByKeyList_With_Redis(self, strKeyword, nSearchArea):
        strKeywordList = []

        if isinstance(strKeyword, list):
            strKeywordList = strKeyword
        else:
            try:
                strKeywordList = [str(strKeyword)]
            except:
                pass
            if strKeyword is None:
                strKeywordList = ['']
            elif isinstance(strKeyword, str):
                strKeywordList = [strKeyword]

        rvRedis = RedisManager.get_4db_points_info()

        if rvRedis is None:
            return self.findPointListByKeyList(strKeyword)

        result = {}
        for k,v in rvRedis.items():
            strName = k
            strNameLower = strName.lower()
            strDescription =  v.get('description')
            strDescriptionLower = strDescription.lower()
            strSourceType =  v.get('sourceType')
            strSourceTypeLower = strSourceType.lower()
            strAddr =  v.get('addr')
            strAddrLower = strAddr.lower()

            if not len(strKeywordList):
                result[k] = v
            else:
                if nSearchArea == 0:  # 只在点名内搜索
                    if len(strKeywordList) > 1:  # 关键词数量大于1时
                        bCount = False
                        if is_int_digit(strKeywordList[-1]):  # 若最后一个字符为数字则以数字结尾的正则匹配
                            pattern = r"^[a-zA-Z0-9_]*" + "[a-zA-Z0-9_]*".join([item.lower() for item in strKeywordList]) + "$"
                            if re.match(pattern, k.lower()):
                                bCount = True
                        else:
                            # pattern = r"[a-zA-Z0-9_]*" + "[a-zA-Z0-9_]*".join([item.lower() for item in strKeywordList])
                            bAllFound = True  # 当所有关键词都能在点名中查询到时（无论关键词顺序）则认为该点名能匹配到
                            for strkeyword in strKeywordList:
                                if k.lower().find(strkeyword.lower()) == -1:
                                    bAllFound = False
                                    break
                            bCount = bAllFound

                        if bCount:
                            result[k] = v

                    else:
                        bSearchedInPointName = True
                        for keyitem in strKeywordList:
                            strKeywordLowcase = keyitem.lower()
                            if strNameLower.find(strKeywordLowcase) < 0:
                                bSearchedInPointName = False
                                break

                        if bSearchedInPointName:
                            result[k] = v

                elif nSearchArea == 1:   # 全部字段搜索
                    bSearchedInPointName = True
                    for keyitem in strKeywordList:
                        strKeywordLowcase = keyitem.lower()
                        if strNameLower.find(strKeywordLowcase) < 0:
                            bSearchedInPointName = False
                            break

                    bSearchedInDescription = True
                    for keyitem in strKeywordList:
                        if strDescription.find(keyitem) < 0:
                            bSearchedInDescription = False
                            break

                    bSearchedInSourceType = True
                    for keyitem in strKeywordList:
                        if strSourceType.find(keyitem) < 0:
                            bSearchedInSourceType = False
                            break

                    bSearchedInAddr = True
                    for keyitem in strKeywordList:
                        if strAddr.find(keyitem) < 0:
                            bSearchedInAddr = False
                            break

                    if bSearchedInPointName or bSearchedInSourceType or bSearchedInAddr or bSearchedInDescription:
                        result[k] = v

        return result

    def findPointListByKeyList(self, strKeyword):

        cur = None
        con = None
        result = {}
        record = [0]
        strKeywordList = []

        if isinstance(strKeyword, list):
            strKeywordList = strKeyword
        else:
            try:
                strKeywordList = [str(strKeyword)]
            except:
                pass
            if strKeyword is None:
                strKeywordList = ['']
            elif isinstance(strKeyword, str):
                strKeywordList = [strKeyword]

        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return None
            # con = self.connect_readonly(dbfileDec)


            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            sql = 'select name, ch_description, SourceType, Param1,high,highhigh,low,lowlow,id from list_point '

            cur.execute(sql)
            data = cur.fetchall()

            for item in data:
                try:
                    strName = item[0].decode('gbk')
                except:
                    continue
                strNameLower = strName.lower()
                strDescription = ''
                if item[1]:
                    try:
                        strDescription = item[1].decode('gbk') if isinstance(item[1], bytes) else ''
                    except:
                        strDescription = ''
                strDescriptionLower = strDescription.lower()
                strSourceType = ''
                if item[2]:
                    try:
                        strSourceType = item[2].decode('gbk') if isinstance(item[2], bytes) else ''
                    except:
                        strSourceType = ''
                strSourceTypeLower = strSourceType.lower()
                strAddr = ''
                if item[3]:
                    try:
                        strAddr = item[3].decode('gbk') if isinstance(item[3], bytes) else ''
                    except:
                        strAddr = ''
                strAddrLower = strAddr.lower()

                try:
                    valueHigh  = item[4].decode('gbk') if isinstance(item[4], bytes) else item[4]
                except:
                    valueHigh = ''

                try:
                    valueHighHigh  = item[5].decode('gbk') if isinstance(item[5], bytes) else item[5]
                except:
                    valueHighHigh = ''

                try:
                    valueLow  = item[6].decode('gbk') if isinstance(item[6], bytes) else item[6]
                except:
                    valueLow = ''

                try:
                    valueLowLow  = item[7].decode('gbk') if isinstance(item[7], bytes) else item[7]
                except:
                    valueLowLow = ''

                if not len(strKeywordList):
                    result[strName] = {
                        'description': strDescription,
                        'sourceType': strSourceType,
                        'addr': strAddr,
                        'high': valueHigh,
                        'highhigh': valueHighHigh,
                        'low': valueLow,
                        'lowlow': valueLowLow
                    }
                else:
                    #search in pointname:
                    bSearchedInPointName = True
                    for keyitem in strKeywordList:
                        strKeywordLowcase = keyitem.lower()
                        if strNameLower.find(strKeywordLowcase) < 0:
                            bSearchedInPointName = False
                            break

                    bSearchedInDescription = True
                    for keyitem in strKeywordList:
                        if strDescription.find(keyitem) < 0:
                            bSearchedInDescription = False
                            break

                    bSearchedInSourceType = True
                    for keyitem in strKeywordList:
                        if strSourceType.find(keyitem) < 0:
                            bSearchedInSourceType = False
                            break

                    bSearchedInAddr = True
                    for keyitem in strKeywordList:
                        if strAddr.find(keyitem) < 0:
                            bSearchedInAddr = False
                            break

                    if bSearchedInPointName or bSearchedInSourceType or bSearchedInAddr or bSearchedInDescription:
                        result[strName] = {
                            'description': strDescription,
                            'sourceType': strSourceType,
                            'addr': strAddr,
                            'high': valueHigh,
                            'highhigh': valueHighHigh,
                            'low': valueLow,
                            'lowlow': valueLowLow
                        }
        except Exception as err:
            print('ERROR in findPointListByKeyList: ' + str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return result

    def getDBFileWholePath(self):
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return None
            return dbfile
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)
            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return None
            return dbfileDec

    def getPointMapsFromS3db_With_Redis(self, s3dbname):
        allPoints = {}
        try:
            rvRedis = RedisManager.get_4db_points_info()
            for k,v in rvRedis.items():
                allPoints[k] = v.get("description", "")
            return allPoints
        except:
            return allPoints


    def getPointMapsFromS3db(self, s3dbname):
        if s3dbname is None:
            return None

        con = None
        cu = None
        try:
            # print('getPointListFromS3db')
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return None
            # con = self.connect_readonly(dbfileDec)


            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('4DB_DIR_CLOUD'), app.config.get('4DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            cu.execute('select name, ch_description from list_point')
            data = cu.fetchall()
            allPoints = {}
            for x in data:
                allPoints[x[0].decode('gbk')] = x[1].decode('gbk')
            return allPoints
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()

    def prepareResouceImageSpecial(self, nImageId):
        s3dbFileNameDec = app.config.get("USE_4DB_NAME")

        if os.path.exists(s3dbFileNameDec):
            statinfo = os.stat(s3dbFileNameDec)
            imageDir = path.join('siteinterface/static/images/plant/project')

            tempPath = path.join('siteinterface')
            if not os.path.exists(tempPath):
                os.mkdir(tempPath)
                logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

            tempPath = path.join('siteinterface/static')
            if not os.path.exists(tempPath):
                os.mkdir(tempPath)
                logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

            tempPath = path.join('siteinterface/static/images')
            if not os.path.exists(tempPath):
                os.mkdir(tempPath)
                logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

            tempPath = path.join('siteinterface/static/images/plant')
            if not os.path.exists(tempPath):
                os.mkdir(tempPath)
                logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

            if not os.path.exists(imageDir):
                os.mkdir(imageDir)
                logging.error('Check find dir not exist, created: %s' % (imageDir.__str__()))


            con = self.connect_readonly(s3dbFileNameDec)
            cur = con.cursor()
            try:
                cur.execute('select id, imagebinary from lib_image where id = %d' % (int(nImageId)))
                for id, img in cur.fetchall():
                    if img:
                        # print('{0}/{1}.png'.format(imageDir,id),'wb')
                        imageFile = open('{0}/{1}.png'.format(imageDir, id), 'wb')
                        imageFile.write(img)
                        imageFile.close()
                bFinished = True
                RedisManager.append_image_id_list_project(id)
            except Exception as e:
                strError = 'ERROR in prepareResouceFromS3db 2#:%s' % (e.__str__())
                print(strError)
                logging.error(strError)

            finally:
                if con is not None:
                    cur.close()
                    con.close()
            return bFinished
        else:
            print("%s is not exist!" % (s3dbFileNameDec))
            return False

        return bFinished

    def prepareResouceFromS3db(self, s3dbFileNameDec, updatetime, clean):
        print('prepareResouceFromS3db: ' + s3dbFileNameDec)
        bFinished = False
        if os.path.exists(s3dbFileNameDec):
            statinfo = os.stat(s3dbFileNameDec)
            imageDir = path.join('siteinterface/static/images/plant/project')
            if (updatetime == None) or (statinfo.st_mtime > updatetime) or (not os.path.exists(imageDir)):
                tempPath = path.join('siteinterface')
                if not os.path.exists(tempPath):
                    os.mkdir(tempPath)
                    logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

                tempPath = path.join('siteinterface/static')
                if not os.path.exists(tempPath):
                    os.mkdir(tempPath)
                    logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

                tempPath = path.join('siteinterface/static/images')
                if not os.path.exists(tempPath):
                    os.mkdir(tempPath)
                    logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

                tempPath = path.join('siteinterface/static/images/plant')
                if not os.path.exists(tempPath):
                    os.mkdir(tempPath)
                    logging.error('Check find dir not exist, created: %s' % (tempPath.__str__()))

                if not os.path.exists(imageDir):
                    os.mkdir(imageDir)
                    logging.error('Check find dir not exist, created: %s' % (imageDir.__str__()))

                if clean:
                    print('remove existing image')
                    for f in listdir(imageDir):
                        f_path = path.join(imageDir, f)
                        try:
                            if path.isfile(f_path):
                                unlink(f_path)
                        except Exception as e:
                            strError = 'ERROR in prepareResouceFromS3db:%s' % (e.__str__())
                            print(strError)
                            logging.error(strError)

                if not os.path.exists(s3dbFileNameDec):
                    print(s3dbFileNameDec + ' file not existing!')
                    return False
                else:
                    print(s3dbFileNameDec + ' file read successfully!')
                con = self.connect_readonly(s3dbFileNameDec )
                cur = con.cursor()
                cur.execute('select id, imagebinary from lib_image')
                try:
                    nIDList = []
                    for id, img in cur.fetchall():
                        if img:
                            # print('{0}/{1}.png'.format(imageDir,id),'wb')
                            imageFile = open('{0}/{1}.png'.format(imageDir, id), 'wb')
                            imageFile.write(img)
                            imageFile.close()
                            nIDList.append(id)
                    bFinished = True
                    RedisManager.set_image_id_list_project(nIDList)
                except Exception as e:
                    strError = 'ERROR in prepareResouceFromS3db 2#:%s' % (e.__str__())
                    print(strError)
                    logging.error(strError)
                cur.execute('select id, imagebinary from lib_image_animation')
                try:
                    for id, img in cur.fetchall():
                        if img:
                            imageFile = open('{0}/animation_{1}.png'.format(imageDir, id), 'wb')
                            imageFile.write(img)
                            imageFile.close()
                except Exception as e:
                    strError = 'ERROR in prepareResouceFromS3db 3#:%s' % (e.__str__())
                    print(strError)
                    logging.error(strError)

                finally:
                    if con is not None:
                        cur.close()
                        con.close()
                return bFinished
        else:
            print("%s is not exist!" % (s3dbFileNameDec))
            return False
        return bFinished

    def connect_readonly(self, strFilePath):
        con =  sqlite3.connect('file:///'+ strFilePath +'?mode=ro', uri=True)
        return con

    def getPlantPageDetails(self, s3dbname, pageGroupId=None, nUserRight=99):
        cu = None
        con = None
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return []
            # con = self.connect_readonly(dbfileDec)
            dbfile = ''

            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), s3dbname)
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cu = con.cursor()
            if pageGroupId is None:
                cu.execute(
                    "SELECT id, name, pagetype, width, hight, unitproperty02, unitproperty03 FROM list_page WHERE unitproperty01 = '1' ORDER BY showOrder")
            else:
                cu.execute(
                    "SELECT id, name, pagetype, width, hight, unitproperty02, unitproperty03 FROM list_page WHERE unitproperty01 = '1' and groupid = %s ORDER BY showOrder" % (
                    str(pageGroupId)))

            data = []
            for x in cu.fetchall():
                url = ''
                if x[5] is not None:
                    url = x[5].decode('gbk')

                try:
                    strMinRight = x[6].decode('gbk')
                    nMinRight = int(strMinRight)
                except Exception as e:
                    nMinRight = 0

                if nUserRight > nMinRight:
                    data.append({'id': x[0], 'name': x[1].decode('gbk'), 'type': x[2].decode('gbk'), 'width': x[3],
                                 'height': x[4], 'url': url})
            return data

        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()

    def getPlantPageGroups(self, s3dbname):
        con = None
        cu = None

        dbfile = ''
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)

        # con = self.connect_readonly(dbfileDec)
        con.text_factory = bytes
        cu = con.cursor()

        groupList = []

        if con != None and cu != None:
            try:
                cu.execute("SELECT id, name, unitproperty01 FROM list_pagegroup")

                items = cu.fetchall()
                for item in items:
                    groupList.append(dict(id=item[0], name=item[1].decode('gbk'), seq=int(item[2].decode("gbk"))))
                groupList.sort(key=lambda x: x["seq"])
            except:
                pass
            finally:
                if cu is not None:
                    cu.close()
                if con is not None:
                    con.close()

        return groupList

    def initTemplate4dbFile(self):
        template_4db = app.config.get("TEMPLATE_DB_FILE_NAME")
        template_4db_dir = os.path.join(os.getcwd(), "siteinterface", "static", "template", template_4db)
        app.config["TEMPLATE_DB_FILE_DIR"] = template_4db_dir

    def create404ImageFileIfNotExist(self):
        strSourceDir = os.path.join(app.static_folder, "images")
        strDestDir = os.path.join(strSourceDir, "plant")
        strDestDir = os.path.join(strDestDir, "project")
        strSourceFilePath = os.path.join(strSourceDir, '404.png')
        strDestFilePath = os.path.join(strDestDir, '-404404404.png')
        if os.path.exists(strDestFilePath):
            return True

        if not os.path.exists(strSourceFilePath):
            return False

        try:
            shutil.copyfile(strSourceFilePath, strDestFilePath)
        except:
            return False

    # strTemplateName: template  best
    def create404ImageFileForTemplateIfNotExist(self, strTemplateName):
        strSourceDir = os.path.join(app.static_folder, "images")
        if strTemplateName == "template":
            strDestDir = os.path.join(strSourceDir, "template")
        else:
            strDestDir = os.path.join(strSourceDir, "template", strTemplateName)

        strSourceFilePath = os.path.join(strSourceDir, '404.png')
        strDestFilePath = os.path.join(strDestDir, '-404404404.png')
        if os.path.exists(strDestFilePath):
            return True

        if not os.path.exists(strSourceFilePath):
            return False

        try:
            shutil.copyfile(strSourceFilePath, strDestFilePath)
        except:
            return False

    def getPlantPageContent_With_Redis(self, pageid):
        pageContent = RedisManager.get_4db_page_content(pageid)

        if isinstance(pageContent, dict):
            fixList = BEOPDataAccess.getInstance().getAllFixPosInfo(pageid)

            dataFix = []
            colorDict = {
                0: "green",
                1: "yellow",
                2: "red"
            }

            if isinstance(fixList, list):
                if len(fixList):
                    for fix in fixList:
                        dataFix.append({
                            "fixId": fix.get("fixId"),
                            "x": fix.get("posX"),
                            "y": fix.get("posY"),
                            "width": 32,
                            "height": 32,
                            "visible": fix.get("visible"),
                            "idPicture": "fix/{0}".format(colorDict.get(fix.get("urgent"), "green")),
                            "layer": 9
                        })

            pageContent.update(dict(fix=dataFix))

        if pageContent is None:
            bufferData = self.getPlant('', pageid)
            RedisManager.set_4db_page_content(pageid, bufferData)
            return bufferData

        return pageContent

    def getPlantPageContentDebugTool_With_Redis(self, pageid):
        # 2023-07-07 debugtool编辑页面后暂时不存入debugtool专用缓存，所以页面内容直接从domdb.4db获取

        # pageContent = RedisManager.get_4db_page_content_DebugTool(pageid)
        #
        # if isinstance(pageContent, dict):
        #     fixList = BEOPDataAccess.getInstance().getAllFixPosInfo(pageid)
        #
        #     dataFix = []
        #     colorDict = {
        #         0: "green",
        #         1: "yellow",
        #         2: "red"
        #     }
        #
        #     if isinstance(fixList, list):
        #         if len(fixList):
        #             for fix in fixList:
        #                 dataFix.append({
        #                     "fixId": fix.get("fixId"),
        #                     "x": fix.get("posX"),
        #                     "y": fix.get("posY"),
        #                     "width": 32,
        #                     "height": 32,
        #                     "visible": fix.get("visible"),
        #                     "idPicture": "fix/{0}".format(colorDict.get(fix.get("urgent"), "green")),
        #                     "layer": 9
        #                 })
        #
        #     pageContent.update(dict(fix=dataFix))
        #
        # if pageContent is None:
        #     bufferData = self.getPlantDebugTool(pageid)
        #     RedisManager.set_4db_page_content_DebugTool(pageid, bufferData)
        #     return bufferData

        dPageContent = self.getPlantDebugTool(pageid)
        fixList = BEOPDataAccess.getInstance().getAllFixPosInfo(pageid)
        dataFix = []
        colorDict = {
            0: "green",
            1: "yellow",
            2: "red"
        }

        if isinstance(fixList, list):
            if len(fixList):
                for fix in fixList:
                    dataFix.append({
                        "fixId": fix.get("fixId"),
                        "x": fix.get("posX"),
                        "y": fix.get("posY"),
                        "width": 32,
                        "height": 32,
                        "visible": fix.get("visible"),
                        "idPicture": "fix/{0}".format(colorDict.get(fix.get("urgent"), "green")),
                        "layer": 9
                    })

        dPageContent.update(dict(fix=dataFix))

        return dPageContent


    def getPlant(self, s3dbname, pageid):
        con = None
        cu = None
        pageId = pageid
        strPrefixFix = "fix/"

        # 所有点信息字典
        allPointInfo = None

        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        dataPage = {}
        dataImages = []
        dataAnimationImages = []
        dataAnimationList = {}
        dataPipeLines = []
        dataEquipments = []
        dataCharts = []
        dataGages = []
        dataButtons = []
        dataRulers = []
        dataCheckboxs = []
        dataTexts = []
        dataRects = []
        dataCustom = []
        dataTimePicker = []
        dataTempDistributions = {}
        dataSystemEquipments = []
        dataTemplateImages = []
        dataLequidLevels = []
        dataFix = []
        dataRectangles = []
        dataStraightLine = []
        dataPolygon = []

        #image_id
        image_id_list_project = RedisManager.get_image_id_list_project()
        image_id_list_template = {}

        con.text_factory = bytes
        cu = con.cursor()

        if con != None and cu != None:
            try:

                # 获取模板设备名列表
                templateEquipNameList = []
                cu.execute("select unitproperty07 as templateFileName from list_unit13 where pageid = %s" % pageId)
                objectList = cu.fetchall()
                for object in objectList:
                    fileName = "template.4db"
                    if object[0] != None:
                        fileName = object[0].decode("gbk")
                    templateEquipName = path.splitext(fileName)[0]
                    if templateEquipName not in templateEquipNameList:
                        templateEquipNameList.append(templateEquipName)
                tFrom = datetime.now()
                # Page
                cu.execute(
                    "SELECT width, hight, pagetype,bgcolor1, bgcolor2, bgimg, name, unitproperty04  FROM list_page WHERE id = %s" % (
                    pageId))

                item = cu.fetchall()

                if len(item) > 0:
                    dataPage = {'id': pageId, 'width': item[0][0], 'height': item[0][1],
                                'type': item[0][2].decode('gbk'),
                                'bgColor1': item[0][3], 'bgColor2': item[0][4], 'bgImgId': item[0][5],
                                'name': item[0][6].decode('gbk'),
                                'navJsonConfig': item[0][7].decode('gbk') if item[0][7] else ""}


                tFrom = datetime.now()
                # Pipeline
                cu.execute(
                    "SELECT id, PointList, pipeWidth, style, idlist, layer,  unitproperty01, innerColor, unitproperty03, unitproperty04, logic, unitproperty05 FROM list_line WHERE pageid = %s" % (
                    pageId))
                for item in cu.fetchall():
                    strs = item[1].decode('gbk').replace('(', '').replace(')', '').replace(',', ';').split(';') if item[
                                                                                                                       1] != None else [
                        '0', '0', '0', '0']
                    color = int(item[7]) if item[7] != None else 0
                    # waterShape: 0-矩形；1-圆形
                    try:
                        waterShape = int(item[11].decode("gbk")) if item[11] != None else 0
                    except:
                        waterShape = 0
                    dataPipeLines.append({'id': item[0] if item[0] != None else 0,
                                          'width': item[2] if item[2] != None else 0,
                                          'direction': item[3] if item[3] != None else 0,
                                          'idCom': item[4].decode('gbk') if item[4] != None else '',
                                          'startX': strs[0], 'startY': strs[1], 'endX': strs[2], 'endY': strs[3],
                                          'layer': item[5] if item[5] != None else 0,
                                          'waterType': item[6].decode('gbk') if item[6] != None else '',
                                          'color': {'r': get_r_from_int(color), "g": get_g_from_int(color),
                                                    'b': get_b_from_int(color)},
                                          'denSity': item[8].decode('gbk') if item[8] != None else '',
                                          'speed': item[9].decode('gbk') if item[9] != None else '',
                                          'logic': item[10] if item[10] != None else 0,
                                          'waterShape': waterShape
                                          })

                # line
                strQuery = "SELECT x, y, width, height, layer, id, pageid, unitproperty02, unitproperty03, " \
                           "unitproperty04, unitproperty06, unitproperty07, unitproperty08, unitproperty09 FROM " \
                           "list_unit19 WHERE pageid = %s and unitproperty01='straightLine'" % pageId
                cu.execute(strQuery)
                for item in cu.fetchall():
                    colorBytes = item[7] if item[7] != None else 0
                    dataStraightLine.append({
                        "x0": item[0] if item[0] != None else 0,
                        "y0": item[1] if item[1] != None else 0,
                        "x1": item[2] if item[2] != None else 0,
                        "y1": item[3] if item[3] != None else 0,
                        "layer": item[4] if item[4] != None else 0,
                        "id": item[5] if item[5] != None else 0,
                        "pageid": item[6] if item[6] != None else 0,
                        "color": colorHexToRgb(colorBytes),
                        "lineWidth": int(float(item[8].decode("gbk"))) if item[8] != None else 0,
                        "lineType": int(float(item[9].decode("gbk"))) if item[9] != None else 0,
                        "startType": int(float(item[10].decode("gbk"))) if item[10] != None else 0,
                        "startSize": int(float(item[11].decode("gbk"))) if item[11] != None else 0,
                        "endType": int(float(item[12].decode("gbk"))) if item[12] != None else 0,
                        "endSize": int(float(item[13].decode("gbk"))) if item[13] != None else 0
                    })

                # 多边形
                cu.execute("SELECT x as coord, width as templatePelId, height as name, layer, id, unitproperty02 as placeHolder, unitproperty03 as templateName, unitproperty06 FROM list_unit19 WHERE pageid = %s and unitproperty01='polygon'" % pageid)
                polys = cu.fetchall()

                # 以模板文件名为键制作模板图元ID字典
                templatePelIdDict = {}
                for object in polys:
                    templateFileName = object[6].decode("gbk") if object[0] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    templatePelId = object[1]
                    if templateFileNameWithoutExt in templatePelIdDict.keys():
                        if templatePelId in templatePelIdDict[templateFileNameWithoutExt]:
                            continue
                        templatePelIdDict[templateFileNameWithoutExt].append(templatePelId)
                    else:
                        templatePelIdDict[templateFileNameWithoutExt] = [templatePelId]

                    image_id_list_template[templateFileName] = RedisManager.get_image_id_list_template(templateFileName)

                # 以模板文件名为键创建模板信息查询字典和text字典
                queryDict = {}
                textQueryDict = {}
                for templateFileNameWithoutExt in templatePelIdDict.keys():
                    templatePelIdList = templatePelIdDict[templateFileNameWithoutExt]

                    clauseTemplatePelIdList = ["page_contain_elements.pageid = {0}".format(pelId) for pelId in
                                               templatePelIdList]
                    clauseAllTextsList = ["pageid = {0}".format(pelId) for pelId in templatePelIdList]

                    strClauseTemplatePelId = " or ".join(clauseTemplatePelIdList)
                    strClauseAllTexts = " or ".join(clauseAllTextsList)

                    strQueryAllNeedTemplate = "SELECT x, y, width, hight, DataComId, pictureid, rotateAngle, " \
                                              "event_content, layer, elementName, bind_content, " \
                                              "page_contain_elements.unitproperty03 AS prop03, page_contain_elements.unitproperty02 AS prop02, " \
                                              "page_contain_elements.pageid as templatePageId FROM " \
                                              "page_contain_elements LEFT JOIN event ON page_contain_elements.elementid = event.id WHERE " + strClauseTemplatePelId

                    strQueryAllTextsInTempalte = "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, " \
                                                 "t.initialValue, t.size, t.font, t.color, t.decimalplace, t.bindstring," \
                                                 " t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.pageid as templatePageId " \
                                                 "FROM list_text t left join list_point p on t.dataComId = p.name WHERE " + strClauseAllTexts

                    queryDict.update({templateFileNameWithoutExt: strQueryAllNeedTemplate})
                    textQueryDict.update({templateFileNameWithoutExt: strQueryAllTextsInTempalte})

                templateDict = {}
                templateTextsDict = {}
                templateDir = path.join(app.static_folder, "template")
                for templateFileNameWithoutExt in queryDict.keys():
                    templatePath = path.join(templateDir, "{0}.4db".format(templateFileNameWithoutExt))

                    if not path.exists(templatePath):
                        continue

                    # 读取模板文件中所有标准设备的信息
                    with SqliteManager(templatePath) as sdb:
                        templates = sdb.exec_query(queryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建模板信息字典
                    for template in templates:
                        templatePageId = template.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateDict.keys():
                            templateDict[key].append(template)
                        else:
                            templateDict[key] = [template]

                    # 读取模板文件中所有text的信息
                    with SqliteManager(templatePath) as sdb:
                        textTemplates = sdb.exec_query(textQueryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建text信息字典
                    for textTemplate in textTemplates:
                        templatePageId = textTemplate.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateTextsDict.keys():
                            templateTextsDict[key].append(textTemplate)
                        else:
                            templateTextsDict[key] = [textTemplate]

                # 开始遍历多边形
                for standEquipIdx, item in enumerate(polys):
                    strNavigation = item[7].decode("gbk") if item[7] else ""
                    templateFileName = item[6].decode("gbk") if item[6] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    template_pel_id = item[1]
                    templateFilePath = path.join(app.static_folder, "template", templateFileName)
                    polyId = item[4] if item[4] != None else 0

                    prefix = "{0}/".format(
                        templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(
                        templateFileNameWithoutExt)

                    if not path.exists(templateFilePath):
                        continue

                    # 以模板文件名+模板图元ID组成的键名
                    templateKey = "{0}_{1}".format(templateFileNameWithoutExt, template_pel_id)

                    placeHolderRaw = ""
                    try:
                        placeHolderRaw = item[5].decode("UTF8") if item[5] != None else ""
                    except Exception as e:
                        strLog = "多边形中占位符解码问题: %s" % e.__str__()
                        print(strLog)
                        logging.error(strLog)

                    # 工作空间中主设备的宽、高、坐标，工作空间：需要插入模板设备的界面
                    coord = item[0].decode("gbk").split(" ")
                    xList = []
                    yList = []
                    for perCoord in coord:
                        xList.append(float(perCoord.split(",")[0]))
                        yList.append(float(perCoord.split(",")[1]))
                    yMax = max(yList)
                    yMin = min(yList)
                    xMax = max(xList)
                    xMin = min(xList)

                    backgroundWidth = xMax - xMin
                    backgroundHeight = yMax - yMin
                    backgroundX = xMin
                    backgroundY = yMin

                    # 生成占位符
                    requestParam = dict()
                    try:
                        for obj in eval(placeHolderRaw):
                            requestParam.update(obj)
                    except Exception as e:
                        strLog = "多边形中占位符字典生成问题: %s" % e.__str__()
                        print(strLog)
                        logging.error(strLog)

                    res = templateDict.get(templateKey, [])
                    pels_width = list()
                    if len(res):
                        pels_width = [pel.get("width") for pel in res]
                    else:
                        strError = 'ERROR in read template id:%s' % (str(templateKey))
                        print(strError)
                        logging.error(strError)
                        continue

                    # 从属图标，如err, enabled, automode图标
                    belongings = list()
                    mainEquip = None
                    for pel in res:
                        if pel.get("width") >= max(pels_width, default=0):
                            mainEquip = pel
                        else:
                            belongings.append(pel)

                    # 主设备旋转角度
                    # rotateAngleMainEquip = int(item[8].decode("gbk")) if item[8] else 0

                    # 计算缩放比例 START 多边形
                    zoomX = 1
                    zoomY = 1
                    mainEquipX = 0
                    mainEquipY = 0
                    if mainEquip:
                        mainEquipX = mainEquip.get("x")
                        mainEquipY = mainEquip.get("y")
                        zoomX = backgroundWidth / mainEquip.get("width")
                        zoomY = backgroundHeight / mainEquip.get("hight")
                    # 计算缩放比例 END

                    # 标准设备的文本内容 START
                    textsList = []
                    textsListFetch = templateTextsDict.get(templateKey, [])
                    for dText in textsListFetch:
                        strPointName = dText.get("dataComId").decode("gbk") if dText.get("dataComId") is not None else ""
                        strTextContent = dText.get("initialvalue").decode("gbk") if dText.get("initialvalue") is not None else ""

                        # 替换点名里的占位符
                        if len(strPointName):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strPointName = strPointName.replace(placeHolder, requestParam.get(key))

                        # 替换文本内容里的占位符
                        if len(strTextContent):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strTextContent = strTextContent.replace(placeHolder, requestParam.get(key))

                        textColor = int(dText.get("color")) if dText.get("color") is not None else 0

                        # text坐标换算
                        textX = dText.get("xpos") if dText.get("xpos") is not None else 0
                        textY = dText.get("ypos") if dText.get("ypos") is not None else 0
                        offsetTextX = (textX - mainEquipX) * zoomX
                        offsetTextY = (textY - mainEquipY) * zoomY
                        xPos = backgroundX + offsetTextX
                        yPox = backgroundY + offsetTextY

                        textsList.append({'id': "{0}_{1}".format(dText.get("id"), standEquipIdx) if dText.get(
                            "id") is not None else 0,
                                          'x': xPos,
                                          'y': yPox,
                                          'width': dText.get("width") if dText.get("width") is not None else 0,
                                          'height': dText.get("height") if dText.get("height") is not None else 0,
                                          'idCom': strPointName,
                                          'text': strTextContent,
                                          'fontSize': dText.get("size") if dText.get("size") is not None else 0,
                                          'font': dText.get("font").decode("gbk") if dText.get(
                                              "font") is not None else "",
                                          'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                    'b': get_b_from_int(textColor)},
                                          'decimalplace': dText.get("decimalplace"),
                                          'bindString': dText.get("bindstring").decode("gbk") if dText.get(
                                              "bindstring") is not None else "",
                                          'showMode': dText.get("showMode") if dText.get(
                                              "showMode") is not None else 0,
                                          'rw': dText.get("R_W") if dText.get("R_W") is not None else 0,
                                          'layer': dText.get("layer") if dText.get("layer") is not None else 0,
                                          'align': dText.get("align") if dText.get("align") is not None else 0,
                                          'bindScript': dText.get("unitproperty05").decode("gbk") if dText.get(
                                              "unitproperty05") is not None else "",
                                          "backgroudFrameStyle": dText.get("unitproperty01").decode(
                                              "gbk") if dText.get("unitproperty01") is not None else 0})
                    # 标准设备的文本内容 END

                    # 处理随主设备一起的图标，如enabled, err, automode START
                    childrenList = []
                    belonging_id_preffix = 999999
                    for belongingIndex, belonging in enumerate(belongings):
                        belonging_id = int("{0}{1}".format(belonging_id_preffix - belongingIndex, polyId))
                        belongingX = belonging.get("x") if belonging.get("x") else 0
                        belongingY = belonging.get("y") if belonging.get("y") else 0

                        # 模板设备页面中，从属图标与主设备之间的坐标偏差 乘以 缩放比例
                        offsetX = (belongingX - mainEquipX) * zoomX
                        offsetY = (belongingY - mainEquipY) * zoomY

                        # 工作空间中从属图标的高宽考虑缩放比例
                        width = belonging.get("width") * zoomX if belonging.get("width") else 0
                        height = belonging.get("hight") * zoomY if belonging.get("hight") else 0

                        # 工作空间中从属图标的坐标等于主设备的坐标加坐标偏差
                        x = backgroundX + offsetX
                        y = backgroundY + offsetY

                        # 点名占位符处理
                        point = belonging.get("DataComId").decode("gbk") if belonging.get("DataComId") else ""
                        if len(point):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                point = point.replace(placeHolder, requestParam.get(key))

                        # 图片
                        pictureid = "{0}{1}".format(prefix, belonging.get("pictureid")) if belonging.get("pictureid", None) is not None else ""
                        if not pictureid in dataImages:
                            template_image_id_list = image_id_list_template.get(templateFileName)
                            try:
                                if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                    tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                    if is_int_digit(tmp):
                                        if int(tmp) not in template_image_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                            except Exception as ept:
                                logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                            dataImages.append(pictureid)

                        # 从属图标的旋转角度需要与主设备一致
                        # rotateAngle = rotateAngleMainEquip

                        # 图层
                        layer = belonging.get("layer") if belonging.get("layer") else 0

                        # title占位符修改
                        strTitle = belonging.get("elementName").decode("gbk") if belonging.get("elementName") else ""
                        elemName = ""
                        if len(strTitle):
                            elemName = replace_place_holder(strTitle, requestParam)

                        strItem11 = belonging.get("prop02").decode("gbk") if belonging.get("prop02") else ""

                        animationStatus = {}
                        str_item = belonging.get("bind_content").decode('gbk') if belonging.get(
                            "bind_content") != None else ''
                        if str_item != "":
                            temp = str_item.split('|')
                            for strStatus in temp:
                                tempStatus = strStatus.split(',')
                                if len(tempStatus) == 4:
                                    animationStatus.update(
                                        {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                         'frameCount': tempStatus[2],
                                                         'interval': tempStatus[3]}})

                                    imgId = "{0}{1}".format(prefix, tempStatus[1])
                                    if imgId not in dataImages:
                                        template_image_id_list = image_id_list_template.get(templateFileName)
                                        try:
                                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                                tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                                if int(tmp) not in template_image_id_list:
                                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                    imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                        except Exception as ept:
                                            logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                                        dataImages.append(imgId)

                        strItem13 = belonging.get("prop03").decode("gbk") if belonging.get("prop03") != None else 0

                        # 获取子设备linkInfo
                        try:
                            ChildrenLinkInfoList = belonging.get("event_content").decode("gbk").split(",")
                            if ChildrenLinkInfoList and isinstance(ChildrenLinkInfoList, list):
                                ChildrenLinkInfoList.append('template')  # 区分常规弹窗
                        except:
                            ChildrenLinkInfoList = []

                        childPlaceHolder = {}
                        if len(ChildrenLinkInfoList):
                            childPlaceHolder = requestParam

                        childrenList.append({
                            "id": belonging_id,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "idCom": point,
                            "idPicture": pictureid,
                            "layer": layer,
                            "name": elemName,
                            "isFromAnimation": strItem11 == "0",
                            "animation": animationStatus,
                            "bindType": int(float(strItem13)),
                            "link": ChildrenLinkInfoList[4],  # 子设备link
                            "linkinfo": ChildrenLinkInfoList,  # 子设备linkInfoList
                            "placeHolder": childPlaceHolder
                        })
                    # 处理随主设备一起的图标，如enabled, err, automode END

                    # 处理belongings的动画问题 START
                    for child in childrenList:
                        dictAnimation = child.get("animation")
                        for dictAnimationValue in dictAnimation.values():
                            if int(dictAnimationValue.get("frameCount")) > 1:
                                childAnimationId = dictAnimationValue.get("animationId").replace(prefix, "")
                                with SqliteManager(templateFilePath) as dbm:
                                    str_sql = '''SELECT * FROM lib_animation WHERE id = ?'''
                                    sql_res = dbm.exec_query(str_sql, (childAnimationId,))
                                animationListWithPrefix = ["{0}{1}".format(prefix, itm) for itm in sql_res[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update({dictAnimationValue.get("animationId"): animationListWithPrefix})
                    # 处理belongings的动画问题 END

                    # 处理主设备 START
                    pictureid = "{0}{1}".format(prefix, mainEquip.get("pictureid")) if mainEquip.get("pictureid", None) is not None else ""
                    if not pictureid in dataImages:
                        template_image_id_list = image_id_list_template.get(templateFileName)
                        try:
                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                if int(tmp) not in template_image_id_list:
                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                    pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                        except Exception as ept:
                            logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                        dataImages.append(pictureid)

                    try:
                        LinkInfoList = mainEquip.get("event_content").decode("gbk").split(",")
                        if LinkInfoList and isinstance(LinkInfoList, list):
                            LinkInfoList.append('template')  # 区分常规弹窗
                    except:
                        LinkInfoList = []

                    layer = item[3] if item[3] else 0

                    strItem11 = mainEquip.get("prop02").decode("gbk") if mainEquip.get("prop02") != None else ""

                    animationStatus = {}
                    str_item = mainEquip.get("bind_content").decode('gbk') if mainEquip.get(
                        "bind_content") != None else ''
                    if str_item != "":
                        temp = str_item.split('|')
                        for strStatus in temp:
                            tempStatus = strStatus.split(',')
                            if len(tempStatus) == 4:
                                animationStatus.update(
                                    {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                     'frameCount': tempStatus[2],
                                                     'interval': tempStatus[3]}})

                                imgId = "{0}{1}".format(prefix, tempStatus[1])
                                if imgId not in dataImages:
                                    template_image_id_list = image_id_list_template.get(templateFileName)
                                    try:
                                        if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                            tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                            if int(tmp) not in template_image_id_list:
                                                self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                    except Exception as ept:
                                        logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                                    dataImages.append(imgId)

                    # title占位符修改
                    strTitle = mainEquip.get("elementName").decode("gbk") if mainEquip.get("elementName") != None else ""

                    elemName = ""
                    if len(strTitle):
                        elemName = replace_place_holder(strTitle, requestParam)

                    # 点名占位符处理
                    point = mainEquip.get("DataComId").decode("gbk") if mainEquip.get("DataComId") != None else ""
                    if len(point):
                        for key in requestParam.keys():
                            placeHolder = "{%s}" % key
                            point = point.replace(placeHolder, requestParam.get(key))

                    strItem13 = mainEquip.get("prop03").decode("gbk") if mainEquip.get("prop03") != None else 0

                    # 处理主设备 END

                    dataPolygon.append({
                        "id": polyId,
                        "coord": item[0].decode("gbk") if item[0] != None else "",
                        "layer": item[3] if item[3] != None else 0,
                        "idCom": point,
                        "pageid": pageid,
                        "idPicture": pictureid,
                        "link": LinkInfoList[4],
                        "linkinfo": LinkInfoList,
                        "name": elemName,
                        'bindType': int(float(strItem13)),
                        "templatePelId": template_pel_id,
                        "children": childrenList,
                        "templateFileName": templateFileNameWithoutExt,
                        "placeHolder": requestParam,
                        "texts": textsList,
                        "navigation": strNavigation
                    })


                # Custom Image
                cu.execute("SELECT elementid, x, y, width, hight, DataComId, pictureid, rotateAngle, bind_content,"
                           "event_content, layer, page_contain_elements.unitproperty02, elementName, "
                           "page_contain_elements.unitproperty03, page_contain_elements.hideScript, page_contain_elements.unitproperty04 FROM page_contain_elements LEFT JOIN event "
                           "ON event.id = page_contain_elements.elementid WHERE page_contain_elements.pageid = %s AND event.pageid =%s" % (pageId, pageId))

                # distinct animation ids
                listAnimationIds = []
                listAnimationIds_prefix_removed = []
                templateEquipNameList.append("/")
                for item in cu.fetchall():
                    LinkInfoList = item[9].decode('gbk').split(',') if item[9] != None else []
                    strItem5 = "" if item[5] is None else item[5].decode("gbk")
                    strItem9 = LinkInfoList[4] if len(LinkInfoList) >= 5 else ""
                    strItem11 = "" if item[11] is None else item[11].decode("gbk")
                    strItem12 = "" if item[12] is None else item[12].decode("gbk")
                    strItem8 = "" if item[8] is None else item[8].decode("gbk")
                    nPictureId = 0 if item[6] is None else item[6]
                    hideScript = item[14].decode("gbk") if item[14] != None else None

                    strItem13 = 0
                    if item[13] == None:
                        strItem13 = 0
                    elif isinstance(item[13], bytes):
                        strItem13 = int(float(item[13].decode("gbk")))
                    elif isinstance(item[13], str):
                        strItem13 = int(float(item[13]))
                    if strItem13 not in [0, 1]:
                        strItem13 = 0

                    if isinstance(item[15], str):
                        customName = item[15]
                    elif isinstance(item[15], bytes):
                        customName = item[15].decode("gbk")
                    else:
                        customName = ""

                    try:
                        if isinstance(image_id_list_project, list) and len(image_id_list_project)>0:
                            if not (nPictureId in image_id_list_project):
                                self.create404ImageFileIfNotExist()
                                nPictureId = -404404404
                    except Exception as e:
                        logging.error('ERROR in get_plant:%s' %(e.__str__()))
                        nPictureId = -404404404

                    if str(nPictureId) not in dataImages:
                        dataImages.append(str(nPictureId))

                    animationStatus = {}
                    if strItem8 != '':
                        for strStatus in strItem8.split('|'):

                            statusList = strStatus.split(',')
                            if len(statusList) != 4:
                                continue

                            strKey = statusList[0]
                            strAnimationId = statusList[1]
                            frameCount = statusList[2]
                            interval = statusList[3]

                            # try:
                            #     if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                            #         if int(strAnimationId) not in image_id_list_project:
                            #             self.create404ImageFileIfNotExist()
                            #             strAnimationId = "-404404404"
                            # except Exception as e:
                            #     logging.error('ERROR in get_plant:%s' % (e.__str__()))
                            #     strAnimationId = "-404404404"

                            animationStatus.update({
                                strKey: dict(animationId=strAnimationId, frameCount=frameCount, interval=interval)
                            })

                            if strAnimationId not in listAnimationIds:
                                listAnimationIds.append(strAnimationId)

                                for templateEquipName in templateEquipNameList:
                                    strAnimationId = strAnimationId.replace(templateEquipName, "")

                                # 移除模板设备名前缀
                                listAnimationIds_prefix_removed.append(strAnimationId)

                            imgId = statusList[1]
                            if not (int(frameCount) == 1 and imgId not in dataImages):
                                continue

                            try:
                                if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                                    if int(imgId) not in image_id_list_project:
                                        self.create404ImageFileIfNotExist()
                                        imgId = -404404404
                            except Exception as e:
                                logging.error('ERROR in get_plant:%s' % (e.__str__()))
                                imgId = -404404404

                            dataImages.append(str(imgId))

                    if isinstance(hideScript, str):
                        if len(hideScript):
                            if allPointInfo == None:
                                allPointInfo = RedisManager.get_4db_points_info()

                            if hideScript not in allPointInfo.keys():
                                continue

                    dataEquipments.append({'id': item[0] if item[0] != None else 0,
                                           'x': item[1] if item[1] != None else 0,
                                           'y': item[2] if item[2] != None else 0,
                                           'width': item[3] if item[3] != None else 0,
                                           'height': item[4] if item[4] != None else 0,
                                           "idCom": strItem5,
                                           'idPicture': nPictureId,
                                           'rotate': item[7] if item[7] != None else 0,
                                           'link': strItem9,
                                           'linkinfo': LinkInfoList,
                                           'layer': item[10] if item[10] != None else 0,
                                           'name': strItem12,
                                           'isFromAnimation': strItem11 == '0',
                                           'animation': animationStatus,
                                           'bindType': strItem13,
                                           "customName": customName})

                # listAnimationIds_prefix_removed = [item.replace(strPrefix, "") for item in listAnimationIds]
                cu.execute("SELECT id, animationlist FROM lib_animation WHERE id IN (%s)" % (
                ','.join(listAnimationIds_prefix_removed)))
                # distinct animation image ids
                for item in cu.fetchall():
                    arrImageIds = item[1].decode('gbk').split(',') if item[1] != None else []
                    dataAnimationList.update({item[0]: arrImageIds})
                    for arrImageId in arrImageIds:
                        if (arrImageId not in dataAnimationImages):
                            dataAnimationImages.append(arrImageId)

                #liquid level:
                cu.execute(
                    "SELECT id, x, y, width, height, layer, unitproperty02, unitproperty03, unitproperty04, unitproperty05, unitproperty06 FROM list_unit06 WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    try:
                        dataLequidLevels.append({'id': item[0] if item[0] != None else 0,
                                           'x': item[1] if item[1] != None else 0,
                                           'y': item[2] if item[2] != None else 0,
                                           'width': item[3] if item[3] != None else 0,
                                           'height': item[4] if item[4] != None else 0,
                                             'layer': item[5] if item[5] != None else 0,
                                           'bindPointName': item[6].decode('gbk') if item[6] != None else '',
                                           'max':item[7].decode('gbk') if item[7] != None else '',
                                           'min': item[8].decode('gbk') if item[8] != None else '',
                                           'maxAlarm':item[9].decode('gbk') if item[9] != None else '',
                                           'minAlarm': item[10].decode('gbk') if item[10] != None else ''})
                    except:
                        continue

                tFrom = datetime.now()
                # Chart
                cu.execute(
                    "SELECT id, x, y, width, height, update_interval, elementType FROM list_chart WHERE pageid = %s" % (
                    pageId))
                for item in cu.fetchall():
                    dataCharts.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'interval': item[5] if item[5] != None else 0,
                                       'data': [],
                                       'elementType': item[6] if item[6] != None else 0})

                tFrom = datetime.now()
                cu.execute("SELECT id, color1, title, pointname FROM detail_chart WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    for chart in dataCharts:
                        if item[0] != None:
                            if (chart["id"] == item[0]):
                                intColor = int(item[1]) if item[1] != None else 0
                                chart["data"].append({'color': {'r': get_r_from_int(intColor),
                                                                "g": get_g_from_int(intColor),
                                                                'b': get_b_from_int(intColor)},
                                                      'title': item[2].decode('gbk') if item[2] != None else '',
                                                      'pointName': item[3].decode('gbk') if item[3] != None else ''})
                                break

                # Button
                cu.execute("SELECT id, x, y, width, height, comm, over, down, disable, textcontent, link, settingpoint, settingvalue, description, layer, \
                textsize, textcolor, unitproperty01, unitproperty02, unitproperty04, unitproperty05, name, hideScript, sourceType FROM list_button WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    textColor = int(item[16]) if item[16] != None else 0
                    arrRelation = []
                    strRelation = item[17].decode('gbk')
                    strPreCheck = item[21].decode("UTF-8") if item[21] != None else ""

                    dPreCheck = {}
                    try:
                        dPreCheck = json.loads(strPreCheck)
                    except:
                        pass

                    PreCheckScript = dPreCheck.get("PreCheckScript", "")
                    PreCheckScriptDescription = dPreCheck.get("PreCheckScriptDescription", "")

                    if len(strRelation) > 0:
                        arrTemp = strRelation.split(',')
                        for i in range(len(arrTemp)):
                            arrItem = arrTemp[i].split('|')
                            arrRelation.append(
                                {'point': arrItem[0], 'type': arrItem[1], 'value': arrItem[2]})

                    buttonSetValue = None
                    if isinstance(item[12], bytes):#设定值是一个字符串语法
                        buttonSetValue = item[12].decode('gbk')
                    else:
                        buttonSetValue = item[12] if item[12] != None else 0

                    hideScript = item[22].decode("gbk") if item[22] != None else None
                    if isinstance(hideScript, str):
                        if len(hideScript):
                            if allPointInfo == None:
                                allPointInfo = RedisManager.get_4db_points_info()

                            if isinstance(allPointInfo, dict):
                                if hideScript not in allPointInfo.keys():
                                    continue

                    if isinstance(item[23], bytes):
                        strStyle = item[23].decode("gbk")
                    elif isinstance(item[23], str):
                        strStyle = item[23]
                    else:
                        strStyle = ""

                    dataButtons.append({'id': item[0] if item[0] != None else 0,
                                        'x': item[1] if item[1] != None else 0,
                                        'y': item[2] if item[2] != None else 0,
                                        'width': item[3] if item[3] != None else 0,
                                        'height': item[4] if item[4] != None else 0,
                                        'comm': item[5] if item[5] != None else 0,
                                        'over': item[6] if item[6] != None else 0,
                                        'down': item[7] if item[7] != None else 0,
                                        'disable': item[8] if item[8] != None else 0,
                                        'text': item[9].decode('gbk') if item[9] != None else '',
                                        'link': item[10] if item[10] != None else 0,
                                        'idCom': item[11].decode('gbk') if item[11] != None else '',
                                        'setValue': buttonSetValue,
                                        'description': item[13].decode('gbk') if item[13] != None else '',
                                        'layer': item[14] if item[14] != None else 0,
                                        'fontSize': item[15] if item[15] != None else 0,
                                        'fontColor': {'b': get_b_from_int(textColor),
                                                      "g": get_g_from_int(textColor),
                                                      'r': get_r_from_int(textColor)},
                                        'relation': arrRelation,
                                        'relatType': item[18].decode('gbk'),
                                        'downloadEnableCondition': item[19].decode('gbk') if item[19] else '',
                                        'downloadURL': item[20].decode('gbk') if item[20] else '',
                                        "PreCheckScript": PreCheckScript,
                                        "PreCheckScriptDescription": PreCheckScriptDescription,
                                        "style": strStyle})

                    if (item[5] != None and item[5] not in dataImages):
                        dataImages.append(str(item[5]))
                    if (item[6] != None and item[6] not in dataImages):
                        dataImages.append(str(item[6]))
                    if (item[7] != None and item[7] not in dataImages):
                        dataImages.append(str(item[7]))
                    if (item[8] != None and item[8] not in dataImages):
                        dataImages.append(str(item[8]))

                # Text
                tFrom = datetime.now()
                cu.execute(
                    "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, t.initialValue, t.size, t.font, t.color, "
                    "t.decimalplace, t.bindstring, t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.unitproperty04, t.hideScript,"
                    " t.font FROM list_text t left join list_point p on t.dataComId = p.name WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    textColor = int(item[9]) if  item[9] != None else 0
                    hideScript = item[19].decode("gbk") if item[19] != None else None

                    if isinstance(hideScript, str):
                        if len(hideScript):
                            if allPointInfo == None:
                                allPointInfo = RedisManager.get_4db_points_info()

                            if isinstance(allPointInfo, dict):
                                if hideScript not in allPointInfo.keys():
                                    continue

                    dataTexts.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'idCom': item[5].decode('gbk') if item[5] != None else '',
                                      'text': item[6].decode('gbk') if item[6] != None else '',
                                      'fontSize': item[7] if item[7] != None else 0,
                                      'font': item[8].decode("gbk") if item[8] != None else '',
                                      'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                'b': get_b_from_int(textColor)}, 'decimalplace': item[10],
                                      'bindString': item[11].decode("gbk") if item[11] != None else '',
                                      'showMode': item[12] if item[12] != None else 0,
                                      'rw': item[13] if item[13] != None else 0,
                                      'layer': item[14] if item[0] != None else 0,
                                      'align': item[15] if item[15] != None else 0,
                                      'bindScript': item[16].decode("gbk") if item[16] != None else '',
                                      "backgroudFrameStyle": item[17].decode("gbk") if item[17] != None else 0,
                                      "unit": item[18].decode("gbk") if item[18] != None else ""})

                # Gage
                tFrom = datetime.now()
                cu.execute(
                    "SELECT ld.id, ld.x, ld.y, ld.width, ld.height, ld.pointname, ld.max, ld.min, lp.pagetype, lp.xposition, lp.yposition, ld.layer, ld.style, ld.main_unit, ld.second_unit FROM list_dashboard ld left join list_page lp on ld.pageid = lp.id WHERE ld.pageid = %s" % (
                    pageId))
                cu.execute(
                    "SELECT ld.id, ld.x, ld.y, ld.width, ld.height, ld.pointname, ld.max, ld.min, lp.pagetype, lp.xposition, lp.yposition, ld.layer, ld.style, ld.main_unit, ld.second_unit FROM list_dashboard ld left join list_page lp on ld.pageid = lp.id WHERE ld.pageid = %s" % (
                    pageId))

                gageTypePathDict = {
                    0: os.path.join("siteinterface", "static", "images", "dial1"),
                    1: os.path.join("siteinterface", "static", "images", "dial2"),
                    2: os.path.join("siteinterface", "static", "images", "dial3")
                }

                for item in cu.fetchall():
                    strPath = gageTypePathDict.get(item[12], None)
                    dataGages.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'idCom': item[5].decode('gbk') if item[5] != None else '',
                                      'max': item[6] if item[6] != None else 0,
                                      'min': item[7] if item[7] != None else 0,
                                      'pagetype': item[8].decode('gbk') if item[8] != None else '',
                                      'xposition': item[9] if item[9] != None else 0,
                                      'yposition': item[10] if item[10] != None else 0,
                                      "layer": item[11] if item[11] != None else 0,
                                      "type": item[12] if item[12] != None else None,
                                      "path": strPath,
                                      "fontColor": item[13] if item[13] != None else 0,
                                      "decimal": item[14] if item[14] != None else 1
                                  })

                # Ruler
                # ---referrences
                tFrom = datetime.now()
                cu.execute("SELECT id, unitproperty02, unitproperty03, unitproperty04, unitproperty05 , unitproperty07 \
                FROM list_unit18 \
                WHERE unitproperty01 = 0 and id in (SELECT id FROM list_unit17 WHERE pageid = %s)" % (pageId))
                dataRulerItems = []
                for item in cu.fetchall():
                    dataRulerItems.append({'id': item[0] if item[0] != None else 0,
                                           'name': item[1].decode('gbk') if item[1] != None else '',
                                           'value': item[2].decode('gbk') if item[2] != None else '',
                                           'idCom': item[3].decode('gbk') if item[3] != None else '',
                                           'link': item[4].decode('gbk') if item[4] != None else '',
                                           'isInUp': item[5].decode('gbk') if item[5] != None else ''})

                # ---level
                tFrom = datetime.now()
                cu.execute("SELECT id, unitproperty02, unitproperty03, unitproperty04 \
                FROM list_unit18 \
                WHERE unitproperty01 = 1 and id in (SELECT id FROM list_unit17 WHERE pageid == %s)" % (pageId))
                levelsItem = []
                levels = []
                colorList = ['#7dbfe0', '#94c84c', '#f0bc7d', '#d17965']
                for item in cu.fetchall():
                    levelsItem.append({'id': item[0] if item[0] != None else 0,
                                       'text': item[1].decode('gbk') if item[1] != None else '',
                                       'max': item[2].decode('gbk') if item[2] != None else '',
                                       'min': item[3].decode('gbk') if item[3] != None else ''})
                if len(levelsItem) != 0:
                    levelsItem.sort(key=lambda x: x['max'])
                    for index in range(len(levelsItem)):
                        l_item = levelsItem[index]
                        levels.append({'color': colorList[index], 'text': l_item['text'], 'min': l_item['min'],
                                       'max': l_item['max']})

                tFrom = datetime.now()
                cu.execute(
                    "SELECT id, x, y, width, height, unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05, unitproperty06 FROM list_unit17 WHERE pageid = %s" % (
                    pageId))
                for item in cu.fetchall():
                    dataTempArrs = []
                    for temp in dataRulerItems:
                        if item[0] != None:
                            if (temp['id'] == item[0]):
                                dataTempArrs.append(temp)
                    dataRulers.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'levels': levels,
                                       'name': item[5].decode('gbk') if item[5] != None else '',
                                       'min': item[7].decode('gbk') if item[7] != None else 0,
                                       'max': item[6].decode('gbk') if item[6] != None else 0,
                                       'mainScale': item[8].decode('gbk') if item[8] != None else '',
                                       'minorScale': item[9].decode('gbk') if item[9] != None else '',
                                       'decimal': item[10].decode('gbk') if item[10] != None else '',
                                       'references': dataTempArrs
                                       })


                # Temp Distribution
                tFrom = datetime.now()
                cu.execute("select lt.id,lt.initialvalue,lt.xpos,lt.ypos,lt.dataComId "
                           "from list_text lt "
                           "where lt.unitproperty02 = 1 and lt.pageid = '%s';" % pageId)
                dataTempDistributions['pageid'] = pageId
                temp_data = []
                temp_point_result = cu.fetchall()
                for item in temp_point_result:
                    temp_data.append({'id': item[0] if item[0] != None else 0,
                                      'value': item[1].decode('gbk') if item[1] != None else '',
                                      'x': item[2] if item[2] != None else 0,
                                      'y': item[3] if item[3] != None else 0,
                                      'idCom': item[4].decode('gbk') if item[4] != None else ''})
                dataTempDistributions['data'] = temp_data


                # @todo 此处查询语句不对，需修改
                tFrom = datetime.now()
                cu.execute(
                    "select x, y, width, height, layer, unitproperty04 from list_unit19 where pageid = '%s' and unitproperty01='planeTempeDistr'" % pageId)
                temp_page_result = cu.fetchone()
                if temp_page_result is not None:
                    dataTempDistributions['x'] = temp_page_result[0]
                    dataTempDistributions['y'] = temp_page_result[1]
                    dataTempDistributions['width'] = temp_page_result[2]
                    dataTempDistributions['height'] = temp_page_result[3]
                    dataTempDistributions['layer'] = temp_page_result[4]

                # Checkbox
                tFrom = datetime.now()
                cu.execute("SELECT id,x,y,width,height,layer,unitproperty01,unitproperty02,unitproperty03,unitproperty04,unitproperty05,unitproperty06,unitproperty07,unitproperty08,unitproperty09,unitproperty10 \
                FROM list_unit07 WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    font_color = item[7].decode('gbk') if item[7] != None else ''
                    text_color = {"r": 255, "g": 255, "b": 255}
                    if font_color:
                        try:
                            text_color = {'r': get_r_from_int(font_color),
                                          'g': get_g_from_int(font_color),
                                          'b': get_b_from_int(font_color)}
                        except:
                            pass
                    try:
                        dataCheckboxs.append({'id': item[0] if item[0] != None else 0,
                                          'x': item[1] if item[1] != None else 0,
                                          'y': item[2] if item[2] != None else 0,
                                          'width': item[3] if item[3] != None else 0,
                                          'height': item[4] if item[4] != None else 0,
                                          'layer': item[5] if item[5] != None else 0,
                                          'idCom': item[11].decode('gbk') if item[11] != None else '',
                                          'type': item[6].decode('gbk') if item[6] != None else '',
                                          'fontColor': text_color,
                                          'fontSize': item[8].decode('gbk') if item[8] != None else '',
                                          'setValue': item[9].decode('gbk') if item[9] != None else '',
                                          'unsetValue': item[10].decode('gbk') if item[10] != None else '',
                                          'text': item[12].decode('gbk') if item[12] != None else '',
                                          'idGroup': item[13].decode('gbk') if item[13] != None else '',
                                          'expression': item[14].decode('gbk') if item[14] != None else '',
                                          'desc': item[15].decode('gbk') if item[15] != None else ''})
                    except:
                        pass


                # import pdb;pdb.set_trace()
                # dottedLine
                tFrom = datetime.now()
                cu.execute("SELECT id,x,y,width,height,layer \
                FROM list_unit19 WHERE pageid = %s and unitproperty01='dottedLineFrame'" % (pageId))
                for item in cu.fetchall():
                    dataRects.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'layer': item[5] if item[5] != None else 0})

                # rectangels
                strQ = "SELECT x, y, width, height, layer, id, pageid, unitproperty02, unitproperty03, " \
                           "unitproperty04, unitproperty05, unitproperty06, unitproperty07, unitproperty08, " \
                           "unitproperty09, unitproperty10, unitproperty11, unitproperty12, unitproperty13, " \
                           "unitproperty14, unitproperty15  FROM list_unit19 WHERE pageid = %s AND unitproperty01 = 'rectangle'" % pageId
                cu.execute(strQ)

                items = cu.fetchall()
                for item in items:
                    colorBytes = item[7] if item[7] != None else 0
                    proper04 = int(item[9].decode("gbk")) if item[9] != None else 0
                    fillColorBytes = item[10] if item[10] != None else colorBytes

                    proper05 = int(item[11].decode("gbk")) if item[11] != None else 0

                    titleColorBytes = b""
                    titleSize = 0
                    try:
                        titleColorBytes = bytes(item[15].decode("gbk").split(",")[0], encoding="gbk")
                        titleSize = float(item[15].decode("gbk").split(",")[1])
                    except:
                        pass

                    bodyColorBytes = b""
                    bodySize = 0
                    try:
                        bodyColorBytes = bytes(item[16].decode("gbk").split(",")[0], encoding="gbk")
                        bodySize = float(item[16].decode("gbk").split(",")[1])
                    except:
                        pass

                    descColorBytes = b""
                    descSize = 0
                    try:
                        descColorBytes = bytes(item[17].decode("gbk").split(",")[0], encoding="gbk")
                        descSize = float(item[17].decode("gbk").split(",")[1])
                    except:
                        pass

                    # 加注释单位
                    rectPointList = []
                    pNameList = []
                    imgList = []
                    decimalList = []
                    rectRawList = item[19].decode("gbk").split("|") if item[19] != None else []
                    for nameImg in rectRawList:
                        if nameImg.count(",") == 0:
                            continue

                        strName = nameImg.split(",")[0]
                        strImg = nameImg.split(",")[1]
                        nDecimal = 2
                        try:
                            nDecimal = int(nameImg.split(",")[2])
                        except:
                            pass
                        pNameList.append(strName)
                        imgList.append(strImg)
                        decimalList.append(nDecimal)

                        try:
                            if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                                if int(strImg) not in image_id_list_project:
                                    self.create404ImageFileIfNotExist()
                                    strImg = -404404404
                        except Exception as e:
                            logging.error('ERROR in get_plant:%s' % (e.__str__()))
                            strImg = -404404404

                        if strImg not in dataImages:
                            dataImages.append(strImg)

                    pointInfoDict = self.getPointInfoFromS3db(pNameList)
                    for idx, pName in enumerate(pNameList):
                        strDesc = ""
                        strUnit = ""
                        strSourceType = ""
                        if pointInfoDict.get(pName):
                            strDesc = pointInfoDict.get(pName).get("description")
                            strUnit = pointInfoDict.get(pName).get("unit")
                            strSourceType = pointInfoDict.get(pName).get("sourceType")

                        rectPointList.append(dict(name=pName, img=imgList[idx], desc=strDesc, unit=strUnit, decimal=decimalList[idx], type=strSourceType))

                    dataRectangles.append({
                        "x": item[0] if item[0] != None else 0,
                        "y": item[1] if item[1] != None else 0,
                        "width": item[2] if item[2] != None else 0,
                        "height": item[3] if item[3] != None else 0,
                        "layer": item[4] if item[4] != None else 0,
                        "id": item[5] if item[5] != None else 0,
                        'color': colorHexToRgb(colorBytes),
                        "lineWidth": float(item[8].decode("gbk")) if item[8] != None else 0,
                        "fillOrNot": 1 if proper04 > 0 else 0,
                        "fillColor": colorHexToRgb(fillColorBytes),
                        "roundOrNot": 1 if proper05 > 0 else 0,
                        "roundYPox": int(float(item[12].decode("gbk"))) if item[12] != None else 0,
                        "roundXPox": int(float(item[13].decode("gbk"))) if item[13] != None else 0,
                        "rectStyle": int(float(item[14].decode("gbk"))) if item[14] != None else 0,
                        "titleColor": colorHexToRgb(titleColorBytes),
                        "titleSize": titleSize,
                        "bodyColor": colorHexToRgb(bodyColorBytes),
                        "bodySize": bodySize,
                        "descColor": colorHexToRgb(descColorBytes),
                        "descSize": descSize,
                        "descOrNot": int(float(item[18].decode("gbk"))) if item[18] != None else 0,
                        "pointList": rectPointList,
                        "title": item[20].decode("utf8") if item[20] != None else ""
                    })

                # Common config
                cu.execute("SELECT id,x,y,width,height,layer,unitproperty02 \
                            FROM list_unit19 WHERE pageid = %s and unitproperty01='generalComponent'" % (pageId))
                for item in cu.fetchall():
                    strConfig = ""
                    try:
                        strConfig = item[6].decode("gbk")
                    except:
                        try:
                            strConfig = item[6].decode("utf8")
                        except:
                            pass
                    dataCustom.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'layer': item[5] if item[5] != None else 0,
                                       'config': strConfig})

                # time select
                cu.execute(
                    "SELECT id,x,y,width,height,layer,bindpoint,RW,datatime FROM list_timeselect WHERE pageid = %s and elementtype= 56" % (
                        pageId))
                for item in cu.fetchall():
                    try:
                        dataTimePicker.append({'id': item[0] if item[0] != None else 0,
                                               'x': item[1] if item[1] != None else 0,
                                               'y': item[2] if item[2] != None else 0,
                                               'width': item[3] if item[3] != None else 0,
                                               'height': item[4] if item[4] != None else 0,
                                               'layer': item[5] if item[5] != None else 0,
                                               'bindpoint': item[6].decode('gbk') if item[6] != None else '',
                                               'RW': item[7],
                                               'timeFixed': item[8]})
                    except:
                        continue

                # 标准设备
                tSysEquip = datetime.now()
                tFrom = datetime.now()
                cu.execute(
                    "SELECT pageid, id, x, y, width, height, unitproperty04, unitproperty06, unitproperty01, layer, unitproperty07, unitproperty08, unitproperty09, unitproperty10 FROM list_unit13 WHERE pageid = %s and width > 0 and height > 0 and layer > 0" % (
                    pageId))
                items = cu.fetchall()

                # 以模板文件名为键制作模板图元ID字典
                templatePelIdDict = {}
                for object in items:
                    templateFileName = object[10].decode("gbk") if object[10] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    templatePelId = eval(object[6])
                    if templateFileNameWithoutExt in templatePelIdDict.keys():
                        if templatePelId in templatePelIdDict[templateFileNameWithoutExt]:
                            continue
                        templatePelIdDict[templateFileNameWithoutExt].append(templatePelId)
                    else:
                        templatePelIdDict[templateFileNameWithoutExt] = [templatePelId]

                    image_id_list_template[templateFileName] = RedisManager.get_image_id_list_template(templateFileName)

                # 以模板文件名为键创建模板信息查询字典和text字典
                queryDict = {}
                textQueryDict = {}
                for templateFileNameWithoutExt in templatePelIdDict.keys():
                    templatePelIdList = templatePelIdDict[templateFileNameWithoutExt]

                    clauseTemplatePelIdList = ["page_contain_elements.pageid = {0} AND event.pageid={0}".format(pelId) for pelId in templatePelIdList]
                    clauseAllTextsList = ["pageid = {0}".format(pelId) for pelId in templatePelIdList]

                    strClauseTemplatePelId = " or ".join(clauseTemplatePelIdList)
                    strClauseAllTexts = " or ".join(clauseAllTextsList)

                    strQueryAllNeedTemplate = "SELECT x, y, width, hight, DataComId, pictureid, rotateAngle, " \
                                              "event_content, layer, elementName, bind_content, " \
                                              "page_contain_elements.unitproperty03 AS prop03, page_contain_elements.unitproperty02 AS prop02, " \
                                              "page_contain_elements.pageid as templatePageId FROM " \
                                              "page_contain_elements LEFT JOIN event ON page_contain_elements.elementid = event.id WHERE " + strClauseTemplatePelId

                    strQueryAllTextsInTempalte = "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, " \
                                                 "t.initialValue, t.size, t.font, t.color, t.decimalplace, t.bindstring," \
                                                 " t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.pageid as templatePageId " \
                                                 "FROM list_text t left join list_point p on t.dataComId = p.name WHERE " + strClauseAllTexts

                    queryDict.update({templateFileNameWithoutExt: strQueryAllNeedTemplate})
                    textQueryDict.update({templateFileNameWithoutExt: strQueryAllTextsInTempalte})

                templateDict = {}
                templateTextsDict = {}
                templateDir = path.join(app.static_folder, "template")
                for templateFileNameWithoutExt in queryDict.keys():
                    templatePath = path.join(templateDir, "{0}.4db".format(templateFileNameWithoutExt))

                    if not path.exists(templatePath):
                        continue

                    # 读取模板文件中所有标准设备的信息
                    with SqliteManager(templatePath) as sdb:
                        templates = sdb.exec_query(queryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建模板信息字典
                    for template in templates:
                        templatePageId = template.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateDict.keys():
                            templateDict[key].append(template)
                        else:
                            templateDict[key] = [template]

                    # 读取模板文件中所有text的信息
                    with SqliteManager(templatePath) as sdb:
                        textTemplates = sdb.exec_query(textQueryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建text信息字典
                    for textTemplate in textTemplates:
                        templatePageId = textTemplate.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateTextsDict.keys():
                            templateTextsDict[key].append(textTemplate)
                        else:
                            templateTextsDict[key] = [textTemplate]


                # 开始遍历该页面内的标准设备
                for standEquipIdx, item in enumerate(items):
                    strNavigation = item[12].decode("gbk") if item[12] else ""
                    templateFileName = item[10].decode("gbk") if item[10] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    template_pel_id = eval(item[6])
                    templateFilePath = path.join(app.static_folder, "template", templateFileName)

                    prefix = "{0}/".format(templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(templateFileNameWithoutExt)

                    if not path.exists(templateFilePath):
                        continue

                    if isinstance(item[13], str):
                        customName = item[13]
                    elif isinstance(item[13], bytes):
                        customName = item[13].decode("gbk")
                    else:
                        customName = ""

                    # 以模板文件名+模板图元ID组成的键名
                    templateKey = "{0}_{1}".format(templateFileNameWithoutExt, template_pel_id)

                    id = item[1] if item[1] else 0

                    prop06 = item[7].decode("gbk") if item[7] != None else ""
                    if not prop06:
                        logging.error("ERROR in getPlant: no placeholder found in {id} from template {templateName} "
                                      "(pageId of domdb.db: {pageId})".format(id=item[1],
                                                                              templateName=templateFileName,
                                                                              pageId=pageId))
                        continue

                    # 工作空间中主设备的宽、高、坐标，工作空间：需要插入模板设备的界面
                    backgroundWidth = item[4] if item[4] else 0
                    backgroundHeight = item[5] if item[5] else 0
                    backgroundX = item[2]
                    backgroundY = item[3]

                    # 生成placeHolder
                    requestParam = dict()
                    for obj in eval(prop06):
                        requestParam.update(obj)

                    res = templateDict.get(templateKey, [])
                    pels_width = list()
                    if len(res):
                        pels_width = [pel.get("width") for pel in res]
                    else:
                        strError = 'ERROR in read template id:%s'%(str(templateKey))
                        print(strError)
                        logging.error(strError)
                        continue

                    # 从属图标，如err, enabled, automode图标
                    belongings = list()
                    mainEquip = None
                    for pel in res:
                        if pel.get("width") >= max(pels_width, default=0):
                            mainEquip = pel
                        else:
                            belongings.append(pel)

                    # 主设备旋转角度
                    rotateAngleMainEquip = int(item[8].decode("gbk")) if item[8] else 0

                    # 计算缩放比例 START
                    zoomX = 1
                    zoomY = 1
                    mainEquipX = 0
                    mainEquipY = 0
                    if mainEquip:
                        mainEquipX = mainEquip.get("x")
                        mainEquipY = mainEquip.get("y")
                        zoomX = backgroundWidth / mainEquip.get("width")
                        zoomY = backgroundHeight / mainEquip.get("hight")
                    # 计算缩放比例 END

                    # 标准设备的文本内容 START
                    textsList = []
                    textsListFetch = templateTextsDict.get(templateKey, [])
                    for dText in textsListFetch:
                        strPointName = dText.get("dataComId").decode("gbk") if dText.get("dataComId") is not None else ""
                        strTextContent = dText.get("initialvalue").decode("gbk") if dText.get("initialvalue") is not None else ""

                        # 替换点名里的占位符
                        if len(strPointName):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strPointName = strPointName.replace(placeHolder, requestParam.get(key))

                        # 替换文本内容里的占位符
                        if len(strTextContent):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strTextContent = strTextContent.replace(placeHolder, requestParam.get(key))

                        textColor = int(dText.get("color")) if dText.get("color") is not None else 0

                        # text坐标换算
                        textX = dText.get("xpos") if dText.get("xpos") is not None else 0
                        textY = dText.get("ypos") if dText.get("ypos") is not None else 0
                        offsetTextX = (textX - mainEquipX) * zoomX
                        offsetTextY = (textY - mainEquipY) * zoomY
                        xPos = backgroundX + offsetTextX
                        yPox = backgroundY + offsetTextY

                        textsList.append({'id': "{0}_{1}".format(dText.get("id"), standEquipIdx) if dText.get("id") is not None else 0,
                                          'x': xPos,
                                          'y': yPox,
                                          'width': dText.get("width") if dText.get("width") is not None else 0,
                                          'height': dText.get("height") if dText.get("height") is not None else 0,
                                          'idCom': strPointName,
                                          'text': strTextContent,
                                          'fontSize': dText.get("size") if dText.get("size") is not None else 0,
                                          'font': dText.get("font").decode("gbk") if dText.get("font") is not None else "",
                                          'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                    'b': get_b_from_int(textColor)},
                                          'decimalplace': dText.get("decimalplace"),
                                          'bindString': dText.get("bindstring").decode("gbk") if dText.get(
                                              "bindstring") is not None else "",
                                          'showMode': dText.get("showMode") if dText.get(
                                              "showMode") is not None else 0,
                                          'rw': dText.get("R_W") if dText.get("R_W") is not None else 0,
                                          'layer': dText.get("layer") if dText.get("layer") is not None else 0,
                                          'align': dText.get("align") if dText.get("align") is not None else 0,
                                          'bindScript': dText.get("unitproperty05").decode("gbk") if dText.get(
                                              "unitproperty05") is not None else "",
                                          "backgroudFrameStyle": dText.get("unitproperty01").decode(
                                              "gbk") if dText.get("unitproperty01") is not None else 0})
                    # 标准设备的文本内容 END

                    tFrom = datetime.now()
                    # 处理随主设备一起的图标，如enabled, err, automode START
                    childrenList = list()
                    belonging_id_preffix = 999999
                    for belongingIndex, belonging in enumerate(belongings):
                        belonging_id = int("{0}{1}".format(belonging_id_preffix - belongingIndex, id))
                        belongingX = belonging.get("x") if belonging.get("x") else 0
                        belongingY = belonging.get("y") if belonging.get("y") else 0

                        # 模板设备页面中，从属图标与主设备之间的坐标偏差 乘以 缩放比例
                        offsetX = (belongingX - mainEquipX) * zoomX
                        offsetY = (belongingY - mainEquipY) * zoomY

                        # 工作空间中从属图标的高宽考虑缩放比例
                        width = belonging.get("width") * zoomX if belonging.get("width") else 0
                        height = belonging.get("hight") * zoomY if belonging.get("hight") else 0

                        # 工作空间中从属图标的坐标等于主设备的坐标加坐标偏差
                        x = backgroundX + offsetX
                        y = backgroundY + offsetY

                        # 点名占位符处理
                        point = belonging.get("DataComId").decode("gbk") if belonging.get("DataComId") else ""
                        if len(point):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                point = point.replace(placeHolder, requestParam.get(key))

                        # 图片
                        pictureid = "{0}{1}".format(prefix, belonging.get("pictureid")) if belonging.get(
                            "pictureid", None) is not None else ""

                        if not pictureid in dataImages:
                            template_image_id_list = image_id_list_template.get(templateFileName)
                            try:
                                if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                    tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                    if is_int_digit(tmp):
                                        if int(tmp) not in template_image_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                            except Exception as ept:
                                logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                            dataImages.append(pictureid)

                        # 从属图标的旋转角度需要与主设备一致
                        rotateAngle = rotateAngleMainEquip

                        # 图层
                        layer = belonging.get("layer") if belonging.get("layer") else 0

                        # title占位符修改
                        strTitle = belonging.get("elementName").decode("gbk") if belonging.get("elementName") else ""
                        elemName = ""
                        if len(strTitle):
                            elemName = replace_place_holder(strTitle, requestParam)

                        strItem11 = belonging.get("prop02").decode("gbk") if belonging.get("prop02") else ""

                        animationStatus = dict()
                        str_item = belonging.get("bind_content").decode('gbk') if belonging.get(
                            "bind_content") != None else ''
                        if str_item != "":
                            temp = str_item.split('|')
                            for strStatus in temp:
                                tempStatus = strStatus.split(',')
                                if len(tempStatus) == 4:
                                    animationStatus.update(
                                        {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                         'frameCount': tempStatus[2],
                                                         'interval': tempStatus[3]}})

                                    imgId = "{0}{1}".format(prefix, tempStatus[1])

                                    if imgId not in dataImages:
                                        template_image_id_list = image_id_list_template.get(templateFileName)
                                        try:
                                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                                tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                                if is_int_digit(tmp):
                                                    if int(tmp) not in template_image_id_list:
                                                        self.create404ImageFileForTemplateIfNotExist(
                                                            templateFileNameWithoutExt)
                                                        imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                        except Exception as ept:
                                            logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                                        dataImages.append(imgId)

                        strItem13 = belonging.get("prop03").decode("gbk") if belonging.get("prop03") != None else 0

                        # 获取子设备linkInfo
                        try:
                            ChildrenLinkInfoList = belonging.get("event_content").decode("gbk").split(",")
                            if ChildrenLinkInfoList and isinstance(ChildrenLinkInfoList, list):
                                ChildrenLinkInfoList.append('template')  # 区分常规弹窗
                            # print(ChildrenLinkInfoList)
                        except:
                            ChildrenLinkInfoList = []

                        childPlaceHolder = {}
                        if len(ChildrenLinkInfoList):
                            childPlaceHolder = requestParam

                        childrenList.append({
                            "id": belonging_id,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "idCom": point,
                            "idPicture": pictureid,
                            "rotateAngle": rotateAngle,
                            "layer": layer,
                            "name": elemName,
                            "isFromAnimation": strItem11 == "0",
                            "animation": animationStatus,
                            "bindType": int(float(strItem13)),
                            "link": ChildrenLinkInfoList[4],            # 子设备link
                            "linkinfo": ChildrenLinkInfoList,            # 子设备linkInfoList
                            "placeHolder": childPlaceHolder
                        })
                    # 处理随主设备一起的图标，如enabled, err, automode END

                    tFrom = datetime.now()
                    # 处理belongings的动画问题 START
                    for child in childrenList:
                        dictAnimation = child.get("animation")
                        for dictAnimationValue in dictAnimation.values():
                            if int(dictAnimationValue.get("frameCount")) > 1:
                                childAnimationId = dictAnimationValue.get("animationId").replace(prefix, "")
                                with SqliteManager(templateFilePath) as dbm:
                                    str_sql = '''SELECT
                                                    *
                                                FROM
                                                    lib_animation
                                                WHERE
                                                    id = ?'''
                                    sql_res = dbm.exec_query(str_sql, (childAnimationId,))
                                animationListWithPrefix = ["{0}{1}".format(prefix, itm) for itm in
                                                           sql_res[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update({
                                    dictAnimationValue.get("animationId"): animationListWithPrefix
                                })
                    # 处理belongings的动画问题 END


                    # 处理主设备 START
                    tFrom = datetime.now()
                    pictureid = "{0}{1}".format(prefix, mainEquip.get("pictureid")) if mainEquip.get(
                        "pictureid", None) != None else ""
                    if not pictureid in dataImages:
                        dataImages.append(pictureid)

                    rotateAngle = int(item[8].decode("gbk")) if item[8] else 0
                    try:
                        LinkInfoList = mainEquip.get("event_content").decode("gbk").split(",")
                        if LinkInfoList and isinstance(LinkInfoList, list):
                            LinkInfoList.append('template')  # 区分常规弹窗
                        # print(LinkInfoList)
                    except:
                        LinkInfoList = []

                    layer = item[9] if item[9] else 0

                    strItem11 = mainEquip.get("prop02").decode("gbk") if mainEquip.get("prop02") != None else ""

                    animationStatus = dict()
                    str_item = mainEquip.get("bind_content").decode('gbk') if mainEquip.get(
                        "bind_content") != None else ''
                    if str_item != "":
                        temp = str_item.split('|')
                        for strStatus in temp:
                            tempStatus = strStatus.split(',')
                            if len(tempStatus) == 4:
                                animationStatus.update(
                                    {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                     'frameCount': tempStatus[2],
                                                     'interval': tempStatus[3]}})

                                imgId = "{0}{1}".format(prefix, tempStatus[1])
                                if imgId not in dataImages:
                                    template_image_id_list = image_id_list_template.get(templateFileName)
                                    try:
                                        if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                            tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                            if is_int_digit(tmp):
                                                if int(tmp) not in template_image_id_list:
                                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                    imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                    except Exception as ept:
                                        logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                                    dataImages.append(imgId)

                    # title占位符修改
                    strTitle = mainEquip.get("elementName").decode("gbk") if mainEquip.get("elementName") != None else ""

                    elemName = ""
                    if len(strTitle):
                        elemName = replace_place_holder(strTitle, requestParam)

                    # 点名占位符处理
                    point = mainEquip.get("DataComId").decode("gbk") if mainEquip.get("DataComId") != None else ""
                    if len(point):
                        for key in requestParam.keys():
                            placeHolder = "{%s}" % key
                            point = point.replace(placeHolder, requestParam.get(key))

                    strItem13 = mainEquip.get("prop03").decode("gbk") if mainEquip.get("prop03") != None else 0
                    # 处理主设备 END


                    dataSystemEquipments.append({
                        "id": item[1] if item[1] != None else "",
                        "x": item[2] if item[2] != None else 0,
                        "y": item[3] if item[3] != None else 0,
                        "width": item[4] if item[4] != None else 0,
                        "height": item[5] if item[5] != None else 0,
                        "idCom": point,
                        "idPicture": pictureid,
                        "rotateAngle": rotateAngleMainEquip,
                        "link": LinkInfoList[4],
                        "linkinfo": LinkInfoList,
                        "layer": layer,
                        "name": elemName,
                        "isFromAnimation": strItem11 == "0",
                        "animation": animationStatus,
                        'bindType': int(float(strItem13)),
                        "templatePelId": template_pel_id,
                        "placeHolder": requestParam,
                        "children": childrenList,
                        "texts": textsList,
                        "templateFileName": templateFileNameWithoutExt,
                        "navigation": strNavigation,
                        "customName": customName
                    })

                    tFrom = datetime.now()
                    # 生成dataTemplateImages
                    for equip in dataSystemEquipments:
                        if not str(equip.get("idPicture")) in dataTemplateImages:
                            dataTemplateImages.append(str(equip.get("idPicture")))
                        dictAnimation = equip.get("animation")
                        for value in dictAnimation.values():
                            if not str(value.get("animationId")) in dataTemplateImages:
                                dataTemplateImages.append(str(value.get("animationId")))

                    # 更新animationlist
                    # template_4db = app.config.get("TEMPLATE_DB_FILE_DIR")
                    with SqliteManager(templateFilePath) as sdb:
                        for img in dataTemplateImages:

                            str_sql = '''SELECT
                                            animationlist
                                        FROM
                                            lib_animation
                                        WHERE
                                            id = ?'''
                            aList = sdb.exec_query(str_sql, (img.replace(prefix, ""),))
                            if len(aList):
                                animation_list = ["{0}{1}".format(prefix, item) for item in
                                                  aList[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update({img: animation_list})

                    # 更新animationList
                    for key in dataAnimationList.keys():
                        for ani in dataAnimationList.get(key):
                            if not ani in dataAnimationImages:
                                dataAnimationImages.append(ani)

            except Exception as e:
                traceback.print_exc()
                logging.error(e.__str__())
            finally:
                if cu is not None:
                    cu.close()
                if con is not None:
                    con.close()

        # 获取报修信息
        tFrom = datetime.now()
        fixList = BEOPDataAccess.getInstance().getAllFixPosInfo(pageId)

        colorDict = {
            0: "green",
            1: "yellow",
            2: "red"
        }

        if fixList is not None and len(fixList):
            for fix in fixList:
                dataFix.append({
                    "fixId": fix.get("fixId"),
                    "x": fix.get("posX"),
                    "y": fix.get("posY"),
                    "width": 32,
                    "height": 32,
                    "visible": fix.get("visible"),
                    "idPicture": "fix/{0}".format(colorDict.get(fix.get("urgent"), "green")),
                    "layer": 9
                })

        dataImages.append("{0}green".format(strPrefixFix))
        dataImages.append("{0}yellow".format(strPrefixFix))
        dataImages.append("{0}red".format(strPrefixFix))

        return {
            'page': dataPage,
            'images': dataImages,
            'animationImages': dataAnimationImages,
            'animationList': dataAnimationList,
            'pipelines': dataPipeLines,
            'equipments': dataEquipments,
            'charts': dataCharts,
            'gages': dataGages,
            'buttons': dataButtons,
            'rulers': dataRulers,
            'checkboxs': dataCheckboxs,
            'texts': dataTexts,
            'rects': dataRects,
            'tempDistributions': dataTempDistributions,
            'customControls': dataCustom,
            'timePickers': dataTimePicker,
            "systemEquipments": dataSystemEquipments,
            "templateImages": dataTemplateImages,
            "liquidLevels": dataLequidLevels,
            "fix": dataFix,
            "rectangles": dataRectangles,
            "straightLine": dataStraightLine,
            "polygons": dataPolygon
        }

    """
    web debugTool专用页面获取接口
    """
    def getPlantDebugTool(self, pageid):
        con = None
        cu = None
        pageId = pageid
        strPrefixFix = "fix/"

        # 所有点信息字典
        allPointInfo = None

        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        dataPage = {}
        dataImages = []
        dataAnimationImages = []
        dataAnimationList = {}
        dataPipeLines = []
        dataEquipments = []
        dataCharts = []
        dataGages = []
        dataButtons = []
        dataRulers = []
        dataCheckboxs = []
        dataTexts = []
        dataRects = []
        dataCustom = []
        dataTimePicker = []
        dataTempDistributions = {}
        dataSystemEquipments = []
        dataTemplateImages = []
        dataLequidLevels = []
        dataFix = []
        dataRectangles = []
        dataStraightLine = []
        dataPolygon = []

        # image_id
        image_id_list_project = RedisManager.get_image_id_list_project()
        image_id_list_template = {}

        con.text_factory = bytes
        cu = con.cursor()

        if con != None and cu != None:
            try:

                # 获取模板设备名列表
                templateEquipNameList = []
                cu.execute("select unitproperty07 as templateFileName from list_unit13 where pageid = %s" % pageId)
                objectList = cu.fetchall()
                for object in objectList:
                    fileName = "template.4db"
                    if object[0] != None:
                        fileName = object[0].decode("gbk")
                    templateEquipName = path.splitext(fileName)[0]
                    if templateEquipName not in templateEquipNameList:
                        templateEquipNameList.append(templateEquipName)
                tFrom = datetime.now()
                # Page
                cu.execute(
                    "SELECT width, hight, pagetype,bgcolor1, bgcolor2, bgimg, name, unitproperty04  FROM list_page WHERE id = %s" % (
                        pageId))

                item = cu.fetchall()

                if len(item) > 0:
                    dataPage = {'id': pageId, 'width': item[0][0], 'height': item[0][1],
                                'type': item[0][2].decode('gbk'),
                                'bgColor1': item[0][3], 'bgColor2': item[0][4], 'bgImgId': item[0][5],
                                'name': item[0][6].decode('gbk'),
                                'navJsonConfig': item[0][7].decode('gbk') if item[0][7] else ""}

                tFrom = datetime.now()
                # Pipeline
                cu.execute(
                    "SELECT id, PointList, pipeWidth, style, idlist, layer,  unitproperty01, innerColor, unitproperty03, unitproperty04, logic, unitproperty05 FROM list_line WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    strs = item[1].decode('gbk').replace('(', '').replace(')', '').replace(',', ';').split(';') if item[
                                                                                                                       1] != None else [
                        '0', '0', '0', '0']
                    color = int(item[7]) if item[7] != None else 0
                    # waterShape: 0-矩形；1-圆形
                    try:
                        waterShape = int(item[11].decode("gbk")) if item[11] != None else 0
                    except:
                        waterShape = 0
                    dataPipeLines.append({'id': item[0] if item[0] != None else 0,
                                          'width': item[2] if item[2] != None else 0,
                                          'direction': item[3] if item[3] != None else 0,
                                          'idCom': item[4].decode('gbk') if item[4] != None else '',
                                          'startX': strs[0], 'startY': strs[1], 'endX': strs[2], 'endY': strs[3],
                                          'layer': item[5] if item[5] != None else 0,
                                          'waterType': item[6].decode('gbk') if item[6] != None else '',
                                          'color': {'r': get_r_from_int(color), "g": get_g_from_int(color),
                                                    'b': get_b_from_int(color)},
                                          'denSity': item[8].decode('gbk') if item[8] != None else '',
                                          'speed': item[9].decode('gbk') if item[9] != None else '',
                                          'logic': item[10] if item[10] != None else 0,
                                          'waterShape': waterShape
                                          })

                # line
                strQuery = "SELECT x, y, width, height, layer, id, pageid, unitproperty02, unitproperty03, " \
                           "unitproperty04, unitproperty06, unitproperty07, unitproperty08, unitproperty09 FROM " \
                           "list_unit19 WHERE pageid = %s and unitproperty01='straightLine'" % pageId
                cu.execute(strQuery)
                for item in cu.fetchall():
                    colorBytes = item[7] if item[7] != None else 0
                    dataStraightLine.append({
                        "x0": item[0] if item[0] != None else 0,
                        "y0": item[1] if item[1] != None else 0,
                        "x1": item[2] if item[2] != None else 0,
                        "y1": item[3] if item[3] != None else 0,
                        "layer": item[4] if item[4] != None else 0,
                        "id": item[5] if item[5] != None else 0,
                        "pageid": item[6] if item[6] != None else 0,
                        "color": colorHexToRgb(colorBytes),
                        "lineWidth": int(float(item[8].decode("gbk"))) if item[8] != None else 0,
                        "lineType": int(float(item[9].decode("gbk"))) if item[9] != None else 0,
                        "startType": int(float(item[10].decode("gbk"))) if item[10] != None else 0,
                        "startSize": int(float(item[11].decode("gbk"))) if item[11] != None else 0,
                        "endType": int(float(item[12].decode("gbk"))) if item[12] != None else 0,
                        "endSize": int(float(item[13].decode("gbk"))) if item[13] != None else 0
                    })

                # 多边形
                cu.execute(
                    "SELECT x as coord, width as templatePelId, height as name, layer, id, unitproperty02 as placeHolder, unitproperty03 as templateName, unitproperty06 FROM list_unit19 WHERE pageid = %s and unitproperty01='polygon'" % pageid)
                polys = cu.fetchall()

                # 以模板文件名为键制作模板图元ID字典
                templatePelIdDict = {}
                for object in polys:
                    templateFileName = object[6].decode("gbk") if object[0] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    templatePelId = object[1]
                    if templateFileNameWithoutExt in templatePelIdDict.keys():
                        if templatePelId in templatePelIdDict[templateFileNameWithoutExt]:
                            continue
                        templatePelIdDict[templateFileNameWithoutExt].append(templatePelId)
                    else:
                        templatePelIdDict[templateFileNameWithoutExt] = [templatePelId]

                    image_id_list_template[templateFileName] = RedisManager.get_image_id_list_template(templateFileName)

                # 以模板文件名为键创建模板信息查询字典和text字典
                queryDict = {}
                textQueryDict = {}
                for templateFileNameWithoutExt in templatePelIdDict.keys():
                    templatePelIdList = templatePelIdDict[templateFileNameWithoutExt]

                    clauseTemplatePelIdList = ["page_contain_elements.pageid = {0}".format(pelId) for pelId in
                                               templatePelIdList]
                    clauseAllTextsList = ["pageid = {0}".format(pelId) for pelId in templatePelIdList]

                    strClauseTemplatePelId = " or ".join(clauseTemplatePelIdList)
                    strClauseAllTexts = " or ".join(clauseAllTextsList)

                    strQueryAllNeedTemplate = "SELECT x, y, width, hight, DataComId, pictureid, rotateAngle, " \
                                              "event_content, layer, elementName, bind_content, " \
                                              "page_contain_elements.unitproperty03 AS prop03, page_contain_elements.unitproperty02 AS prop02, " \
                                              "page_contain_elements.pageid as templatePageId FROM " \
                                              "page_contain_elements LEFT JOIN event ON page_contain_elements.elementid = event.id WHERE " + strClauseTemplatePelId

                    strQueryAllTextsInTempalte = "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, " \
                                                 "t.initialValue, t.size, t.font, t.color, t.decimalplace, t.bindstring," \
                                                 " t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.pageid as templatePageId " \
                                                 "FROM list_text t left join list_point p on t.dataComId = p.name WHERE " + strClauseAllTexts

                    queryDict.update({templateFileNameWithoutExt: strQueryAllNeedTemplate})
                    textQueryDict.update({templateFileNameWithoutExt: strQueryAllTextsInTempalte})

                templateDict = {}
                templateTextsDict = {}
                templateDir = path.join(app.static_folder, "template")
                for templateFileNameWithoutExt in queryDict.keys():
                    templatePath = path.join(templateDir, "{0}.4db".format(templateFileNameWithoutExt))

                    if not path.exists(templatePath):
                        continue

                    # 读取模板文件中所有标准设备的信息
                    with SqliteManager(templatePath) as sdb:
                        templates = sdb.exec_query(queryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建模板信息字典
                    for template in templates:
                        templatePageId = template.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateDict.keys():
                            templateDict[key].append(template)
                        else:
                            templateDict[key] = [template]

                    # 读取模板文件中所有text的信息
                    with SqliteManager(templatePath) as sdb:
                        textTemplates = sdb.exec_query(textQueryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建text信息字典
                    for textTemplate in textTemplates:
                        templatePageId = textTemplate.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateTextsDict.keys():
                            templateTextsDict[key].append(textTemplate)
                        else:
                            templateTextsDict[key] = [textTemplate]

                # 开始遍历多边形
                for standEquipIdx, item in enumerate(polys):
                    strNavigation = item[7].decode("gbk") if item[7] else ""
                    templateFileName = item[6].decode("gbk") if item[6] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    template_pel_id = item[1]
                    templateFilePath = path.join(app.static_folder, "template", templateFileName)
                    polyId = item[4] if item[4] != None else 0

                    prefix = "{0}/".format(
                        templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(
                        templateFileNameWithoutExt)

                    if not path.exists(templateFilePath):
                        continue

                    # 以模板文件名+模板图元ID组成的键名
                    templateKey = "{0}_{1}".format(templateFileNameWithoutExt, template_pel_id)

                    placeHolderRaw = ""
                    try:
                        placeHolderRaw = item[5].decode("UTF8") if item[5] != None else ""
                    except Exception as e:
                        strLog = "多边形中占位符解码问题: %s" % e.__str__()
                        print(strLog)
                        logging.error(strLog)

                    # 工作空间中主设备的宽、高、坐标，工作空间：需要插入模板设备的界面
                    coord = item[0].decode("gbk").split(" ")
                    xList = []
                    yList = []
                    for perCoord in coord:
                        xList.append(float(perCoord.split(",")[0]))
                        yList.append(float(perCoord.split(",")[1]))
                    yMax = max(yList)
                    yMin = min(yList)
                    xMax = max(xList)
                    xMin = min(xList)

                    backgroundWidth = xMax - xMin
                    backgroundHeight = yMax - yMin
                    backgroundX = xMin
                    backgroundY = yMin

                    # 生成占位符
                    requestParam = dict()
                    try:
                        for obj in eval(placeHolderRaw):
                            requestParam.update(obj)
                    except Exception as e:
                        strLog = "多边形中占位符字典生成问题: %s" % e.__str__()
                        print(strLog)
                        logging.error(strLog)

                    res = templateDict.get(templateKey, [])
                    pels_width = list()
                    if len(res):
                        pels_width = [pel.get("width") for pel in res]
                    else:
                        strError = 'ERROR in read template id:%s' % (str(templateKey))
                        print(strError)
                        logging.error(strError)
                        continue

                    # 从属图标，如err, enabled, automode图标
                    belongings = list()
                    mainEquip = None
                    for pel in res:
                        if pel.get("width") >= max(pels_width, default=0):
                            mainEquip = pel
                        else:
                            belongings.append(pel)

                    # 主设备旋转角度
                    # rotateAngleMainEquip = int(item[8].decode("gbk")) if item[8] else 0

                    # 计算缩放比例 START 多边形
                    zoomX = 1
                    zoomY = 1
                    mainEquipX = 0
                    mainEquipY = 0
                    if mainEquip:
                        mainEquipX = mainEquip.get("x")
                        mainEquipY = mainEquip.get("y")
                        zoomX = backgroundWidth / mainEquip.get("width")
                        zoomY = backgroundHeight / mainEquip.get("hight")
                    # 计算缩放比例 END

                    # 标准设备的文本内容 START
                    textsList = []
                    textsListFetch = templateTextsDict.get(templateKey, [])
                    for dText in textsListFetch:
                        strPointName = dText.get("dataComId").decode("gbk") if dText.get(
                            "dataComId") is not None else ""
                        strTextContent = dText.get("initialvalue").decode("gbk") if dText.get(
                            "initialvalue") is not None else ""

                        # 替换点名里的占位符
                        if len(strPointName):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strPointName = strPointName.replace(placeHolder, requestParam.get(key))

                        # 替换文本内容里的占位符
                        if len(strTextContent):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strTextContent = strTextContent.replace(placeHolder, requestParam.get(key))

                        textColor = int(dText.get("color")) if dText.get("color") is not None else 0

                        # text坐标换算
                        textX = dText.get("xpos") if dText.get("xpos") is not None else 0
                        textY = dText.get("ypos") if dText.get("ypos") is not None else 0
                        offsetTextX = (textX - mainEquipX) * zoomX
                        offsetTextY = (textY - mainEquipY) * zoomY
                        xPos = backgroundX + offsetTextX
                        yPox = backgroundY + offsetTextY

                        textsList.append({'id': "{0}_{1}".format(dText.get("id"), standEquipIdx) if dText.get(
                            "id") is not None else 0,
                                          'x': xPos,
                                          'y': yPox,
                                          'width': dText.get("width") if dText.get("width") is not None else 0,
                                          'height': dText.get("height") if dText.get("height") is not None else 0,
                                          'idCom': strPointName,
                                          'text': strTextContent,
                                          'fontSize': dText.get("size") if dText.get("size") is not None else 0,
                                          'font': dText.get("font").decode("gbk") if dText.get(
                                              "font") is not None else "",
                                          'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                    'b': get_b_from_int(textColor)},
                                          'decimalplace': dText.get("decimalplace"),
                                          'bindString': dText.get("bindstring").decode("gbk") if dText.get(
                                              "bindstring") is not None else "",
                                          'showMode': dText.get("showMode") if dText.get(
                                              "showMode") is not None else 0,
                                          'rw': dText.get("R_W") if dText.get("R_W") is not None else 0,
                                          'layer': dText.get("layer") if dText.get("layer") is not None else 0,
                                          'align': dText.get("align") if dText.get("align") is not None else 0,
                                          'bindScript': dText.get("unitproperty05").decode("gbk") if dText.get(
                                              "unitproperty05") is not None else "",
                                          "backgroudFrameStyle": dText.get("unitproperty01").decode(
                                              "gbk") if dText.get("unitproperty01") is not None else 0})
                    # 标准设备的文本内容 END

                    # 处理随主设备一起的图标，如enabled, err, automode START
                    childrenList = []
                    belonging_id_preffix = 999999
                    for belongingIndex, belonging in enumerate(belongings):
                        belonging_id = int("{0}{1}".format(belonging_id_preffix - belongingIndex, polyId))
                        belongingX = belonging.get("x") if belonging.get("x") else 0
                        belongingY = belonging.get("y") if belonging.get("y") else 0

                        # 模板设备页面中，从属图标与主设备之间的坐标偏差 乘以 缩放比例
                        offsetX = (belongingX - mainEquipX) * zoomX
                        offsetY = (belongingY - mainEquipY) * zoomY

                        # 工作空间中从属图标的高宽考虑缩放比例
                        width = belonging.get("width") * zoomX if belonging.get("width") else 0
                        height = belonging.get("hight") * zoomY if belonging.get("hight") else 0

                        # 工作空间中从属图标的坐标等于主设备的坐标加坐标偏差
                        x = backgroundX + offsetX
                        y = backgroundY + offsetY

                        # 点名占位符处理
                        point = belonging.get("DataComId").decode("gbk") if belonging.get("DataComId") else ""
                        if len(point):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                point = point.replace(placeHolder, requestParam.get(key))

                        # 图片
                        pictureid = "{0}{1}".format(prefix, belonging.get("pictureid")) if belonging.get("pictureid",
                                                                                                         None) is not None else ""
                        if not pictureid in dataImages:
                            template_image_id_list = image_id_list_template.get(templateFileName)
                            try:
                                if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                    tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                    if is_int_digit(tmp):
                                        if int(tmp) not in template_image_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                            except Exception as ept:
                                logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                            dataImages.append(pictureid)

                        # 从属图标的旋转角度需要与主设备一致
                        # rotateAngle = rotateAngleMainEquip

                        # 图层
                        layer = belonging.get("layer") if belonging.get("layer") else 0

                        # title占位符修改
                        strTitle = belonging.get("elementName").decode("gbk") if belonging.get("elementName") else ""
                        elemName = ""
                        if len(strTitle):
                            elemName = replace_place_holder(strTitle, requestParam)

                        strItem11 = belonging.get("prop02").decode("gbk") if belonging.get("prop02") else ""

                        animationStatus = {}
                        str_item = belonging.get("bind_content").decode('gbk') if belonging.get(
                            "bind_content") != None else ''
                        if str_item != "":
                            temp = str_item.split('|')
                            for strStatus in temp:
                                tempStatus = strStatus.split(',')
                                if len(tempStatus) == 4:
                                    animationStatus.update(
                                        {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                         'frameCount': tempStatus[2],
                                                         'interval': tempStatus[3]}})

                                    imgId = "{0}{1}".format(prefix, tempStatus[1])
                                    if imgId not in dataImages:
                                        template_image_id_list = image_id_list_template.get(templateFileName)
                                        try:
                                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                                tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                                if int(tmp) not in template_image_id_list:
                                                    self.create404ImageFileForTemplateIfNotExist(
                                                        templateFileNameWithoutExt)
                                                    imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                        except Exception as ept:
                                            logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                                        dataImages.append(imgId)

                        strItem13 = belonging.get("prop03").decode("gbk") if belonging.get("prop03") != None else 0

                        # 获取子设备linkInfo
                        try:
                            ChildrenLinkInfoList = belonging.get("event_content").decode("gbk").split(",")
                            if ChildrenLinkInfoList and isinstance(ChildrenLinkInfoList, list):
                                ChildrenLinkInfoList.append('template')  # 区分常规弹窗
                        except:
                            ChildrenLinkInfoList = []

                        childPlaceHolder = {}
                        if len(ChildrenLinkInfoList):
                            childPlaceHolder = requestParam

                        childrenList.append({
                            "id": belonging_id,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "idCom": point,
                            "idPicture": pictureid,
                            "layer": layer,
                            "name": elemName,
                            "isFromAnimation": strItem11 == "0",
                            "animation": animationStatus,
                            "bindType": int(float(strItem13)),
                            "link": ChildrenLinkInfoList[4],  # 子设备link
                            "linkinfo": ChildrenLinkInfoList,  # 子设备linkInfoList
                            "placeHolder": childPlaceHolder
                        })
                    # 处理随主设备一起的图标，如enabled, err, automode END

                    # 处理belongings的动画问题 START
                    for child in childrenList:
                        dictAnimation = child.get("animation")
                        for dictAnimationValue in dictAnimation.values():
                            if int(dictAnimationValue.get("frameCount")) > 1:
                                childAnimationId = dictAnimationValue.get("animationId").replace(prefix, "")
                                with SqliteManager(templateFilePath) as dbm:
                                    str_sql = '''SELECT * FROM lib_animation WHERE id = ?'''
                                    sql_res = dbm.exec_query(str_sql, (childAnimationId,))
                                animationListWithPrefix = ["{0}{1}".format(prefix, itm) for itm in
                                                           sql_res[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update(
                                    {dictAnimationValue.get("animationId"): animationListWithPrefix})
                    # 处理belongings的动画问题 END

                    # 处理主设备 START
                    pictureid = "{0}{1}".format(prefix, mainEquip.get("pictureid")) if mainEquip.get("pictureid",
                                                                                                     None) is not None else ""
                    if not pictureid in dataImages:
                        template_image_id_list = image_id_list_template.get(templateFileName)
                        try:
                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                if int(tmp) not in template_image_id_list:
                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                    pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                        except Exception as ept:
                            logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                        dataImages.append(pictureid)

                    try:
                        LinkInfoList = mainEquip.get("event_content").decode("gbk").split(",")
                        if LinkInfoList and isinstance(LinkInfoList, list):
                            LinkInfoList.append('template')  # 区分常规弹窗
                    except:
                        LinkInfoList = []

                    layer = item[3] if item[3] else 0

                    strItem11 = mainEquip.get("prop02").decode("gbk") if mainEquip.get("prop02") != None else ""

                    animationStatus = {}
                    str_item = mainEquip.get("bind_content").decode('gbk') if mainEquip.get(
                        "bind_content") != None else ''
                    if str_item != "":
                        temp = str_item.split('|')
                        for strStatus in temp:
                            tempStatus = strStatus.split(',')
                            if len(tempStatus) == 4:
                                animationStatus.update(
                                    {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                     'frameCount': tempStatus[2],
                                                     'interval': tempStatus[3]}})

                                imgId = "{0}{1}".format(prefix, tempStatus[1])
                                if imgId not in dataImages:
                                    template_image_id_list = image_id_list_template.get(templateFileName)
                                    try:
                                        if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                            tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                            if int(tmp) not in template_image_id_list:
                                                self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                    except Exception as ept:
                                        logging.error("ERROR in get_plant polygon: %s" % ept.__str__())

                                    dataImages.append(imgId)

                    # title占位符修改
                    strTitle = mainEquip.get("elementName").decode("gbk") if mainEquip.get(
                        "elementName") != None else ""

                    elemName = ""
                    if len(strTitle):
                        elemName = replace_place_holder(strTitle, requestParam)

                    # 点名占位符处理
                    point = mainEquip.get("DataComId").decode("gbk") if mainEquip.get("DataComId") != None else ""
                    if len(point):
                        for key in requestParam.keys():
                            placeHolder = "{%s}" % key
                            point = point.replace(placeHolder, requestParam.get(key))

                    strItem13 = mainEquip.get("prop03").decode("gbk") if mainEquip.get("prop03") != None else 0

                    # 处理主设备 END

                    dataPolygon.append({
                        "id": polyId,
                        "coord": item[0].decode("gbk") if item[0] != None else "",
                        "layer": item[3] if item[3] != None else 0,
                        "idCom": point,
                        "pageid": pageid,
                        "idPicture": pictureid,
                        "link": LinkInfoList[4],
                        "linkinfo": LinkInfoList,
                        "name": elemName,
                        'bindType': int(float(strItem13)),
                        "templatePelId": template_pel_id,
                        "children": childrenList,
                        "templateFileName": templateFileNameWithoutExt,
                        "placeHolder": requestParam,
                        "texts": textsList,
                        "navigation": strNavigation
                    })

                # Custom Image
                strQ = "SELECT elementid, x, y, width, hight, DataComId, pictureid, rotateAngle, bind_content," \
                           "event_content, layer, page_contain_elements.unitproperty02, elementName, " \
                           "page_contain_elements.unitproperty03, page_contain_elements.hideScript, page_contain_elements.unitproperty04 FROM page_contain_elements LEFT JOIN event " \
                           "ON event.id = page_contain_elements.elementid WHERE page_contain_elements.pageid = %s AND event.pageid =%s" % (
                           pageId, pageId)
                cu.execute(strQ)

                # distinct animation ids
                listAnimationIds = []
                listAnimationIds_prefix_removed = []
                templateEquipNameList.append("/")
                items = cu.fetchall()
                for item in items:
                    LinkInfoList = item[9].decode('gbk').split(',') if item[9] != None else []
                    strItem5 = "" if item[5] is None else item[5].decode("gbk")
                    strItem9 = LinkInfoList[4] if len(LinkInfoList) >= 5 else ""
                    strItem11 = "" if item[11] is None else item[11].decode("gbk")
                    strItem12 = "" if item[12] is None else item[12].decode("gbk")
                    strItem8 = "" if item[8] is None else item[8].decode("gbk")
                    nPictureId = 0 if item[6] is None else item[6]
                    hideScript = item[14].decode("gbk") if item[14] != None else None

                    strItem13 = 0
                    if item[13] == None:
                        strItem13 = 0
                    elif isinstance(item[13], bytes):
                        strItem13 = int(float(item[13].decode("gbk")))
                    elif isinstance(item[13], str):
                        strItem13 = int(float(item[13]))
                    if strItem13 not in [0, 1]:
                        strItem13 = 0

                    if isinstance(item[15], str):
                        customName = item[15]
                    elif isinstance(item[15], bytes):
                        customName = item[15].decode("gbk")
                    else:
                        customName = ""

                    try:
                        if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                            if not (nPictureId in image_id_list_project):
                                self.create404ImageFileIfNotExist()
                                nPictureId = -404404404
                    except Exception as e:
                        logging.error('ERROR in get_plant:%s' % (e.__str__()))
                        nPictureId = -404404404

                    if str(nPictureId) not in dataImages:
                        dataImages.append(str(nPictureId))

                    animationStatus = {}
                    strAnimationIdList = []
                    if strItem8 != '':
                        for strStatus in strItem8.split('|'):

                            statusList = strStatus.split(',')
                            if len(statusList) != 4:
                                continue

                            strKey = statusList[0]
                            strAnimationId = statusList[1]
                            frameCount = statusList[2]
                            interval = statusList[3]

                            if strAnimationId not in strAnimationIdList:
                                strAnimationIdList.append(strAnimationId)

                            animationStatus.update({
                                strKey: dict(animationId=strAnimationId, frameCount=frameCount, interval=interval, frameImgIdList=[])
                            })

                            if strAnimationId not in listAnimationIds:
                                listAnimationIds.append(strAnimationId)

                                for templateEquipName in templateEquipNameList:
                                    strAnimationId = strAnimationId.replace(templateEquipName, "")

                                # 移除模板设备名前缀
                                listAnimationIds_prefix_removed.append(strAnimationId)

                            imgId = statusList[1]
                            if not (int(frameCount) == 1 and imgId not in dataImages):
                                continue

                            try:
                                if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                                    if int(imgId) not in image_id_list_project:
                                        self.create404ImageFileIfNotExist()
                                        imgId = -404404404
                            except Exception as e:
                                logging.error('ERROR in get_plant:%s' % (e.__str__()))
                                imgId = -404404404

                            dataImages.append(str(imgId))

                    dFrameImgIdMap, msg = self.getFrameImgIdListOfAnimation(strAnimationIdList)
                    for thing in animationStatus.values():
                        if thing.get("animationId") in dFrameImgIdMap.keys():
                            thing["frameImgIdList"].extend(dFrameImgIdMap.get(thing.get("animationId")))

                    dataEquipments.append({'id': item[0] if item[0] != None else 0,
                                           'x': item[1] if item[1] != None else 0,
                                           'y': item[2] if item[2] != None else 0,
                                           'width': item[3] if item[3] != None else 0,
                                           'height': item[4] if item[4] != None else 0,
                                           "idCom": strItem5,
                                           'idPicture': nPictureId,
                                           'rotate': item[7] if item[7] != None else 0,
                                           'link': strItem9,
                                           'linkinfo': LinkInfoList,
                                           'layer': item[10] if item[10] != None else 0,
                                           'name': strItem12,
                                           'isFromAnimation': strItem11 == '0',
                                           'animation': animationStatus,
                                           'bindType': strItem13,
                                           "hideScript": hideScript,
                                           "customName": customName})

                # listAnimationIds_prefix_removed = [item.replace(strPrefix, "") for item in listAnimationIds]
                cu.execute("SELECT id, animationlist FROM lib_animation WHERE id IN (%s)" % (
                    ','.join(listAnimationIds_prefix_removed)))
                # distinct animation image ids
                for item in cu.fetchall():
                    arrImageIds = item[1].decode('gbk').split(',') if item[1] != None else []
                    dataAnimationList.update({item[0]: arrImageIds})
                    for arrImageId in arrImageIds:
                        if (arrImageId not in dataAnimationImages):
                            dataAnimationImages.append(arrImageId)

                # liquid level:
                cu.execute(
                    "SELECT id, x, y, width, height, layer, unitproperty02, unitproperty03, unitproperty04, unitproperty05, unitproperty06 FROM list_unit06 WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    try:
                        dataLequidLevels.append({'id': item[0] if item[0] != None else 0,
                                                 'x': item[1] if item[1] != None else 0,
                                                 'y': item[2] if item[2] != None else 0,
                                                 'width': item[3] if item[3] != None else 0,
                                                 'height': item[4] if item[4] != None else 0,
                                                 'layer': item[5] if item[5] != None else 0,
                                                 'bindPointName': item[6].decode('gbk') if item[6] != None else '',
                                                 'max': item[7].decode('gbk') if item[7] != None else '',
                                                 'min': item[8].decode('gbk') if item[8] != None else '',
                                                 'maxAlarm': item[9].decode('gbk') if item[9] != None else '',
                                                 'minAlarm': item[10].decode('gbk') if item[10] != None else ''})
                    except:
                        continue

                tFrom = datetime.now()
                # Chart
                cu.execute(
                    "SELECT id, x, y, width, height, update_interval, elementType FROM list_chart WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    dataCharts.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'interval': item[5] if item[5] != None else 0,
                                       'data': [],
                                       'elementType': item[6] if item[6] != None else 0})

                tFrom = datetime.now()
                cu.execute("SELECT id, color1, title, pointname FROM detail_chart WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    for chart in dataCharts:
                        if item[0] != None:
                            if (chart["id"] == item[0]):
                                intColor = int(item[1]) if item[1] != None else 0
                                chart["data"].append({'color': {'r': get_r_from_int(intColor),
                                                                "g": get_g_from_int(intColor),
                                                                'b': get_b_from_int(intColor)},
                                                      'title': item[2].decode('gbk') if item[2] != None else '',
                                                      'pointName': item[3].decode('gbk') if item[3] != None else ''})
                                break

                # Button
                cu.execute("SELECT id, x, y, width, height, comm, over, down, disable, textcontent, link, settingpoint, settingvalue, description, layer, \
                textsize, textcolor, unitproperty01, unitproperty02, unitproperty04, unitproperty05, name, hideScript, sourceType FROM list_button WHERE pageid = %s" % (
                    pageId))
                for item in cu.fetchall():
                    textColor = int(item[16]) if item[16] != None else 0
                    arrRelation = []
                    strRelation = item[17].decode('gbk')
                    strPreCheck = item[21].decode("UTF-8") if item[21] != None else ""

                    dPreCheck = {}
                    try:
                        dPreCheck = json.loads(strPreCheck)
                    except:
                        pass

                    PreCheckScript = dPreCheck.get("PreCheckScript", "")
                    PreCheckScriptDescription = dPreCheck.get("PreCheckScriptDescription", "")

                    if len(strRelation) > 0:
                        arrTemp = strRelation.split(',')
                        for i in range(len(arrTemp)):
                            arrItem = arrTemp[i].split('|')
                            arrRelation.append(
                                {'point': arrItem[0], 'type': arrItem[1], 'value': arrItem[2]})

                    buttonSetValue = None
                    if isinstance(item[12], bytes):  # 设定值是一个字符串语法
                        buttonSetValue = item[12].decode('gbk')
                    else:
                        buttonSetValue = item[12] if item[12] != None else 0

                    hideScript = item[22].decode("gbk") if item[22] != None else None

                    strStyle = ""
                    if isinstance(item[23], bytes):
                        strStyle = item[23].decode("gbk")
                    elif isinstance(item[23], str):
                        strStyle = ""

                    dataButtons.append({'id': item[0] if item[0] != None else 0,
                                        'x': item[1] if item[1] != None else 0,
                                        'y': item[2] if item[2] != None else 0,
                                        'width': item[3] if item[3] != None else 0,
                                        'height': item[4] if item[4] != None else 0,
                                        'comm': item[5] if item[5] != None else 0,
                                        'over': item[6] if item[6] != None else 0,
                                        'down': item[7] if item[7] != None else 0,
                                        'disable': item[8] if item[8] != None else 0,
                                        'text': item[9].decode('gbk') if item[9] != None else '',
                                        'link': item[10] if item[10] != None else 0,
                                        'idCom': item[11].decode('gbk') if item[11] != None else '',
                                        'setValue': buttonSetValue,
                                        'description': item[13].decode('gbk') if item[
                                                                                     13] != None else '',
                                        'layer': item[14] if item[14] != None else 0,
                                        'fontSize': item[15] if item[15] != None else 0,
                                        'fontColor': {'b': get_b_from_int(textColor),
                                                      "g": get_g_from_int(textColor),
                                                      'r': get_r_from_int(textColor)},
                                        'relation': arrRelation,
                                        'relatType': item[18].decode('gbk'),
                                        'downloadEnableCondition': item[19].decode('gbk') if item[19] else '',
                                        'downloadURL': item[20].decode('gbk') if item[20] else '',
                                        "PreCheckScript": PreCheckScript,
                                        "PreCheckScriptDescription": PreCheckScriptDescription,
                                        "hideScript": hideScript,
                                        "style": strStyle})

                    if (item[5] != None and item[5] not in dataImages):
                        dataImages.append(str(item[5]))
                    if (item[6] != None and item[6] not in dataImages):
                        dataImages.append(str(item[6]))
                    if (item[7] != None and item[7] not in dataImages):
                        dataImages.append(str(item[7]))
                    if (item[8] != None and item[8] not in dataImages):
                        dataImages.append(str(item[8]))

                # Text
                tFrom = datetime.now()
                cu.execute(
                    "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, t.initialValue, t.size, t.font, t.color, "
                    "t.decimalplace, t.bindstring, t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.unitproperty04, t.hideScript,"
                    " t.font FROM list_text t left join list_point p on t.dataComId = p.name WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    textColor = int(item[9]) if item[9] != None else 0
                    hideScript = item[19].decode("gbk") if item[19] != None else None

                    dataTexts.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'idCom': item[5].decode('gbk') if item[5] != None else '',
                                      'text': item[6].decode('gbk') if item[6] != None else '',
                                      'fontSize': item[7] if item[7] != None else 0,
                                      'font': item[8].decode("gbk") if item[8] != None else '',
                                      'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                'b': get_b_from_int(textColor)}, 'decimalplace': item[10],
                                      'bindString': item[11].decode("gbk") if item[11] != None else '',
                                      'showMode': item[12] if item[12] != None else 0,
                                      'rw': item[13] if item[13] != None else 0,
                                      'layer': item[14] if item[0] != None else 0,
                                      'align': item[15] if item[15] != None else 0,
                                      'bindScript': item[16].decode("gbk") if item[16] != None else '',
                                      "backgroudFrameStyle": item[17].decode("gbk") if item[17] != None else 0,
                                      "unit": item[18].decode("gbk") if item[18] != None else "",
                                      "hideScript": hideScript})

                # Gage
                tFrom = datetime.now()
                cu.execute(
                    "SELECT ld.id, ld.x, ld.y, ld.width, ld.height, ld.pointname, ld.max, ld.min, lp.pagetype, lp.xposition, lp.yposition, ld.layer, ld.style, ld.main_unit, ld.second_unit FROM list_dashboard ld left join list_page lp on ld.pageid = lp.id WHERE ld.pageid = %s" % (
                        pageId))
                cu.execute(
                    "SELECT ld.id, ld.x, ld.y, ld.width, ld.height, ld.pointname, ld.max, ld.min, lp.pagetype, lp.xposition, lp.yposition, ld.layer, ld.style, ld.main_unit, ld.second_unit FROM list_dashboard ld left join list_page lp on ld.pageid = lp.id WHERE ld.pageid = %s" % (
                        pageId))

                gageTypePathDict = {
                    0: os.path.join("siteinterface", "static", "images", "dial1"),
                    1: os.path.join("siteinterface", "static", "images", "dial2"),
                    2: os.path.join("siteinterface", "static", "images", "dial3")
                }

                for item in cu.fetchall():
                    strPath = gageTypePathDict.get(item[12], None)
                    dataGages.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'idCom': item[5].decode('gbk') if item[5] != None else '',
                                      'max': item[6] if item[6] != None else 0,
                                      'min': item[7] if item[7] != None else 0,
                                      'pagetype': item[8].decode('gbk') if item[8] != None else '',
                                      'xposition': item[9] if item[9] != None else 0,
                                      'yposition': item[10] if item[10] != None else 0,
                                      "layer": item[11] if item[11] != None else 0,
                                      "type": item[12] if item[12] != None else None,
                                      "path": strPath,
                                      "fontColor": item[13] if item[13] != None else 0,
                                      "decimal": item[14] if item[14] != None else 1
                                      })

                # Ruler
                # ---referrences
                tFrom = datetime.now()
                cu.execute("SELECT id, unitproperty02, unitproperty03, unitproperty04, unitproperty05 , unitproperty07 \
                FROM list_unit18 \
                WHERE unitproperty01 = 0 and id in (SELECT id FROM list_unit17 WHERE pageid = %s)" % (pageId))
                dataRulerItems = []
                for item in cu.fetchall():
                    dataRulerItems.append({'id': item[0] if item[0] != None else 0,
                                           'name': item[1].decode('gbk') if item[1] != None else '',
                                           'value': item[2].decode('gbk') if item[2] != None else '',
                                           'idCom': item[3].decode('gbk') if item[3] != None else '',
                                           'link': item[4].decode('gbk') if item[4] != None else '',
                                           'isInUp': item[5].decode('gbk') if item[5] != None else ''})

                # ---level
                tFrom = datetime.now()
                cu.execute("SELECT id, unitproperty02, unitproperty03, unitproperty04 \
                FROM list_unit18 \
                WHERE unitproperty01 = 1 and id in (SELECT id FROM list_unit17 WHERE pageid == %s)" % (pageId))
                levelsItem = []
                levels = []
                colorList = ['#7dbfe0', '#94c84c', '#f0bc7d', '#d17965']
                for item in cu.fetchall():
                    levelsItem.append({'id': item[0] if item[0] != None else 0,
                                       'text': item[1].decode('gbk') if item[1] != None else '',
                                       'max': item[2].decode('gbk') if item[2] != None else '',
                                       'min': item[3].decode('gbk') if item[3] != None else ''})
                if len(levelsItem) != 0:
                    levelsItem.sort(key=lambda x: x['max'])
                    for index in range(len(levelsItem)):
                        l_item = levelsItem[index]
                        levels.append({'color': colorList[index], 'text': l_item['text'], 'min': l_item['min'],
                                       'max': l_item['max']})

                tFrom = datetime.now()
                cu.execute(
                    "SELECT id, x, y, width, height, unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05, unitproperty06 FROM list_unit17 WHERE pageid = %s" % (
                        pageId))
                for item in cu.fetchall():
                    dataTempArrs = []
                    for temp in dataRulerItems:
                        if item[0] != None:
                            if (temp['id'] == item[0]):
                                dataTempArrs.append(temp)
                    dataRulers.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'levels': levels,
                                       'name': item[5].decode('gbk') if item[5] != None else '',
                                       'min': item[7].decode('gbk') if item[7] != None else 0,
                                       'max': item[6].decode('gbk') if item[6] != None else 0,
                                       'mainScale': item[8].decode('gbk') if item[8] != None else '',
                                       'minorScale': item[9].decode('gbk') if item[9] != None else '',
                                       'decimal': item[10].decode('gbk') if item[10] != None else '',
                                       'references': dataTempArrs
                                       })

                # Temp Distribution
                tFrom = datetime.now()
                cu.execute("select lt.id,lt.initialvalue,lt.xpos,lt.ypos,lt.dataComId "
                           "from list_text lt "
                           "where lt.unitproperty02 = 1 and lt.pageid = '%s';" % pageId)
                dataTempDistributions['pageid'] = pageId
                temp_data = []
                temp_point_result = cu.fetchall()
                for item in temp_point_result:
                    temp_data.append({'id': item[0] if item[0] != None else 0,
                                      'value': item[1].decode('gbk') if item[1] != None else '',
                                      'x': item[2] if item[2] != None else 0,
                                      'y': item[3] if item[3] != None else 0,
                                      'idCom': item[4].decode('gbk') if item[4] != None else ''})
                dataTempDistributions['data'] = temp_data

                # @todo 此处查询语句不对，需修改
                tFrom = datetime.now()
                cu.execute(
                    "select x, y, width, height, layer, unitproperty04 from list_unit19 where pageid = '%s' and unitproperty01='planeTempeDistr'" % pageId)
                temp_page_result = cu.fetchone()
                if temp_page_result is not None:
                    dataTempDistributions['x'] = temp_page_result[0]
                    dataTempDistributions['y'] = temp_page_result[1]
                    dataTempDistributions['width'] = temp_page_result[2]
                    dataTempDistributions['height'] = temp_page_result[3]
                    dataTempDistributions['layer'] = temp_page_result[4]

                # Checkbox
                tFrom = datetime.now()
                cu.execute("SELECT id,x,y,width,height,layer,unitproperty01,unitproperty02,unitproperty03,unitproperty04,unitproperty05,unitproperty06,unitproperty07,unitproperty08,unitproperty09,unitproperty10 \
                FROM list_unit07 WHERE pageid = %s" % (pageId))
                for item in cu.fetchall():
                    font_color = item[7].decode('gbk') if item[7] != None else ''
                    text_color = {"r": 255, "g": 255, "b": 255}
                    if font_color:
                        try:
                            text_color = {'r': get_r_from_int(int(font_color)),
                                          'g': get_g_from_int(int(font_color)),
                                          'b': get_b_from_int(int(font_color))}
                        except:
                            pass
                    try:
                        dataCheckboxs.append({'id': item[0] if item[0] != None else 0,
                                              'x': item[1] if item[1] != None else 0,
                                              'y': item[2] if item[2] != None else 0,
                                              'width': item[3] if item[3] != None else 0,
                                              'height': item[4] if item[4] != None else 0,
                                              'layer': item[5] if item[5] != None else 0,
                                              'idCom': item[11].decode('gbk') if item[11] != None else '',
                                              'type': item[6].decode('gbk') if item[6] != None else '',
                                              'fontColor': text_color,
                                              'fontSize': item[8].decode('gbk') if item[8] != None else '',
                                              'setValue': item[9].decode('gbk') if item[9] != None else '',
                                              'unsetValue': item[10].decode('gbk') if item[10] != None else '',
                                              'text': item[12].decode('gbk') if item[12] != None else '',
                                              'idGroup': item[13].decode('gbk') if item[13] != None else '',
                                              'expression': item[14].decode('gbk') if item[14] != None else '',
                                              'desc': item[15].decode('gbk') if item[15] != None else ''})
                    except:
                        pass

                # import pdb;pdb.set_trace()
                # dottedLine
                tFrom = datetime.now()
                cu.execute("SELECT id,x,y,width,height,layer \
                FROM list_unit19 WHERE pageid = %s and unitproperty01='dottedLineFrame'" % (pageId))
                for item in cu.fetchall():
                    dataRects.append({'id': item[0] if item[0] != None else 0,
                                      'x': item[1] if item[1] != None else 0,
                                      'y': item[2] if item[2] != None else 0,
                                      'width': item[3] if item[3] != None else 0,
                                      'height': item[4] if item[4] != None else 0,
                                      'layer': item[5] if item[5] != None else 0})

                # rectangels
                cu.execute("SELECT x, y, width, height, layer, id, pageid, unitproperty02, unitproperty03, "
                           "unitproperty04, unitproperty05, unitproperty06, unitproperty07, unitproperty08, "
                           "unitproperty09, unitproperty10, unitproperty11, unitproperty12, unitproperty13, "
                           "unitproperty14, unitproperty15  FROM list_unit19 WHERE pageid = %s AND unitproperty01 = 'rectangle'" % pageId)

                items = cu.fetchall()
                for item in items:
                    colorBytes = item[7] if item[7] != None else 0
                    strColorBytes = colorBytes.decode("gbk")
                    fFrameTrans = 100
                    try:
                        fFrameTrans = float(strColorBytes.split("#")[2]) * 100
                    except:
                        pass

                    proper04 = int(item[9].decode("gbk")) if item[9] != None else 0
                    fillColorBytes = item[10] if item[10] != None else colorBytes
                    strFillColorBytes = fillColorBytes.decode("gbk")
                    fFillTrans = 100
                    try:
                        fFillTrans = float(strFillColorBytes.split("#")[2]) * 100
                    except:
                        pass

                    proper05 = int(item[11].decode("gbk")) if item[11] != None else 0

                    titleColorBytes = b""
                    titleSize = 0
                    fTitleTrans = 100
                    try:
                        titleColorBytes = bytes(item[15].decode("gbk").split(",")[0], encoding="gbk")
                        titleSize = float(item[15].decode("gbk").split(",")[1])
                        fTitleTrans = float(item[15].decode("gbk").split(",")[0].split("#")[2]) * 100
                    except:
                        pass

                    bodyColorBytes = b""
                    bodySize = 0
                    fBodyTrans = 100
                    try:
                        bodyColorBytes = bytes(item[16].decode("gbk").split(",")[0], encoding="gbk")
                        bodySize = float(item[16].decode("gbk").split(",")[1])
                        fBodyTrans = float(item[16].decode("gbk").split(",")[0].split("#")[2]) * 100
                    except:
                        pass

                    descColorBytes = b""
                    descSize = 0
                    fDescTrans = 100
                    try:
                        descColorBytes = bytes(item[17].decode("gbk").split(",")[0], encoding="gbk")
                        descSize = float(item[17].decode("gbk").split(",")[1])
                        fDescTrans = float(item[17].decode("gbk").split(",")[0].split("#")[2]) * 100
                    except:
                        pass

                    # 加注释单位
                    rectPointList = []
                    pNameList = []
                    imgList = []
                    decimalList = []
                    rectRawList = item[19].decode("gbk").split("|") if item[19] != None else []
                    for nameImg in rectRawList:
                        if nameImg.count(",") == 0:
                            continue

                        strName = nameImg.split(",")[0]
                        strImg = nameImg.split(",")[1]
                        nDecimal = 2
                        try:
                            nDecimal = int(nameImg.split(",")[2])
                        except:
                            pass
                        pNameList.append(strName)
                        imgList.append(strImg)
                        decimalList.append(nDecimal)

                        try:
                            if isinstance(image_id_list_project, list) and len(image_id_list_project) > 0:
                                if int(strImg) not in image_id_list_project:
                                    self.create404ImageFileIfNotExist()
                                    strImg = -404404404
                        except Exception as e:
                            logging.error('ERROR in get_plant:%s' % (e.__str__()))
                            strImg = -404404404

                        if strImg not in dataImages:
                            dataImages.append(strImg)

                    pointInfoDict = self.getPointInfoFromS3db(pNameList)
                    for idx, pName in enumerate(pNameList):
                        strDesc = ""
                        strUnit = ""
                        strSourceType = ""
                        if pointInfoDict.get(pName):
                            strDesc = pointInfoDict.get(pName).get("description")
                            strUnit = pointInfoDict.get(pName).get("unit")
                            strSourceType = pointInfoDict.get(pName).get("sourceType")

                        rectPointList.append(
                            dict(name=pName, img=imgList[idx], desc=strDesc, unit=strUnit, decimal=decimalList[idx],
                                 type=strSourceType))

                    strRectangleTitle = ""
                    if isinstance(item[20], str):
                        strRectangleTitle = item[20]
                    elif isinstance(item[20], bytes):
                        try:
                            strRectangleTitle = item[20].decode("gbk")
                        except:
                            try:
                                strRectangleTitle = item[20].decode("utf8")
                            except:
                                pass

                    dataRectangles.append({
                        "x": item[0] if item[0] != None else 0,
                        "y": item[1] if item[1] != None else 0,
                        "width": item[2] if item[2] != None else 0,
                        "height": item[3] if item[3] != None else 0,
                        "layer": item[4] if item[4] != None else 0,
                        "id": item[5] if item[5] != None else 0,
                        'color': colorHexToRgb(colorBytes),
                        "frameTrans": fFrameTrans,
                        "lineWidth": float(item[8].decode("gbk")) if item[8] != None else 0,
                        "fillOrNot": 1 if proper04 > 0 else 0,
                        "fillColor": colorHexToRgb(fillColorBytes),
                        "fillTrans": fFillTrans,
                        "roundOrNot": 1 if proper05 > 0 else 0,
                        "roundYPox": int(float(item[12].decode("gbk"))) if item[12] != None else 0,
                        "roundXPox": int(float(item[13].decode("gbk"))) if item[13] != None else 0,
                        "rectStyle": int(float(item[14].decode("gbk"))) if item[14] != None else 0,
                        "titleColor": colorHexToRgb(titleColorBytes),
                        "titleTrans": fTitleTrans,
                        "titleSize": titleSize,
                        "bodyColor": colorHexToRgb(bodyColorBytes),
                        "bodyTrans": fBodyTrans,
                        "bodySize": bodySize,
                        "descColor": colorHexToRgb(descColorBytes),
                        "descTrans": fDescTrans,
                        "descSize": descSize,
                        "descOrNot": int(float(item[18].decode("gbk"))) if item[18] != None else 0,
                        "pointList": rectPointList,
                        "title": strRectangleTitle
                    })

                # Common config
                cu.execute("SELECT id,x,y,width,height,layer,unitproperty02 \
                            FROM list_unit19 WHERE pageid = %s and unitproperty01='generalComponent'" % (pageId))
                for item in cu.fetchall():
                    strConfig = ""
                    try:
                        strConfig = item[6].decode("gbk")
                    except:
                        try:
                            strConfig = item[6].decode("utf8")
                        except:
                            pass
                    dataCustom.append({'id': item[0] if item[0] != None else 0,
                                       'x': item[1] if item[1] != None else 0,
                                       'y': item[2] if item[2] != None else 0,
                                       'width': item[3] if item[3] != None else 0,
                                       'height': item[4] if item[4] != None else 0,
                                       'layer': item[5] if item[5] != None else 0,
                                       'config': strConfig})

                # time select
                cu.execute(
                    "SELECT id,x,y,width,height,layer,bindpoint,RW,datatime FROM list_timeselect WHERE pageid = %s and elementtype= 56" % (
                        pageId))
                for item in cu.fetchall():
                    try:
                        dataTimePicker.append({'id': item[0] if item[0] != None else 0,
                                               'x': item[1] if item[1] != None else 0,
                                               'y': item[2] if item[2] != None else 0,
                                               'width': item[3] if item[3] != None else 0,
                                               'height': item[4] if item[4] != None else 0,
                                               'layer': item[5] if item[5] != None else 0,
                                               'bindpoint': item[6].decode('gbk') if item[6] != None else '',
                                               'RW': item[7],
                                               'timeFixed': item[8]})
                    except:
                        continue

                # 标准设备
                tSysEquip = datetime.now()
                tFrom = datetime.now()
                cu.execute(
                    "SELECT pageid, id, x, y, width, height, unitproperty04, unitproperty06, unitproperty01, layer, unitproperty07, unitproperty08, unitproperty09, unitproperty03, unitproperty05, unitproperty10 FROM list_unit13 WHERE pageid = %s and width > 0 and height > 0 and layer > 0" % (
                        pageId))
                items = cu.fetchall()

                # 以模板文件名为键制作模板图元ID字典
                templatePelIdDict = {}
                for object in items:
                    templateFileName = object[10].decode("gbk") if object[10] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    templatePelId = eval(object[6])
                    if templateFileNameWithoutExt in templatePelIdDict.keys():
                        if templatePelId in templatePelIdDict[templateFileNameWithoutExt]:
                            continue
                        templatePelIdDict[templateFileNameWithoutExt].append(templatePelId)
                    else:
                        templatePelIdDict[templateFileNameWithoutExt] = [templatePelId]

                    image_id_list_template[templateFileName] = RedisManager.get_image_id_list_template(templateFileName)

                # 以模板文件名为键创建模板信息查询字典和text字典
                queryDict = {}
                textQueryDict = {}
                for templateFileNameWithoutExt in templatePelIdDict.keys():
                    templatePelIdList = templatePelIdDict[templateFileNameWithoutExt]

                    clauseTemplatePelIdList = ["page_contain_elements.pageid = {0} AND event.pageid={0}".format(pelId)
                                               for pelId in templatePelIdList]
                    clauseAllTextsList = ["pageid = {0}".format(pelId) for pelId in templatePelIdList]

                    strClauseTemplatePelId = " or ".join(clauseTemplatePelIdList)
                    strClauseAllTexts = " or ".join(clauseAllTextsList)

                    strQueryAllNeedTemplate = "SELECT x, y, width, hight, DataComId, pictureid, rotateAngle, " \
                                              "event_content, layer, elementName, bind_content, " \
                                              "page_contain_elements.unitproperty03 AS prop03, page_contain_elements.unitproperty02 AS prop02, " \
                                              "page_contain_elements.pageid as templatePageId FROM " \
                                              "page_contain_elements LEFT JOIN event ON page_contain_elements.elementid = event.id WHERE " + strClauseTemplatePelId

                    strQueryAllTextsInTempalte = "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, " \
                                                 "t.initialValue, t.size, t.font, t.color, t.decimalplace, t.bindstring," \
                                                 " t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.pageid as templatePageId " \
                                                 "FROM list_text t left join list_point p on t.dataComId = p.name WHERE " + strClauseAllTexts

                    queryDict.update({templateFileNameWithoutExt: strQueryAllNeedTemplate})
                    textQueryDict.update({templateFileNameWithoutExt: strQueryAllTextsInTempalte})

                templateDict = {}
                templateTextsDict = {}
                templateDir = path.join(app.static_folder, "template")
                for templateFileNameWithoutExt in queryDict.keys():
                    templatePath = path.join(templateDir, "{0}.4db".format(templateFileNameWithoutExt))

                    if not path.exists(templatePath):
                        continue

                    # 读取模板文件中所有标准设备的信息
                    with SqliteManager(templatePath) as sdb:
                        templates = sdb.exec_query(queryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建模板信息字典
                    for template in templates:
                        templatePageId = template.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateDict.keys():
                            templateDict[key].append(template)
                        else:
                            templateDict[key] = [template]

                    # 读取模板文件中所有text的信息
                    with SqliteManager(templatePath) as sdb:
                        textTemplates = sdb.exec_query(textQueryDict[templateFileNameWithoutExt])

                    # 以模板文件名+模板页面ID为键创建text信息字典
                    for textTemplate in textTemplates:
                        templatePageId = textTemplate.get("templatePageId")
                        key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                        if key in templateTextsDict.keys():
                            templateTextsDict[key].append(textTemplate)
                        else:
                            templateTextsDict[key] = [textTemplate]

                # 开始遍历该页面内的标准设备
                for standEquipIdx, item in enumerate(items):
                    strNavigation = item[12].decode("gbk") if item[12] else ""
                    templateFileName = item[10].decode("gbk") if item[10] != None else "template.4db"
                    templateFileNameWithoutExt = path.splitext(templateFileName)[0]
                    template_pel_id = eval(item[6])
                    templateFilePath = path.join(app.static_folder, "template", templateFileName)

                    nEntranceGroupId = int(item[13].decode("gbk"))
                    stdEquipName = item[14].decode("gbk")

                    if isinstance(item[15], str):
                        customName = item[15]
                    elif isinstance(item[15], bytes):
                        customName = item[15].decode("gbk")
                    else:
                        customName = ""

                    prefix = "{0}/".format(
                        templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(
                        templateFileNameWithoutExt)

                    if not path.exists(templateFilePath):
                        continue

                    # 以模板文件名+模板图元ID组成的键名
                    templateKey = "{0}_{1}".format(templateFileNameWithoutExt, template_pel_id)

                    id = item[1] if item[1] else 0

                    prop06 = item[7].decode("gbk") if item[7] != None else ""
                    if not prop06:
                        logging.error("ERROR in getPlant: no placeholder found in {id} from template {templateName} "
                                      "(pageId of domdb.db: {pageId})".format(id=item[1],
                                                                              templateName=templateFileName,
                                                                              pageId=pageId))
                        continue

                    # 工作空间中主设备的宽、高、坐标，工作空间：需要插入模板设备的界面
                    backgroundWidth = item[4] if item[4] else 0
                    backgroundHeight = item[5] if item[5] else 0
                    backgroundX = item[2]
                    backgroundY = item[3]

                    # 生成placeHolder
                    requestParam = dict()
                    for obj in eval(prop06):
                        requestParam.update(obj)

                    res = templateDict.get(templateKey, [])
                    pels_width = list()
                    if len(res):
                        pels_width = [pel.get("width") for pel in res]
                    else:
                        strError = 'ERROR in read template id:%s' % (str(templateKey))
                        print(strError)
                        logging.error(strError)
                        continue

                    # 从属图标，如err, enabled, automode图标
                    belongings = list()
                    mainEquip = None
                    for pel in res:
                        if pel.get("width") >= max(pels_width, default=0):
                            mainEquip = pel
                        else:
                            belongings.append(pel)

                    # 主设备旋转角度
                    rotateAngleMainEquip = int(item[8].decode("gbk")) if item[8] else 0

                    # 计算缩放比例 START
                    zoomX = 1
                    zoomY = 1
                    mainEquipX = 0
                    mainEquipY = 0
                    if mainEquip:
                        mainEquipX = mainEquip.get("x")
                        mainEquipY = mainEquip.get("y")
                        zoomX = backgroundWidth / mainEquip.get("width")
                        zoomY = backgroundHeight / mainEquip.get("hight")
                    # 计算缩放比例 END

                    # 标准设备的文本内容 START
                    textsList = []
                    textsListFetch = templateTextsDict.get(templateKey, [])
                    for dText in textsListFetch:
                        strPointName = dText.get("dataComId").decode("gbk") if dText.get(
                            "dataComId") is not None else ""
                        strTextContent = dText.get("initialvalue").decode("gbk") if dText.get(
                            "initialvalue") is not None else ""

                        # 替换点名里的占位符
                        if len(strPointName):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strPointName = strPointName.replace(placeHolder, requestParam.get(key))

                        # 替换文本内容里的占位符
                        if len(strTextContent):
                            for key in requestParam.keys():
                                placeHolder = "{%s}" % key
                                strTextContent = strTextContent.replace(placeHolder, requestParam.get(key))

                        textColor = int(dText.get("color")) if dText.get("color") is not None else 0

                        # text坐标换算
                        textX = dText.get("xpos") if dText.get("xpos") is not None else 0
                        textY = dText.get("ypos") if dText.get("ypos") is not None else 0
                        offsetTextX = (textX - mainEquipX) * zoomX
                        offsetTextY = (textY - mainEquipY) * zoomY
                        xPos = backgroundX + offsetTextX
                        yPox = backgroundY + offsetTextY

                        textsList.append({'id': "{0}_{1}".format(dText.get("id"), standEquipIdx) if dText.get(
                            "id") is not None else 0,
                                          'x': xPos,
                                          'y': yPox,
                                          'width': dText.get("width") if dText.get("width") is not None else 0,
                                          'height': dText.get("height") if dText.get("height") is not None else 0,
                                          'idCom': strPointName,
                                          'text': strTextContent,
                                          'fontSize': dText.get("size") if dText.get("size") is not None else 0,
                                          'font': dText.get("font").decode("gbk") if dText.get(
                                              "font") is not None else "",
                                          'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                                                    'b': get_b_from_int(textColor)},
                                          'decimalplace': dText.get("decimalplace"),
                                          'bindString': dText.get("bindstring").decode("gbk") if dText.get(
                                              "bindstring") is not None else "",
                                          'showMode': dText.get("showMode") if dText.get(
                                              "showMode") is not None else 0,
                                          'rw': dText.get("R_W") if dText.get("R_W") is not None else 0,
                                          'layer': dText.get("layer") if dText.get("layer") is not None else 0,
                                          'align': dText.get("align") if dText.get("align") is not None else 0,
                                          'bindScript': dText.get("unitproperty05").decode("gbk") if dText.get(
                                              "unitproperty05") is not None else "",
                                          "backgroudFrameStyle": dText.get("unitproperty01").decode(
                                              "gbk") if dText.get("unitproperty01") is not None else 0})
                    # 标准设备的文本内容 END

                    tFrom = datetime.now()
                    # 处理随主设备一起的图标，如enabled, err, automode START
                    childrenList = list()
                    belonging_id_preffix = 999999
                    for belongingIndex, belonging in enumerate(belongings):
                        belonging_id = int("{0}{1}".format(belonging_id_preffix - belongingIndex, id))
                        belongingX = belonging.get("x") if belonging.get("x") else 0
                        belongingY = belonging.get("y") if belonging.get("y") else 0

                        # 模板设备页面中，从属图标与主设备之间的坐标偏差 乘以 缩放比例
                        offsetX = (belongingX - mainEquipX) * zoomX
                        offsetY = (belongingY - mainEquipY) * zoomY

                        # 工作空间中从属图标的高宽考虑缩放比例
                        width = belonging.get("width") * zoomX if belonging.get("width") else 0
                        height = belonging.get("hight") * zoomY if belonging.get("hight") else 0

                        # 工作空间中从属图标的坐标等于主设备的坐标加坐标偏差
                        x = backgroundX + offsetX
                        y = backgroundY + offsetY

                        # 点名占位符处理
                        point = belonging.get("DataComId").decode("gbk") if belonging.get("DataComId") else ""
                        if len(point):
                            for key in requestParam.keys():
                                if not isinstance(key, str):
                                    continue

                                if not isinstance(requestParam.get(key), str):
                                    continue

                                placeHolder = "{%s}" % key
                                point = point.replace(placeHolder, requestParam.get(key))

                        # 图片
                        pictureid = "{0}{1}".format(prefix, belonging.get("pictureid")) if belonging.get(
                            "pictureid", None) is not None else ""

                        if not pictureid in dataImages:
                            template_image_id_list = image_id_list_template.get(templateFileName)
                            try:
                                if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                    tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                                    if is_int_digit(tmp):
                                        if int(tmp) not in template_image_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                            except Exception as ept:
                                logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                            dataImages.append(pictureid)

                        # 从属图标的旋转角度需要与主设备一致
                        rotateAngle = rotateAngleMainEquip

                        # 图层
                        layer = belonging.get("layer") if belonging.get("layer") else 0

                        # title占位符修改
                        strTitle = belonging.get("elementName").decode("gbk") if belonging.get("elementName") else ""
                        elemName = ""
                        if len(strTitle):
                            elemName = replace_place_holder(strTitle, requestParam)

                        strItem11 = belonging.get("prop02").decode("gbk") if belonging.get("prop02") else ""

                        animationStatus = dict()
                        str_item = belonging.get("bind_content").decode('gbk') if belonging.get(
                            "bind_content") != None else ''
                        if str_item != "":
                            temp = str_item.split('|')
                            for strStatus in temp:
                                tempStatus = strStatus.split(',')
                                if len(tempStatus) == 4:
                                    animationStatus.update(
                                        {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                         'frameCount': tempStatus[2],
                                                         'interval': tempStatus[3]}})

                                    imgId = "{0}{1}".format(prefix, tempStatus[1])

                                    if imgId not in dataImages:
                                        template_image_id_list = image_id_list_template.get(templateFileName)
                                        try:
                                            if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                                tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                                if is_int_digit(tmp):
                                                    if int(tmp) not in template_image_id_list:
                                                        self.create404ImageFileForTemplateIfNotExist(
                                                            templateFileNameWithoutExt)
                                                        imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                        except Exception as ept:
                                            logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                                        dataImages.append(imgId)

                        strItem13 = belonging.get("prop03").decode("gbk") if belonging.get("prop03") != None else 0

                        # 获取子设备linkInfo
                        try:
                            ChildrenLinkInfoList = belonging.get("event_content").decode("gbk").split(",")
                            if ChildrenLinkInfoList and isinstance(ChildrenLinkInfoList, list):
                                ChildrenLinkInfoList.append('template')  # 区分常规弹窗
                            # print(ChildrenLinkInfoList)
                        except:
                            ChildrenLinkInfoList = []

                        childPlaceHolder = {}
                        if len(ChildrenLinkInfoList):
                            childPlaceHolder = requestParam

                        childrenList.append({
                            "id": belonging_id,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "idCom": point,
                            "idPicture": pictureid,
                            "rotateAngle": rotateAngle,
                            "layer": layer,
                            "name": elemName,
                            "isFromAnimation": strItem11 == "0",
                            "animation": animationStatus,
                            "bindType": int(float(strItem13)),
                            "link": ChildrenLinkInfoList[4],  # 子设备link
                            "linkinfo": ChildrenLinkInfoList,  # 子设备linkInfoList
                            "placeHolder": childPlaceHolder
                        })
                    # 处理随主设备一起的图标，如enabled, err, automode END

                    tFrom = datetime.now()
                    # 处理belongings的动画问题 START
                    for child in childrenList:
                        dictAnimation = child.get("animation")
                        for dictAnimationValue in dictAnimation.values():
                            if int(dictAnimationValue.get("frameCount")) > 1:
                                childAnimationId = dictAnimationValue.get("animationId").replace(prefix, "")
                                with SqliteManager(templateFilePath) as dbm:
                                    str_sql = '''SELECT
                                                    *
                                                FROM
                                                    lib_animation
                                                WHERE
                                                    id = ?'''
                                    sql_res = dbm.exec_query(str_sql, (childAnimationId,))
                                animationListWithPrefix = ["{0}{1}".format(prefix, itm) for itm in
                                                           sql_res[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update({
                                    dictAnimationValue.get("animationId"): animationListWithPrefix
                                })
                    # 处理belongings的动画问题 END

                    # 处理主设备 START
                    tFrom = datetime.now()
                    pictureid = "{0}{1}".format(prefix, mainEquip.get("pictureid")) if mainEquip.get(
                        "pictureid", None) != None else ""
                    if not pictureid in dataImages:
                        dataImages.append(pictureid)

                    rotateAngle = int(item[8].decode("gbk")) if item[8] else 0
                    try:
                        LinkInfoList = mainEquip.get("event_content").decode("gbk").split(",")
                        if LinkInfoList and isinstance(LinkInfoList, list):
                            LinkInfoList.append('template')  # 区分常规弹窗
                        # print(LinkInfoList)
                    except:
                        LinkInfoList = []

                    layer = item[9] if item[9] else 0

                    strItem11 = mainEquip.get("prop02").decode("gbk") if mainEquip.get("prop02") != None else ""

                    animationStatus = dict()
                    str_item = mainEquip.get("bind_content").decode('gbk') if mainEquip.get(
                        "bind_content") != None else ''
                    if str_item != "":
                        temp = str_item.split('|')
                        for strStatus in temp:
                            tempStatus = strStatus.split(',')
                            if len(tempStatus) == 4:
                                animationStatus.update(
                                    {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                     'frameCount': tempStatus[2],
                                                     'interval': tempStatus[3]}})

                                imgId = "{0}{1}".format(prefix, tempStatus[1])
                                if imgId not in dataImages:
                                    template_image_id_list = image_id_list_template.get(templateFileName)
                                    try:
                                        if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                            tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                            if is_int_digit(tmp):
                                                if int(tmp) not in template_image_id_list:
                                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                    imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                    except Exception as ept:
                                        logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                                    dataImages.append(imgId)

                    # title占位符修改
                    strTitle = mainEquip.get("elementName").decode("gbk") if mainEquip.get(
                        "elementName") != None else ""

                    elemName = ""
                    if len(strTitle):
                        elemName = replace_place_holder(strTitle, requestParam)

                    # 点名占位符处理
                    point = mainEquip.get("DataComId").decode("gbk") if mainEquip.get("DataComId") != None else ""
                    if len(point):
                        for key in requestParam.keys():
                            placeHolder = "{%s}" % key
                            point = point.replace(placeHolder, requestParam.get(key))

                    strItem13 = mainEquip.get("prop03").decode("gbk") if mainEquip.get("prop03") != None else 0
                    # 处理主设备 END

                    dataSystemEquipments.append({
                        "id": item[1] if item[1] != None else "",
                        "x": item[2] if item[2] != None else 0,
                        "y": item[3] if item[3] != None else 0,
                        "width": item[4] if item[4] != None else 0,
                        "height": item[5] if item[5] != None else 0,
                        "idCom": point,
                        "idPicture": pictureid,
                        "rotateAngle": rotateAngleMainEquip,
                        "link": LinkInfoList[4],
                        "linkinfo": LinkInfoList,
                        "layer": layer,
                        "name": elemName,
                        "isFromAnimation": strItem11 == "0",
                        "animation": animationStatus,
                        'bindType': int(float(strItem13)),
                        "templatePelId": template_pel_id,
                        "placeHolder": requestParam,
                        "children": childrenList,
                        "texts": textsList,
                        "templateFileName": templateFileNameWithoutExt,
                        "navigation": strNavigation,
                        "entranceGroupId": nEntranceGroupId,
                        "templateName": stdEquipName,
                        "customName": customName
                    })

                    tFrom = datetime.now()
                    # 生成dataTemplateImages
                    for equip in dataSystemEquipments:
                        if not str(equip.get("idPicture")) in dataTemplateImages:
                            dataTemplateImages.append(str(equip.get("idPicture")))
                        dictAnimation = equip.get("animation")
                        for value in dictAnimation.values():
                            if not str(value.get("animationId")) in dataTemplateImages:
                                dataTemplateImages.append(str(value.get("animationId")))

                    # 更新animationlist
                    # template_4db = app.config.get("TEMPLATE_DB_FILE_DIR")
                    with SqliteManager(templateFilePath) as sdb:
                        for img in dataTemplateImages:

                            str_sql = '''SELECT
                                            animationlist
                                        FROM
                                            lib_animation
                                        WHERE
                                            id = ?'''
                            aList = sdb.exec_query(str_sql, (img.replace(prefix, ""),))
                            if len(aList):
                                animation_list = ["{0}{1}".format(prefix, item) for item in
                                                  aList[0].get("animationlist").decode("gbk").split(",")]
                                dataAnimationList.update({img: animation_list})

                    # 更新animationList
                    for key in dataAnimationList.keys():
                        for ani in dataAnimationList.get(key):
                            if not ani in dataAnimationImages:
                                dataAnimationImages.append(ani)

            except Exception as e:
                traceback.print_exc()
                logging.error(e.__str__())
            finally:
                if cu is not None:
                    cu.close()
                if con is not None:
                    con.close()

        # 获取报修信息
        tFrom = datetime.now()
        fixList = BEOPDataAccess.getInstance().getAllFixPosInfo(pageId)

        colorDict = {
            0: "green",
            1: "yellow",
            2: "red"
        }

        if fixList is not None and len(fixList):
            for fix in fixList:
                dataFix.append({
                    "fixId": fix.get("fixId"),
                    "x": fix.get("posX"),
                    "y": fix.get("posY"),
                    "width": 32,
                    "height": 32,
                    "visible": fix.get("visible"),
                    "idPicture": "fix/{0}".format(colorDict.get(fix.get("urgent"), "green")),
                    "layer": 9
                })

        dataImages.append("{0}green".format(strPrefixFix))
        dataImages.append("{0}yellow".format(strPrefixFix))
        dataImages.append("{0}red".format(strPrefixFix))

        return {
            'page': dataPage,
            'images': dataImages,
            'animationImages': dataAnimationImages,
            'animationList': dataAnimationList,
            'pipelines': dataPipeLines,
            'equipments': dataEquipments,
            'charts': dataCharts,
            'gages': dataGages,
            'buttons': dataButtons,
            'rulers': dataRulers,
            'checkboxs': dataCheckboxs,
            'texts': dataTexts,
            'rects': dataRects,
            'tempDistributions': dataTempDistributions,
            'customControls': dataCustom,
            'timePickers': dataTimePicker,
            "systemEquipments": dataSystemEquipments,
            "templateImages": dataTemplateImages,
            "liquidLevels": dataLequidLevels,
            "fix": dataFix,
            "rectangles": dataRectangles,
            "straightLine": dataStraightLine,
            "polygons": dataPolygon
        }



    """
    获取二级模板弹窗标准设备信息
    cu: 来自一级模板页面中的游标
    pageId: 一级模板页面ID
    dPlaceHolder: 来自一级模板页面的占位符
    """
    def getSecondaryDialogStandardEquipmentInfo(self, cu, pageId, dPlaceHolder):
        cu.execute("SELECT width, hight FROM list_page WHERE id=%s" % pageId)
        pageSizeInfo = cu.fetchall()
        nWidth = pageSizeInfo[0][0]
        nHeight = pageSizeInfo[0][1]

        lRes = []
        dataImages = []
        dataAnimationList = {}
        cu.execute("SELECT pageid, id, x, y, width, height, unitproperty04, unitproperty06, unitproperty01, layer, unitproperty07, unitproperty08, unitproperty09 FROM list_unit13 WHERE pageid = %s and width > 0 and height > 0 and layer > 0" % (
                    pageId))
        items = cu.fetchall()

        image_id_list_template = {}

        # 以模板文件名为键制作模板图元ID字典
        templatePelIdDict = {}
        for object in items:
            templateFileName = object[10].decode("gbk") if object[10] != None else "template.4db"
            templateFileNameWithoutExt = path.splitext(templateFileName)[0]
            templatePelId = eval(object[6])
            if templateFileNameWithoutExt in templatePelIdDict.keys():
                if templatePelId in templatePelIdDict[templateFileNameWithoutExt]:
                    continue
                templatePelIdDict[templateFileNameWithoutExt].append(templatePelId)
            else:
                templatePelIdDict[templateFileNameWithoutExt] = [templatePelId]

            image_id_list_template[templateFileName] = RedisManager.get_image_id_list_template(templateFileName)

        # 以模板文件名为键创建模板信息查询字典和text字典
        queryDict = {}
        textQueryDict = {}
        for templateFileNameWithoutExt in templatePelIdDict.keys():
            templatePelIdList = templatePelIdDict[templateFileNameWithoutExt]

            clauseTemplatePelIdList = ["page_contain_elements.pageid = {0}".format(pelId) for pelId in
                                       templatePelIdList]
            clauseAllTextsList = ["pageid = {0}".format(pelId) for pelId in templatePelIdList]

            strClauseTemplatePelId = " or ".join(clauseTemplatePelIdList)
            strClauseAllTexts = " or ".join(clauseAllTextsList)

            strQueryAllNeedTemplate = "SELECT x, y, width, hight, DataComId, pictureid, rotateAngle, " \
                                      "event_content, layer, elementName, bind_content, " \
                                      "page_contain_elements.unitproperty03 AS prop03, page_contain_elements.unitproperty02 AS prop02, " \
                                      "page_contain_elements.pageid as templatePageId FROM " \
                                      "page_contain_elements LEFT JOIN event ON page_contain_elements.elementid = event.id WHERE " + strClauseTemplatePelId

            strQueryAllTextsInTempalte = "SELECT t.id, t.xpos, t.ypos, t.width, t.height, t.dataComId, " \
                                         "t.initialValue, t.size, t.font, t.color, t.decimalplace, t.bindstring," \
                                         " t.showMode, p.R_W, layer, t.align, t.unitproperty05, t.unitproperty01, t.pageid as templatePageId " \
                                         "FROM list_text t left join list_point p on t.dataComId = p.name WHERE " + strClauseAllTexts

            queryDict.update({templateFileNameWithoutExt: strQueryAllNeedTemplate})
            textQueryDict.update({templateFileNameWithoutExt: strQueryAllTextsInTempalte})

        templateDict = {}
        templateTextsDict = {}
        templateDir = path.join(app.static_folder, "template")
        for templateFileNameWithoutExt in queryDict.keys():
            templatePath = path.join(templateDir, "{0}.4db".format(templateFileNameWithoutExt))

            if not path.exists(templatePath):
                continue

            # 读取模板文件中所有标准设备的信息
            with SqliteManager(templatePath) as sdb:
                templates = sdb.exec_query(queryDict[templateFileNameWithoutExt])

            # 以模板文件名+模板页面ID为键创建模板信息字典
            for template in templates:
                templatePageId = template.get("templatePageId")
                key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                if key in templateDict.keys():
                    templateDict[key].append(template)
                else:
                    templateDict[key] = [template]

            # 读取模板文件中所有text的信息
            with SqliteManager(templatePath) as sdb:
                textTemplates = sdb.exec_query(textQueryDict[templateFileNameWithoutExt])

            # 以模板文件名+模板页面ID为键创建text信息字典
            for textTemplate in textTemplates:
                templatePageId = textTemplate.get("templatePageId")
                key = "{0}_{1}".format(templateFileNameWithoutExt, templatePageId)
                if key in templateTextsDict.keys():
                    templateTextsDict[key].append(textTemplate)
                else:
                    templateTextsDict[key] = [textTemplate]

        # 开始遍历该页面内的标准设备
        for standEquipIdx, item in enumerate(items):
            strNavigation = item[12].decode("gbk") if item[12] else ""
            templateFileName = item[10].decode("gbk") if item[10] != None else "template.4db"
            templateFileNameWithoutExt = path.splitext(templateFileName)[0]
            template_pel_id = eval(item[6])
            templateFilePath = path.join(app.static_folder, "template", templateFileName)

            prefix = "{0}/".format(
                templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(
                templateFileNameWithoutExt)

            if not path.exists(templateFilePath):
                continue

            # 以模板文件名+模板图元ID组成的键名
            templateKey = "{0}_{1}".format(templateFileNameWithoutExt, template_pel_id)

            id = item[1] if item[1] else 0

            prop06 = item[7].decode("gbk") if item[7] != None else ""
            if not prop06:
                logging.error("ERROR in getPlant: no placeholder found in {id} from template {templateName} "
                              "(pageId of domdb.db: {pageId})".format(id=item[1],
                                                                      templateName=templateFileName,
                                                                      pageId=pageId))
                continue

            # 工作空间中主设备的宽、高、坐标，工作空间：需要插入模板设备的界面
            backgroundWidth = item[4] if item[4] else 0
            backgroundHeight = item[5] if item[5] else 0
            backgroundX = item[2]
            backgroundY = item[3]

            # placeHolder等于一级模板的占位符
            requestParam = dPlaceHolder

            res = templateDict.get(templateKey, [])
            pels_width = list()
            if len(res):
                pels_width = [pel.get("width") for pel in res]
            else:
                strError = 'ERROR in read template id:%s' % (str(templateKey))
                print(strError)
                logging.error(strError)
                continue

            # 从属图标，如err, enabled, automode图标
            belongings = list()
            mainEquip = None
            for pel in res:
                if pel.get("width") >= max(pels_width, default=0):
                    mainEquip = pel
                else:
                    belongings.append(pel)

            # 主设备旋转角度
            rotateAngleMainEquip = int(item[8].decode("gbk")) if item[8] else 0

            # 计算缩放比例 START
            zoomX = 1
            zoomY = 1
            mainEquipX = 0
            mainEquipY = 0
            if mainEquip:
                mainEquipX = mainEquip.get("x")
                mainEquipY = mainEquip.get("y")
                zoomX = backgroundWidth / mainEquip.get("width")
                zoomY = backgroundHeight / mainEquip.get("hight")
            # 计算缩放比例 END

            # 标准设备的文本内容 START
            textsList = []
            textsListFetch = templateTextsDict.get(templateKey, [])
            for dText in textsListFetch:
                strPointName = dText.get("dataComId").decode("gbk") if dText.get("dataComId") is not None else ""
                strTextContent = dText.get("initialvalue").decode("gbk") if dText.get(
                    "initialvalue") is not None else ""

                # 替换点名里的占位符
                if len(strPointName):
                    for key in requestParam.keys():
                        placeHolder = "{%s}" % key
                        strPointName = strPointName.replace(placeHolder, requestParam.get(key))

                # 替换文本内容里的占位符
                if len(strTextContent):
                    for key in requestParam.keys():
                        placeHolder = "{%s}" % key
                        strTextContent = strTextContent.replace(placeHolder, requestParam.get(key))

                textColor = int(dText.get("color")) if dText.get("color") is not None else 0

                # text坐标换算
                textX = dText.get("xpos") if dText.get("xpos") is not None else 0
                textY = dText.get("ypos") if dText.get("ypos") is not None else 0
                offsetTextX = (textX - mainEquipX) * zoomX
                offsetTextY = (textY - mainEquipY) * zoomY
                xPos = backgroundX + offsetTextX
                yPox = backgroundY + offsetTextY

                textsList.append(
                    {'id': "{0}_{1}".format(dText.get("id"), standEquipIdx) if dText.get("id") is not None else 0,
                     'x': xPos,
                     'y': yPox,
                     'width': dText.get("width") if dText.get("width") is not None else 0,
                     'height': dText.get("height") if dText.get("height") is not None else 0,
                     'idCom': strPointName,
                     'text': strTextContent,
                     'fontSize': dText.get("size") if dText.get("size") is not None else 0,
                     'font': dText.get("font").decode("gbk") if dText.get(
                         "font") is not None else "",
                     'color': {'r': get_r_from_int(textColor), "g": get_g_from_int(textColor),
                               'b': get_b_from_int(textColor)},
                     'decimalplace': dText.get("decimalplace"),
                     'bindString': dText.get("bindstring").decode("gbk") if dText.get(
                         "bindstring") is not None else "",
                     'showMode': dText.get("showMode") if dText.get(
                         "showMode") is not None else 0,
                     'rw': dText.get("R_W") if dText.get("R_W") is not None else 0,
                     'layer': dText.get("layer") if dText.get("layer") is not None else 0,
                     'align': dText.get("align") if dText.get("align") is not None else 0,
                     'bindScript': dText.get("unitproperty05").decode("gbk") if dText.get(
                         "unitproperty05") is not None else "",
                     "backgroudFrameStyle": dText.get("unitproperty01").decode(
                         "gbk") if dText.get("unitproperty01") is not None else 0})
            # 标准设备的文本内容 END

            tFrom = datetime.now()
            # 处理随主设备一起的图标，如enabled, err, automode START
            childrenList = list()
            belonging_id_preffix = 999999
            for belongingIndex, belonging in enumerate(belongings):
                belonging_id = int("{0}{1}".format(belonging_id_preffix - belongingIndex, id))
                belongingX = belonging.get("x") if belonging.get("x") else 0
                belongingY = belonging.get("y") if belonging.get("y") else 0

                # 模板设备页面中，从属图标与主设备之间的坐标偏差 乘以 缩放比例
                offsetX = (belongingX - mainEquipX) * zoomX
                offsetY = (belongingY - mainEquipY) * zoomY

                # 工作空间中从属图标的高宽考虑缩放比例
                width = belonging.get("width") * zoomX if belonging.get("width") else 0
                height = belonging.get("hight") * zoomY if belonging.get("hight") else 0

                # 工作空间中从属图标的坐标等于主设备的坐标加坐标偏差
                x = backgroundX + offsetX
                y = backgroundY + offsetY

                # 点名占位符处理
                point = belonging.get("DataComId").decode("gbk") if belonging.get("DataComId") else ""
                if len(point):
                    for key in requestParam.keys():
                        placeHolder = "{%s}" % key
                        point = point.replace(placeHolder, requestParam.get(key))

                # 图片
                pictureid = "{0}{1}".format(prefix, belonging.get("pictureid")) if belonging.get(
                    "pictureid") else ""

                if not pictureid in dataImages:
                    template_image_id_list = image_id_list_template.get(templateFileName)
                    try:
                        if isinstance(template_image_id_list, list) and len(template_image_id_list):
                            tmp = pictureid.replace("{0}/".format(templateFileNameWithoutExt), "")
                            if is_int_digit(tmp):
                                if int(tmp) not in template_image_id_list:
                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                    pictureid = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                    except Exception as ept:
                        logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                    dataImages.append(pictureid)

                # 从属图标的旋转角度需要与主设备一致
                rotateAngle = rotateAngleMainEquip

                # 图层
                layer = belonging.get("layer") if belonging.get("layer") else 0

                # title占位符修改
                strTitle = belonging.get("elementName").decode("gbk") if belonging.get("elementName") else ""
                elemName = ""
                if len(strTitle):
                    elemName = replace_place_holder(strTitle, requestParam)

                strItem11 = belonging.get("prop02").decode("gbk") if belonging.get("prop02") else ""

                animationStatus = dict()
                str_item = belonging.get("bind_content").decode('gbk') if belonging.get(
                    "bind_content") != None else ''
                if str_item != "":
                    temp = str_item.split('|')
                    for strStatus in temp:
                        tempStatus = strStatus.split(',')
                        if len(tempStatus) == 4:
                            animationStatus.update(
                                {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                                 'frameCount': tempStatus[2],
                                                 'interval': tempStatus[3]}})

                            imgId = "{0}{1}".format(prefix, tempStatus[1])

                            if imgId not in dataImages:
                                template_image_id_list = image_id_list_template.get(templateFileName)
                                try:
                                    if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                        tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                        if is_int_digit(tmp):
                                            if int(tmp) not in template_image_id_list:
                                                self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                                imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                                except Exception as ept:
                                    logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                                dataImages.append(imgId)

                strItem13 = belonging.get("prop03").decode("gbk") if belonging.get("prop03") != None else 0

                # 获取子设备linkInfo
                try:
                    ChildrenLinkInfoList = belonging.get("event_content").decode("gbk").split(",")
                    if ChildrenLinkInfoList and isinstance(ChildrenLinkInfoList, list):
                        ChildrenLinkInfoList.append('template')  # 区分常规弹窗
                    # print(ChildrenLinkInfoList)
                except:
                    ChildrenLinkInfoList = []

                childPlaceHolder = {}
                if len(ChildrenLinkInfoList):
                    childPlaceHolder = requestParam

                childrenList.append({
                    "id": belonging_id,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "idCom": point,
                    "idPicture": pictureid,
                    "rotateAngle": rotateAngle,
                    "layer": layer,
                    "name": elemName,
                    "isFromAnimation": strItem11 == "0",
                    "animation": animationStatus,
                    "bindType": int(float(strItem13)),
                    "link": ChildrenLinkInfoList[4],  # 子设备link
                    "linkinfo": ChildrenLinkInfoList,  # 子设备linkInfoList
                    "placeHolder": childPlaceHolder
                })
            # 处理随主设备一起的图标，如enabled, err, automode END

            tFrom = datetime.now()
            # 处理belongings的动画问题 START
            for child in childrenList:
                dictAnimation = child.get("animation")
                for dictAnimationValue in dictAnimation.values():
                    if int(dictAnimationValue.get("frameCount")) > 1:
                        childAnimationId = dictAnimationValue.get("animationId").replace(prefix, "")
                        with SqliteManager(templateFilePath) as dbm:
                            str_sql = '''SELECT
                                                            *
                                                        FROM
                                                            lib_animation
                                                        WHERE
                                                            id = ?'''
                            sql_res = dbm.exec_query(str_sql, (childAnimationId,))
                        animationListWithPrefix = ["{0}{1}".format(prefix, itm) for itm in
                                                   sql_res[0].get("animationlist").decode("gbk").split(",")]
                        dataAnimationList.update({
                            dictAnimationValue.get("animationId"): animationListWithPrefix
                        })
            # 处理belongings的动画问题 END

            # 处理主设备 START
            tFrom = datetime.now()
            pictureid = "{0}{1}".format(prefix, mainEquip.get("pictureid")) if mainEquip.get(
                "pictureid") != None else ""
            if not pictureid in dataImages:
                dataImages.append(pictureid)

            rotateAngle = int(item[8].decode("gbk")) if item[8] else 0
            try:
                LinkInfoList = mainEquip.get("event_content").decode("gbk").split(",")
                if LinkInfoList and isinstance(LinkInfoList, list):
                    LinkInfoList.append('template')  # 区分常规弹窗
                # print(LinkInfoList)
            except:
                LinkInfoList = []

            layer = item[9] if item[9] else 0

            strItem11 = mainEquip.get("prop02").decode("gbk") if mainEquip.get("prop02") != None else ""

            animationStatus = dict()
            str_item = mainEquip.get("bind_content").decode('gbk') if mainEquip.get(
                "bind_content") != None else ''
            if str_item != "":
                temp = str_item.split('|')
                for strStatus in temp:
                    tempStatus = strStatus.split(',')
                    if len(tempStatus) == 4:
                        animationStatus.update(
                            {tempStatus[0]: {'animationId': "{0}{1}".format(prefix, tempStatus[1]),
                                             'frameCount': tempStatus[2],
                                             'interval': tempStatus[3]}})

                        imgId = "{0}{1}".format(prefix, tempStatus[1])
                        if imgId not in dataImages:
                            template_image_id_list = image_id_list_template.get(templateFileName)
                            try:
                                if isinstance(template_image_id_list, list) and len(template_image_id_list):
                                    tmp = imgId.replace("{0}/".format(templateFileNameWithoutExt), "")
                                    if is_int_digit(tmp):
                                        if int(tmp) not in template_image_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            imgId = "{0}/{1}".format(templateFileNameWithoutExt, -404404404)
                            except Exception as ept:
                                logging.error("ERROR in get_plant system equipment: %s" % ept.__str__())

                            dataImages.append(imgId)

            # title占位符修改
            strTitle = mainEquip.get("elementName").decode("gbk") if mainEquip.get("elementName") != None else ""

            elemName = ""
            if len(strTitle):
                elemName = replace_place_holder(strTitle, requestParam)

            # 点名占位符处理
            point = mainEquip.get("DataComId").decode("gbk") if mainEquip.get("DataComId") != None else ""
            if len(point):
                for key in requestParam.keys():
                    placeHolder = "{%s}" % key
                    point = point.replace(placeHolder, requestParam.get(key))

            strItem13 = mainEquip.get("prop03").decode("gbk") if mainEquip.get("prop03") != None else 0
            # 处理主设备 END

            lRes.append({
                "id": item[1] if item[1] != None else "",
                "x": item[2] if item[2] != None else 0,
                "y": item[3] if item[3] != None else 0,
                "width": item[4] if item[4] != None else 0,
                "height": item[5] if item[5] != None else 0,
                "idCom": point,
                "idPicture": pictureid,
                "rotateAngle": rotateAngleMainEquip,
                "link": LinkInfoList[4],
                "linkinfo": LinkInfoList,
                "layer": layer,
                "name": elemName,
                "isFromAnimation": strItem11 == "0",
                "animation": animationStatus,
                'bindType': int(float(strItem13)),
                "templatePelId": template_pel_id,
                "placeHolder": requestParam,
                "children": childrenList,
                "texts": textsList,
                "templateFileName": templateFileNameWithoutExt,
                "navigation": strNavigation
            })

        return dict(infoList=lRes, imageList=dataImages, animationList=dataAnimationList)


    """
    pageId: 一级模板页面ID
    templateFileNameWithoutExt: 一级模板文件名
    """
    def getSystemEquipmentPage(self, pageId, dictParam, templateFileNameWithoutExt):
        dataButtons = list()
        dataTexts = list()
        dataImages = list()
        dataEquipments = list()
        dataAnimationImages = list()
        dataAnimationList = dict()
        dataTimePickers = list()
        dataRulers = list()
        dataPipelines = list()
        dataCharts = list()
        dataPage = dict()
        dataTempDistributions = dict()
        dataGages = list()
        dataRects = list()
        dataCustomControls = list()
        dataCheckboxs = list()
        dataRectangles = []
        dataSystemEquipments = []

        dRealtimeDataMap = RedisManager.get_realtime_data()

        # 所有点信息字典
        allPointInfo = None

        domdb_4db = ''
        template_4db = ''
        strPrefix = "{0}/".format(templateFileNameWithoutExt) if templateFileNameWithoutExt == "template" else "template/{0}/".format(templateFileNameWithoutExt)

        templateFileName = "{0}.4db".format(templateFileNameWithoutExt)
        img_id_list = RedisManager.get_image_id_list_template(templateFileName)


        if not app.config.get("USE_4DB_FILE_FORMAT"):
            return []

        if not app.config.get("TEMPLATE_DB_FILE_DIR"):
            return []

        domdb_4db = app.config.get("USE_4DB_NAME")
        TEMPLATE_DB_FILE_DIR = app.config.get("TEMPLATE_DB_FILE_DIR")
        template_4db = TEMPLATE_DB_FILE_DIR

        if templateFileNameWithoutExt != "template":
            template_4db = os.path.join(os.path.dirname(TEMPLATE_DB_FILE_DIR), "{0}.4db".format(templateFileNameWithoutExt))

        if not template_4db:
            return []

        if not domdb_4db:
            return []

        con = self.connect_readonly(template_4db)
        con.text_factory = bytes
        cu = con.cursor()
        if con == None or cu == None:
            return []

        try:
            # Buttons
            strQuery = "SELECT id, x, y, width, height, comm, over, down, disable, textcontent, link, settingpoint, " \
                       "settingvalue, description, layer, textsize, textcolor, unitproperty01 AS prop01, unitproperty02 " \
                       "AS prop02, unitproperty04 AS prop04, unitproperty05 AS prop05, name, hideScript FROM list_button " \
                       "WHERE pageid = %s" % pageId

            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            buttons = []
            for item in fetchAll:
                button = {}
                button["id"] = item[0]
                button["x"] = item[1]
                button["y"] = item[2]
                button["width"] = item[3]
                button["height"] = item[4]
                button["comm"] = item[5]
                button["over"] = item[6]
                button["down"] = item[7]
                button["disable"] = item[8]
                button["textcontent"] = item[9]
                button["link"] = item[10]
                button["settingpoint"] = item[11]

                if isinstance(item[12], bytes):
                    try:
                        strSettingValue = item[12].decode("gbk")
                    except:
                        strSettingValue = item[12].decode("UTF8")
                elif isinstance(item[12], str):
                    strSettingValue = item[12]
                elif item[12] == None:
                    strSettingValue = ""
                elif isinstance(item[12], int) or isinstance(item[12], float):
                    strSettingValue = str(item[12])
                else:
                    strSettingValue = ""

                strSettingValue = replace_place_holder(strSettingValue, dictParam)
                strSettingValueSplit = strSettingValue.split(",")
                strSettingValueSplitProc = []
                for obj in strSettingValueSplit:
                    if re.match(r"^<%[0-9a-zA-Z_]*%>$", obj):
                        setValuePtNm = obj.replace("<%", "").replace("%>", "")
                        setValue = dRealtimeDataMap.get(setValuePtNm, "")
                    else:
                        setValue = obj
                    strSettingValueSplitProc.append(str(setValue))

                button["settingvalue"] = ",".join(strSettingValueSplitProc)

                button["description"] = item[13]
                button["layer"] = item[14]
                button["textsize"] = item[15]
                button["textcolor"] = item[16]
                button["prop01"] = item[17]
                button["prop02"] = item[18]
                button["prop04"] = item[19]
                button["prop05"] = item[20]
                button["strPreCheck"] = item[21].decode("UTF-8") if item[21] != None else ""
                button["hideScript"] = item[22].decode("gbk") if item[22] != None else None
                buttons.append(button)

            for button in buttons:
                point = button.get("settingpoint").decode("gbk") if button.get("settingpoint") != None else ""
                description = button.get("description").decode("gbk") if button.get("description") is not None else ""
                comm = "{0}{1}".format(strPrefix, button.get("comm")) if button.get("comm") is not None else ""
                over = "{0}{1}".format(strPrefix, button.get("over")) if button.get("over") is not None else ""
                down = "{0}{1}".format(strPrefix, button.get("down")) if button.get("down") is not None else ""
                disable = "{0}{1}".format(strPrefix, button.get("disable")) if button.get("disable") is not None else ""
                strPreCheck = button.get("strPreCheck", "")
                

                dPreCheck = {}
                try:
                    dPreCheck = json.loads(strPreCheck)
                except:
                    pass

                PreCheckScript = dPreCheck.get("PreCheckScript", "")
                PreCheckScriptDescription = dPreCheck.get("PreCheckScriptDescription", "")

                PreCheckScriptProc = replace_place_holder(PreCheckScript, dictParam)
                PreCheckScriptDescriptionProc = replace_place_holder(PreCheckScriptDescription, dictParam)

                # 字体颜色处理
                text_color = button.get("textcolor")
                font_color = dict()
                if text_color is not None:
                    font_color = {'b': get_b_from_int(text_color),
                                  'g': get_g_from_int(text_color),
                                  'r': get_r_from_int(text_color)}

                # 处理relation
                relation = list()
                prop01 = button.get("prop01").decode("gbk")
                if len(prop01):
                    for obj in prop01.split(","):
                        sub_obj = obj.split("|")
                        relation.append({"point": replace_place_holder(sub_obj[0], dictParam), "type": sub_obj[1],
                                         "value": sub_obj[2]})

                # 隐藏脚本占位符替换
                hideScriptContent = button["hideScript"]
                if isinstance(hideScriptContent, str):
                    hideScriptContent = replace_place_holder(hideScriptContent, dictParam)

                if isinstance(hideScriptContent, str):
                    if len(hideScriptContent):
                        if allPointInfo == None:
                            allPointInfo = RedisManager.get_4db_points_info()

                        if isinstance(allPointInfo, dict):
                            if hideScriptContent not in allPointInfo.keys():
                                continue

                dataButtons.append({
                    "id": button.get("id") if button.get("id") != None else 0,
                    "x": button.get("x") if button.get("x") != None else 0,
                    "y": button.get("y") if button.get("y") != None else 0,
                    "width": button.get("width") if button.get("width") != None else 0,
                    "height": button.get("height") if button.get("height") != None else 0,
                    "comm": comm,
                    "over": over,
                    "down": down,
                    "disable": disable,
                    "text": button.get("textcontent").decode("gbk").replace(" ", "") if button.get(
                        "textcontent") != None else "",
                    "link": button.get("link") if button.get("link") != None else 0,
                    "idCom": replace_place_holder(point, dictParam),
                    "setValue": button.get("settingvalue") if button.get("settingvalue") != None else 0,
                    "description": replace_place_holder(description, dictParam),
                    "layer": button.get("layer") if button.get("layer") != None else 0,
                    "fontSize": button.get("textsize") if button.get("textsize") != None else 0,
                    "fontColor": font_color,
                    "relation": relation,
                    "relatType": button.get("prop02").decode("gbk") if button.get("prop02") != None else "",
                    "downloadEnableCondition": button.get("prop04").decode("gbk") if button.get(
                        "prop04") != None else "",
                    "downloadURL": button.get("prop05").decode("gbk") if button.get("prop05") != None else "",
                    "PreCheckScript": PreCheckScriptProc,
                    "PreCheckScriptDescription": PreCheckScriptDescriptionProc
                })

                for image in [button.get("comm"), button.get("over"), button.get("down"), button.get("disable")]:
                    if image is not None and image not in dataImages:
                        try:
                            if isinstance(img_id_list, list) and len(img_id_list):
                                if image not in img_id_list:
                                    self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                    image = -404404404
                        except Exception as ept:
                            logging.error("ERROR in getSystemEquipmentPage: %s" % ept.__str__())

                        dataImages.append("{0}{1}".format(strPrefix, str(image)))

            # Texts
            strQuery = "SELECT lt.id AS id, lt.xpos AS xpos, lt.ypos AS ypos, lt.width AS width, lt.height AS height, " \
                       "lt.dataComId AS dataComId, lt.initialvalue AS strText, lt.size AS fontSize, lt.font AS font, " \
                       "lt.color AS color, lt.decimalplace AS decimalPlace, lt.bindstring AS bindString, lt.showMode AS" \
                       " showMode, lp.R_W AS R_W, lt.layer AS layer, lt.align AS align, lt.unitproperty05 AS porp05, lt.unitproperty01 AS prop01, lt.hideScript AS hideScript FROM " \
                       "list_text lt LEFT JOIN list_point lp ON lt.dataComId = lp.name WHERE pageid = %s" % pageId

            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            texts = []
            for item in fetchAll:
                text = {}
                text["id"] = item[0]
                text["xpos"] = item[1]
                text["ypos"] = item[2]
                text["width"] = item[3]
                text["height"] = item[4]
                text["dataComId"] = item[5]
                text["strText"] = item[6]
                text["fontSize"] = item[7]
                text["font"] = item[8]
                text["color"] = item[9]
                text["decimalPlace"] = item[10]
                text["bindString"] = item[11]
                text["showMode"] = item[12]
                text["R_W"] = item[13]
                text["layer"] = item[14]
                text["align"] = item[15]
                text["porp05"] = item[16]
                text["prop01"] = item[17]
                text["hideScript"] = item[18].decode("gbk") if item[18] != None else None
                texts.append(text)

            for text in texts:
                # 点名占位符处理
                point = text.get("dataComId").decode("gbk") if text.get("dataComId") != None else ""
                if len(point):
                    for key in dictParam.keys():
                        placeHolder = "{%s}" % key
                        point = point.replace(placeHolder, dictParam.get(key))

                # 处理绑了点的text的读写属性
                R_W = 0
                if len(point):
                    try:
                        conn = self.connect_readonly(domdb_4db)
                        conn.text_factory = bytes
                        cursor = conn.cursor()

                        strQuery = "SELECT R_W FROM list_point WHERE name = '%s'" % point
                        cursor.execute(strQuery)
                        pointFetch = cursor.fetchall()
                        rwList = []
                        for item in pointFetch:
                            rwDict = {}
                            rwDict["R_W"] = item[0]
                            rwList.append(rwDict)

                        R_W = rwList[0]["R_W"]
                    except:
                        pass

                # text内容占位符处理
                textContent = text.get("strText").decode("gbk") if text.get("strText") != None else ""
                if len(textContent):
                    for key in dictParam.keys():
                        placeHolder = "{%s}" % key
                        textContent = textContent.replace(placeHolder, dictParam.get(key))

                # 字体颜色处理
                text_color = text.get("color")
                if text_color is not None:
                    font_color = {'r': get_r_from_int(text_color.decode("gbk")),
                                  'g': get_g_from_int(text_color.decode("gbk")),
                                  'b': get_b_from_int(text_color.decode("gbk"))}
                else:
                    font_color = dict()

                decimal = 0
                if text.get("decimalPlace"):
                    decimal = text.get("decimalPlace")

                # 隐藏脚本占位符替换
                hideScriptContent = text["hideScript"]
                if isinstance(hideScriptContent, str):
                    for key in dictParam.keys():
                        placeHolder = "{%s}" % key
                        hideScriptContent = hideScriptContent.replace(placeHolder, dictParam.get(key))

                if isinstance(hideScriptContent, str):
                    if len(hideScriptContent):
                        if allPointInfo == None:
                            allPointInfo = RedisManager.get_4db_points_info()

                        if isinstance(allPointInfo, dict):
                            if hideScriptContent not in allPointInfo.keys():
                                continue

                dataTexts.append({
                    "id": text.get("id") if text.get("id") != None else 0,
                    "x": text.get("xpos") if text.get("xpos") != None else 0,
                    "y": text.get("ypos") if text.get("ypos") != None else 0,
                    "width": text.get("width") if text.get("width") != None else 0,
                    "height": text.get("height") if text.get("height") != None else 0,
                    "idCom": point,
                    "text": textContent,
                    "fontSize": text.get("fontSize") if text.get("fontSize") != None else 0,
                    "font": text.get("font").decode("gbk") if text.get("font") != None else "",
                    "color": font_color,
                    "bindString": text.get("bindString").decode("gbk") if text.get("bindString") != None else "",
                    "showMode": text.get("showMode") if text.get("showMode") != None else 0,
                    "rw": R_W,
                    "layer": text.get("layer") if text.get("layer") != None else 0,
                    "align": text.get("align") if text.get("align") != None else 0,
                    "bindScript": text.get("porp05").decode("gbk") if text.get("porp05") != None else "",
                    "decimalplace": decimal,
                    "backgroudFrameStyle": text.get("prop01").decode("gbk")
                })

            # Images & equipments
            strQuery = "SELECT pce.elementid AS elementid, pce.x AS x, pce.y AS y, pce.width AS width, pce.hight AS " \
                       "height, pce.DataComId AS idCom, pce.pictureid AS pictureId, pce.rotateAngle AS rotateAngle, " \
                       "et.bind_content AS bindContent, et.event_content AS eventContent, pce.layer AS layer, " \
                       "pce.unitproperty02 AS prop02, pce.elementName AS elemName, pce.unitproperty03 AS prop03, hideScript " \
                       "FROM page_contain_elements pce LEFT JOIN event et ON pce.elementid = et.id WHERE pce.pageid = %s" % pageId

            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            imgs = []
            for item in fetchAll:
                img = {}
                img["elementid"] = item[0]
                img["x"] = item[1]
                img["y"] = item[2]
                img["width"] = item[3]
                img["height"] = item[4]
                img["idCom"] = item[5]
                img["pictureId"] = item[6]
                img["rotateAngle"] = item[7]
                img["bindContent"] = item[8]
                img["eventContent"] = item[9]
                img["layer"] = item[10]
                img["prop02"] = item[11]
                img["elemName"] = item[12]
                img["prop03"] = item[13]
                img["hideScript"] = item[14].decode("gbk") if item[14] != None else None
                imgs.append(img)

            listAnimationIds = list()
            for img in imgs:
                # 点名占位符处理
                point = img.get("idCom").decode("gbk") if img.get("idCom") is not None else ""
                idPicture = "{0}{1}".format(strPrefix, img.get("pictureId")) if img.get("pictureId") is not None else ""

                animationStatus = dict()
                bindContent = img.get("bindContent").decode("gbk") if img.get("bindContent") != None else ""
                if bindContent != "":
                    bindContentObjs = bindContent.split("|")
                    for bindContentObj in bindContentObjs:
                        statusList = bindContentObj.split(",")
                        if len(statusList) == 4:
                            animationId = "{0}{1}".format(strPrefix, statusList[1]) if statusList[1] is not None else ""
                            animationStatus.update({
                                statusList[0]: {
                                    "animationId": animationId,
                                    "frameCount": statusList[2],
                                    "interval": statusList[3]
                                }
                            })
                            if statusList[1] not in listAnimationIds:
                                listAnimationIds.append(animationId)

                            if int(statusList[2]) == 1 and statusList[1] not in dataImages:

                                imgId = statusList[1]
                                try:
                                    if isinstance(img_id_list, list) and len(img_id_list):
                                        if int(imgId) not in img_id_list:
                                            self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                            imgId = -404404404
                                except Exception as ept:
                                    logging.error("ERROR in getSystemEquipmentPage: %s" % ept.__str__())

                                dataImages.append("{0}{1}".format(strPrefix, imgId))

                linkInfoList = img.get("eventContent").decode("gbk").split(",") if img.get(
                    "eventContent") != None else list()
                bindType = img.get("prop03").decode("gbk") if img.get("prop03") != None else "0"
                prop02 = img.get("prop02")

                hideScriptContent = img["hideScript"]
                if isinstance(hideScriptContent, str):
                    hideScriptContent = replace_place_holder(hideScriptContent, dictParam)

                if isinstance(hideScriptContent, str):
                    if len(hideScriptContent):
                        if allPointInfo == None:
                            allPointInfo = RedisManager.get_4db_points_info()

                        if isinstance(allPointInfo, dict):
                            if hideScriptContent not in allPointInfo.keys():
                                continue

                dataEquipments.append({
                    "id": img.get("elementid") if img.get("elementid") != None else 0,
                    "x": img.get("x") if img.get("x") != None else 0,
                    "y": img.get("y") if img.get("y") != None else 0,
                    "width": img.get("width") if img.get("width") != None else 0,
                    "height": img.get("height") if img.get("height") != None else 0,
                    "idCom": replace_place_holder(point, dictParam),
                    "idPicture": idPicture,
                    "rotate": img.get("rotateAngle") if img.get("rotateAngle") != None else 0,
                    "link": linkInfoList[4] if len(linkInfoList) >= 5 else "",
                    "linkinfo": linkInfoList,
                    "layer": img.get("layer") if img.get("layer") != None else 0,
                    "name": img.get("elemName").decode("gbk") if img.get("elemName") != None else "",
                    "isFromAnimation": prop02 == "0",
                    "animation": animationStatus,
                    "bindType": int(float(bindType))
                })

            # Imags
            strQuery = "SELECT DISTINCT pictureid FROM page_contain_elements WHERE pageid = %s" % pageId
            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            imgs = []
            for item in fetchAll:
                img = {}
                img["pictureid"] = item[0]
                imgs.append(img)

            for img in imgs:
                if img.get("pictureid") != None and str(img.get("pictureid")) not in dataImages:
                    pictureid = img.get("pictureid")
                    try:
                        if isinstance(img_id_list, list) and len(img_id_list):
                            if pictureid not in img_id_list:
                                self.create404ImageFileForTemplateIfNotExist(templateFileNameWithoutExt)
                                pictureid = -404404404
                    except Exception as ept:
                        logging.error("ERROR in getSystemEquipmentPage: %s" % ept.__str__())

                    dataImages.append("{0}{1}".format(strPrefix, pictureid))

            # checkbox
            strQuery = "SELECT id, x, y, width, height, layer, unitproperty01 as prop01, unitproperty02 as prop02, " \
                       "unitproperty03 as prop03, unitproperty04 as prop04, unitproperty05 as prop05, unitproperty06 as " \
                       "prop06, unitproperty07 as prop07, unitproperty08 as prop08, unitproperty09 as prop09, unitproperty10 as prop10 " \
                       "FROM list_unit07 WHERE pageid = %s" % pageId

            cu.execute(strQuery)
            fetchAll = cu.fetchall()
            boxes = []
            for item in fetchAll:
                box = {}
                box["id"] = item[0]
                box["x"] = item[1]
                box["y"] = item[2]
                box["width"] = item[3]
                box["height"] = item[4]
                box["layer"] = item[5]
                box["prop01"] = item[6]
                box["prop02"] = item[7]
                box["prop03"] = item[8]
                box["prop04"] = item[9]
                box["prop05"] = item[10]
                box["prop06"] = item[11]
                box["prop07"] = item[12]
                box["prop08"] = item[13]
                box["prop09"] = item[14]
                box["prop10"] = item[15]
                boxes.append(box)

            for item in boxes:
                font_color = item.get("prop02").decode('gbk') if item.get("prop02") != None else ''
                text_color = {"r": 255, "g": 255, "b": 255}
                if font_color:
                    try:
                        text_color = {'r': get_r_from_int(font_color),
                                      'g': get_g_from_int(font_color),
                                      'b': get_b_from_int(font_color)}
                    except:
                        pass
                point = item.get("prop06").decode('gbk') if item.get("prop06") != None else ''
                pointProcess = replace_place_holder(point, dictParam)
                strDesc = item.get("prop10").decode("gbk") if item.get("prop10") != None else ""
                strDescProcess = replace_place_holder(strDesc, dictParam)
                dataCheckboxs.append({'id': item.get("id") if item.get("id") != None else 0,
                                      'x': item.get("x") if item.get("x") != None else 0,
                                      'y': item.get("y") if item.get("y") != None else 0,
                                      'width': item.get("width") if item.get("width") != None else 0,
                                      'height': item.get("height") if item.get("height") != None else 0,
                                      'layer': item.get("layer") if item.get("layer") != None else 0,
                                      'idCom': pointProcess,
                                      'type': item.get("prop01").decode('gbk') if item.get("prop01") != None else '',
                                      'fontColor': text_color,
                                      'fontSize': item.get("prop03").decode('gbk') if item.get("prop03") != None else '',
                                      'setValue': item.get("prop04").decode('gbk') if item.get("prop04") != None else '',
                                      'unsetValue': item.get("prop05").decode('gbk') if item.get("prop05") != None else '',
                                      'text': item.get("prop07").decode('gbk') if item.get("prop07") != None else '',
                                      'idGroup': item.get("prop08").decode('gbk') if item.get("prop08") != None else '',
                                      'expression': item.get("prop09").decode('gbk') if item.get("prop09") != None else '',
                                      "desc": strDescProcess})

            # animationList & animationImags
            listAniIds = [ani.replace(strPrefix, "") for ani in listAnimationIds]
            strQuery = "SELECT id, animationlist FROM lib_animation WHERE id IN (%s)" % (','.join(listAniIds))

            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            aImgs = []
            for item in fetchAll:
                aImg = {}
                aImg["id"] = item[0]
                aImg["animationlist"] = item[1]
                aImgs.append(aImg)

            for aImg in aImgs:
                objs = aImg.get("animationlist").decode("gbk").split(",") if aImg.get(
                    "animationlist") != None else list()
                objs_prefix_added = ["{0}{1}".format(strPrefix, item) for item in objs]
                dataAnimationList.update({
                    "{0}{1}".format(strPrefix, aImg.get("id")): objs_prefix_added
                })
                for obj in objs:
                    if obj not in dataAnimationImages:
                        dataAnimationImages.append("{0}{1}".format(strPrefix, obj))

            # page
            strQuery = "SELECT width, hight, pagetype, bgcolor1, bgcolor2, bgimg, name, unitproperty04 FROM list_page WHERE id = %s" % pageId
            cu.execute(strQuery)
            fetchAll = cu.fetchall()

            pageInfo = []
            for item in fetchAll:
                page = {}
                page["width"] = item[0]
                page["hight"] = item[1]
                page["pagetype"] = item[2]
                page["bgcolor1"] = item[3]
                page["bgcolor2"] = item[4]
                page["bgimg"] = item[5]
                page["name"] = item[6]
                page["navJsonConfig"] = item[7].decode("gbk") if item[7] else ""
                pageInfo.append(page)

            dataPage.update({
                'id': pageId,
                'width': pageInfo[0]["width"],
                'height': pageInfo[0]["hight"],
                'type': pageInfo[0]["pagetype"].decode("gbk"),
                'bgColor1': pageInfo[0]["bgcolor1"],
                'bgColor2': pageInfo[0]["bgcolor2"],
                'bgImgId': pageInfo[0]["bgimg"],
                'name': pageInfo[0]["name"].decode("gbk"),
                'navJsonConfig': pageInfo[0]["navJsonConfig"]
            })

            # rectangles
            cu.execute("SELECT x, y, width, height, layer, id, pageid, unitproperty02, unitproperty03, "
                       "unitproperty04 FROM list_unit19 WHERE pageid = %s AND unitproperty01 = 'rectangle'" % pageId)
            for item in cu.fetchall():
                colorBytes = item[7] if item[7] != None else 0
                proper04 = int(item[9].decode("gbk")) if item[9] != None else 0
                dataRectangles.append({
                    "x": item[0] if item[0] != None else 0,
                    "y": item[1] if item[1] != None else 0,
                    "width": item[2] if item[2] != None else 0,
                    "height": item[3] if item[3] != None else 0,
                    "layer": item[4] if item[4] != None else 0,
                    "id": item[5] if item[5] != None else 0,
                    'color': colorHexToRgb(colorBytes),
                    "lineWidth": float(item[8].decode("gbk")) if item[8] != None else 0,
                    "fillOrNot": True if proper04 > 0 else False
                })

            # 管道
            cu.execute(
                "SELECT id, PointList, pipeWidth, style, idlist, layer,  unitproperty01, innerColor, unitproperty03, unitproperty04, logic, unitproperty05 FROM list_line WHERE pageid = %s" % (
                    pageId))
            for item in cu.fetchall():
                strs = item[1].decode('gbk').replace('(', '').replace(')', '').replace(',', ';').split(';') if item[1] != None else ['0', '0', '0', '0']
                color = int(item[7]) if item[7] != None else 0

                # waterShape: 0-矩形；1-圆形
                try:
                    waterShape = int(item[11].decode("gbk")) if item[11] != None else 0
                except:
                    waterShape = 0

                dataPipelines.append({'id': item[0] if item[0] != None else 0,
                                      'width': item[2] if item[2] != None else 0,
                                      'direction': item[3] if item[3] != None else 0,
                                      'idCom': item[4].decode('gbk') if item[4] != None else '',
                                      'startX': strs[0],
                                      'startY': strs[1],
                                      'endX': strs[2],
                                      'endY': strs[3],
                                      'layer': item[5] if item[5] != None else 0,
                                      'waterType': item[6].decode('gbk') if item[6] != None else '',
                                      'color': {'r': get_r_from_int(color), "g": get_g_from_int(color),
                                                'b': get_b_from_int(color)},
                                      'denSity': item[8].decode('gbk') if item[8] != None else '',
                                      'speed': item[9].decode('gbk') if item[9] != None else '',
                                      'logic': item[10] if item[10] != None else 0,
                                      'waterShape': waterShape
                                      })

            # 二级模板设备
            dSecTemplateInfo = self.getSecondaryDialogStandardEquipmentInfo(cu, pageId, dictParam)

            lSecTemplateInfo = dSecTemplateInfo["infoList"]
            lSecTemplateImage = dSecTemplateInfo["imageList"]
            lSecTemplateAnimation = dSecTemplateInfo["animationList"]

            dataImages.extend(lSecTemplateImage)
            dataAnimationImages.extend(lSecTemplateAnimation)

            dataSystemEquipments.extend(lSecTemplateInfo)

        except Exception as e:

            traceback.print_exc()
            print(e.__str__())
            logging.error(e.__str__())
        finally:
            return {"buttons": dataButtons,
                    "texts": dataTexts,
                    "images": list(set(dataImages)),
                    "equipments": dataEquipments,
                    "animationImages": dataAnimationImages,
                    "animationList": dataAnimationList,
                    "timePickers": dataTimePickers,
                    "rulers": dataRulers,
                    "pipelines": dataPipelines,
                    "charts": dataCharts,
                    "page": dataPage,
                    "tempDistributions": dataTempDistributions,
                    "gages": dataGages,
                    "checkboxs": dataCheckboxs,
                    "rects": dataRects,
                    "customControls": dataCustomControls,
                    "rectangles": dataRectangles,
                    "systemEquipments": dataSystemEquipments
                    }

    def getPageType(self, pageid):
        try:
            dbfile = ""
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return list()

            if not len(dbfile):
                return {}

            with SqliteManager(dbfile) as sdb:
                str_sql = '''SELECT
                                name AS pageName,
                                pagetype AS pageType,
                                unitproperty04 as content
                            FROM
                                list_page
                            WHERE
                                id = ?'''
                sql_data = sdb.exec_query(str_sql, (pageid,))
                pageName = sql_data[0].get("pageName").decode("gbk") if sql_data[0].get("pageName", None) else ""
                pageType = sql_data[0].get("pageType").decode("gbk") if sql_data[0].get("pageType", None) else ""
                strContent = sql_data[0].get("content").decode("gbk") if sql_data[0].get("content", None) else ""
                return {"pageName": pageName, "pageType": pageType, "navJsonConfig": strContent}
        except Exception as e:
            logging.error("ERROR in getPageType: %s" % e.__str__())
            return {}




    def TestDB(self, dbname):
        # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
        # dbfileDec = '{}.dec'.format(dbfile)
        #
        # if not os.path.exists(dbfileDec):
        #     print(dbfileDec + ' file not existing!')
        #     return None
        # con = self.connect_readonly(dbfileDec)
        bOK = True
        con = self.connect_readonly(dbname)
        con.text_factory = bytes
        cu = con.cursor()
        # Page
        try:
            cu.execute("select * from project_config")
        except:
            bOK = False

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return bOK

    def ReadRealDBparam(self):
        # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
        # dbfileDec = '{}.dec'.format(dbfile)
        #
        # if not os.path.exists(dbfileDec):
        #     print(dbfileDec + ' file not existing!')
        #     return None
        # con = self.connect_readonly(dbfileDec)


        dbfile = ''
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        con.text_factory = bytes
        cu = con.cursor()
        # Page
        cu.execute(
            "select ProjectID, ProjectName, ScreenWidth, ScreenHeight, Version, XupTime, HostIP, DataBaseName,RealTimeDBName,UserName,AutoLogin,"
            "DTUPortNumber, DTUBaudrate, HostIP2, port, unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05 from project_config")
        dbParamList = []
        for item in cu.fetchall():
            nValue = 0
            try:
                if item[18]:
                    nValue = int(item[18])
            except:
                nValue = 0

            try:
                strDBName = item[7].decode('gbk')
            except:
                strDBName = 'beopdata'

            try:
                strRealtimeDBName = item[8].decode('gbk')
            except:
                strRealtimeDBName = 'beopdata'

            try:
                strUserName = item[9].decode('gbk')
            except:
                strUserName = 'root'

            dbParamList.append(
                {'DBIP': 'localhost', 'DBName': strDBName, 'RealtimeDBName': strRealtimeDBName, 'UserName': strUserName,
                 'AutoLogin': item[10], 'DTUPortNumber': item[11], 'DTUBaudrate': item[12], 'Port': item[14],
                 'MenuGroupEnabled': (nValue == 1)})

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return dbParamList[0] if len(dbParamList) > 0 else None

    def GetMenuGroupEnabled(self, dbname):
        # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
        # dbfileDec = '{}.dec'.format(dbfile)
        #
        # if not os.path.exists(dbfileDec):
        #     print(dbfileDec + ' file not existing!')
        #     return None
        # con = self.connect_readonly(dbfileDec)


        dbfile = ''
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        con.text_factory = bytes
        cu = con.cursor()
        # Page
        cu.execute("select unitproperty04 from project_config")

        bMenuGroup = False
        for item in cu.fetchall():
            nValue = 0
            try:
                if item[0]:
                    nValue = int(item[0])
            except:
                nValue = 0
            bMenuGroup = (nValue == 1)

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return bMenuGroup

    def GetRealtimeDBName(self, dbFilePath):
        # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
        # dbfileDec = '{}.dec'.format(dbfile)
        #
        # if not os.path.exists(dbfileDec):
        #     print(dbfileDec + ' file not existing!')
        #     return None
        # con = self.connect_readonly(dbfileDec)




        con = self.connect_readonly(dbFilePath)

        con.text_factory = bytes
        cu = con.cursor()
        # Page
        cu.execute("select RealTimeDBName from project_config")

        strRealtimeDBName = 'beopdata'
        for item in cu.fetchall():
            nValue = 0
            try:
                if item[0]:
                    strRealtimeDBName = item[0].decode('gbk')
            except:
                pass

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return strRealtimeDBName

    # update version to 4
    def update4DBVersionTo4(self, dbname):
        bSuccess = False
        try:
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return list()

            with SqliteManager(dbfile) as dbm:
                str_sql = '''SELECT
                                unitproperty05 as prop05
                            FROM
                                project_config'''
                sql_data = dbm.exec_query(str_sql)

            db_version = sql_data[0].get("prop05").decode("gbk")

            if db_version is None or db_version == "1" or db_version == "2" or db_version == "3":
                with SqliteManager(dbfile) as dbm:
                    str_sql1 = '''CREATE TABLE
                                IF
                                    NOT EXISTS logic_drawing (
                                         of_logic_id TEXT(128) NOT NULL,
                                         content TEXT,
                                         version_time DATETIME,
                                         locked BOOL,
                                         locked_time BIGINT,
                                         locked_user_id INTEGER,
                                         PRIMARY KEY (of_logic_id)                                         
                                    )'''
                    dbm.exec_none_query(str_sql1)

                    str_sql2 = '''UPDATE project_config
                                    SET unitproperty05 = 4'''
                    dbm.exec_none_query(str_sql2)

            bSuccess = True
        except Exception as e:
            print(e)
        finally:
            return bSuccess


    # update version
    def update4DBVersionFrom1To2(self, dbname):
        bSuccess = False
        queueList = []
        fkag = 0
        # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'),s3dbname)
        # dbfileDec = '{}.dec'.format(dbfile)
        #
        # if not os.path.exists(dbfileDec):
        #     print(dbfileDec + ' file not existing!')
        #     return None
        # con = self.connect_readonly(dbfileDec)

        dbfile = ''
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), dbname)
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        con.text_factory = bytes
        cu = con.cursor()
        # read version
        strVersion = cu.execute("select unitproperty05 from project_config ")
        result = strVersion.fetchall()
        for item in result:
            resultAll = item[0]
            if resultAll is None or resultAll.decode('gbk') == '1':
                try:
                    cu.execute(
                        'CREATE TABLE IF NOT EXISTS "list_dllthread"  ("threadname" TEXT(255) NOT NULL,"threadtimetype" INTEGER,"threadtimedefine" TEXT)')
                    cu.execute(
                        'CREATE TABLE IF NOT EXISTS "dllrelationship" ("fromdllname" TEXT(255),"fromdlloutputname" TEXT(255),"todllname" TEXT(255),"todllinputname" TEXT(255))')
                    cu.execute('CREATE TABLE IF NOT EXISTS "modbusclientconfig" ("name" TEXT(255),"content" TEXT)')
                    cu.execute("update project_config set unitproperty05 = 3")
                except Exception as e:
                    logging.error('ERROR in update4DBVersionFrom1To2 : %s' % (e.__str__()))
                    return False

            elif resultAll is None or resultAll.decode('gbk') == '2':
                local_config = cu.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='local_config'")
                local_config = local_config.fetchall()
                # 判断表是否存在
                if len(local_config) == 0:
                    cu.execute('CREATE TABLE "local_config" ("name" TEXT,"content" TEXT)')
                cu.execute("update project_config set unitproperty05 = 3")
            bSuccess = con.commit()
        if cu is not None:
            cu.close()
        if con is not None:
            con.close()
        return bSuccess

    def test_valid_4db(self, dbFilename):
        try:
            dbfile = ''
            con = self.connect_readonly(dbFilename)
            con.text_factory = bytes
            cu = con.cursor()
            # Page
            cu.execute(
                "select ProjectID, ProjectName, ScreenWidth, ScreenHeight, Version, XupTime, HostIP, DataBaseName,RealTimeDBName,UserName,AutoLogin,"
                "DTUPortNumber, DTUBaudrate, HostIP2, port, unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05 from project_config")
            dbParamList = []
            for item in cu.fetchall():
                dbParamList.append(
                    {'DBIP': 'localhost', 'DBName': item[7].decode('gbk') if item[7] else '',
                     'RealtimeDBName': item[8].decode('gbk') if item[8] else '',
                     'UserName': item[9].decode('gbk') if item[9] else '',
                     'AutoLogin': item[10],
                     'DTUPortNumber': item[11], 'DTUBaudrate': item[12], 'Port': item[14],
                     'RealtimeDBName': item[8].decode('gbk')})

            if len(dbParamList) > 0:
                return True
        except Exception as e:
            strErr = 'ERROR in test_valid_4db :%s, exception: %s' % (dbFilename, e.__str__())
            logging.error()
            return False
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return False

    def initTemplateImagesFiles(self, s4dbFileName):
        strLog = 'Start prepare 4db images files...'
        logging.error(strLog)

        bFileReady = False
        while not bFileReady:
            bDomdb = self.prepareResouceFromS3db(s4dbFileName, None, True)

            # 准备模板文件图片及动画
            strTemplateDir = os.path.join(app.static_folder, "template")
            templateFileList = []
            for subdir, dirs, files in os.walk(strTemplateDir):
                for file in files:
                    if os.path.splitext(file)[1] == ".4db":
                        templateFileList.append(os.path.join(strTemplateDir, file))

            bTemplate = self.prepareTemplateResouceFrom4db(templateFileList)
            bFileReady = bDomdb and bTemplate
            time.sleep(5)
            if not bFileReady:
                logging.error('try again prepare resource file.')

        strLog = 'Start calculating engine finished.'
        logging.error(strLog)

    def initAutoLoadDBFile(self, strSystemDBFileName='domdb.4db'):
        s4dbFileName = self.search4dbOrS3db(strSystemDBFileName)
        if not s4dbFileName:
            strLog = 'ERROR: %s file not found.' % (strSystemDBFileName)
            logging.error(strLog)
        if s4dbFileName:
            if not s4dbFileName.endswith(strSystemDBFileName):
                process_stop_all()
                time.sleep(5)
                corePath = app.config['CORE_PATH']
                sys4dbFile = os.path.join(corePath, strSystemDBFileName)
                os.rename(s4dbFileName, sys4dbFile)
                s4dbFileName = sys4dbFile
                process_restart_domcore()
                process_restart_domlogic()

            app.config.update(dict(USE_4DB_NAME=s4dbFileName, USE_4DB_FILE_FORMAT=1))
            # app.config.update('USE_4DB_FILE_FORMAT', 1)
            strLog = 'Site Calc&Web service starting'
            logging.error(strLog)

            # check db version and update
            self.update4DBVersionFrom1To2(s4dbFileName)
            self.update4DBVersionTo4(s4dbFileName)
            self.prepareSqliteTables()

        else:
            # s3dbFileName = searchS3db()
            app.config.update(dict(USE_4DB_FILE_FORMAT=0))
            s3dbFileName = self.search4dbOrS3db('.s3db')
            if not s3dbFileName:
                strLog = 'ERROR: s3db file not found.'
                logging.error(strLog)
                return False
            else:
                strLog = 'Site Calc&Web starting'
                logging.error(strLog)

                strLog = 'Start prepare s3db images files...Please wait about 30 seconds.'
                logging.error(strLog)

                if self.decryptS3db(s3dbFileName):
                    bFileReady = False
                    while not bFileReady:
                        bFileReady = self.prepareResouceFromS3db(s3dbFileName + '.dec', None,
                                                                                           True)
                        time.sleep(5)
                        if not bFileReady:
                            logging.error('ERROR in preparing resource file.')

                    strLog = 'Start calculating engine finished.'
                    logging.error(strLog)

        self.prepareResourceFromDomImgLib()
        return True

    def searchS3db(self, ):
        currentPath = os.getcwd()
        print('currentPath: ' + currentPath)
        fatherPath = os.path.dirname(currentPath)
        print('find s3db in path: ' + fatherPath)
        word = '.s3db'
        findFileName = ''
        for filename in os.listdir(fatherPath):
            fp = os.path.join(fatherPath, filename)
            fp = fp.replace('\\', '/')
            fnLower = filename.lower()

            if os.path.isfile(fp) and word in fnLower:
                findFileName = fp
                break

        if findFileName:
            return findFileName

    def search4dbOrS3db(self, word):
        currentPath = os.getcwd()

        print('currentPath: ' + currentPath)
        fatherPath = os.path.dirname(currentPath)
        app.config.update(dict(CORE_PATH=fatherPath))
        strInfo = 'start to find %s in path: ' % (word) + fatherPath
        print(strInfo)
        logging.error(strInfo)
        # word = '.4db'
        findFileName = ''
        for filename in os.listdir(fatherPath):
            fp = os.path.join(fatherPath, filename)
            fp = fp.replace('\\', '/')
            fnLower = filename.lower()

            if os.path.isfile(fp) and word in fnLower and fnLower==word:
                # test this file:
                if self.TestDB(fp):
                    findFileName = fp
                else:
                    os.remove(fp)

        if findFileName:
            strInfo = '%s file found! filename:%s' % (word, findFileName)
            logging.error(strInfo)
            return findFileName

    def decryptS3db(self, s3dbFileName):
        try:
            path = os.getcwd() + '/S3dbConvert.exe'
            ShellExecute(0, 'open', path, s3dbFileName, '', 0)

            app.config.update(dict(S3DB_DIR_CLOUD=path, S3DB_NAME=s3dbFileName))
            time.sleep(40)
            return True
        except Exception as e:
            logging.error('ERROR when decryptS3db: %s' % (e.__str__()))
            return False

    def deleteLocalConfig(self, dbname, key):
        bSuccess = False
        cu = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
                # con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), dbname)
                # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)

            con.text_factory = bytes
            cu = con.cursor()
            strQuery = "DELETE FROM local_config where name='%s'" % key
            cu.execute(strQuery)
            con.commit()
            bSuccess = True
        except Exception as e:
            pass
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
            return bSuccess


    # 保存modbusclient设置
    def saveLocalConfig(self, dbname, configfield, dConfig):
        bSuccess = False
        cu = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
                # con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), dbname)
                # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)

            con.text_factory = bytes
            cu = con.cursor()
            flag = self.getInstance().getValueByKeyInLocalConfig(configfield)
            sConfig = json.dumps(dConfig, ensure_ascii=False).encode('gbk')
            if flag == None:
                cu.execute("insert INTO local_config (name, content) VALUES (?, ?)", (configfield, sConfig))
                con.commit()
                bSuccess = True
            else:
                strQuery = "update local_config set content=? where name=?"
                cu.execute(strQuery, (sConfig, configfield))
                con.commit()
                bSuccess = True
        except Exception as e:
            print(e.__str__())
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return bSuccess

    # 更新modbusclient
    def getValueByKeyInLocalConfig(self, configfield):
        bSuccess = False
        rv = None
        dbfile = ''
        cu = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                print('ERROR in getValueByKeyInLocalConfig: s3db file not supported for this  function!')
                return []

            con.text_factory = bytes
            cu = con.cursor()

            result = cu.execute("select content from local_config where name='%s'" % (configfield))
            result = result.fetchall()
            if len(result) == 0:
                rv = None
            else:
                try:
                    rv = result[0][0].decode('gbk') if result[0][0] != None else ''
                except:
                    rv = result[0][0].decode('utf-8') if result[0][0] != None else ''
        except:
            pass
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return rv

    # 更新modbusclient
    def getValueByKeyInLocalConfigMul(self, configfieldList):
        bSuccess = False
        rv = {}
        dbfile = ''
        cu = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return {}
                con = self.connect_readonly(dbfile)
            else:
                print('ERROR in getValueByKeyInLocalConfig: s3db file not supported for this  function!')
                return {}

            con.text_factory = bytes
            cu = con.cursor()

            cu.execute("select name,content from local_config")
            resultDataList = cu.fetchall()
            for item in resultDataList:
                strConfigName = item[0].decode('gbk')
                if strConfigName in configfieldList:
                    rv[strConfigName] = item[1].decode('gbk')
                    try:
                        rv[strConfigName] = json.loads(rv[strConfigName])
                    except:
                        pass
            return rv
        except Exception as ee:
            pass
        finally:
            if cu is not None:
                cu.close()
            if con is not None:
                con.close()
        return rv


    def GetBackupRealtimePointValuesStatus(self):
        bSuccess = False
        rv = None
        dbfile = ''
        cu = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                print('ERROR in GetBackupRealtimePointValuesStatus: s3db file not supported for this  function!')
                return []

            con.text_factory = bytes
            cu = con.cursor()
            cu.execute("select pointtime,pointname,pointvalue from backup_realtimedata_input")
            recoverDataList = []
            for item in cu.fetchall():
                recoverDataList.append(
                    {'pointname': item[1].decode('gbk'), 'pointtime': item[0].decode('gbk'),
                     'pointvalue': item[2].decode('gbk')})
        except Exception as e:
            print(e.__str__())

        return recoverDataList




    def getAutoReportTemplateIdListFileFrom4DB(self, strFindTemplateName=None):
        cur = None
        con = None
        result = []
        bSuccess = False
        try:

            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            if strFindTemplateName:
                # reserve01: fileType   reserve02:fileTimeType    reserve03: fileTimeDefine
                sql = 'select id,file_name,file_time,file_description,reserve01,reserve02,reserve03,reserve04,reserve05 from template_files where file_name = ? or file_name = ?'
                param = [strFindTemplateName, strFindTemplateName.encode("gbk")]
            else:
                sql = 'select id,file_name,file_time,file_description,reserve01,reserve02,reserve03,reserve04,reserve05 from template_files'
                param = []

            cur.execute(sql, tuple(param))
            data = cur.fetchall()

            for item in data:
                try:
                    strFileName = item[1]
                    try:
                        strFileName = item[1].decode("gbk")
                    except:
                        strFileName = item[1].decode("UTF8")

                    strFileTime = item[2]
                    if isinstance(item[2], bytes):
                        strFileTime = item[2].decode('gbk')

                    strFileDescription = item[3]
                    if isinstance(item[3], bytes):
                        strFileDescription = item[3].decode('gbk')

                    strFileType = item[4]
                    if isinstance(item[4], bytes):
                        strFileType = item[4].decode('gbk')
                    nFileType = 0
                    try:
                        nFileType = AttachFileType(int(strFileType))
                    except:
                        pass

                    strFileTimeType = item[5]
                    if isinstance(item[5], bytes):
                        strFileTimeType = item[5].decode('gbk')
                    nFileTimeType = 0
                    try:
                        nFileTimeType = AttachReportFileTimeType(int(strFileTimeType))
                    except:
                        pass

                    strFileTimeConfig = item[6]
                    if isinstance(item[6], bytes):
                        strFileTimeConfig = item[6].decode('gbk')

                    if isinstance(strFileTimeConfig, str) and strFileTimeConfig.find(".") >= 0:
                        nIndexDot = strFileTimeConfig.find(".")
                        strFront = strFileTimeConfig[:nIndexDot]
                        strLatter = strFileTimeConfig[(nIndexDot+1):]
                        if is_int_digit(strFront) and is_int_digit(strLatter):
                            nFront = int(strFront)
                            fLatter = float("0.{digit}".format(digit=strLatter))
                            nMinute = int(fLatter * 60)
                            if nFront >= 0 and nFront <= 23 and nMinute >= 0 and nMinute <= 59:
                                strFileTimeConfig = "{front:02}:{latter:02}".format(front=nFront, latter=nMinute)

                    strUserOfRoleEmailBody = item[7]
                    if isinstance(item[7], bytes):
                        strUserOfRoleEmailBody = item[7].decode("gbk")

                    dUserOfRoleEmailBody = {}
                    try:
                        dUserOfRoleEmailBody = json.loads(strUserOfRoleEmailBody)
                    except:
                        pass

                    userOfRoleList = dUserOfRoleEmailBody.get("EmailSendUserRole", [])
                    strEmailBody = dUserOfRoleEmailBody.get("Body", "")

                    result.append(
                        dict(id=item[0], file_name=strFileName, file_time=strFileTime, file_description=strFileDescription,
                             fileType=nFileType, fileTimeType=nFileTimeType, fileTimeConfig=strFileTimeConfig, userOfRoleList=userOfRoleList, emailBody=strEmailBody))
                except Exception as e:
                    print(e.__str__())
                    pass

        except Exception as err:
            strError = 'ERROR in getAutoReportTemplateIdListFileFrom4DB:' + str(err)
            print(strError)

        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

        return result

    def getTemplateFileFrom4DB(self, templateName, strSaveAsFilePath):
        cur = None
        con = None
        result = []
        bSuccess = False
        templateNameGbk = templateName.encode("gbk")
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return False
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return False
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            sql = 'select file_binary from template_files where file_name = ? or file_name = ?'
            cur.execute(sql, (templateName, templateNameGbk))
            data = cur.fetchall()
            for item in data:
                result.append({
                    'text': item[0]
                })
            if result:
                with open(strSaveAsFilePath, 'wb') as f:
                    f.write(result[0]['text'])
                    bSuccess = True
        except Exception as err:
            strLog = "ERROR in getTemplateFileFrom4DB: %s" % err.__str__()
            logging.error(strLog)
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

        return bSuccess

    def deleteTemplateFileFrom4db(self, templateName):
        cur = None
        con = None
        strMsg = ""
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)

            con.text_factory = bytes
            cur = con.cursor()

            templateNameGBK = templateName.encode("gbk")

            strDelSQL = "delete from template_files where file_name = ? or file_name = ?"
            paramsDel = (templateNameGBK, templateName)
            cur.execute(strDelSQL, paramsDel)
            con.commit()
            bSuccess = True
        except Exception as e:
            strError = e.__str__()
            print(strError)
            if strError.find("database") != -1 and strError.find("locked") != -1:
                strMsg = "domdb.4db正在被占用，请稍后再试"

            bSuccess = False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
            return bSuccess

    # add by golding
    def saveTemplateFileTo4DB(self, templateName, strFilePath, strTime, nFileTimeType, description, nFileType=0, userOfRoleList=[], emailBody=None):
        cur = None
        con = None
        strMsg = ""
        bSuccess = False
        try:

            if isinstance(strTime, str):
                if strTime.find(":") >= 0 and strTime.count(":") == 1:
                    strTimeProcessed = None
                    try:
                        nIndex = strTime.find(":")
                        strFront = strTime[:nIndex]
                        nFront = int(strFront)

                        strLatter = strTime[nIndex+1:]
                        fLatter = round(float(strLatter) / 60.0, 2)

                        fTime = nFront + fLatter
                        strTimeProcessed = str(fTime)
                    except:
                        pass

                    if strTimeProcessed != None:
                        strTime = strTimeProcessed

            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            con.text_factory = bytes
            cur = con.cursor()

            cur.execute("CREATE TABLE IF NOT EXISTS template_files(id int,file_name TEXT, file_binary TEXT,file_time TEXT,file_description TEXT,reserve01 TEXT,reserve02 TEXT,reserve03 TEXT,reserve04 TEXT,reserve05 TEXT)")
            con.commit()

            templateNameGBK = templateName.encode("gbk")
            descriptionGBK = description.encode("gbk")

            with open(strFilePath, 'rb') as f:
                # result = sqlite3.Binary(f.read())
                blobData = f.read()

                strDelSQL = "delete from template_files where file_name = ? or file_name = ?"
                paramsDel = (templateNameGBK, templateName)
                cur.execute(strDelSQL, paramsDel)
                con.commit()

                if nFileType == 2:
                    if len(userOfRoleList):
                        dUserOfRoleAndEmailBody = {"EmailSendUserRole": userOfRoleList}
                        if isinstance(emailBody, str):
                            if len(emailBody):
                                dUserOfRoleAndEmailBody.update({"Body": emailBody})

                        strUserOfRoleAndEmailBody = json.dumps(dUserOfRoleAndEmailBody)
                        strInsertSQL = "insert into template_files(id,file_name,file_binary,file_time, file_description, reserve01, reserve03, reserve02, reserve04) values(?,?,?,?,?,?,?,?,?)"
                        paramsInsert = (self.getMaxIdInTable('template_files') + 1, templateNameGBK, blobData,
                                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'), descriptionGBK, nFileType,
                                        strTime, nFileTimeType, strUserOfRoleAndEmailBody)
                    else:
                        strInsertSQL = "insert into template_files(id,file_name,file_binary,file_time, file_description, reserve01, reserve03, reserve02) values(?,?,?,?,?,?,?,?)"
                        paramsInsert = (self.getMaxIdInTable('template_files') + 1, templateNameGBK, blobData, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), descriptionGBK, nFileType, strTime, nFileTimeType)
                else:
                    strInsertSQL = "insert into template_files(id,file_name,file_binary,file_time, file_description, reserve01) values(?,?,?,?,?,?)"
                    paramsInsert = (self.getMaxIdInTable('template_files') + 1, templateNameGBK, blobData, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '', nFileType)

                cur.execute(strInsertSQL, paramsInsert)
                con.commit()

                bSuccess = True
        except Exception as e:
            strError = e.__str__()
            print(strError)
            if strError.find("database") != -1 and strError.find("locked") != -1:
                strMsg = "domdb.4db正在被占用，请稍后再试"

            bSuccess = False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

        return bSuccess, strMsg

    def getMaxIdInTable(self, tableName):
        if app.config.get("USE_4DB_FILE_FORMAT"):
            dbfile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbfile):
                print(dbfile + ' file not existing!')
                return []
            con = self.connect_readonly(dbfile)
        else:
            dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            dbfileDec = '{}.dec'.format(dbfile)

            if not os.path.exists(dbfileDec):
                print(dbfileDec + ' file not existing!')
                return []
            con = self.connect_readonly(dbfileDec)
        con.text_factory = bytes
        cu = con.cursor()
        # Page
        cu.execute("select max(id) from %s" % (tableName))
        nID = 0
        for item in cu.fetchall():
            if item[0]:
                nID = item[0]

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return nID

    def InitLogoFiles(self):
        logofilepath = os.path.join(app.static_folder, "images")
        bSucFetch = False
        for file in ["logo.png", "logo2.png", "logo3.png", "logo4.png", "logo5.png", "logo6.png", "logo7.png", "logo8.png", "logo9.png", "logo10.png"]:
            logofilename = os.path.join(logofilepath, file)
            try:
                if os.path.exists(logofilename):
                    os.remove(logofilename)
            except Exception as e:
                strError = 'ERROR in init logo files: %s' % (e.__str__())
                return False

            bSucFetch = self.getTemplateFileFrom4DB(file, logofilename)

            # if not bSucFetch:
            #     print('{0} not defined in 4db.'.format(file))

        logofilename = os.path.join(logofilepath, "logo_small.png")
        try:
            if os.path.exists(logofilename):
                os.remove(logofilename)
        except Exception as e:
            strError = 'ERROR in init logo files: %s' % (e.__str__())
            print(strError)
            logging.error(strError)
            return False

        bSuccess = self.getTemplateFileFrom4DB('logo_small.png', logofilename)
        if not bSuccess:
            print('logo_small.png not defined in 4db.')

        return True

    def InitModbusServerFileComparingTime(self):
        cwd = os.getcwd()
        strCoreDir = os.path.dirname(cwd)
        domModbusServerDir = os.path.join(strCoreDir, 'domModbusServer')
        if not os.path.exists(domModbusServerDir):
            return True

        bNeedToRelease = False
        filePath = os.path.join(domModbusServerDir, "modbus_point_table.xlsx")
        if not os.path.exists(filePath):
            bNeedToRelease = True
        else:
            fileTime = time.localtime(os.stat(filePath).st_mtime)
            tLocalFileTime = datetime.now().replace(year=fileTime.tm_year, month=fileTime.tm_mon, day=fileTime.tm_mday, hour=fileTime.tm_hour, minute=fileTime.tm_min, second=fileTime.tm_sec, microsecond=0)
            fileList = self.getAutoReportTemplateIdListFileFrom4DB("modbus_point_table.xlsx")

            if not len(fileList):
                return True

            tDomdbFileTime = None
            try:
                strDomdbFileTime = fileList[0].get("file_time")
                tDomdbFileTime = datetime.strptime(strDomdbFileTime, "%Y-%m-%d %H:%M:%S")
            except:
                pass

            if not isinstance(tDomdbFileTime, datetime):
                bNeedToRelease = True
            else:
                if isinstance(tLocalFileTime, datetime) and isinstance(tDomdbFileTime, datetime):
                    if tDomdbFileTime > tLocalFileTime + timedelta(minutes=1):
                        bNeedToRelease = True

        if not bNeedToRelease:
            return True

        try:
            if os.path.exists(filePath):
                os.remove(filePath)
        except Exception as e:
            strError = 'ERROR in init modbus_point_table files: %s' % (e.__str__())
            print(strError)
            logging.error(strError)
            return False
        bSuccess = self.getTemplateFileFrom4DB('modbus_point_table.xlsx', filePath)
        if not bSuccess:
            print('modbus_point_table.xlsx not defined in 4db.')
        else:
            print('modbus_point_table.xlsx extracted from 4db.')

        return True

    def InitModbusServerFile(self):
        cwd = os.getcwd()
        strCoreDir = os.path.dirname(cwd)
        tablefilepath = os.path.join(strCoreDir, 'domModbusServer')
        if not os.path.exists(tablefilepath):
            return True

        tablefilename = os.path.join(tablefilepath, "modbus_point_table.xlsx")
        try:
            if os.path.exists(tablefilename):
                os.remove(tablefilename)
        except Exception as e:
            strError = 'ERROR in init modbus_point_table files: %s' % (e.__str__())
            print(strError)
            logging.error(strError)
            return False
        bSuccess = self.getTemplateFileFrom4DB('modbus_point_table.xlsx', tablefilename)
        if not bSuccess:
            print('modbus_point_table.xlsx not defined in 4db.')
        else:
            print('modbus_point_table.xlsx extracted from 4db.')

        return True

    def AddVPointIfNotExist(self, pointName, pointDescription):

        if self.getPointInfoFromS3db([pointName]):
            return None

        cur = None
        con = None
        result = []
        bSuccess = False
        try:
            # dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
            # dbfileDec = '{}.dec'.format(dbfile)
            #
            # if not os.path.exists(dbfileDec):
            #     print(dbfileDec + ' file not existing!')
            #     return None

            # con = self.connect_readonly(dbfileDec)

            dbfile = ''
            newPointId = self.getMaxIdInTable('list_point') + 1
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                # con = self.connect_readonly(dbfile)
                con = sqlite3.connect(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
                # con = self.connect_readonly(dbfileDec)

            con.text_factory = bytes
            cur = con.cursor()
            insertSQL = "INSERT INTO list_point(id, type, name, SourceType, R_W, ch_description, unit, high, highhigh, low, " \
                        "lowlow, Param1, Param2, Param3, Param4, Param5, Param6, Param7, Param8, Param9, Param10, Param11, Param15, Param16, Param17, Param18)\
                                                VALUES(%d, %d, '%s', '%s', %d, ?, '%s', %d, '%s', '%s', %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d, %d, %d)" % (
                        newPointId,
                        0, pointName, "vpoint", 0, "", -1, "", "", 0, "", "", "", "", "", "", "", "", "", "", 2, "", 2,
                        2, 2)

            params = (pointDescription.encode('gbk'),)

            cur.execute(insertSQL, params)
            bSuccess = con.commit()

        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return newPointId

    def saveVPointCalculationEquation(self, strPointName, strPointEquation, strDescription):
        cur = None
        con = None
        result = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfile)
                #con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = sqlite3.connect(dbfileDec)
                #con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()

            sql = 'update list_point set Param1 = ?, ch_description= ? where SourceType = \'vpoint\' and name = ?'
            params = (strPointEquation, strDescription.encode('gbk'),  strPointName)
            try:
                cur.execute(sql, params)
            except sqlite3.InternalError  as e:
                print(str(e))
            except sqlite3.DatabaseError as e1:
                print(str(e1))
            except sqlite3.DataError as e2:
                print(str(e2))
            except sqlite3.IntegrityError as e3:
                print(str(e3))
            except sqlite3.InterfaceError as e4:
                print(str(e4))
            except sqlite3.NotSupportedError as e6:
                print(str(e6))
            except sqlite3.OperationalError as e7:
                print(str(e7))

            result = con.commit()

        except Exception as err:
            print(str(err))
            result = False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return result

    def GetVPointCalculationList(self, ):
        cur = None
        con = None
        result = []
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()

            sql = 'select name, ch_description, SourceType, Param1, Param2 from list_point where SourceType = \'vpoint\' and Param1 is not NULL and Param1!=\'\''
            cur.execute(sql)
            data = cur.fetchall()

            for item in data:
                bValid = True
                try:
                    strExpression = item[3].decode('gbk')
                    if strExpression.find('<%') < 0 and strExpression.find('%>') < 0 and strExpression.find(
                            '(') < 0 and strExpression.find(')') < 0:
                        bValid = False
                except:
                    continue

                if not bValid:
                    continue

                nPeriod = 32
                try:
                    strPeriod = item[4].decode('gbk')
                    nPeriod = int(float(strPeriod))
                except:
                    nPeriod = 32

                if nPeriod <= 1:
                    nPeriod = 1
                elif nPeriod <= 2:
                    nPeriod = 2
                elif nPeriod <= 4:
                    nPeriod = 4
                elif nPeriod <= 8:
                    nPeriod = 8
                elif nPeriod <= 16:
                    nPeriod = 16
                elif nPeriod <= 32:
                    nPeriod = 32
                elif nPeriod <= 64:
                    nPeriod = 64
                elif nPeriod <= 128:
                    nPeriod = 128
                elif nPeriod <= 256:
                    nPeriod = 256
                elif nPeriod <= 512:
                    nPeriod = 512
                else:
                    nPeriod = 32

                if len(strExpression) > 0:
                    result.append({
                        'name': item[0].decode('gbk'),
                        'description': item[1].decode('gbk'),
                        'sourceType': item[2].decode('gbk'),
                        'expression': item[3].decode('gbk'),
                        'period': nPeriod
                    })
        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return result

    def prepareTemplateResouceFrom4db(self, templateFileList):
        try:
            if not len(templateFileList):
                return True

            staticFolder = app.static_folder
            if not os.path.exists(staticFolder):
                os.mkdir(staticFolder)
                logging.error('Check find dir not exist, created: %s' % (staticFolder.__str__()))

            imageDir = os.path.join(staticFolder, "images")
            if not os.path.exists(imageDir):
                os.mkdir(imageDir)
                logging.error('Check find dir not exist, created: %s' % (imageDir.__str__()))

            # 删除模板图片文件夹
            templateDir = os.path.join(imageDir, "template")

            #golding:2022-03-31:以下三行暂时屏蔽，解压模板时不删除目录中所有文件，后面需要的话会覆盖，带来的问题是图片文件可能越来越多，也没问题
            #if os.path.exists(templateDir):
            #    shutil.rmtree(templateDir)

            if not os.path.exists(templateDir):
                os.mkdir(templateDir)

            for templatePath in templateFileList:
                print("start to prepare resource from: %s" % templatePath)
                if not os.path.exists(templatePath):
                    continue

                templateFileName = os.path.basename(templatePath)
                templateImageDir = os.path.join(templateDir, os.path.splitext(templateFileName)[0])
                if templateFileName == "template.4db":
                    templateImageDir = templateDir

                if not os.path.exists(templateImageDir):
                    os.mkdir(templateImageDir)

                # 连接模板文件
                con = self.connect_readonly(templatePath)
                cur = con.cursor()

                # 解压图片
                cur.execute('select id, imagebinary from lib_image')
                nIDList = []
                try:
                    for id, img in cur.fetchall():
                        if img:
                            imageFile = open('{0}/{1}.png'.format(templateImageDir, id), 'wb')
                            imageFile.write(img)
                            imageFile.close()
                            nIDList.append(id)
                except Exception as e:
                    strError = 'ERROR in prepareTemplateResouceFrom4db 1#:%s' % (e.__str__())
                    print(strError)
                    logging.error(strError)

                # 解压动画
                cur.execute('select id, imagebinary from lib_image_animation')
                try:

                    for id, img in cur.fetchall():
                        if img:
                            imageFile = open('{0}/animation_{1}.png'.format(templateImageDir, id), 'wb')
                            imageFile.write(img)
                            imageFile.close()
                            nIDList.append(id)

                    RedisManager.set_image_id_list_template(templateFileName, nIDList)
                except Exception as e:
                    strError = 'ERROR in prepareTemplateResouceFrom4db 2#:%s' % (e.__str__())
                    print(strError)
                    logging.error(strError)

                if con is not None:
                    cur.close()
                    con.close()

            return True

        except Exception as e:
            strLog = "ERROR in prepareTemplateResouceFrom4db: %s" % e.__str__()
            print(strLog)
            logging.error(strLog)
            return False


    def InsertRecordToContainElements(self, id, name, type, x, y, width, height, ):
        pass


    def getPointListForExport(self, projId=0):
        cur = None
        con = None
        data = []
        try:

            if not app.config.get("USE_4DB_NAME"):
                return []

            dbFilePath = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbFilePath):
                return []

            con = sqlite3.connect(dbFilePath)
            con.text_factory = bytes
            cur = con.cursor()
            sql = 'select id,name,SourceType,ch_description,unit,R_W,Param1,Param2,Param3,Param4,Param5,Param6,Param7,Param8,Param9,Param10,high,highhigh,low,lowlow,Param11,Param15,Param16,Param17,Param18 from list_point ORDER BY id'
            cur.execute(sql)
            data = cur.fetchall()

        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return data

    def SaveBackupRealtimePointValuesStatus(self, projId=0):

        cur = None
        con = None
        bSuccess = False
        try:
            dbfile = ''
            if app.config.get("USE_4DB_FILE_FORMAT"):
                con = self.get_con(projId)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = str
            cur = con.cursor()

            sql = "CREATE TABLE IF NOT EXISTS backup_realtimedata_input(pointtime TIMESTAMP NOT NULL DEFAULT current_timestamp,pointname varchar(255), pointvalue varchar(2560))";
            cur.execute(sql)
            con.commit()

            sql = "delete from backup_realtimedata_input;"
            cur.execute(sql)
            con.commit()

            allDataList, allDataMap = BEOPDataAccess.getInstance().getInputTable()
            allVirtualPoints = self.getPointInfoFromS3db(None, 'vpoint')

            insertSQL = "insert into backup_realtimedata_input(pointtime,pointname,pointvalue)  values(?,?,?)"
            strTimeNow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params = []
            for k, v in allVirtualPoints.items():
                if allDataMap.get(k):
                    params.append((strTimeNow, k, allDataMap.get(k)))
            cur.executemany(insertSQL, tuple(params))
            bSuccess = con.commit()
        except Exception as err:
            print(str(err))
            logging.error('ERROR in SaveBackupRealtimePointValuesStatus: %s' % (err.__str__()))
            bSuccess = False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return bSuccess

    def getAllPersayControllerPointInfo(self, controllerIp):
        conn = None
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            pointList = []
            strQuery = "SELECT name, Param2, Param3, R_W, Param4 FROM list_point where SourceType = 'PersagyController' and Param1 = '%s'" % controllerIp
            cur.execute(strQuery)
            items = cur.fetchall()

            for item in items:
                nAddress = numericItemToInt(item[2].decode("gbk"))

                if not isinstance(nAddress, int):
                    continue

                multiple = "1"
                try:
                    multiple = "1" if item[4].decode("gbk") == "0" else item[4].decode("gbk")
                except:
                    pass

                pointList.append({
                    "name": item[0].decode("gbk"),
                    "type": item[1].decode("gbk"),
                    "address": nAddress,
                    "R_W": item[3],
                    "multiple": multiple
                })
                # strAddress = "{0}{1:02d}".format(item[1].decode("gbk"), nAddress)


            return pointList

        except Exception as e:
            strLog = "ERROR in getAllPersayControllerPointInfo: %s" % e.__str__()
            logging.error(strLog)
            return []
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    def getAllPersagyControllerWritablePoints(self, controllerIp):
        conn = None
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            strQuery = "SELECT name, Param2, Param3 FROM list_point where SourceType = 'PersagyController' and Param1 = '%s' and R_W = 1" % controllerIp
            cur.execute(strQuery)
            items = cur.fetchall()

            pointMap = {}
            for item in items:
                nAddress = numericItemToInt(item[2].decode("gbk"))
                if not isinstance(nAddress, int):
                    continue
                pointMap.update({
                    item[0].decode("gbk"): {"type": item[1].decode("gbk"), "address": nAddress}
                })

            return pointMap

        except Exception as e:
            strLog = "ERROR in getAllPersagyControllerWritablePoints: %s" % e.__str__()
            logging.error(strLog)
            return {}
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    def getModeGroupDefine(self):
        modeGroupDict = {}
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            strQuery = "SELECT content FROM local_config WHERE name = 'mode_group_define'"
            cur.execute(strQuery)
            items = cur.fetchall()
            groupList = json.loads(items[0][0].decode("gbk")).get("groupList")

            for idx, group in enumerate(groupList):
                modeGroupDict.update({idx: group.get("name")})

            return modeGroupDict

        except Exception as e:
            strLog = "ERROR in getModeGroupDefine: %s" % e.__str__()
            logging.error(strLog)
            return {}
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    def getLogixPointsByIp(self, plcIp):
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            strQuery = "SELECT name FROM list_point where SourceType = 'logix' and Param1 = '%s'" % plcIp
            cur.execute(strQuery)
            items = cur.fetchall()

            pointList = []
            for item in items:
                pointList.append(item[0].decode("gbk"))

            return pointList

        except Exception as e:
            logging.error("ERROR in getLogixPointsByIp:%s" % e.__str__())
            return []
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

    def getPointPageMap(self):
        conn = None
        pointPageMap = {}
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            cur.execute(
                "SELECT id, pageId, dataComId FROM list_text ")
            for item in cur.fetchall():
                strPointName = item[2].decode('gbk') if item[2] != None else ''
                if strPointName:
                    if not pointPageMap.get(strPointName):
                        pointPageMap[strPointName] = []

                    pointPageMap[strPointName].append(item[1])


        except Exception as e:
            logging.error("ERROR in getPointPageMap:%s" % e.__str__())
            return []
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

        return pointPageMap

    def filterFddPoints(self, restrict):
        try:
            if not app.config.get("USE_4DB_FILE_FORMAT"):
                return []

            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return []

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return []

            strQuery = "SELECT name, Param3, Param4, Param5, Param6, Param7, Param8, Param9, Param10 FROM list_point WHERE sourceType='vpoint'"

            # 查询条件待处理
            whereClauseList = []
            if len(restrict):
                for item in restrict:
                    itemList = item.split("|")
                    tmp = "Param{0}='{1}'".format(int(itemList[0])+2, itemList[1] + "|" + itemList[2])
                    whereClauseList.append(tmp)
                strQuery += " and " + " and ".join(whereClauseList)

            cur.execute(strQuery)

            items = cur.fetchall()
            pointMap = {}
            for item in items:
                pointName = item[0].decode("gbk")
                for i in range(1, 9):
                    if len(item[i].decode("gbk").split("|")) > 1:
                        if pointName not in pointMap.keys():
                            pointMap.update({pointName: {}})
                        pointMap.get(pointName).update({item[i].decode("gbk").split("|")[0]: item[i].decode("gbk").split("|")[1]})

            return dict(code=0, data=pointMap)

        except Exception as e:

            logging.error("ERROR in filterFddPoints: %s" % e.__str__())
            return dict(code=1, data=[])

    def UpdateFaultPointsToRedis(self):
        try:
            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return False

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return False

            strQuery = "SELECT name, ch_description, Param3, Param4, Param5, Param6, Param7, Param8, Param9, Param10 FROM list_point WHERE SourceType='vpoint' AND Param2='fault'"
            items = cur.execute(strQuery)

            faultPointInfo = {}
            criticalMap = {1: "低", 2: "中", 3: "高"}

            for item in items:
                pointInfo = {}
                name = item[0].decode("gbk")
                description = item[1].decode("gbk")

                try:
                    pointDetail = eval(item[2].decode("gbk")) if item[2].decode("gbk") is not None else {}
                except:
                    pointDetail = {}

                nCritical = pointDetail.get("critical", 1)

                strCritical = criticalMap.get(nCritical, "")

                department = pointDetail.get("department", "")

                group = pointDetail.get("group", "")

                pointInfo.update({"description": description, "critical": strCritical, "department": department, "group": group})

                viewsDict = {}
                for i in range(3, 10):
                    content = item[i].decode("gbk").split("|")
                    if len(content) > 1:
                        strKey = get_fault_view_en_name(content[0])
                        if not strKey:
                            continue
                        viewsDict.update({strKey: content[1]})

                pointInfo.update({"views": viewsDict})
                faultPointInfo.update({name: pointInfo})

            RedisManager.set("FaultPointInfo", faultPointInfo)
            return True

        except Exception as e:
            logging.error("ERROR in UpdateFaultPointsToRedis: %s" % e.__str__())
            return False

    def UpdateFaultViewInfoToRedis(self):
        try:
            faultView = self.getValueByKeyInLocalConfig("fdd_specy")
            if not isinstance(faultView, str):
                return False

            views = {}
            dFaultView = json.loads(faultView)
            for item in dFaultView.get("group"):
                children = []
                for viewSub in item.get("children"):
                    children.append(viewSub.get("name"))

                viewEn = get_fault_view_en_name(item.get("name"))

                if viewEn is None:
                    continue

                views.update({viewEn: children})

            RedisManager.set("FaultViewInfo", views)
            return True
        except Exception as e:
            logging.error("ERROR in UpdateFaultViewInfoToRedis: %s" % e.__str__())
            return False

    def UpdateFaultAuthInfoToRedis(self):
        try:
            faultAuth = self.getValueByKeyInLocalConfig("fdd_auth")
            if not isinstance(faultAuth, str):
                return False

            infoDict = json.loads(faultAuth)

            FaultPersonNameMap = {}
            FaultPersonNameMapChEn = {}
            for key, value in infoDict.items():
                try:
                    FaultPersonNameMap.update({key: value.get("name_zh")})
                    FaultPersonNameMapChEn.update({value.get("name_zh"): key})
                except:
                    pass

            FaultAuthInfo = {}
            for nameEn, dInfo in infoDict.items():
                visable = dInfo.get("visable")
                visableDict = {}
                for viewZh, itemList in visable.items():
                    if not is_english_word(viewZh):
                        viewEn = get_fault_view_en_name(viewZh)
                    else:
                        viewEn = viewZh
                    if not viewEn:
                        continue
                    visableDict.update({viewEn: itemList})
                FaultAuthInfo.update({nameEn: dict(visable=visableDict,
                                                       group=dInfo.get("group"),
                                                       role=dInfo.get("role"),
                                                       name_zh=dInfo.get("name_zh"))})

            RedisManager.set("FaultAuthInfo", FaultAuthInfo)
            RedisManager.set("FaultPersonNameMap", FaultPersonNameMap)
            RedisManager.set("FaultPersonNameMapChEn", FaultPersonNameMapChEn)

            return True
        except Exception as e:
            logging.error("ERROR in UpdateFaultAuthToRedis: %s" % e.__str__())
            return False

    def updateAllPointInfoIntoRedis(self):
        try:
            infoDict = self.getPointInfoFromS3db(None)
            RedisManager.set("all_point_info", infoDict)
            return True
        except Exception as e:
            logging.error("ERROR in updateAllPointInfoIntoRedis: %s" % e.__str__())
            return False

    """
    检查是否存点名重名的情况
    """
    def hasDuplicatedPointName(self, strPointName, id):
        try:
            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return None

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return None

            strQuery = "SELECT COUNT(name) FROM list_point WHERE name='%s' and id != %s" % (strPointName, id)
            cur.execute(strQuery)
            data = cur.fetchall()
            if not data:
                return None
            if not len(data):
                return None
            if not len(data[0]):
                return None
            if data[0][0] > 0:
                return True
            return False

        except Exception as e:
            logging.error("ERROR in hasDuplicatedPointName: %s" % e.__str__())
            return None

    def pointExists(self, strPointName):
        try:
            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return False

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return False

            strQuery = "SELECT COUNT(name) FROM list_point WHERE name='%s'" % strPointName
            cur.execute(strQuery)
            data = cur.fetchall()
            if not data:
                return False
            if not len(data):
                return False
            if not len(data[0]):
                return False
            if data[0][0] > 0:
                return True
            return False
        except Exception as e:
            logging.error("ERROR in pointExists: %s" % e.__str__())
            return False


    def getReportNameList(self):
        try:
            domdbFile = app.config.get("USE_4DB_NAME")
            if not os.path.exists(domdbFile):
                print("{0}不存在".format(domdbFile))
                return False

            conn = self.connect_readonly(domdbFile)
            conn.text_factory = bytes
            cur = conn.cursor()

            if conn is None or cur is None:
                return False

            strQuery = "SELECT DISTINCT file_description FROM template_files"
            cur.execute(strQuery)
            items = cur.fetchall()

            if not items:
                return []

            dataList = []
            for item in items:
                dataList.append(item[0].decode("gbk"))

            return dataList
        except Exception as e:
            logging.error("ERROR in getReportNameList: %s" % e.__str__())
            return []

    def addHideScriptToDomdb(self):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addHideScriptToDomdb: %s doesn't exist" % dbFilePath)
            return False

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strQ1 = "ALTER TABLE list_text ADD COLUMN hideScript  TEXT"
            strQ2 = "ALTER TABLE list_button ADD COLUMN hideScript  TEXT"
            strQ3 = "ALTER TABLE page_contain_elements ADD COLUMN hideScript  TEXT"

            try:
                cur.execute(strQ1)
            except:
                pass

            try:
                cur.execute(strQ2)
            except:
                pass

            try:
                cur.execute(strQ3)
            except:
                pass

            return True
        except Exception as error:
            logging.error("ERROR in BEOPSqliteAccess::addHideScriptToDomdb: %s" % error.__str__())
            return False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

    def addHideScriptToTemplate4db(self):
        staticDir = app.static_folder
        templateDir = os.path.join(staticDir, "template")

        for rootDir, dirs, files in os.walk(templateDir):
            for file in files:
                if len(os.path.splitext(file)) != 2:
                    continue

                if os.path.splitext(file)[1] != ".4db":
                    continue

                filePath = os.path.join(templateDir, file)
                if not os.path.exists(filePath):
                    continue

                con = sqlite3.connect(filePath)
                con.text_factory = bytes
                cur = con.cursor()

                try:
                    strQ1 = "ALTER TABLE list_text ADD COLUMN hideScript  TEXT"
                    strQ2 = "ALTER TABLE list_button ADD COLUMN hideScript  TEXT"
                    strQ3 = "ALTER TABLE page_contain_elements ADD COLUMN hideScript  TEXT"

                    try:
                        cur.execute(strQ1)
                    except:
                        pass

                    try:
                        cur.execute(strQ2)
                    except:
                        pass

                    try:
                        cur.execute(strQ3)
                    except:
                        pass

                except Exception as error:
                    logging.error("ERROR in BEOPSqliteAccess::addHideScriptToTemplate4db: %s" % error.__str__())
                finally:
                    if cur is not None:
                        cur.close()
                    if con is not None:
                        con.close()

                    print("add hideScript to {fileName}".format(fileName=file))
                    time.sleep(0.2)

    def addSourceTypeToListButtonTable(self):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addSourceTypeToListButtonTable: %s doesn't exist" % dbFilePath)
            return False

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strQ = "ALTER TABLE list_button ADD COLUMN sourceType TEXT"

            try:
                cur.execute(strQ)
            except:
                pass

            return True
        except Exception as error:
            logging.error("ERROR in BEOPSqliteAccess::addSourceTypeToListButtonTable: %s" % error.__str__())
            return False
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()


    def get_point_sources_from_domdb(self):
        cur = None
        con = None
        result = []
        try:
            dbFilePath = app.config.get("USE_4DB_NAME")
            if not os.path.exists(dbFilePath):
                return []

            con = self.connect_readonly(dbFilePath)

            con.text_factory = bytes
            cur = con.cursor()

            sql = 'select DISTINCT SourceType from list_point'

            cur.execute(sql)
            data = cur.fetchall()

            for item in data:
                try:
                    it4 = item[0]

                    if isinstance(item[0], bytes):
                        it4 = item[0].decode('gbk')

                    result.append(it4)

                except:
                    continue
        except Exception as err:
            print(str(err))
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        return result

    def updateFireModeScriptIntoMemory(self):
        script = self.getValueByKeyInLocalConfig("fire_mode_script_define")
        if script == None:
            return None

        if not isinstance(script, str):
            return None

        if not len(script):
            return None

        app.config.update(dict(FIRE_MODE_SCRIPT=script))

    def deleteBackendFileFrom4DB(self, nId):
        cur = None
        con = None
        strMsg = ""
        bSuccess = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            con.text_factory = bytes
            cur = con.cursor()

            cur.execute("delete from template_files where id = ?", (str(nId),))
            con.commit()

            bSuccess = True
        except Exception as e:
            strError = e.__str__()
            print(strError)
            if strError.find("database") != -1 and strError.find("locked") != -1:
                strMsg = "domdb.4db正在被占用，请稍后再试"

            bSuccess = False

        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

        return bSuccess, strMsg

    def updateBackendFileInfoOf4DB(self, nId, nType, strTime, nTimeType, strDesc, filePath, userOfRoleList, emailBody):
        # reserve01: fileType   reserve02:fileTimeType    reserve03: fileTimeDefine   reserver04: 报表自动推送的权限等级和邮件正文
        qSetList = []
        paramList = []
        cur = None
        con = None
        strMsg = ""
        bSuccess = False
        try:
            if strTime.find(":") >= 0 and strTime.count(":") == 1:
                strTimeProcessed = None
                try:
                    nIndex = strTime.find(":")
                    strFront = strTime[:nIndex]
                    nFront = int(strFront)

                    strLatter = strTime[nIndex+1:]
                    fLatter = round(float(strLatter) / 60.0, 2)

                    fTime = nFront + fLatter
                    strTimeProcessed = str(fTime)
                except:
                    pass

                if strTimeProcessed != None:
                    strTime = strTimeProcessed

            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return False, "domdb.4db not found"
                con = sqlite3.connect(dbfile, timeout=10)

            con.text_factory = bytes
            cur = con.cursor()

            cur.execute("SELECT reserve04 FROM template_files WHERE id = ?", (nId,))
            items = cur.fetchall()

            dRoleInfoOrig = {}
            try:
                dRoleInfoOrig = json.loads(items[0][0].decode("gbk"))
            except:
                pass

            if nType != None:
                qSetList.append("reserve01 = ?")
                paramList.append(nType)

            if strTime != None:
                qSetList.append("reserve03 = ?")
                paramList.append(strTime)

            if nTimeType != None:
                qSetList.append("reserve02=?")
                paramList.append(nTimeType)

            if strDesc != None:
                qSetList.append("file_description=?")
                paramList.append(strDesc.encode("gbk"))

            bReserve04NeedUpdate = False
            if len(userOfRoleList):
                dRoleInfoOrig.update({"EmailSendUserRole": userOfRoleList})
                bReserve04NeedUpdate = True

            if isinstance(emailBody, str):
                if len(emailBody):
                    dRoleInfoOrig.update({"Body": emailBody})
                    if emailBody == '""' or emailBody == "''":
                        dRoleInfoOrig.update({"Body": ""})
                    bReserve04NeedUpdate = True

            if bReserve04NeedUpdate:
                qSetList.append("reserve04=?")
                paramList.append(json.dumps(dRoleInfoOrig))

            if filePath != None:
                fileName = os.path.basename(filePath)

                with open(filePath, "rb") as f:
                    # fileBinary = sqlite3.Binary(f.read())
                    fileBinary = f.read()
                    qSetList.append("file_binary=?")
                    paramList.append(fileBinary)

                    qSetList.append("file_name=?")
                    paramList.append(fileName.encode("gbk"))

                    qSetList.append("file_time=?")
                    paramList.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            strQ = "update template_files set " + ",".join(qSetList) + " where id = ?"
            paramList.append(nId)

            cur.execute(strQ, tuple(paramList))
            con.commit()

            bSuccess = True

        except Exception as e:
            strError = e.__str__()
            print(strError)
            if strError.find("database") != -1 and strError.find("locked") != -1:
                strMsg = "domdb.4db正在被占用，请稍后再试"
            bSuccess = False

        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

        return bSuccess, strMsg

    def prepareSqliteTables(self):
        cur = None
        con = None
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return

                con = sqlite3.connect(dbfile, timeout=10)

            con.text_factory = bytes
            cur = con.cursor()

            strQ = "CREATE TABLE IF NOT EXISTS local_config(name varchar, content varchar)"
            cur.execute(strQ)
            con.commit()

        except Exception as e:
            print(e.__str__())
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()

    def updatePoint(self, nId, name, source, description, unit, rw, param1, param2, param3, param4, param5, param6, param7, param8,
                                               param9, param10, high, highhigh, low, lowlow, storageCycle, custom, system, equipment, sysType, decimal):
        cur = None
        con = None
        bSuc = False
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")

                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return
                con = sqlite3.connect(dbfile, timeout=10)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return

                con = sqlite3.connect(dbfile, timeout=10)

            con.text_factory = bytes
            cur = con.cursor()

            queryList = []
            paramList = []
            if source != None:
                queryList.append("SourceType=?")
                paramList.append(source)
            if description != None:
                queryList.append("ch_description=?")
                paramList.append(description.encode('gbk'))
            if unit != None:
                strTUnit = ""
                try:
                    strTUnit = unit.encode("gbk")
                except:
                    try:
                        strTUnit = unit.encode("utf8")
                    except:
                        pass

                queryList.append("unit=?")
                paramList.append(strTUnit)
            if rw != None:
                queryList.append("R_W=?")
                paramList.append(str(rw))
            if param1 != None:
                queryList.append("Param1=?")
                paramList.append(param1)
            if param2 != None:
                queryList.append("Param2=?")
                paramList.append(param2)
            if param3 != None:
                queryList.append("Param3=?")
                paramList.append(param3)
            if param4 != None:
                queryList.append("Param4=?")
                paramList.append(param4.encode("gbk"))
            if param5 != None:
                queryList.append("Param5=?")
                paramList.append(param5)
            if param6 != None:
                queryList.append("Param6=?")
                paramList.append(param6)
            if param7 != None:
                queryList.append("Param7=?")
                paramList.append(param7)
            if param8 != None:
                queryList.append("Param8=?")
                paramList.append(param8)
            if param9 != None:
                queryList.append("Param9=?")
                paramList.append(param9)
            if param10 != None:
                queryList.append("Param10=?")
                paramList.append(param10)
            if high != None:
                queryList.append("high=?")
                paramList.append(high)
            if highhigh != None:
                queryList.append("highhigh=?")
                paramList.append(highhigh)
            if low != None:
                queryList.append("low=?")
                paramList.append(low)
            if lowlow != None:
                queryList.append("lowlow=?")
                paramList.append(lowlow)
            if storageCycle != None:
                queryList.append("Param11=?")
                paramList.append(storageCycle)
            if custom != None:
                queryList.append("Param15=?")
                paramList.append(custom)
            if system != None:
                queryList.append("Param16=?")
                paramList.append(system)
            if equipment != None:
                queryList.append("Param17=?")
                paramList.append(equipment)
            if sysType != None:
                queryList.append("Param18=?")
                paramList.append(sysType)
            if decimal != None:
                queryList.append("Param19=?")
                paramList.append(decimal)
            if name != None:
                queryList.append("name=?")
                paramList.append(name)

            if not len(queryList):
                return True

            strQ = "UPDATE list_point SET "
            strQ += ",".join(queryList)
            strQ += " WHERE id=?"
            paramList.append(nId)

            cur.execute(strQ, paramList)
            con.commit()
            bSuc = True

        except Exception as e:
            print(e.__str__())
        finally:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
            return bSuc

    def getVersionOfDllFile(self, dllNameWithoutExt):
        dllNameList = []
        if isinstance(dllNameWithoutExt, list):
            dllNameList = dllNameWithoutExt
        elif isinstance(dllNameWithoutExt, str):
            dllNameList = [dllNameWithoutExt]

        cur = None
        con = None
        dAll = {}
        dAllStringVersion = {}
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()
            strQuery = "SELECT unitproperty01, unitproperty03 FROM list_dllstore WHERE unitproperty03 in (" + ",".join(["'{0}'".format(obj) for obj in dllNameList]) + ")"
            cur.execute(strQuery)
            items = cur.fetchall()

            for item in items:
                if isinstance(item[0], bytes):
                    try:
                        version = item[0].decode("gbk")
                    except:
                        version = item[0].decode("utf-8")
                else:
                    version = item[0]

                version = version.replace("V", "").replace("v", "")
                nVersion = convert_version(version)

                if isinstance(item[1], bytes):
                    try:
                        name = item[1].decode("gbk")
                    except:
                        name = item[1].decode("utf-8")
                else:
                    name = item[1]

                if name not in dAll.keys():
                    dAll.update({name: None})
                    dAllStringVersion.update({name: ""})

                if isinstance(nVersion, int):
                    if not isinstance(dAll[name], int):
                        dAll[name] = nVersion
                        dAllStringVersion[name] = version
                    else:
                        if nVersion < dAll[name]:
                            dAll[name] = nVersion
                            dAllStringVersion[name] = version

        except Exception as e:
            pass
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return dAll, dAllStringVersion


    def getAllLogic(self, logicName=None):
        cur = None
        con = None
        dLogic = {}
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()

            if logicName:
                if logicName.find(".dll") >= 0:
                    logicName = logicName.replace(".dll", "")
                dllName = "{logicName}.dll".format(logicName=logicName)
                strQuery = "SELECT DLLName, importtime, author, unitproperty01, unitproperty02, unitproperty03, unitproperty04, periodicity, id FROM list_dllstore WHERE DllName='%s'" % dllName
            else:
                strQuery = "SELECT DLLName, importtime, author, unitproperty01, unitproperty02, unitproperty03, unitproperty04, periodicity, id FROM list_dllstore"

            cur.execute(strQuery)
            items = cur.fetchall()
            for item in items:
                dllName = None
                importTime = None
                author = None
                version = None
                description = None
                dllFileName = None
                period = None
                id = None
                threadName = None

                if isinstance(item[0], bytes):
                    try:
                        dllName = item[0].decode("gbk")  # start_ch.dll
                    except:
                        dllName = item[0].decode("utf-8")
                else:
                    dllName = item[0]

                if isinstance(item[1], bytes):
                    try:
                        importTime = item[1].decode("gbk")
                    except:
                        importTime = item[1].decode("utf-8")
                else:
                    importTime = item[1]

                if isinstance(item[2], bytes):
                    try:
                        author = item[2].decode("gbk")
                    except:
                        author = item[2].decode("utf-8")
                else:
                    author = item[2]

                if isinstance(item[3], bytes):
                    try:
                        version = item[3].decode("gbk")
                    except:
                        version = item[3].decode("utf-8")
                else:
                    version = item[3]

                if isinstance(item[4], bytes):
                    try:
                        description = item[4].decode("gbk")
                    except:
                        description = item[4].decode("utf-8")
                else:
                    description = item[4]

                if isinstance(item[5], bytes):
                    try:
                        dllFileName = item[5].decode("gbk")   # StandardOneClickStartV2
                    except:
                        dllFileName = item[5].decode("utf-8")
                else:
                    dllFileName = item[5]

                if isinstance(item[7], bytes):
                    try:
                        period = int(item[7].decode("gbk"))
                    except:
                        period = int(item[7].decode("utf-8"))
                else:
                    period = int(item[7])

                if isinstance(item[8], bytes):
                    try:
                        id = item[8].decode("gbk")
                    except:
                        id = item[8].decode("utf-8")
                else:
                    id = item[8]

                if isinstance(item[6], bytes):
                    try:
                        threadName = item[6].decode("gbk")
                    except:
                        threadName = item[6].decode("utf-8")
                else:
                    threadName = item[6]

                if dllName == None or importTime == None or author == None or version == None or description == None or dllFileName == None or period == None or id == None or threadName == None:
                    continue

                logicName = dllName.replace(".dll", "")
                introduction = ""
                if isinstance(description, str):
                    splitList = description.split("\r\n")
                    if len(splitList):
                        introduction = splitList[0].strip()

                dLogic.update({dllName: dict(importTime=importTime,
                                             author=author,
                                             version=version.replace("V", ""),
                                             description=description,
                                             dllFileName=dllFileName,
                                             period=period,
                                             onoff=0,
                                             logicName=logicName,
                                             id=int(id),
                                             threadName=threadName,
                                             introduction=introduction
                                             )})

        except Exception as e:
            print(e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return dLogic

    def getLogicConfig(self, logicName):
        cur = None
        con = None
        paramList = []
        try:
            if app.config.get("USE_4DB_FILE_FORMAT"):
                dbfile = app.config.get("USE_4DB_NAME")
                if not os.path.exists(dbfile):
                    print(dbfile + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfile)
            else:
                dbfile = os.path.join(app.config.get('S3DB_DIR_CLOUD'), app.config.get('S3DB_NAME'))
                dbfileDec = '{}.dec'.format(dbfile)

                if not os.path.exists(dbfileDec):
                    print(dbfileDec + ' file not existing!')
                    return []
                con = self.connect_readonly(dbfileDec)
            con.text_factory = bytes
            cur = con.cursor()

            dllName = logicName + ".dll"
            dllNameGbk = dllName.encode("gbk")
            strQuery = "SELECT vname, pname, ptype, vexplain, INorOut, unitproperty02 FROM list_paramterConfig WHERE DllName=? OR DllName=?"
            cur.execute(strQuery, (dllName, dllNameGbk))

            items = cur.fetchall()

            for item in items:
                paramName = None
                curValue = None
                paramType = None
                description = None
                typeCanEdit = None
                inorout = None

                if isinstance(item[0], bytes):
                    try:
                        paramName = item[0].decode("gbk")
                    except:
                        paramName = item[0].decode("utf-8")
                else:
                    paramName = item[0]

                if isinstance(item[1], bytes):
                    try:
                        curValue = item[1].decode("gbk")
                    except:
                        curValue = item[1].decode("utf-8")
                else:
                    curValue = item[1]

                if isinstance(item[2], bytes):
                    try:
                        paramType = item[2].decode("gbk")
                    except:
                        paramType = item[2].decode("utf-8")
                else:
                    paramType = item[2]

                if isinstance(item[3], bytes):
                    try:
                        description = item[3].decode("gbk")
                    except:
                        description = item[3].decode("utf-8")
                else:
                    description = item[3]

                if isinstance(item[5], bytes):
                    try:
                        typeCanEdit = item[5].decode("gbk")
                    except:
                        typeCanEdit = item[5].decode("utf-8")
                else:
                    typeCanEdit = item[5]

                if isinstance(item[4], bytes):
                    try:
                        inorout = item[4].decode("gbk")
                    except:
                        inorout = item[4].decode("utf-8")
                else:
                    inorout = item[4]

                if paramName == None or curValue == None or paramType == None or description == None or typeCanEdit == None or inorout == None:
                    continue

                parameterType = paramType
                if paramType == "strconst":
                    parameterType = "const"

                paramList.append(dict(paramName=paramName, curValue=curValue, paramType=parameterType,
                                      description=description, inorout=inorout, typeCanEdit=typeCanEdit))

        except Exception as e:
            print(e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return paramList

    def editLogicConfig(self, logicName, editList):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::editLogicConfig: %s doesn't exist" % dbFilePath)
            return False

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        errList = []
        paramList = []
        queryList = []
        bSuc = False
        try:
            dllName = logicName + ".dll"

            for item in editList:
                dataList = []
                if item.get("paramName", None) == None:
                    errList.append("输入参数有误，缺少paramName")
                    continue

                if item.get("curValue", None) == None:
                    errList.append("输入参数有误，缺少curValue")
                    continue

                strQuery = "UPDATE list_paramterConfig SET pname=?"
                dataList.append(item["curValue"].encode("gbk"))

                if item.get("paramType", None):
                    if item.get("paramType") not in ["point", "const"]:
                        errList.append("输入参数有误，paramType只能为point或const")
                    else:
                        strQuery += ", ptype=?"
                        dataList.append(item["paramType"])

                strQuery += " WHERE (vname=? or vname=?) AND DllName=?"
                dataList.append(item["paramName"])
                dataList.append(item["paramName"].encode("gbk"))
                dataList.append(dllName)

                cur.execute(strQuery, tuple(dataList))

            con.commit()
            bSuc = True
            errList = list(set(errList))
        except Exception as e:
            con.rollback()
            strLog = "ERROR in editLogicConfig: %s" % e.__str__()
            log_info_to_file('editLogicConfig_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc, ";".join(errList)

    def deleteLogic(self, logicName):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::deleteLogic: %s doesn't exist" % dbFilePath)
            return False

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        bSuc = False
        try:
            dllName = logicName + ".dll"

            cur.execute("DELETE FROM list_paramterConfig WHERE DllName = ?", (dllName,))
            cur.execute("DELETE FROM list_dllstore WHERE DllName = ?", (dllName,))
            con.commit()
            bSuc = True
        except Exception as e:
            con.rollback()
            strLog = "ERROR in deleteLogic: %s" % e.__str__()
            log_info_to_file('deleteLogic_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc

    def addLogic(self, nId, logicName, author, period, dllContent, version, description, dllFileNameWithoutExt, dataList):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return False, ""

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()

        bSuc = False
        errList = []
        try:
            dllName = logicName + ".dll"
            importTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if period == None:
                period = "20"
            if not isinstance(period, str):
                period = str(period)

            # 插入策略概览信息
            strInsertDll = "INSERT INTO list_dllstore (id, DllName, importtime, author, periodicity, dllcontent, unitproperty01, unitproperty02, unitproperty03, unitproperty04) VALUES (?,?,?,?,?,?,?,?,?,?)"
            cur.execute(strInsertDll, (str(nId),
                                       dllName,
                                       importTime,
                                       author.encode("gbk"),
                                       period,
                                       dllContent,
                                       version,
                                       description.encode("gbk"),
                                       dllFileNameWithoutExt,
                                       logicName))

            # 清除可能的策略配参
            cur.execute("DELETE FROM list_paramterConfig WHERE DllName=?", (dllName,))

            # 插入策略配参
            strInsertParam = "INSERT INTO list_paramterConfig (vname, pname, ptype, vexplain, DllName, INorOut, unitproperty02) VALUES (?,?,?,?,?,?,?)"
            paramList = []
            for dParam in dataList:
                paramName = dParam.get("name", "")
                if not isinstance(paramName, str):
                    paramName = str(paramName)

                paramValue = dParam.get("defaultValue", "")
                if not isinstance(paramValue, str):
                    paramValue = str(paramValue)

                paramType = dParam.get("type", "")
                if not isinstance(paramType, str):
                    paramType = str(paramType)

                description = dParam.get("remark", "")
                if not isinstance(description, str):
                    description = str(description)

                if not isinstance(dllName, str):
                    dllName = str(dllName)

                typeModifiable = dParam.get("typeModifiable", "0")
                if not isinstance(typeModifiable, str):
                    typeModifiable = str(typeModifiable)

                tplValue = (paramName.encode("gbk"),
                            paramValue.encode("gbk"),
                            paramType,
                            description.encode("gbk"),
                            dllName,
                            "0",
                            typeModifiable)
                paramList.append(tplValue)

            cur.executemany(strInsertParam, tuple(paramList))

            con.commit()
            bSuc = True
        except Exception as e:
            con.rollback()
            strLog = "ERROR in addLogic:%s" % e.__str__()
            log_info_to_file('addLogic_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
            errList.append("新建策略({logicName})失败:{err}".format(logicName=logicName, err=e.__str__()))
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc, ";".join(errList)

    def editLogicName(self, oldName, newName):
        oldDllName = "{name}.dll".format(name=oldName)
        newDllName = "{name}.dll".format(name=newName)
        bSuc = False
        strErrMsg = "修改成功"
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return False, "修改策略名称失败，原因:domdb.4db不存在"

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("UPDATE list_dllstore SET DllName=?, unitproperty04=? WHERE DllName=?", (newDllName, newName, oldDllName))
            cur.execute("UPDATE list_paramterConfig SET DllName=? WHERE DllName=?", (newDllName, oldDllName))
            con.commit()
            bSuc = True
        except Exception as e:
            con.rollback()
            strLog = "ERROR in editLogicName:%s" % e.__str__()
            log_info_to_file('editLogicName_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
            strErrMsg = "修改策略名称失败，原因:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc, strErrMsg

    def editLogicPeriod(self, logicName, period):
        bSuc = False
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::editLogicPeriod: %s doesn't exist" % dbFilePath)
            return False, "domdb.4db连接失败"

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            dllName = "{logicName}.dll".format(logicName=logicName)
            cur.execute("UPDATE list_dllstore SET periodicity = ? WHERE DllName=?", (str(period), dllName))
            con.commit()
            bSuc = True
        except Exception as e:
            strLog = "ERROR in editLogicPeriod:%s" % e.__str__()
            log_info_to_file('editLogicPeriod%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc

    def updateLogic(self, dllFileName, author, dllDescription, version, dllContent, newConfigList):
        bSuc = False
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return False, "domdb.4db连接失败", []

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        errMsg = ""
        try:
            # 查找使用该策略的所有dllName
            # ["start_ch.dll", "standby.dll"]
            dllNameList = []
            strQueryDllList = "SELECT DllName FROM list_dllstore WHERE unitproperty03=?"
            cur.execute(strQueryDllList, (dllFileName,))
            items = cur.fetchall()
            for item in items:
                if isinstance(item[0], bytes):
                    try:
                        dllName = item[0].decode("gbk")
                    except:
                        dllName = item[0].decode("utf8")
                else:
                    dllName = item[0]
                dllNameList.append(dllName)

            if not len(dllNameList):
                return False, "当前策略池中未发现{logic}策略".format(logic=dllFileName), []

            dllNameListWithQuote = ["'{name}'".format(name=item) for item in dllNameList]

            # 查询当前策略配参
            # {"start_ch.dll": {"Enable": {"curValue": "1", "paramType": "const", "description": "", "typeCanEdit": "1", "inorout": "0"}, "": {}}
            dExistingConfig = {}
            strQueryConfig = "SELECT vname, pname, ptype, vexplain, INorOut, unitproperty02, DllName FROM list_paramterConfig WHERE DllName in (%s)" % (','.join(dllNameListWithQuote))
            cur.execute(strQueryConfig)
            items = cur.fetchall()

            for item in items:
                paramName = None
                curValue = None
                paramType = None
                description = None
                typeCanEdit = None
                inorout = None
                dllNameWithExt = None
                if isinstance(item[0], bytes):
                    try:
                        paramName = item[0].decode("gbk")
                    except:
                        paramName = item[0].decode("utf-8")
                else:
                    paramName = item[0]

                if isinstance(item[1], bytes):
                    try:
                        curValue = item[1].decode("gbk")
                    except:
                        curValue = item[1].decode("utf-8")
                else:
                    curValue = item[1]

                if isinstance(item[2], bytes):
                    try:
                        paramType = item[2].decode("gbk")
                    except:
                        paramType = item[2].decode("utf-8")
                else:
                    paramType = item[2]

                if isinstance(item[3], bytes):
                    try:
                        description = item[3].decode("gbk")
                    except:
                        description = item[3].decode("utf-8")
                else:
                    description = item[3]

                if isinstance(item[5], bytes):
                    try:
                        typeCanEdit = item[5].decode("gbk")
                    except:
                        typeCanEdit = item[5].decode("utf-8")
                else:
                    typeCanEdit = item[5]

                if isinstance(item[4], bytes):
                    try:
                        inorout = item[4].decode("gbk")
                    except:
                        inorout = item[4].decode("utf-8")
                else:
                    inorout = item[4]

                if isinstance(item[6], bytes):
                    try:
                        dllNameWithExt = item[6].decode("gbk")
                    except:
                        dllNameWithExt = item[6].decode("utf-8")
                else:
                    dllNameWithExt = item[6]

                if paramName == None or curValue == None or paramType == None or description == None or typeCanEdit == None or inorout == None or dllNameWithExt == None:
                    continue

                if dllNameWithExt not in dExistingConfig.keys():
                    dExistingConfig.update({dllNameWithExt: {}})

                dExistingConfig[dllNameWithExt].update({paramName: dict(curValue=curValue,
                                                                        paramType=paramType,
                                                                        description=description,
                                                                        typeCanEdit=typeCanEdit,
                                                                        inorout=inorout)})

            # 整理准备替换进去的策略配参
            # {"start_ch.dll": [("Enable", b"1", "const", b"启用禁用", "start_ch.dll", "0", "1"), ...],
            # "standby.dll": []}
            dToUpdateLogicConfig = {}
            for dllName in dllNameList:
                toUpdateParamList = []
                for dParam in newConfigList:
                    paramName = dParam.get("name", "")
                    if not isinstance(paramName, str):
                        paramName = str(paramName)

                    paramValue = dParam.get("defaultValue", "")
                    if not isinstance(paramValue, str):
                        paramValue = str(paramValue)

                    existingParamValue = dExistingConfig[dllName].get(paramName, {}).get("curValue", None)
                    if existingParamValue == None:
                        toUpdateParamValue = paramValue
                    else:
                        toUpdateParamValue = existingParamValue

                    paramType = dParam.get("type", "")
                    if not isinstance(paramType, str):
                        paramType = str(paramType)

                    existingParamType = dExistingConfig[dllName].get(paramName, {}).get("paramType", None)
                    if existingParamType is None:
                        toUpdateParamType = paramType
                    else:
                        toUpdateParamType = existingParamType

                    description = dParam.get("remark", "")
                    if not isinstance(description, str):
                        description = str(description)
                    toUpdateDescription = description

                    typeModifiable = dParam.get("typeModifiable", "0")
                    if not isinstance(typeModifiable, str):
                        typeModifiable = str(typeModifiable)
                    toUpdateTypeModifiable = typeModifiable

                    toUpdateParamList.append(
                        (paramName,
                        toUpdateParamValue.encode("gbk"),
                        toUpdateParamType,
                        toUpdateDescription.encode("gbk"),
                        dllName,
                        "0",
                        toUpdateTypeModifiable)
                    )

                dToUpdateLogicConfig.update({dllName: toUpdateParamList})

            # 更新导入时间、作者、dll文件二进制内容、策略描述、版本号
            strUpdateGeneral = "UPDATE list_dllstore SET importtime=?, author=?, dllcontent=?, unitproperty01=?, unitproperty02=? WHERE DllName in (%s)" % (','.join(dllNameListWithQuote))
            cur.execute(strUpdateGeneral, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                           author,
                                           dllContent,
                                           version,
                                           dllDescription.encode("gbk")))

            # 更新策略配参
            strDelete = "DELETE FROM list_paramterConfig WHERE DllName=?"
            strInsert = "INSERT INTO list_paramterConfig (vname, pname, ptype, vexplain, DllName, INorOut, unitproperty02) VALUES (?,?,?,?,?,?,?)"
            for dllName in dllNameList:
                cur.execute(strDelete, (dllName,))
                cur.executemany(strInsert, tuple(dToUpdateLogicConfig[dllName]))

            con.commit()
            bSuc = True
            return bSuc, "更新成功", dllNameList
        except Exception as e:
            con.rollback()
            strLog = "ERROR in updateLogic:%s" % e.__str__()
            log_info_to_file('updateLogic_%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
            errMsg = strLog
            return False, errMsg
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def logicConsistencyCheck(self, logicName):
        dAllLogic = self.getAllLogic(logicName)

        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return False, "domdb.4db连接失败"

        dLogicInfo = dAllLogic.get("{logicName}.dll".format(logicName=logicName))
        threadName = dLogicInfo.get("threadName", "")

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strQuery = "select DllName from list_dllstore where unitproperty04 = ?"
            cur.execute(strQuery, (threadName,))
            itemList = cur.fetchall()

            tarList = []
            if isinstance(itemList, list):
                for item in itemList:
                    try:
                        tar = item[0].decode("gbk")
                    except:
                        tar = item[0].decode("UTF8")
                    tarList.append(tar.replace(".dll", ""))

            bThreadAndLogicOneToOne = False  # 一个策略对应一个线程
            bNeedConsistency = False
            tarList = list(set(tarList))
            if len(tarList) == 1:
                bThreadAndLogicOneToOne = True
                if tarList[0] != threadName:
                    bNeedConsistency = True
                else:
                    bNeedConsistency = False
                
            if bThreadAndLogicOneToOne:
                if bNeedConsistency:
                    strQuery = "UPDATE list_dllstore SET unitproperty04=? WHERE DllName=?"
                    cur.execute(strQuery, (logicName, "{name}.dll".format(name=logicName)))
                    con.commit()
                return True, ""
            else:
                return False, "同一个线程中有多个策略"

        except Exception as e:
            strLog = "%s" % e.__str__()
            log_info_to_file('logicConsistencyCheck%s.log' % datetime.now().strftime('%Y_%m_%d'), strLog)
            errMsg = strLog
            return False, errMsg
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getDisplayManage(self):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return {}

        nEnableNaviSecondryMenu = None
        nRememberPassword = None
        nAutoLogoutTimeout = None

        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT unitproperty04 FROM project_config WHERE ProjectID=1")
            projectConfig = cur.fetchall()

            try:
                nEnableNaviSecondryMenu = int(projectConfig[0][0].decode("gbk"))
            except:
                pass

            strQ = "CREATE TABLE IF NOT EXISTS local_config(name varchar, content varchar)"
            cur.execute(strQ)
            con.commit()

            cur.execute("SELECT content FROM local_config WHERE name='account_manage_config'")

            item = cur.fetchall()

            dInfo = {}
            try:
                dInfo = json.loads(item[0][0].decode("gbk"))
            except Exception as e:
                pass

            nAutoLogout = dInfo.get("auto_log_out", 0)
            nRememberPassword = dInfo.get("remember_pwd_enable", 0)
            nAutoLogoutTimeout = dInfo.get("auto_log_out_timeout", 0)

        except:
            pass
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return dict(enable_secondary_navi_menu=True if nEnableNaviSecondryMenu else False,
                        remember_password=True if nRememberPassword else False,
                        auto_log_out_timeout=nAutoLogoutTimeout)


    def setDisplayManage(self, bEnableNaviSecondryMenu, bRememberPassword, nAutoLogoutTimeout):
        dbFilePath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(dbFilePath):
            logging.error("ERROR in BEOPSqliteAccess::addLogic: %s doesn't exist" % dbFilePath)
            return {}

        bSuc = False
        con = sqlite3.connect(dbFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            item = "1" if bEnableNaviSecondryMenu else "0"
            cur.execute("UPDATE project_config SET unitproperty04=? WHERE ProjectID=1", (item.encode("gbk"),))

            cur.execute("SELECT content FROM local_config WHERE name='account_manage_config'")
            item = cur.fetchall()

            dInfo = {}
            try:
                dInfo = json.loads(item[0][0].decode("gbk"))
            except:
                pass

            dInfo.update(dict(auto_log_out=1 if nAutoLogoutTimeout > 0 else 0,
                              auto_log_out_timeout=nAutoLogoutTimeout,
                              remember_pwd_enable=1 if bRememberPassword else 0))
            cur.execute("UPDATE local_config SET content=? WHERE name='account_manage_config'", (str(dInfo).replace("'", '"').encode("gbk"),))
            con.commit()
            bSuc = True
        except:
            pass
        finally:
            if cur:
                cur.close()
            if con:
                con.close()
            return bSuc

    def getTemplateFileInfo(self, templateFilePath):
        if not os.path.exists(templateFilePath):
            return False, "{file}不存在".format(file=templateFilePath), {}

        rt = None
        con = sqlite3.connect(templateFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT content FROM local_config WHERE name=?", ("globalconfig",))
            res = cur.fetchall()
            if not len(res):
                return True, "未发现版本号配置", {}

            try:
                rt = res[0][0].decode("UTF8") if res[0][0] != None else ""
            except:
                rt = res[0][0].decode("gbk") if res[0][0] != None else ""

            if rt == None:
                return True, "获取版本号失败", {}

            try:
                dInfo = json.loads(rt)
            except:
                return True, "未发现版本号配置", {}


            version = dInfo.get("version", None)
            if version == None:
                return True, "模板文件中未发现版本号配置", {}

            if not re.match(r"^([0-9]*\.[0-9]*\.[0-9]*)*$", version):
                return True, "模板文件版本号格式有误", {}

            return True, "", dict(version=version)

        except Exception as e:
            return True, "获取版本号失败:{err}".format(err=e.__str__()), {}

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_page_contain_elements(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT elementid, DataComId FROM page_contain_elements")
            rowList = cur.fetchall()

            for row in rowList:
                nId = row[0]
                dataComId = row[1].decode("gbk") if row[1] != None else ""

                if dataComId.find(strToRepalce) >= 0:
                    dataComIdNew = dataComId.replace(strToRepalce, strReplaceWith)
                    dataComIdNew = dataComIdNew.encode("gbk")
                    cur.execute("UPDATE page_contain_elements SET DataComId=? WHERE elementid=?", (dataComIdNew, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_unit19(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT id, unitproperty02, unitproperty14 FROM list_unit19")
            rowList = cur.fetchall()

            for row in rowList:
                nId = row[0]
                item02 = row[1].decode("gbk") if row[1] != None else ""
                item14 = row[2].decode("gbk") if row[2] != None else ""

                if item02.find(strToRepalce) >= 0:
                    item02New = item02.replace(strToRepalce, strReplaceWith)
                    item02New = item02New.encode("gbk")
                    cur.execute("UPDATE list_unit19 SET unitproperty02=? WHERE id=?", (item02New, nId))

                if item14.find(strToRepalce) >= 0:
                    item14New = item14.replace(strToRepalce, strReplaceWith)
                    item14New = item14New.encode("gbk")
                    cur.execute("UPDATE list_unit19 SET unitproperty14=? WHERE id=?", (item14New, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_paramterConfig(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT vname, pname, DllName FROM list_paramterConfig")

            rowList = cur.fetchall()

            for row in rowList:
                vname = row[0]
                pname = row[1].decode("gbk") if row[1] != None else ""
                DllName = row[2].decode("gbk") if row[2] != None else ""
                vnameDecode = row[0].decode("gbk")

                if pname.find(strToRepalce) >= 0:
                    if DllName:
                        pnameNew = pname.replace(strToRepalce, strReplaceWith)
                        pnameNew = pnameNew.encode("gbk")
                        cur.execute("UPDATE list_paramterConfig SET pname=? WHERE (vname=? OR vname=?) AND DllName=?", (pnameNew, vname,vnameDecode, DllName))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_local_config(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT name, content FROM local_config")

            rowList = cur.fetchall()
            for row in rowList:
                name = row[0].decode("gbk") if row[0] != None else ""
                content = row[1].decode("gbk") if row[1] != None else ""
                if content.find(strToRepalce) >= 0:
                    contentNew = content.replace(strToRepalce, strReplaceWith)
                    contentNew = contentNew.encode("gbk")
                    if name:
                        cur.execute("UPDATE local_config SET content=? WHERE name=?", (contentNew, name))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_unit13(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT id, unitproperty06 FROM list_unit13")
            rowList = cur.fetchall()

            for row in rowList:
                nId = row[0]
                item06 = row[1].decode("gbk") if row[1] != None else ""

                if item06.find(strToRepalce) >= 0:
                    item06New = item06.replace(strToRepalce, strReplaceWith)
                    item06New = item06New.encode("gbk")
                    cur.execute("UPDATE list_unit13 SET unitproperty06=? WHERE id=?", (item06New, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_text(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT id,dataComId  FROM list_text")

            idxList = [18]  # 需查询替换前缀的字段索引列表
            rowList = cur.fetchall()

            for row in rowList:
                nId = row[0]
                item = row[1].decode("gbk") if row[1] != None else ""
                if item.find(strToRepalce) >= 0:
                    itemNew = item.replace(strToRepalce, strReplaceWith)
                    itemNew = itemNew.encode("gbk")
                    cur.execute("UPDATE list_text SET dataComId=? WHERE id=?", (itemNew, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def replacePointPrefixFrom_list_point(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT id, name,Param1  FROM list_point")

            rowList = cur.fetchall()

            for row in rowList:
                nId = row[0]
                pointName = row[1].decode("gbk") if row[1] != None else ""
                Param1 = row[2].decode("gbk") if row[2] != None else ""
                if pointName.find(strToRepalce) >= 0:
                    pointNameNew = pointName.replace(strToRepalce, strReplaceWith)
                    cur.execute("UPDATE list_point SET name=? WHERE id=?", (pointNameNew, nId))

                if Param1.find(strToRepalce) >= 0:
                    Param1New = Param1.replace(strToRepalce, strReplaceWith)
                    Param1New = Param1New.encode("gbk")
                    cur.execute("UPDATE list_point SET Param1=? WHERE id=?", (Param1New, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_button(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT id, settingpoint, unitproperty01 FROM list_button")
            rowList = cur.fetchall()
            for row in rowList:
                nId = row[0]
                settingpoint = row[1].decode("gbk") if row[1] != None else ""
                item01 = row[2].decode("gbk") if row[2] != None else ""
                if settingpoint.find(strToRepalce) >= 0:
                    settingpointNew = settingpoint.replace(strToRepalce, strReplaceWith)
                    settingpointNew = settingpointNew.encode("gbk")
                    cur.execute("UPDATE list_button SET settingpoint=? WHERE id=?", (settingpointNew, nId))


                if item01.find(strToRepalce) >= 0:
                    item01New = item01.replace(strToRepalce, strReplaceWith)
                    item01New = item01New.encode("gbk")
                    cur.execute("UPDATE list_button SET unitproperty01=? WHERE id=?", (item01New, nId))

            con.commit()
            return True, ""

        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())

        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def replacePointPrefixFrom_list_line(self, strToRepalce, strReplaceWith, domdbPath):
        if not os.path.exists(domdbPath):
            return False, "{file}不存在".format(file=domdbPath), {}

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            cur.execute("SELECT idlist, pageid, id FROM list_line")
            itemList = cur.fetchall()
            if isinstance(itemList, list):
                for item in itemList:
                    if len(item):
                        if isinstance(item[0], bytes):
                            try:
                                strItem0 = item[0].decode("gbk")
                            except:
                                strItem0 = item[0].decode("UTF8")
                        elif isinstance(item[0], str):
                            strItem0 = item[0]
                        elif item[0] == None:
                            strItem0 = ""
                        else:
                            strItem0 = ""

                        nPageId = item[1]
                        nId = item[2]

                        if strItem0.find(strToRepalce) >= 0:
                            strItem0New = strItem0.replace(strToRepalce, strReplaceWith)
                            strItem0New = strItem0New.encode("gbk")
                            cur.execute("UPDATE list_line SET idlist=? WHERE id=? AND pageid=?", (strItem0New, nId, nPageId))

            con.commit()
            return True, ""
        except Exception as e:
            return False, "替换失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def getMaxSortNumOfPageGroup(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT unitproperty01 FROM list_pagegroup"
            cur.execute(strQuery)
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                try:
                    nSort = item[0].decode("gbk")
                except:
                    nSort = item[0].decode("UTF8")

                nNum = None
                try:
                    nNum = int(nSort)
                except:
                    nNum = None

                if isinstance(nNum, int):
                    nList.append(nNum)

            if len(nList):
                nCurMaxNum = max(nList)
            else:
                nCurMaxNum = 0

            return nCurMaxNum, ""
        except Exception as e:
            return None, "获取分组最大排序号失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def addPageGroup(self, nGroupId, name, nSortNum):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "添加失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "INSERT INTO list_pagegroup (id, name, unitproperty01) VALUES (?,?,?)"
            cur.execute(strQuery, (nGroupId, name.encode("gbk"), str(nSortNum).encode("gbk")))
            con.commit()
            return True, "添加成功"
        except Exception as e:
            return False, "添加失败:%s" % e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def deletePageGroup(self, nGroupId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "删除失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id FROM list_page WHERE groupid=?"
            cur.execute(strQuery, (nGroupId,))
            items = cur.fetchall()

            nPageIdList = []
            for item in items:
                try:
                    nPageIdList.append(item[0])
                except:
                    pass

            if len(nPageIdList):
                self.deleteElementsFromPage(nPageIdList)

            strDel1 = "DELETE FROM list_pagegroup WHERE id = ?"
            strDel2 = "DELETE FROM list_page WHERE groupid=?"
            cur.execute(strDel1, (nGroupId,))
            cur.execute(strDel2, (nGroupId,))
            con.commit()
            return True, "删除成功"
        except Exception as e:
            return False, "删除失败:%s" % e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def updatePageGroup(self, nGroupId, name):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "修改失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "UPDATE list_pagegroup SET name = ? WHERE id = ?"
            cur.execute(strQuery, (name.encode("gbk"), nGroupId))
            con.commit()
            return True, "修改成功"
        except Exception as e:
            return False, "修改失败:%s" % e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getPageGroup(self, nGroupId=None):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return [], "修改失败，domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        dataList = []
        try:
            strQuery = 'SELECT id, name, unitproperty01 FROM list_pagegroup'
            param = []
            if nGroupId != None:
                strQuery = 'SELECT id, name, unitproperty01 FROM list_pagegroup WHERE id = ?'
                param = [nGroupId]

            cur.execute(strQuery, tuple(param))
            itemList = cur.fetchall()

            if not isinstance(itemList, list):
                return [], "获取失败"

            for item in itemList:
                try:
                    name = item[1].decode("gbk")
                except:
                    name = item[1].decode("UTF8")

                nSortNum = None
                try:
                    nSortNum = int(item[2].decode("gbk"))
                except:
                    nSortNum = int(item[2].decode("UTF8"))

                dataList.append(dict(id=item[0],
                                     name=name,
                                     sortNum=nSortNum))
            return dataList, "获取成功"
        except Exception as e:
            return [], "获取失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getMaxShowOrderNumOfPage(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT showOrder FROM list_page"
            cur.execute(strQuery)
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                nNum = item[0]

                if isinstance(nNum, int):
                    nList.append(nNum)

            if len(nList):
                nCurMaxNum = max(nList)
            else:
                nCurMaxNum = 0

            return nCurMaxNum, ""
        except Exception as e:
            return None, "获取分组最大排序号失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def addPage(self, name, nPageId, nPageType, nWidth, nHeight, nDisplay, nMinAuth, nShowOrder, nGroupId, needUpdateShowOrderList):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "页面添加失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            bgColor1 = 16777215
            bgColor2 = 16777215
            bgimg = 0
            xPosition = 0
            yPosition = 0
            unitproperty02 = "report"
            strPageType = "fullscreen"
            if nPageType == 0:
                strPageType = "fullscreen"
            elif nPageType == 1:
                strPageType = "floating"
            strInsert = "INSERT INTO list_page (id, name, bgcolor1, bgcolor2, bgimg, groupid, width, hight, pagetype, " \
                       "showOrder, xposition, yposition, unitproperty01, unitproperty02, unitproperty03) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            cur.execute(strInsert, (nPageId, name.encode("gbk"), bgColor1, bgColor2, bgimg, nGroupId, nWidth, nHeight, strPageType.encode("gbk"), nShowOrder, xPosition, yPosition, nDisplay, unitproperty02.encode("gbk"), nMinAuth))

            if len(needUpdateShowOrderList):
                strUpdate = "UPDATE list_page SET showOrder=? WHERE id=?"
                cur.executemany(strUpdate, tuple(needUpdateShowOrderList))

            con.commit()
            return True, "添加成功"
        except Exception as e:
            return False, "添加失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def deletePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "页面删除失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "DELETE FROM list_page WHERE id=?"
            cur.execute(strQuery, (nPageId,))
            con.commit()
            return True, "删除成功"
        except Exception as e:
            return False, "删除失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def updatePageInfo(self, nPageId, name, strPageType, nWidth, nHeight, nDisplay, nMinAuth, bgcolor1, bgcolor2):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "修改失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            sqlList = []
            paramList = []

            strQuery = "UPDATE list_page SET "
            if name != None:
                sqlList.append("name=?")
                paramList.append(name.encode("gbk"))

            if strPageType != None:
                sqlList.append("pagetype=?")
                paramList.append(strPageType.encode("gbk"))

            if nWidth != None:
                sqlList.append("width=?")
                paramList.append(nWidth)

            if nHeight != None:
                sqlList.append("hight=?")
                paramList.append(nHeight)

            if nDisplay != None:
                sqlList.append("unitproperty01=?")
                paramList.append(nDisplay)

            if nMinAuth != None:
                sqlList.append("unitproperty03=?")
                paramList.append(nMinAuth)

            if bgcolor1 != None:
                sqlList.append("bgcolor1=?")
                paramList.append(bgcolor1)

            if bgcolor2 != None:
                sqlList.append("bgcolor2=?")
                paramList.append(bgcolor2)

            strQuery += ",".join(sqlList)
            strQuery += " WHERE id=?"
            paramList.append(nPageId)

            if len(paramList) <= 1:
                return True, "无可修改项"

            cur.execute(strQuery, tuple(paramList))
            con.commit()
            return True, "修改成功"
        except Exception as e:
            return False, "删除失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getPageInfo(self, nPageId=None):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, {}, "修改失败，domdb.4db不存在"

        dPageGroup = {}
        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strQuery = "SELECT p.id, p.name, p.bgcolor1, p.bgcolor2, p.groupid, p.width, p.hight, p.pagetype, p.showOrder, p.unitproperty01, p.unitproperty03, g.name FROM list_page p LEFT JOIN list_pagegroup g ON p.groupid = g.id ORDER BY showOrder"
            param = ()
            if nPageId != None:
                strQuery = "SELECT p.id, p.name, p.bgcolor1, p.bgcolor2, p.groupid, p.width, p.hight, p.pagetype, p.showOrder, p.unitproperty01, p.unitproperty03, g.name FROM list_page p LEFT JOIN list_pagegroup g ON p.groupid = g.id WHERE p.id=? ORDER BY showOrder"
                param = (nPageId,)

            cur.execute(strQuery, param)
            items = cur.fetchall()

            groupList = []

            for item in items:
                nId = item[0]
                name = item[1].decode("gbk")
                bgcolor1 = item[2]
                bgcolor2 = item[3]
                groupId = item[4]
                width = item[5]
                height = item[6]
                strPageType = item[7].decode("gbk")
                nPageType = get_page_type_num(strPageType)
                showOrder = item[8]

                nDisplay = None
                try:
                    nDisplay = int(item[9].decode("gbk")) if isinstance(item[9], bytes) else int(item[9])
                except:
                    pass

                nMinAuth = None
                try:
                    nMinAuth = int(item[10].decode("gbk")) if isinstance(item[10], bytes) else int(item[10])
                except:
                    pass

                strGroupName = ""
                try:
                    strGroupName = item[11].decode("gbk") if isinstance(item[11], bytes) else item[11]
                except:
                    pass

                if groupId not in dPageGroup.keys():
                    dPageGroup.update({groupId: dict(groupId=groupId, pageList=[], groupName=strGroupName)})

                dRgbColor1 = {}
                if isinstance(bgcolor1, int):
                    dRgbColor1 = {'r': get_r_from_int(bgcolor1), "g": get_g_from_int(bgcolor1), 'b': get_b_from_int(bgcolor1)}

                dRgbColor2 = {}
                if isinstance(bgcolor1, int):
                    dRgbColor2 = {'r': get_r_from_int(bgcolor2), "g": get_g_from_int(bgcolor2), 'b': get_b_from_int(bgcolor2)}

                if not len(groupList):
                    groupList.append(dict(groupId=groupId, groupName=strGroupName, pageList=[]))

                if groupList[-1].get("groupId") != groupId:
                    groupList.append(dict(groupId=groupId, groupName=strGroupName, pageList=[]))

                groupList[-1]["pageList"].append(dict(pageId=nId,
                                        name=name,
                                        bgcolor1=dRgbColor1,
                                        bgcolor2=dRgbColor2,
                                        width=width,
                                        height=height,
                                        pageType=nPageType,
                                        showOrder=showOrder,
                                        display=nDisplay,
                                        minAuth=nMinAuth,
                                        groupId=groupId))

                dPageGroup[groupId]["pageList"].append(dict(pageId=nId,
                                        name=name,
                                        bgcolor1=dRgbColor1,
                                        bgcolor2=dRgbColor2,
                                        width=width,
                                        height=height,
                                        pageType=nPageType,
                                        showOrder=showOrder,
                                        display=nDisplay,
                                        minAuth=nMinAuth,
                                        groupId=groupId))

            # 补齐没有页面的pageGroup
            strQueryPageGroup = "SELECT id, name FROM list_pagegroup"
            cur.execute(strQueryPageGroup)
            pageGroupItems = cur.fetchall()
            if pageGroupItems == None:
                return [], {}, "查询失败"

            for pageGroup in pageGroupItems:
                bExists = False
                for grp in groupList:
                    if pageGroup[0] == grp.get("groupId"):
                        bExists = True
                        break

                if not bExists:
                    groupList.append(dict(groupId=pageGroup[0],
                                          groupName=pageGroup[1].decode("gbk"),
                                          pageList=[]))

            return groupList, dPageGroup, "获取成功"

        except Exception as e:
            return [], {}, "获取失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def getPageIdList(self, pageId=None):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "查询页面id列表失败，domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()

        try:
            strQuery = "SELECT id FROM list_page"
            paramList = []
            if pageId != None:
                strQuery = "SELECT id FROM list_page WHERE id=?"
                paramList = [pageId]

            cur.execute(strQuery, tuple(paramList))
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "查询页面id列表失败"

            nIdList = []
            for item in items:
                if len(item):
                    nIdList.append(item[0])

            return nIdList, ""

        except Exception as e:
            return [], "获取页面id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getCustomControlsIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id FROM list_unit19 WHERE pageid=? AND unitproperty01 = 'generalComponent'"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "获取自定义组件id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def getTextIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_text WHERE pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "获取text id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getButtonIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_button WHERE pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "获取button id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getCheckboxIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_unit07 WHERE pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "获取checkbox id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getImageIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT elementid FROM page_contain_elements WHERE elementtype=49 AND pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "图片id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getLineIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_line WHERE pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "管道id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getSysEquipIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_unit13 WHERE pageid=?"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "标准设备id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getRectangleIdListOfOnePage(self, nPageId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_unit19 WHERE pageid=? AND unitproperty01 = 'rectangle'"
            cur.execute(strQuery, (nPageId,))
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                if len(item):
                    if isinstance(item[0], bytes):
                        nTextId = item[0].decode("gbk")
                    else:
                        nTextId = item[0]
                    nList.append(nTextId)

            return nList, ""
        except Exception as e:
            return None, "矩形框id列表失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getMaxidOfText(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        nCurMaxNum = None
        try:
            strQuery = "SELECT id FROM list_text"
            cur.execute(strQuery)
            itemList = cur.fetchall()

            nList = []
            for item in itemList:
                nNum = item[0]

                if isinstance(nNum, int):
                    nList.append(nNum)

            if len(nList):
                nCurMaxNum = max(nList)
            else:
                nCurMaxNum = 0

            return nCurMaxNum, ""
        except Exception as e:
            return None, "获取最大text id失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    addImageEventParamList
    [(nPageId, nImageId, strEventContent, strBindContent), ...]
    
    updateImageEventContentParamList:
    [(nPageId, nImageId, eventBindPoint, eventEquipType, eventType, eventInnerLink, eventEquipName, eventOuterLink),...]
    
    updateImageBindContentParamList:
    [(nPageId, nImageId, strBindContent.encode("gbk")), ...]
    """
    def updatePageContent(self, nPageId, addTextList, removeTextList, updateTextList, addCustList, removeCustList, updateCustList,
                          addButtonList, removeButtonList, updateButtonList, addCheckboxList, removeCheckboxList, updateCheckboxList, addImageList, removeImageList, updateImageList,
                          addImageEventParamList, updateImageEventContentParamList, updateImageBindContentParamList, addLineList, removeLineList, updateLineList, addSysEquipList,
                          removeSysEquipList, updateSysEquipList, addRectangleList, removeRectangleList, updateRectangleList):

        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "修改失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            if len(addTextList):
                cur.executemany(addTextList[0], tuple(addTextList[1]))
            if len(removeTextList):
                cur.executemany(removeTextList[0], tuple(removeTextList[1]))
            if len(updateTextList):
                for sql, param in updateTextList:
                    cur.execute(sql, tuple(param))

            if len(addCustList):
                cur.executemany(addCustList[0], tuple(addCustList[1]))
            if len(removeCustList):
                cur.executemany(removeCustList[0], tuple(removeCustList[1]))
            if len(updateCustList):
                for sql, param in updateCustList:
                    cur.execute(sql, tuple(param))

            if len(addButtonList):
                cur.executemany(addButtonList[0], tuple(addButtonList[1]))
            if len(removeButtonList):
                cur.executemany(removeButtonList[0], tuple(removeButtonList[1]))
            if len(updateButtonList):
                for sql, param in updateButtonList:
                    cur.execute(sql, tuple(param))

            if len(addCheckboxList):
                cur.executemany(addCheckboxList[0], tuple(addCheckboxList[1]))
            if len(removeCheckboxList):
                cur.executemany(removeCheckboxList[0], tuple(removeCheckboxList[1]))
            if len(updateCheckboxList):
                for sql, param in updateCheckboxList:
                    cur.execute(sql, tuple(param))

            if len(addLineList):
                cur.executemany(addLineList[0], tuple(addLineList[1]))
            if len(removeLineList):
                cur.executemany(removeLineList[0], tuple(removeLineList[1]))
            if len(updateLineList):
                for sql, param in updateLineList:
                    cur.execute(sql, tuple(param))

            if len(addImageList):
                cur.executemany(addImageList[0], tuple(addImageList[1]))
            if len(removeImageList):
                cur.executemany(removeImageList[0], tuple(removeImageList[1]))
            if len(updateImageList):
                for sql, param in updateImageList:
                    cur.execute(sql, tuple(param))

            if len(addSysEquipList):
                cur.executemany(addSysEquipList[0], addSysEquipList[1])
            if len(removeSysEquipList):
                cur.executemany(removeSysEquipList[0], tuple(removeSysEquipList[1]))
            if len(updateSysEquipList):
                for sql, param in updateSysEquipList:
                    cur.execute(sql, tuple(param))

            if len(addRectangleList):
                cur.executemany(addRectangleList[0], addRectangleList[1])
            if len(removeRectangleList):
                cur.executemany(removeRectangleList[0], tuple(removeRectangleList[1]))
            if len(updateRectangleList):
                for sql, param in updateRectangleList:
                    cur.execute(sql, tuple(param))

            """
            为图片增加点击事件
            """
            if len(addImageEventParamList):
                delEventParamList = []
                for item in addImageEventParamList:
                    delEventParamList.append(
                        (item[0], item[1])
                    )

                # 若在该页面中已存在该elementid对应的图片则先删除再添加
                strDel = "DELETE FROM event WHERE pageid=? AND id=?"
                cur.executemany(strDel, tuple(delEventParamList))

                strInsert = "INSERT INTO event (pageid, id, event_content, bContentIsExpress, bRestore, bind_content) VALUES (?, ?, ?, '0', '0', ?)"
                cur.executemany(strInsert, tuple(addImageEventParamList))


            """
            更新event_content和bind_content
            """
            dToUpdatePool = {} # 更新池
            dToInsertPool = {} # 插入池

            # 分别遍历updateImageEventContentParamList和updateImageBindContentParamList将涉及到的图片元素的id和所在页面id整理处查询条件列表
            queryCurrentParam = []
            if len(updateImageEventContentParamList):
                for tpl in updateImageEventContentParamList:
                    key = "(pageid={pageid} AND id={id})".format(pageid=tpl[0], id=tpl[1])
                    if key not in queryCurrentParam:
                        queryCurrentParam.append(key)

            if len(updateImageBindContentParamList):
                for tpl in updateImageBindContentParamList:
                    key = "(pageid={pageid} AND id={id})".format(pageid=tpl[0], id=tpl[1])
                    if key not in queryCurrentParam:
                        queryCurrentParam.append(key)

            # 将已存在的event_content和bind_content查出来
            dExisting = {}
            if len(queryCurrentParam):
                cur.execute("SELECT pageid, id, event_content, bind_content FROM event WHERE " + " OR ".join(queryCurrentParam))
                items = cur.fetchall()

                if isinstance(items, list):
                    for item in items:
                        ec = item[2]
                        if isinstance(item[2], bytes):
                            ec = item[2].decode("gbk")
                        elif item[2] == None:
                            ec = ""

                        bc = item[3]
                        if isinstance(item[3], bytes):
                            bc = item[3].decode("gbk")
                        elif item[3] == None:
                            bc = ""
                        dExisting.update({"{pageId}###{elementId}".format(pageId=item[0],
                                                                          elementId=item[1]): dict(event_content=ec, bind_content=bc)})

            # 遍历updateImageEventContentParamList，若图片元素存在event里则记入待更新池，若不存在则记入插入池
            for tpl in updateImageEventContentParamList:
                key = "{pageId}###{elementId}".format(pageId=tpl[0], elementId=tpl[1])
                if key in dExisting.keys():
                    lEventContent = dExisting.get(key).get("event_content").split(",")
                    for idx, strItem in enumerate(tpl):
                        if idx in [0, 1]:
                            continue

                        if strItem != None:
                            if len(lEventContent) >= (idx-2)+1:
                                lEventContent[idx-2] = str(strItem)
                            else:
                                lEventContent.append(str(strItem))
                        else:
                            if len(lEventContent) < (idx-2) + 1:
                                lEventContent.append("")

                    strEventContentUpdated = ",".join(lEventContent)
                    if key in dToUpdatePool.keys():
                        dToUpdatePool[key].update(dict(event_content=strEventContentUpdated))
                    else:
                        dToUpdatePool.update({key: dict(event_content=strEventContentUpdated)})
                else:
                    lEventContent = []
                    for idx, strItem in enumerate(tpl):
                        if idx in [0, 1]:
                            continue
                        lEventContent.append("" if strItem == None else str(strItem))
                    strEventContent = ",".join(lEventContent)
                    if key in dToInsertPool.keys():
                        dToInsertPool[key].update(dict(event_content=strEventContent))
                    else:
                        dToInsertPool.update({key: dict(event_content=strEventContent)})

            # 遍历updateImageBindContentParamList，若图片元素存在event则记入待更新池，若不存在则记入插入池
            for tpl in updateImageBindContentParamList:
                key = "{pageId}###{elementId}".format(pageId=tpl[0], elementId=tpl[1])
                if key in dExisting.keys():
                    if key in dToUpdatePool.keys():
                        dToUpdatePool[key].update(dict(bind_content=tpl[2]))
                    else:
                        dToUpdatePool.update({key: dict(bind_content=tpl[2])})
                else:
                    if key in dToInsertPool.keys():
                        dToInsertPool[key].update(dict(bind_content=tpl[2]))
                    else:
                        dToInsertPool.update({key: dict(bind_content=tpl[2])})

            if dToUpdatePool:
                param1 = []  # event_content, bind_content 都有
                param2 = [] # 只有event_content
                param3 = []  # 只有bind_content
                for strPageIdElemId, dTemp in dToUpdatePool.items():
                    pageid = int(strPageIdElemId.split("###")[0])
                    elemId = int(strPageIdElemId.split("###")[1])
                    if dTemp.get("event_content", None) != None and dTemp.get("bind_content", None) != None:
                        ec = dTemp.get("event_content", "")
                        if not isinstance(ec, bytes):
                            ec = ec.encode("gbk")

                        bc = dTemp.get("bind_content", "")
                        if not isinstance(bc, bytes):
                            bc = bc.encode("gbk")

                        param1.append(
                            (ec, bc, pageid, elemId)
                        )

                    elif dTemp.get("event_content", None) != None and dTemp.get("bind_content", None) == None:
                        ec = dTemp.get("event_content", "")
                        if not isinstance(ec, bytes):
                            ec = ec.encode("gbk")

                        param2.append(
                            (ec, pageid, elemId)
                        )
                    elif dTemp.get("event_content", None) == None and dTemp.get("bind_content", None) != None:
                        bc = dTemp.get("bind_content", "")
                        if not isinstance(bc, bytes):
                            bc = bc.encode("gbk")

                        param3.append(
                            (bc, pageid, elemId)
                        )

                if len(param1):
                    cur.executemany("UPDATE event SET event_content=?, bind_content=? WHERE pageid=? AND id=?", tuple(param1))
                if len(param2):
                    cur.executemany("UPDATE event SET event_content=? WHERE pageid=? AND id=?", tuple(param2))
                if len(param3):
                    cur.executemany("UPDATE event SET bind_content=? WHERE pageid=? AND id=?", tuple(param3))

            if dToInsertPool:
                param = []

                for strPageIdElemId, dTemp in dToInsertPool.items():
                    pageid = int(strPageIdElemId.split("###")[0])
                    elemId = int(strPageIdElemId.split("###")[1])

                    if dTemp.get("event_content", None) != None and dTemp.get("bind_content", None) != None:
                        ec = dTemp.get("event_content", "")
                        if not isinstance(ec, bytes):
                            ec = ec.encode("gbk")

                        bc = dTemp.get("bind_content", "")
                        if not isinstance(bc, bytes):
                            bc = bc.encode("gbk")

                        param.append(
                            (pageid, elemId, ec, bc)
                        )
                    elif dTemp.get("event_content", None) != None and dTemp.get("bind_content", None) == None:
                        ec = dTemp.get("event_content", "")
                        if not isinstance(ec, bytes):
                            ec = ec.encode("gbk")
                        param.append(
                            (pageid, elemId, ec, "".encode("gbk"))
                        )
                    elif dTemp.get("event_content", None) == None and dTemp.get("bind_content", None) != None:
                        bc = dTemp.get("bind_content", "")
                        if not isinstance(bc, bytes):
                            bc = bc.encode("gbk")

                        param.append(
                            (pageid, elemId, "".encode("gbk"), bc)
                        )

                if len(param):
                    cur.executemany("INSERT INTO event (pageid, id, event_content, bind_content) VALUES (?, ?, ?, ?)", tuple(param))

            con.commit()
            return True, ""
        except Exception as e:
            return False, "修改页面(pageId:{id})内容失败:{err}".format(err=e.__str__(), id=nPageId)
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def deleteElementFromLibImageAnimation(self, nId):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return False, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return False, "图库文件不存在，请升级后台"

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, animationlist FROM lib_animation WHERE id=?"
            cur.execute(strQuery, (nId,))
            items = cur.fetchall()

            paramList2 = []
            try:
                strItem = items[0][1].decode("gbk")
                strItemList = strItem.split(",")
                for obj in strItemList:
                    paramList2.append(
                        (int(obj),)
                    )
            except:
                pass

            strDel1 = "DELETE FROM lib_animation WHERE id=?"
            paramList1 = [nId]

            strDel2 = "DELETE FROM lib_image_animation WHERE id =?"

            cur.execute(strDel1, tuple(paramList1))
            cur.executemany(strDel2, tuple(paramList2))
            con.commit()
            return True, ""

        except Exception as e:
            return False, "删除动画失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    def deleteElementFromDomLibImage(self, nId):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return False, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return False, "图库文件不存在，请升级后台"

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strDel = "DELETE FROM lib_image WHERE id = ?"
            cur.execute(strDel, (nId,))
            con.commit()
            return True, ""
        except Exception as e:
            return False, "删除图片失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def addElementToDomLibImageAnimation(self, animationName, fileList, nCategory):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return False, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return False, "图库文件不存在，请升级后台"

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()

        nMaxIdLA, msg = self.getMaxIdInDomImgLibTable("lib_animation")
        if nMaxIdLA == None:
            return None, msg

        try:
            strInsert1 = "INSERT INTO lib_image_animation (id, name, specy, imagebinary, filetype, remark, issystemimage) VALUES (?,?,?,?,?,?,?)"
            paramList1 = []

            strIdList = []
            for item in fileList:
                fileBinary = open(item.get("path"), "rb").read()
                paramList1.append(
                    (item.get("nId"), item.get("name").encode("gbk"), str(nCategory).encode("gbk"), fileBinary,"png".encode("gbk"), "动画".encode("gbk"), 1)
                )
                strIdList.append(str(item.get("nId")))

            strInsert2 = "INSERT INTO lib_animation (id, name, animationlist) VALUES (?,?,?)"
            paramList2 = [nMaxIdLA + 1, animationName.encode("gbk"), ",".join(strIdList).encode("gbk")]

            cur.executemany(strInsert1, tuple(paramList1))
            cur.execute(strInsert2, tuple(paramList2))
            con.commit()
            return True, ""
        except Exception as e:
            return False, "添加动画失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def addElementToDomImgLib(self, nId, fileName, fileBinary, strFileType, nCate):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return False, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return False, "图库文件不存在，请升级后台"

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strCate = str(nCate)
            strInsert = "INSERT INTO lib_image (ID, name, specy, imagebinary, filetype, remark, issystemimage, unitproperty01, unitproperty02) VALUES (?,?,?,?,?,?,?,?,?)"
            cur.execute(strInsert, (nId, fileName.encode("gbk"), strCate.encode("gbk"), fileBinary, strFileType.encode("gbk"), "自定义图元".encode("gbk"), 1, "0".encode("gbk"), "0".encode("gbk")))
            con.commit()

            return True, "添加图片成功"

        except Exception as e:
            return False, "添加图片失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def upgradeDllNameForSeparateThreads(self, oldDllName, newDllName):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "修改失败，domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strUpdate1 = "UPDATE list_dllstore SET unitproperty04=?, DllName=? WHERE DllName=? or DllName=?"
            strUpdate2 = "UPDATE list_paramterConfig SET DllName=? WHERE DllName=? or DllName=?"

            cur.execute(strUpdate1, (newDllName.replace(".dll", ""),
                                     newDllName,
                                     oldDllName,
                                     oldDllName.encode("gbk")))
            cur.execute(strUpdate2, (newDllName,
                                     oldDllName,
                                     oldDllName.encode("gbk")))
            con.commit()
            return True, ""
        except Exception as e:
            return False, "{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    获取包含某个关键词点名的模板详情页面id列表
    """
    def getPageIdsContainPointsOfKeyword(self, filePath, keyword):
        con = sqlite3.connect(filePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT pageid FROM list_text WHERE dataComId LIKE '%{keyword}%'".format(keyword=keyword)
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            nPageIdList = []
            for item in itemList:
                if len(item):
                    try:
                        nPageId = int(item[0])
                        if nPageId not in nPageIdList:
                            nPageIdList.append(nPageId)
                    except:
                        pass

            strQuery = "SELECT pageid FROM page_contain_elements WHERE DataComId like '%{keyword}%'".format(keyword=keyword)
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            for item in itemList:
                if len(item):
                    try:
                        nPageId = int(item[0])
                        if nPageId not in nPageIdList:
                            nPageIdList.append(nPageId)
                    except:
                        pass

            strQuery = "SELECT pageid FROM list_unit07 WHERE unitproperty06 like '%{keyword}%'".format(
                keyword=keyword)
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            for item in itemList:
                if len(item):
                    try:
                        nPageId = int(item[0])
                        if nPageId not in nPageIdList:
                            nPageIdList.append(nPageId)
                    except:
                        pass

            strQuery = "SELECT pageid FROM list_button WHERE settingpoint like '%{keyword}%'".format(
                keyword=keyword)
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            for item in itemList:
                if len(item):
                    try:
                        nPageId = int(item[0])
                        if nPageId not in nPageIdList:
                            nPageIdList.append(nPageId)
                    except:
                        pass

            return nPageIdList, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    获取模板详情界面所对应的模板入口页面id
    pageIdList: 模板详情界面id列表
    """
    def getEntrancePageIdList(self, filePath, pageIdList):
        con = sqlite3.connect(filePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT pageid, event_content FROM event WHERE event_content LIKE "
            strWhereList = []
            for pageId in pageIdList:
                strWhereList.append("'%{pageId}%'".format(pageId=pageId))

            strQuery += " OR event_content LIKE ".join(strWhereList)
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            nEntrancePageIdList = []
            for item in itemList:
                nEntrancePageId = None
                try:
                    nEntrancePageId = int(item[0])
                except:
                    pass

                strLinkContent = None
                try:
                    strLinkContent = item[1].decode("gbk")
                except:
                    pass

                if nEntrancePageId == None or strLinkContent == None:
                    continue

                strLinkContentSplit = strLinkContent.split(",")

                nPieceList = []
                for strPiece in strLinkContentSplit:
                    if len(strPiece):
                        try:
                            nPiece = int(strPiece)
                            nPieceList.append(nPiece)
                        except:
                            pass

                if len(nPieceList) >= 2:
                    if nPieceList[-2] in pageIdList:
                        if nEntrancePageId not in nEntrancePageIdList:
                            nEntrancePageIdList.append(nEntrancePageId)

            return nEntrancePageIdList, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    获取模板名称与占位符Map
    """
    def getTemplateNamePlaceHolderMap(self, filePath):
        con = sqlite3.connect(filePath)
        con.text_factory = bytes
        cur = con.cursor()
        strVersion = "无版本号"
        try:
            strQuery = "SELECT content FROM local_config WHERE name = 'globalconfig'"
            cur.execute(strQuery)
            items = cur.fetchall()
            if items == None:
                return None, "", "查询失败"

            dJson = {}
            try:
                dJson = json.loads(items[0][0].decode("gbk"))
            except:
                pass

            dMap = {}
            for templateName, dPlaceHolder in dJson.items():
                if templateName.find("模板") >= 0:
                    continue

                if templateName == "version" and re.match(r"^([0-9]*|\.)*$", dPlaceHolder):
                    strVersion = dPlaceHolder
                    continue

                dMap.update({templateName: dPlaceHolder})

            return dMap, strVersion, ""

        except Exception as e:
            return None, "", e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getPageIdNameMap(self, filePath, nPageIdList):
        con = sqlite3.connect(filePath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, name FROM list_page WHERE id in (" + ",".join(["'{nId}'".format(nId=nId) for nId in nPageIdList]) + ")"
            cur.execute(strQuery)
            items = cur.fetchall()
            if items == None:
                return None

            dMap = {}
            for item in items:
                nPageId = None
                try:
                    nPageId = int(item[0])
                except:
                    pass

                strPageName = None
                try:
                    strPageName = item[1].decode("gbk")
                except:
                    strPageName = item[1].decode("utf8")

                if nPageId == None or strPageName == None:
                    continue

                dMap.update({nPageId: strPageName})

            return dMap, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    获取标准设备名称与跳转进入的模板页面id键值对
    """
    def getStdEquipEntrancePageNameAndTemplatePageId(self, templateFilePath, stdEquipNameList):
        if not os.path.exists(templateFilePath):
            return None, "{filePath}不存在".format(filePath=templateFilePath)

        con = self.connect_readonly(templateFilePath)
        con.text_factory = bytes
        cur = con.cursor()
        nEntrancePageIdList = []

        try:
            # 获取跳转进入的详情页面id
            strQueryGetDetailPageid = "SELECT id, name FROM list_page"
            cur.execute(strQueryGetDetailPageid)
            detailPages = cur.fetchall()
            if detailPages == None:
                return None, "查询失败"

            nDetailPageIdList = []
            for item in detailPages:
                nId = None
                try:
                    nId = item[0]
                except:
                    pass

                try:
                    strPageName = item[1].decode("gbk")
                except:
                    strPageName = item[1].decode("utf8")

                if nId == None or strPageName == None:
                    continue
                if strPageName not in stdEquipNameList:
                    nDetailPageIdList.append(nId)

            strQuery = "SELECT e.event_content, lpg.name, lp.name, lp.groupid, lp.id FROM event e LEFT JOIN list_page lp ON e.pageid=lp.id LEFT JOIN list_pagegroup lpg ON lp.groupid = lpg.id"
            cur.execute(strQuery)
            itemList = cur.fetchall()
            if itemList == None:
                return None, "查询失败"

            res = {}
            for item in itemList:
                strEventContent = None
                strGroupName = None
                strPageName = None

                try:
                    strEventContent = item[0].decode("gbk")
                except:
                    pass

                try:
                    strGroupName = item[1].decode("gbk")
                except:
                    pass

                try:
                    strPageName = item[2].decode("gbk")
                except:
                    pass

                nGroupId = item[3]
                nEntrancePageId = item[4]  # 模板的入口图元所在的页面id

                if strEventContent == None or strGroupName == None or strPageName == None:
                    continue

                # 如果页面名称不在标准设备名称列表中则跳过
                if strPageName not in stdEquipNameList:
                    continue

                if strPageName.startswith("bsd"):  # 过滤佰诗得
                    continue

                strEventContentSplit = strEventContent.split(",")

                nPieceList = []
                for strPiece in strEventContentSplit:
                    if len(strPiece):
                        try:
                            nPiece = int(strPiece)
                            nPieceList.append(nPiece)
                        except:
                            pass

                if len(nPieceList) >= 2:
                    if nPieceList[-2] in nDetailPageIdList:
                        res.update({strPageName: dict(detailPageId=nPieceList[-2], groupName=strGroupName, groupId=nGroupId, entrancePageId=nEntrancePageId, elementId=None)})  # elementId：模板入口图元图片id

                nEntrancePageIdList.append(nEntrancePageId)

            if len(nEntrancePageIdList):
                dPageIdAndElementIdMap = {}
                strQuery = "SELECT pageid, elementid, width, hight, pictureid FROM page_contain_elements WHERE pageid in (" + ",".join(["{n}".format(n=nId) for nId in nEntrancePageIdList]) + ")"
                cur.execute(strQuery)
                arrList = cur.fetchall()
                if isinstance(arrList, list):
                    for arr in arrList:
                        if arr[0] not in dPageIdAndElementIdMap.keys():
                            dPageIdAndElementIdMap.update({arr[0]: dict(elementId=-1, width=0, height=0, entrancePictureId=-1)})
                        if arr[2] > dPageIdAndElementIdMap[arr[0]].get("width") and arr[3] > dPageIdAndElementIdMap[arr[0]].get("height"):
                            dPageIdAndElementIdMap[arr[0]].update(dict(elementId=arr[1], width=arr[2], height=arr[3], entrancePictureId=arr[4]))

                if dPageIdAndElementIdMap:
                    for obj in res.values():
                        if dPageIdAndElementIdMap.get(obj.get("entrancePageId", None), None) != None:
                            if dPageIdAndElementIdMap[obj["entrancePageId"]].get("elementId") != -1:
                                obj.update(dict(elementId=dPageIdAndElementIdMap[obj["entrancePageId"]].get("elementId"),
                                                entrancePictureId=dPageIdAndElementIdMap[obj["entrancePageId"]].get("entrancePictureId")))

            return res, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getElementFromDomLibImageAnimation(self, nameKeword=None):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return False, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return False, "图库文件不存在，请升级后台"

        categoryMap, les = get_dom_image_lib_category()

        if isinstance(nameKeword, str):
            nameKeword = nameKeword.lower()

        con = self.connect_readonly(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, name, animationlist FROM lib_animation"

            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "查询失败"

            imgIdList = []
            imgList = []
            for item in items:
                nId = item[0]
                name = ""
                try:
                    name = item[1].decode("gbk")
                except:
                    try:
                        name = item[1].decode("utf8")
                    except:
                        pass

                if isinstance(nameKeword, str):
                    if name.lower().find(nameKeword) == -1:
                        continue

                dImgCate = {}
                imgNameList = []
                try:
                    strAnimation = item[2].decode("gbk")
                    animationList = strAnimation.split(",")
                    for obj in animationList:
                        nImgId = int(obj)
                        dImgCate.update({nImgId: None})
                        imgNameList.append("animation_{id}.png".format(id=nImgId))
                        if nImgId not in imgIdList:
                            imgIdList.append(nImgId)

                except:
                    pass

                imgList.append(dict(id=nId, name=name, imgNameList=imgNameList, imgCate=dImgCate))

            dImgIdCate = {}
            if len(imgIdList):
                strQueryImgInfo = "SELECT id, specy FROM lib_image_animation WHERE id in (" + ",".join([str(nImgId) for nImgId in imgIdList]) + ")"
                cur.execute(strQueryImgInfo)
                arrs = cur.fetchall()
                for arr in arrs:
                    strCate = ""
                    if isinstance(arr[1], str):
                        strCate = arr[1]
                    elif isinstance(arr[1], bytes):
                        try:
                            strCate = arr[1].decode("gbk")
                        except:
                            try:
                                strCate = arr[1].decode("utf8")
                            except:
                                pass

                    if is_int_digit(strCate):
                        nCate = int(strCate)
                    else:
                        nCate = 11

                    dImgIdCate.update({arr[0]: nCate})

            for img in imgList:
                nCategory = 11
                strCategoryName = "其他"
                for nImgId in img.get("imgCate").keys():
                    nCate = dImgIdCate.get(nImgId, 11)
                    img["imgCate"].update({nImgId: nCate})
                    strCategoryName = categoryMap.get(nCate, "其他")
                    nCategory = nCate

                img.update(dict(categoryId=nCategory, categoryName=strCategoryName))

            return imgList, ""
        except Exception as e:
            return None, [], e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getAnimationMapFromDomImgLib(self):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return None, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return None, "图库文件不存在，请升级后台"

        dRes = {}

        con = self.connect_readonly(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, name, animationlist FROM lib_animation"
            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "获取图库中的所有动画失败"
            if not len(items):
                return None, "获取图库中的所有动画失败"

            for item in items:
                if item[0] not in dRes.keys():
                    dRes.update({item[0]: {}})

                animationList = []
                if isinstance(item[2], bytes):
                    animationList = item[2].decode("gbk").split(",")
                elif isinstance(item[2], str):
                    animationList = item[2].split(",")

                dRes[item[0]].update(dict(name=item[1].decode("gbk"), animationList=animationList))

            return dRes, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getElementFromLibImage(self, nameKeword=None):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None,None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, name, remark, specy FROM lib_image"

            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, None, "查询失败"

            dRes = {}
            imgList = []
            for item in items:
                nId = item[0]
                name = ""
                try:
                    name = item[1].decode("gbk")
                except:
                    try:
                        name = item[1].decode("utf8")
                    except:
                        pass

                if isinstance(nameKeword, str):
                    if name.lower().find(nameKeword) == -1:
                        continue

                remark = ""
                if isinstance(item[2], bytes):
                    try:
                        remark = item[2].decode("gbk")
                    except:
                        try:
                            remark = item[2].decode("utf8")
                        except:
                            pass
                elif isinstance(item[2], str):
                    remark = item[2]

                nSpecy = 11
                if isinstance(item[3], bytes):
                    try:
                        nSpecy = int(item[3].decode("gbk"))
                    except:
                        try:
                            nSpecy = int(item[3].decode("utf8"))
                        except:
                            pass
                elif isinstance(item[3], str):
                    try:
                        nSpecy = int(item[3])
                    except:
                        pass

                if nId not in dRes.keys():
                    dRes.update({nId: {}})

                dRes[nId].update(dict(name=name, remark=remark, specy=nSpecy))
                imgList.append(dict(id=nId, name=name, remark=remark, specy=nSpecy))

            return dRes, imgList, ""
        except Exception as e:
            return None, [], e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getElementFromDomLibImage(self, nameKeword=None):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return None, None, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return None, None,  "图库文件不存在，请升级后台"

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, name, remark, specy FROM lib_image"

            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, None, "查询失败"

            dRes = {}
            imgList = []
            for item in items:
                nId = item[0]
                name = ""
                try:
                    name = item[1].decode("gbk")
                except:
                    try:
                        name = item[1].decode("utf8")
                    except:
                        pass

                if isinstance(nameKeword, str):
                    if name.lower().find(nameKeword) == -1:
                        continue

                remark = ""
                if isinstance(item[2], bytes):
                    try:
                        remark = item[2].decode("gbk")
                    except:
                        try:
                            remark = item[2].decode("utf8")
                        except:
                            pass
                elif isinstance(item[2], str):
                    remark = item[2]

                nSpecy = 11
                if isinstance(item[3], bytes):
                    try:
                        nSpecy = int(item[3].decode("gbk"))
                    except:
                        try:
                            nSpecy = int(item[3].decode("utf8"))
                        except:
                            pass
                elif isinstance(item[3], str):
                    try:
                        nSpecy = int(item[3])
                    except:
                        pass

                if nId not in dRes.keys():
                    dRes.update({nId: {}})

                dRes[nId].update(dict(name=name, remark=remark, specy=nSpecy))
                imgList.append(dict(id=nId, name=name, remark=remark, specy=nSpecy))

            return dRes, imgList, ""
        except Exception as e:
            return None, [], e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    将磁盘.\static\images\button下的标准button图片存入lib_image并更新到redis
    red/green/yellow 为风格名称
    """
    def prepareStandardButtonImages(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        fileNameList, dStyle = get_standard_button_image_from_static()
        if fileNameList == None or dStyle == None:
            return None, "检查发现后台图片静态文件夹不存在，请先升级后台"

        if fileNameList == 0 or dStyle == 0:
            return None, "检查发现某个风格的按钮缺失一个或多个情况下的特定图片，请先升级后台"

        if not isinstance(fileNameList, list) or not isinstance(dStyle, dict):
            return None, "后台图片静态文件获取失败，请先升级后台"

        if not len(fileNameList) or not len(dStyle):
            return None, "未获取到后台静态图片文件信息，可能静态文件夹为空，请先升级后台"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            delParamList = []
            sqlList = []
            strDel = "DELETE FROM lib_image WHERE "
            for fileName in fileNameList:
                sqlList.append("unitproperty05=?")
                delParamList.append(fileName.encode("gbk"))

            strDel += " OR ".join(sqlList)

            strInsert = "INSERT INTO lib_image (ID, name, specy, imagebinary, filetype, remark, issystemimage, unitproperty01, unitproperty02, unitproperty05) VALUES (?,?,?,?,?,?,?,?,?,?)"
            nMaxId = self.getMaxIdInTable("lib_image")
            nId = nMaxId + 1

            dStdBtn = {}
            insertParamList = []
            fileDir = os.path.join(app.static_folder, "images", "button")
            for fileName in fileNameList:
                fileWithExt = "{name}.png".format(name=fileName)
                insertParamList.append(
                    (nId, fileWithExt.encode("gbk"), "10".encode("gbk"),
                     open(os.path.join(fileDir, fileWithExt), "rb").read(),
                     "png".encode("gbk"), "标准按键".encode("gbk"), 1, "0".encode("gbk"), "0".encode("gbk"),
                     fileName.encode("gbk"))
                )

                styleName = fileName.replace("over", "").replace("down", "").replace("disabled", "")
                tag = None
                if fileName.find("over") >= 0:
                    tag = "over"
                elif fileName.find("disabled") >= 0:
                    tag = "disabled"
                elif fileName.find("down") >= 0:
                    tag = "down"
                elif styleName == fileName:
                    tag = "comm"

                if len(styleName):
                    if isinstance(tag, str):
                        if styleName not in dStdBtn.keys():
                            dStdBtn.update({styleName: {}})
                        dStdBtn[styleName].update({tag: nId})

                nId += 1

            cur.execute(strDel, tuple(delParamList))
            cur.executemany(strInsert, tuple(insertParamList))
            con.commit()

            if RedisManager.is_alive():
                RedisManager.set("standard_button_image_style_map", dStdBtn)

            return True, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    """
    dStdBtn:
    {
        "red": {
            "comm": 1,
            "over": 2,
            "down": 3,
            "disabled": 4
        },
        "green": {
            "comm": 11,
            "over": 22,
            "down": 33",
            "disabled": 44
        },
        "yellow": {
            "comm": 111,
            "over": 222",
            "down": 333",
            "disabled": 444
        }
    }
    """
    def getStandardButtonImageInfo(self):
        if RedisManager.is_alive():
            dStdBtn = RedisManager.get("standard_button_image_style_map")
            if isinstance(dStdBtn, dict):
                return dStdBtn, ""

        fileNameList, dStyle = get_standard_button_image_from_static()
        if fileNameList == None or dStyle == None:
            return None, "检查发现后台图片静态文件夹不存在，请先升级后台"

        if fileNameList == 0 or dStyle == 0:
            return None, "检查发现某个风格的按钮缺失一个或多个情况下的特定图片，请先升级后台"

        if not isinstance(fileNameList, list) or not isinstance(dStyle, dict):
            return None, "后台图片静态文件获取失败，请先升级后台"

        if not len(fileNameList) or not len(dStyle):
            return None, "未获取到后台静态图片文件信息，可能静态文件夹为空，请先升级后台"

        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        dStdBtn = {}
        try:
            strQuery = "SELECT ID, unitproperty05 FROM lib_image WHERE "
            queryParamList = []
            sqlList = []
            for fileName in fileNameList:
                sqlList.append("unitproperty05=?")
                queryParamList.append(fileName.encode("gbk"))

            strQuery += " OR ".join(sqlList)

            cur.execute(strQuery, tuple(queryParamList))
            items = cur.fetchall()

            if not isinstance(items, list):
                return None, "获取标准按键信息失败"

            for item in items:
                key = item[1].decode("gbk")
                nImgId = item[0]
                if not isinstance(key, str):
                    continue
                if not len(key):
                    continue

                if key.find("disabled") == -1 and key.find("down") == -1 and key.find("over") == -1:
                    if key not in dStdBtn.keys():
                        dStdBtn.update({key: dict(comm=nImgId)})
                    else:
                        dStdBtn[key].update(dict(comm=nImgId))

                elif key.find("disabled") >= 0:
                    styleName = key.replace("disabled", "")
                    if len(styleName):
                        if styleName not in dStdBtn.keys():
                            dStdBtn.update({styleName: dict(comm=None)})
                        dStdBtn[styleName].update(dict(disabled=nImgId))

                elif key.find("down") >= 0:
                    styleName = key.replace("down", "")
                    if len(styleName):
                        if styleName not in dStdBtn.keys():
                            dStdBtn.update({styleName: dict(comm=None)})
                        dStdBtn[styleName].update(dict(down=nImgId))

                elif key.find("over") >= 0:
                    styleName = key.replace("over", "")
                    if len(styleName):
                        if styleName not in dStdBtn.keys():
                            dStdBtn.update({styleName: dict(comm=None)})
                        dStdBtn[styleName].update(dict(over=nImgId))

            return dStdBtn, ""
        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getLogicCustomName(self, dllName, roomName):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT DllName FROM list_dllstore WHERE unitproperty03 = ? or unitproperty03 = ?"
            cur.execute(strQuery, (dllName, dllName.encode("gbk")))
            items = cur.fetchall()
            if not isinstance(items, list):
                return "", "未发现dllName为{dllName}的策略配置".format(dllName=dllName)
            if not len(items):
                return "", "未发现dllName为{dllName}的策略配置".format(dllName=dllName)

            if len(items) == 1:
                curstomLogicName = None
                if isinstance(items[0][0], bytes):
                    try:
                        curstomLogicName = items[0][0].decode("gbk")
                    except:
                        curstomLogicName = items[0][0].decode("utf8")
                elif isinstance(items[0][0], str):
                    curstomLogicName = items[0][0]

                if isinstance(curstomLogicName, str) and len(curstomLogicName):
                    return curstomLogicName, ""
                return "", "获取用户自定义的策略名称失败"

            curstomLogicNameList = []
            for item in items:
                if not len(item):
                    continue
                name = None
                if isinstance(item[0], bytes):
                    try:
                        name = item[0].decode("gbk")
                    except:
                        name = item[0].decode("utf8")
                elif isinstance(item[0], str):
                    name = item[0]

                if isinstance(name, str) and len(name):
                    curstomLogicNameList.append(name)

            if not len(curstomLogicNameList):
                return "", ""

            strQuery2 = "SELECT vname, pname, DllName FROM list_paramterConfig WHERE "
            sqlList = []
            paramList = []
            for obj in curstomLogicNameList:
                sqlList.append("DllName=?")
                paramList.append(obj)
                sqlList.append("DllName=?")
                paramList.append(obj.encode("gbk"))

            strQuery2 += " OR ".join(sqlList)

            cur.execute(strQuery2, tuple(paramList))
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "查询失败"

            for item in items:
                if isinstance(item[0], bytes):
                    configName = item[0].decode("gbk")
                elif isinstance(item[0], str):
                    configName = item[0]
                else:
                    configName = item[0]

                if isinstance(item[1], bytes):
                    configValue = item[1].decode("gbk")
                elif isinstance(item[1], str):
                    configValue = item[1]
                else:
                    configValue = item[1]

                if isinstance(item[2], bytes):
                    customName = item[2].decode("gbk")
                elif isinstance(item[2], str):
                    customName = item[2]
                else:
                    customName = item[2]

                if configName == "RoomName" and configValue == roomName:
                    return customName, ""

            return "", "未发现指定的用户自定义策略名称"

        except Exception as e:
            return None, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def updateReportTemplateFile(self, nId, fileName, filePath):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strUpdate = "UPDATE template_files SET file_binary =?,file_name=?  WHERE id=?"
            cur.execute(strUpdate, (open(filePath, "rb").read(), fileName.encode("gbk"), nId))
            con.commit()
            return True, ""
        except Exception as e:
            return False, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getAllPageOrderByShowOrder(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = self.connect_readonly(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strQuery = "SELECT id, groupid, showOrder FROM list_page ORDER BY showOrder"
            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "获取页面id及排序信息失败"

            dataList = []
            for item in items:
                dataList.append(dict(id=item[0], groupId=item[1], order=item[2]))
            return dataList, ""
        except Exception as e:
            return None, "获取页面id及排序信息失败: %s" % e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def movePageToOtherGroup(self, nPageId, nTarGroupId, orderTplList):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strUpdate1 = "UPDATE list_page SET groupid = ? WHERE id = ?"
            cur.execute(strUpdate1, (nTarGroupId, nPageId))

            if len(orderTplList):
                strUpdate2 = "UPDATE list_page SET showOrder =? WHERE id=?"
                cur.executemany(strUpdate2, tuple(orderTplList))

            con.commit()
            return True, ""
        except Exception as e:
            return False, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def exchangePageShowOrder(self, nCurPageId, nCurOrder, oppositePageId, oppositeShowOrder):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strUpdate = "UPDATE list_page SET showOrder =? WHERE id=?"
            cur.executemany(strUpdate, ((nCurOrder, oppositePageId),
                                        (oppositeShowOrder, nCurPageId)))
            con.commit()
            return True, ""
        except Exception as e:
            return False, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def movePageGroupUpDown(self, paramList):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strUpdate = "UPDATE list_page SET showOrder=? WHERE id=?"
            cur.executemany(strUpdate, tuple(paramList))
            con.commit()
            return True, ""
        except Exception as e:
            return False, e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    def getMaxIdInDomImgLibTable(self, tableName):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return None, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return None, "图库文件不存在，请升级后台"

        con = self.connect_readonly(imgLibPath)

        con.text_factory = bytes
        cu = con.cursor()
        cu.execute("select max(id) from %s" % (tableName))
        nID = 0
        for item in cu.fetchall():
            if item[0]:
                nID = item[0]

        if cu is not None:
            cu.close()
        if con is not None:
            con.close()

        return nID, ""

    # nPictureId 为 DOMImageLib.4db -> lib_image 中的id
    # 将DOMImageLib.4db中的图片复制一个到domdb.4db中
    # 返回插入domdb.4db lib_image中的id
    def copyImgFromDomLibImage(self, nPictureId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return None, "图库文件不存在，请升级后台"

        imgLibPath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgLibPath):
            return None, "图库文件不存在，请升级后台"

        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)

        plantDir = os.path.join(imagesDir, "plant")
        if not os.path.exists(plantDir):
            os.mkdir(plantDir)

        projectDir = os.path.join(plantDir, "project")
        if not os.path.exists(projectDir):
            os.mkdir(projectDir)

        con = sqlite3.connect(imgLibPath)
        con.text_factory = bytes
        cur = con.cursor()
        stuff = None
        errMsg = ""
        try:
            strQuery = "SELECT id, name, specy, imagebinary, filetype, remark, issystemimage, unitproperty01, unitproperty02 FROM lib_image WHERE id=?"

            cur.execute(strQuery, (nPictureId,))
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "查询失败"

            if not len(items[0]):
                return None, "图库中未发现id为{id}的图片".format(id=nPictureId)

            stuff = list(items[0])

        except Exception as e:
            stuff = None
            errMsg = "图库中获取图片信息报错:%s" % e.__str__()
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

        if not isinstance(stuff, list):
            return None, errMsg

        if len(stuff) < 9:
            return None, "获取图库中的图片信息失败"

        nMaxId = self.getMaxIdInTable("lib_image")
        nId = nMaxId + 1
        stuff[0] = nId

        con = sqlite3.connect(domdbPath)
        con.text_factory = bytes
        cur = con.cursor()
        try:
            strInsert = "INSERT INTO lib_image (ID, name, specy, imagebinary, filetype, remark, issystemimage, unitproperty01, unitproperty02) VALUES (?,?,?,?,?,?,?,?,?)"
            cur.execute(strInsert, tuple(stuff))
            con.commit()

            # 将图片存入静态文件夹下
            fileBinary = stuff[3]
            imgFilePath = os.path.join(projectDir, "{id}.png".format(id=nId))
            try:
                os.remove(imgFilePath)
            except:
                pass

            with open(imgFilePath, "wb") as f:
                f.write(fileBinary)

            RedisManager.add_image_id_list_project(nId)
            return nId, ""

        except Exception as e:
            return None, "添加图片失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

    # 将动画从DomImageLib.4db中复制一份到domdb.4db中
    def copyAnimationFromDomLibImage(self, nAnimationId):
        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)

        plantDir = os.path.join(imagesDir, "plant")
        if not os.path.exists(plantDir):
            os.mkdir(plantDir)

        projectDir = os.path.join(plantDir, "project")
        if not os.path.exists(projectDir):
            os.mkdir(projectDir)

        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, None, "domdb.4db不存在"

        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            return None, None, "DOMImageLib.4db不存在，需升级dompysite"

        imgFilePath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgFilePath):
            return None, None, "DOMImageLib.4db不存在，需升级dompysite"

        nMaxIdLibAnimation = self.getMaxIdInTable("lib_animation")
        nIdLibAnimation = nMaxIdLibAnimation + 1

        nMaxIdLibImageAnimation = self.getMaxIdInTable("lib_image_animation")
        nMaxIdLibImageAnimationStart = nMaxIdLibImageAnimation + 1

        animationStuff = None      # DOMImageLib.4db中的动画
        animationImageStuffList = []  # DOMImageLib.4db中的动画图片
        nFrame = 1  # 帧数（动画的图片数量）


        con = None
        cur = None
        try:
            con = self.connect_readonly(imgFilePath)
            con.text_factory = bytes
            cur = con.cursor()

            strQuery = "SELECT id, name, animationlist FROM lib_animation WHERE id = ?"
            cur.execute(strQuery, (nAnimationId,))
            items = cur.fetchall()
            if not isinstance(items, list) or not len(items):
                return None, None, "从图库中转移动画至domdb.4db失败"

            if not len(items[0]):
                return None, None, "从图库中转移动画至domdb.4db失败"

            animationStuff = items[0]
            if len(animationStuff) < 3:
                return None, None, "图库中的动画(id:{id})有误".format(id=nAnimationId)
            animationStuff = list(animationStuff)
            animationStuff[0] = nIdLibAnimation

            strAnimationImageIdList = None
            if isinstance(items[0][2], str):
                strAnimationImageIdList = items[0][2].split(",")
            elif isinstance(items[0][2], bytes):
                strAnimationImageIdList = items[0][2].decode("gbk").split(",")

            if not isinstance(strAnimationImageIdList, list) or not len(strAnimationImageIdList):
                return None, None, "动画(id:{id})在DOMImageLib未发现图片"

            nFrame = len(strAnimationImageIdList)

            strQuery = "SELECT id, name, specy, imagebinary, filetype, remark, issystemimage FROM lib_image_animation WHERE id in (" + ",".join(strAnimationImageIdList) + ")"
            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list) or not len(items):
                return None, None, "从图库中转移动画至domdb.4db失败"

            nAnimationListNew = []  # 转移进入domdb.4db的lib_image_animation时图片id序列需要重做
            for item in items:
                if len(item) < 7:
                    continue
                item = list(item)
                item[0] = nMaxIdLibImageAnimationStart
                animationImageStuffList.append(tuple(item))

                nAnimationListNew.append(str(nMaxIdLibImageAnimationStart))
                nMaxIdLibImageAnimationStart += 1

            animationStuff[2] = ",".join(nAnimationListNew).encode("gbk")

        except Exception as e:
            return None, None, "从图库中转移动画至domdb.4db失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()

        if animationStuff == None:
            return None, None, "图库中未发现该动画(id:{id})".format(id=nAnimationId)

        if not len(animationImageStuffList):
            return None, None, "图库中动画(id:{id})不包含图片".format(id=nAnimationId)

        try:
            con = sqlite3.connect(domdbPath)
            cur = con.cursor()

            strInsert1 = "INSERT INTO lib_animation (id, name, animationlist) VALUES (?,?,?)"
            strInsert2 = "INSERT INTO lib_image_animation (id, name, specy, imagebinary, filetype, remark, issystemimage) VALUES (?,?,?,?,?,?,?)"

            cur.execute(strInsert1, tuple(animationStuff))
            cur.executemany(strInsert2, tuple(animationImageStuffList))
            con.commit()

            # 将animation图片放在静态文件夹下
            for obj in animationImageStuffList:
                imgPath = os.path.join(projectDir, "animation_{id}.png".format(id=obj[0]))
                try:
                    os.remove(imgPath)
                except:
                    pass

                with open(imgPath, "wb") as f:
                    f.write(obj[3])

            return nIdLibAnimation, nFrame, ""
        except Exception as e:
            return None, None, "从图库中转移动画至domdb.4db失败:{err}".format(err=e.__str__())
        finally:
            if cur:
                cur.close()
            if con:
                con.close()


    # 解压\static\img_lib\DOMImageLib.4db里的图片
    def prepareResourceFromDomImgLib(self):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imgFilePath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgFilePath):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)

        domImgLibDir = os.path.join(imagesDir, "dom-img-lib")
        if not os.path.exists(domImgLibDir):
            os.mkdir(domImgLibDir)

        # 清除dom-img-lib下的图片
        for fileName in listdir(domImgLibDir):
            filePath = path.join(domImgLibDir, fileName)
            try:
                if path.isfile(filePath):
                    unlink(filePath)
            except Exception as e:
                strError = 'prepareResourceFromDomImgLib清除dom-img-lib下的元素时报错:%s' % (e.__str__())
                print(strError)
                logging.error(strError)

        con = None
        cur = None
        try:
            con = self.connect_readonly(imgFilePath)
            con.text_factory = bytes
            cur = con.cursor()

            try:
                cur.execute("SELECT id, imagebinary FROM lib_image")
                items = cur.fetchall()
                for item in items:
                    elemPath = os.path.join(domImgLibDir, "{name}.png".format(name=item[0]))
                    with open(elemPath, "wb") as f:
                        f.write(item[1])
            except Exception as e1:
                strLog = "解压DOMImageLib.4db中的图片时报错:%s" % e1.__str__()
                print(strLog)
                logging.error(strLog)

            try:
                cur.execute("SELECT id, imagebinary FROM lib_image_animation")
                items = cur.fetchall()
                for item in items:
                    elemPath = os.path.join(domImgLibDir, "animation_{name}.png".format(name=item[0]))
                    with open(elemPath, "wb") as f:
                        f.write(item[1])

            except Exception as e2:
                strLog = "解压DOMImageLib.4db中的动画时报错:%s" % e2.__str__()
                print(strLog)
                logging.error(strLog)

        except Exception as e:
            strLog = "连接DOMImageLib.4db时报错: %s" % e.__str__()
            print(strLog)
            logging.error(strLog)

        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()

    # 从DomImageLib.4db解压出指定的图片
    def releaseImgFromDomImageLib(self, nImgIdOrList):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imgFilePath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgFilePath):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)

        domImgLibDir = os.path.join(imagesDir, "dom-img-lib")
        if not os.path.exists(domImgLibDir):
            os.mkdir(domImgLibDir)

        idList = []
        if isinstance(nImgIdOrList, list):
            idList = nImgIdOrList
        elif isinstance(nImgIdOrList, int):
            idList.append(nImgIdOrList)

        if not len(idList):
            return

        for nId in idList:
            fPath = os.path.join(domImgLibDir, "{id}.png".format(id=nId))
            if os.path.exists(fPath):
                try:
                    os.remove(fPath)
                except:
                    pass

        con = None
        cur = None
        try:
            con = self.connect_readonly(imgFilePath)
            con.text_factory = bytes
            cur = con.cursor()

            try:
                cur.execute("SELECT id, imagebinary FROM lib_image WHERE id in (" + ",".join([str(obj) for obj in idList]) + ")")
                items = cur.fetchall()
                for item in items:
                    elemPath = os.path.join(domImgLibDir, "{name}.png".format(name=item[0]))
                    with open(elemPath, "wb") as f:
                        f.write(item[1])
            except Exception as e1:
                strLog = "从DomImageLib.4db解压出指定的图片时报错:%s" % e1.__str__()
                print(strLog)
                logging.error(strLog)

        except Exception as e:
            strLog = "ERROR in releaseImgFromDomImageLib:%s" % e.__str__()
            print(strLog)
            logging.error(strLog)
        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()

    # 从DomImageLib.4db解压出指定的动画
    def releaseAnimationFromDomImageLib(self, nImgIdOrList):
        imgLibDir = os.path.join(app.static_folder, "img_lib")
        if not os.path.exists(imgLibDir):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imgFilePath = os.path.join(imgLibDir, "DOMImageLib.4db")
        if not os.path.exists(imgFilePath):
            print("DOMImageLib.4db不存在，需升级dompysite")
            return

        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)

        domImgLibDir = os.path.join(imagesDir, "dom-img-lib")
        if not os.path.exists(domImgLibDir):
            os.mkdir(domImgLibDir)

        idList = []
        if isinstance(nImgIdOrList, list):
            idList = nImgIdOrList
        elif isinstance(nImgIdOrList, int):
            idList.append(nImgIdOrList)

        if not len(idList):
            return

        for nId in idList:
            fPath = os.path.join(domImgLibDir, "{id}.png".format(id=nId))
            if os.path.exists(fPath):
                try:
                    os.remove(fPath)
                except:
                    pass

        con = None
        cur = None
        try:
            con = self.connect_readonly(imgFilePath)
            con.text_factory = bytes
            cur = con.cursor()

            try:
                cur.execute("SELECT id, imagebinary FROM lib_image_animation WHERE id in (" + ",".join([str(obj) for obj in idList]) + ")")
                items = cur.fetchall()
                for item in items:
                    elemPath = os.path.join(domImgLibDir, "animation_{id}.png".format(id=item[0]))
                    with open(elemPath, "wb") as f:
                        f.write(item[1])
            except Exception as e1:
                strLog = "从DomImageLib.4db解压出指定的动画时报错:%s" % e1.__str__()
                print(strLog)
                logging.error(strLog)

        except Exception as e:
            strLog = "ERROR in releaseAnimationFromDomImageLib:%s" % e.__str__()
            print(strLog)
            logging.error(strLog)
        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()

    # nItemId: domdb.4db中图片或动画id
    def getBindContentOnElement(self, nPageId, nElementId, nItemId):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return -1, None, None, None, None, "domdb.4db不存在"

        tarValue = None
        tarId = None
        tarFrame = None
        tarInterval = None
        con = None
        cur = None
        try:
            con = self.connect_readonly(domdbPath)
            con.text_factory = bytes
            cur = con.cursor()

            strQuery = "select e.bind_content from page_contain_elements pce left join event e on pce.elementid = e.id where pce.pageid = ? and pce.elementid = ?"
            cur.execute(strQuery, (nPageId, nElementId))
            items = cur.fetchall()
            if not isinstance(items, list):
                return 0, None, None, None, None, "获取元素的bind_content失败"

            if not len(items[0]):
                return 0, None, None, None, None, "获取元素的bind_content失败"

            if isinstance(items[0][0], str):
                strBindContent = items[0][0]
            elif isinstance(items[0][0], bytes):
                strBindContent = items[0][0].decode("gbk")
            else:
                strBindContent = None

            if strBindContent == None:
                return 0, None, None, None, None, "获取元素的bind_content失败"

            bindList = strBindContent.split("|")
            for strObj in bindList:
                strObjSplit = strObj.split(",")
                if len(strObjSplit) < 4:
                    continue

                try:
                    value = strObjSplit[0]
                    nId = int(strObjSplit[1])
                    nFrame = int(strObjSplit[2])
                    nInterval = int(strObjSplit[3])
                    if nId == nItemId:
                        tarValue = value
                        tarId = nId
                        tarFrame = nFrame
                        tarInterval = nInterval
                        break
                except:
                    pass

            if tarFrame== None:
                return -2, None, None, None, None, "未找到元素id为{id}的枚举量信息".format(id=nItemId)
            return 1, tarValue, tarId, tarFrame, tarInterval, ""

        except Exception as e:
            strLog = "ERROR in getBindContentOnElement:%s" % e.__str__()
            print(strLog)
            logging.error(strLog)
        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()

    def getFrameImgIdListOfAnimation(self, strAnimationIdList):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return None, "domdb.4db不存在"

        con = None
        cur = None
        try:
            con = self.connect_readonly(domdbPath)
            con.text_factory = bytes
            cur = con.cursor()

            strQuery = "SELECT animationlist, id FROM lib_animation WHERE id in (" + ",".join(strAnimationIdList) +")"
            cur.execute(strQuery)
            items = cur.fetchall()
            if not isinstance(items, list):
                return None, "获取动画对应的每一帧图片id列表失败"

            rt = {}
            for item in items:
                if isinstance(item[0], str):
                    strObj = item[0]
                elif isinstance(item[0], bytes):
                    strObj = item[0].decode("gbk")
                else:
                    strObj = None

                if strObj == None:
                    continue

                frameImgIdList = strObj.split(",")
                rt.update({str(item[1]): frameImgIdList})

            return rt, ""

        except Exception as e:
            strLog = "ERROR in getFrameImgIdListOfAnimation:%s" % e.__str__()
            print(strLog)
            logging.error(strLog)
        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()

    # 将所有页面的内容刷新一次至redis debug tool专用缓存中
    def initAllPageInfoIntoRedis_DebugTool(self):
        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return

        pageIdList, msg = self.getPageIdList()
        if not len(pageIdList):
            return

        for pageId in pageIdList:
            rvContent = self.getPlantDebugTool(pageId)
            if rvContent == None:
                continue
            RedisManager.set_4db_page_content_DebugTool(pageId, rvContent)

    def deleteElementsFromPage(self, nPageIdOrList, typeTag=None):
        nPageIdList = []
        if isinstance(nPageIdOrList, int):
            nPageIdList.append(nPageIdOrList)
        elif isinstance(nPageIdOrList, list):
            nPageIdList = nPageIdOrList

        if not len(nPageIdList):
            return True, ""

        domdbPath = app.config.get("USE_4DB_NAME")
        if not os.path.exists(domdbPath):
            return False, "domdb.4db不存在"

        con = None
        cur = None
        try:
            con = sqlite3.connect(domdbPath)
            con.text_factory = bytes
            cur = con.cursor()

            queryList = []
            if typeTag == "text" or typeTag == None:
                strDel = "DELETE FROM list_text WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "customControls" or typeTag == None:
                strDel = "DELETE FROM list_unit19 WHERE unitproperty01 = 'generalComponent' AND pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "button" or typeTag == None:
                strDel = "DELETE FROM list_button WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "checkbox" or typeTag == None:
                strDel = "DELETE FROM list_unit07 WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "image" or typeTag == None:
                strDel1 = "DELETE FROM page_contain_elements WHERE elementtype = 49 AND pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                strDel2 = "DELETE FROM event WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel1)
                queryList.append(strDel2)
            if typeTag == "line" or typeTag == None:
                strDel = "DELETE FROM list_line WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "systemEquipment" or typeTag == None:
                strDel = "DELETE FROM list_unit13 WHERE pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)
            if typeTag == "rectangle" or typeTag == None:
                strDel = "DELETE FROM list_unit19 WHERE unitproperty01 = 'rectangle' AND pageid in (" + ",".join([str(nId) for nId in nPageIdList]) + ")"
                queryList.append(strDel)

            if not len(queryList):
                return True, ""

            for sql in queryList:
                cur.execute(sql)
            con.commit()
            return True, ""
        except Exception as e:
            strLog = "ERROR in deleteElementsFromPage:%s" % e.__str__()
            print(strLog)
            logging.error(strLog)
            return False, strLog
        finally:
            if cur != None:
                cur.close()
            if con != None:
                con.close()


