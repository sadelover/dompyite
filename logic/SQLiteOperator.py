#-*- coding: utf-8 -*-
__author__ = 'murphy'

from logic.SQLiteDataAccess import SQLiteDataAccess
from logic.Config import *
from logic.LogOperator import LogOperator
from datetime import datetime
import os
from os import path
from siteinterface import app

# search file
def search(path, word):
    for filename in os.listdir(path):
        fp = os.path.join(path, filename)
        if os.path.isfile(fp) and word in filename:
            return fp


#sqlite数据库操作类
class SQLiteOperator:
    _access = SQLiteDataAccess(**sqlite_config)
    _log_tables = []    # ???
    #_dbPathName = sqlite_config.get('database') + '.dec'

    currentPath = path.dirname(__file__)
    fatherPath = os.path.dirname(currentPath)
    fatherPath2 = os.path.dirname(fatherPath)
    # _dbPathName = search(fatherPath2, 's3db')
    # _dbPathName += '.dec'
    _dbPathName = search(fatherPath2, '4db')

    if _dbPathName == None:
        _dbPathName = search(fatherPath2, 's3db')
        if _dbPathName is not None:
            _dbPathName += '.dec'

    # if  app.config.get('USE_4DB_FILE_FORMAT'):
    #     
    # else :
    #     _dbPathName = search(fatherPath2, 's3db')
    #     _dbPathName += '.dec'


    # _dbPathName = search(fatherPath2, '4db')
    #读表
    @staticmethod
    def get_formula_group():
        rt = []
        try:
            sql = 'select unitproperty02, unitproperty03 from list_unit20 where unitproperty01 = 2001 and unitproperty04 != 0'
            rt = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
        except Exception as e:
            LogOperator().writeLog('Sqlite get_formula_group error, ' + str(e))
        return rt

    @staticmethod
    def get_formula_item(name):
        rt = []
        try:
            sql = 'select unitproperty02, unitproperty03 from list_unit20 where unitproperty01 = 2002 and unitproperty04 = "%s"' % (name)
            rt = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
        except Exception as e:
            LogOperator().writeLog('Sqlite get_formula_item error, ' + str(e))
        return rt

    @staticmethod
    def get_formula_all():
        rt = []
        try:
            arr1 = []
            sql1 = 'select unitproperty02, unitproperty03 from list_unit20 where unitproperty01 = 2001 and unitproperty04 != 0'
            arr1 = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql1)

            arr2 = []
            sql2 = 'select unitproperty02, unitproperty03, unitproperty04 from list_unit20 where unitproperty01 = 2002'
            arr2 = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql2)

            for item1 in arr1:
                name1 = str(item1[0])
                nPeriod = int(item1[1])
                dictEach = {'name':name1, 'period':nPeriod, 'contain':[]}
                for item2 in arr2:
                    name2 = str(item2[0])
                    formula = str(item2[1])
                    parent = str(item2[2])
                    if name1 == parent:
                        dictEach['contain'].append({'name2':name2, 'formula':formula})
                rt.append(dictEach)

        except Exception as e:
            LogOperator().writeLog('Sqlite get_formula_all error, ' + str(e))
        return rt

    #@staticmethod
    #def get_formula_all():
    #    rt = []
    #    try:
    #        sql = 'select unitproperty02, unitproperty03, unitproperty05 from list_unit20 where unitproperty01 = 2001 and unitproperty04 != 0'
    #        rt = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
    #    except Exception as e:
    #        LogOperator().writeLog(str(e))
    #    return rt

    @staticmethod
    def get_formula_by_period(period):
        rt = []
        try:
            #sql = 'select unitproperty02, unitproperty03, unitproperty05 from list_unit20 where unitproperty01 = 2001 and unitproperty04 != 0'
            sql = 'select unitproperty02, unitproperty05 from list_unit20 where unitproperty01 = 2001 and unitproperty04 != 0 and unitproperty03 = %d' % (period)
            rt = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
        except Exception as e:
            LogOperator().writeLog('Sqlite get_formula_by_period error, ' + str(e))
        return rt

    @staticmethod
    def get_data_string(point):
        rt = []
        try:
            if isinstance(point, str):
                pointList = [point]
            else:
                pointList = point
            dbrv = {}
            sql = 'select unitproperty02, unitproperty05 from list_unit20 where ' \
                  'unitproperty01 = 2001 and ' \
                  'unitproperty04 != 0 and ' \
                  'unitproperty02 in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
            for x in rvQuery:
                dbrv.update(**{x[0]:str(x[1])})
            if isinstance(point, str):
                rt = dbrv.get(point, None)
            else:
                for pt in pointList:
                    rt.append(dbrv.get(pt, None))
        except Exception as e:
            LogOperator().writeLog('Sqlite get_data_string error, ' + str(e))
        return rt

    @staticmethod
    def get_data_int(point):
        rt = []
        try:
            if isinstance(point, str):
                pointList = [point]
            else:
                pointList = point
            dbrv = {}
            sql = 'select unitproperty02, unitproperty05 from list_unit20 where ' \
                  'unitproperty01 = 2001 and ' \
                  'unitproperty04 != 0 and ' \
                  'unitproperty02 in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
            for x in rvQuery:
                try:
                    v = int(float(x[1]))
                except:
                    v = None
                dbrv.update(**{x[0]:v})
            if isinstance(point, str):
                rt = dbrv.get(point, None)
            else:
                for pt in pointList:
                    rt.append(dbrv.get(pt, None))
        except Exception as e:
            LogOperator().writeLog('Sqlite get_data_int error, ' + str(e))
        return rt

    @staticmethod
    def get_data_float(point):
        rt = []
        try:
            if isinstance(point, str):
                pointList = [point]
            else:
                pointList = point
            dbrv = {}
            sql = 'select unitproperty02, unitproperty05 from list_unit20 where ' \
                  'unitproperty01 = 2001 and ' \
                  'unitproperty04 != 0 and ' \
                  'unitproperty02 in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = SQLiteOperator._access.query(SQLiteOperator._dbPathName, sql)
            for x in rvQuery:
                try:
                    v = float(x[1])
                except:
                    v = None
                dbrv.update(**{x[0]:v})
            if isinstance(point, str):
                rt = dbrv.get(point, None)
            else:
                for pt in pointList:
                    rt.append(dbrv.get(pt, None))
        except Exception as e:
            LogOperator().writeLog('Sqlite get_data_float error, ' + str(e))
        return rt

    #写输出表
    @staticmethod
    def set_data(point, value):
        rt = False
        try:
            if isinstance(point, str):
                if isinstance(value, list):
                    return False
                pointList = [point]
                valueList = [value]
            else:
                if isinstance(point, list) and isinstance(value, list):
                    pointList = point
                    valueList = value
                else:
                    return False
            if pointList and valueList:
                if len(pointList) == len(valueList):
                    count = 0
                    for i in range(0, len(pointList)):
                        sql = 'insert into list_unit20(unitproperty01, unitproperty02, unitproperty05) values(2001, %s, %s) on duplicate key update pointvalue=%s'
                        parameters = (pointList[i], valueList[i], valueList[i])
                        r = SQLiteOperator._access.update(SQLiteOperator._dbPathName, sql, parameters)
                        if not r:
                            LogOperator().writeLog('set list_unit20 failed, pointname=%s, pointvalue=%s'%(pointList[i], valueList[i]))
                        else:
                            count += 1
                    if count == len(pointList):
                        rt = True
        except Exception as e:
            LogOperator().writeLog('Sqlite set_data error, ' + str(e))
        return rt

    #写用户的log
    @staticmethod
    def write_log(strText):
        try:
            if strText:
                table_name = SQLiteOperator.create_log_table_if_not_exist()
                if table_name is not None:
                    sql = "INSERT INTO "+ table_name + " VALUES(now(), %s);"
                    r = SQLiteOperator._access.update(SQLiteOperator._dbPathName, sql, (strText,))
                    if not r:
                        LogOperator().writeLog('execute sql(%s) failed' % (sql,))
                        return False
        except Exception as e:
            LogOperator().writeLog('Sqlite write_log error, ' + str(e))
            return False
        return True


    @staticmethod
    def create_log_table_if_not_exist():
        try:
            now = datetime.now()
            table_name = 'log_{0:04d}_{1:02d}_{2:02d}'.format(now.year, now.month, now.day)
            if not SQLiteOperator._log_tables:
                SQLiteOperator._log_tables = SQLiteOperator.get_all_log_table_names()
            if table_name not in SQLiteOperator._log_tables:
                sql = "CREATE TABLE " + table_name + "(`time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00', " \
                                                     "`loginfo` varchar(1024) DEFAULT NULL) ENGINE = InnoDB DEFAULT CHARSET = utf8;"
                r = SQLiteOperator._access.update(SQLiteOperator._dbPathName, sql, ())
                if not r:
                    LogOperator().writeLog('create table %s failed' % (table_name,))
                    return None
                else:
                    SQLiteOperator._log_tables.append(table_name)
        except Exception as e:
            LogOperator().writeLog('Sqlite create_log_table_if_not_exist error, ' + str(e))
            return None
        return table_name

    @staticmethod
    def get_all_log_table_names():
        rt = []
        try:
            sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s and TABLE_NAME like 'log_%%'"
            parameters = (SQLiteOperator._dbPathName,)
            ret = SQLiteOperator._access.query('INFORMATION_SCHEMA', sql, parameters)
            if ret:
                rt = [x[0] for x in ret]
        except Exception as e:
            LogOperator().writeLog('Sqlite get_all_log_table_names error, ' + str(e))
        return rt