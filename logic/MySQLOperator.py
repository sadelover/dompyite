#-*- coding: utf-8 -*-
__author__ = 'yan'

from logic.MySQLDataAccess import MySQLDataAccess
from logic.Config import *
from logic.LogOperator import LogOperator
from datetime import datetime

#mysql数据库操作类
class MySQLOperator:
    """description of class"""

    _access = MySQLDataAccess(**mysql_config)
    _log_tables = []

    #读历史数据
    @staticmethod
    def get_history_data(point, timeStart, timeEnd, timeFormat):
        rt = []
        try:
            if isinstance(point, str):
                pointList = [point]
            else:
                pointList = point
            dbrv = {}

            strTableName = 'historydata'
            if 's5' == timeFormat:
                strTableName += '_5second'
            elif 'm1' == timeFormat:
                strTableName += '_minute'
            elif 'm5' == timeFormat:
                strTableName += '_5minute'
            elif 'h1' == timeFormat:
                strTableName += '_hour'
            else:
                return rt

            start = datetime.strptime(timeStart, '%Y-%m-%d %H:%M:%S')
            startSuffix = start.strftime('_%Y_%m_%d')
            strTableName += startSuffix

            sql = 'select pointname, value, time from %s where ' \
                  'pointname in (%s) and time > "%s" and time < "%s"'\
                  % (strTableName, str(pointList).replace('[', '').replace(']', ''), timeStart, timeEnd)
            rt = MySQLOperator._access.query(mysql_config.get('database'), sql)
        except Exception as e:
            LogOperator().writeLog('MySql get_history_data error, ' + str(e))
        return rt

    #读实时表
    @staticmethod
    def get_data_string(point):
        rt = []
        try:
            if isinstance(point, str):
                pointList = [point]
            else:
                pointList = point
            dbrv = {}
            sql = 'select pointname, pointvalue from realtimedata_input where ' \
                  'pointname in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = MySQLOperator._access.query(mysql_config.get('database'), sql)
            for x in rvQuery:
                dbrv.update(**{x[0]:str(x[1])})
            if isinstance(point, str):
                rt = dbrv.get(point, None)
            else:
                for pt in pointList:
                    rt.append(dbrv.get(pt, None))
        except Exception as e:
            LogOperator().writeLog('MySql get_data_string error, ' + str(e))
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
            sql = 'select pointname, pointvalue from realtimedata_input where ' \
                  'pointname in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = MySQLOperator._access.query(mysql_config.get('database'), sql)
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
            LogOperator().writeLog('MySql get_data_int error, ' + str(e))
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
            sql = 'select pointname, pointvalue from realtimedata_input where ' \
                  'pointname in (%s)' % (str(pointList).replace('[', '').replace(']', ''))
            rvQuery = MySQLOperator._access.query(mysql_config.get('database'), sql)
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
            LogOperator().writeLog('MySql get_data_float error, ' + str(e))
        return rt

    #写输出表
    @staticmethod
    def set_data_string(point, value):
        rt = False
        try:
            if isinstance(point, str):
                pointList = [point]
                valueList = [value]
            else:
                return False
            if pointList and valueList:
                if len(pointList) == len(valueList):
                    count = 0
                    for i in range(0, len(pointList)):
                        sql = 'insert into realtimedata_output(pointname, pointvalue) values(%s, %s) on duplicate key update pointvalue=%s'
                        parameters = (pointList[i], valueList[i], valueList[i])
                        r = MySQLOperator._access.update(mysql_config.get('database'), sql, parameters)
                        if not r:
                            LogOperator().writeLog('set realtimedata_output failed, pointname=%s, pointvalue=%s'%(pointList[i], valueList[i]))
                        else:
                            count += 1
                    if count == len(pointList):
                        rt = True
        except Exception as e:
            LogOperator().writeLog('MySql set_data error, ' + str(e))
        return rt

    @staticmethod
    def set_data_string_batch(point, value):
        rt = False
        try:
            if isinstance(point, list) and isinstance(value, list):
                pointList = point
                valueList = value
            else:
                return False

            if pointList and valueList:
                if len(pointList) == len(valueList):
                    count = 0
                    for i in range(0, len(pointList)):
                        sql = 'insert into realtimedata_output(pointname, pointvalue) values(%s, %s) on duplicate key update pointvalue=%s'
                        parameters = (pointList[i], valueList[i], valueList[i])
                        r = MySQLOperator._access.update(mysql_config.get('database'), sql, parameters)
                        if not r:
                            LogOperator().writeLog('set realtimedata_output failed, pointname=%s, pointvalue=%s' % (
                            pointList[i], valueList[i]))
                        else:
                            count += 1
                    if count == len(pointList):
                        rt = True
        except Exception as e:
            LogOperator().writeLog('MySql set_data error, ' + str(e))
        return rt


    #写用户的log
    @staticmethod
    def write_log(strText):
        try:
            if strText:
                table_name = MySQLOperator.create_log_table_if_not_exist()
                if table_name is not None:
                    sql = "INSERT INTO "+ table_name + " VALUES(now(), %s);"
                    r = MySQLOperator._access.update(mysql_config.get('database'), sql, (strText,))
                    if not r:
                        LogOperator().writeLog('execute sql(%s) failed' % (sql,))
                        return False
        except Exception as e:
            LogOperator().writeLog('MySql write_log error, ' + str(e))
            return False
        return True


    @staticmethod
    def create_log_table_if_not_exist():
        try:
            now = datetime.now()
            table_name = 'log_{0:04d}_{1:02d}_{2:02d}'.format(now.year, now.month, now.day)
            if not MySQLOperator._log_tables:
                MySQLOperator._log_tables = MySQLOperator.get_all_log_table_names()
            if table_name not in MySQLOperator._log_tables:
                sql = "CREATE TABLE " + table_name + "(`time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00', " \
                                                     "`loginfo` varchar(1024) DEFAULT NULL) ENGINE = InnoDB DEFAULT CHARSET = utf8;"
                r = MySQLOperator._access.update(mysql_config.get('database'), sql, ())
                if not r:
                    LogOperator().writeLog('create table %s failed' % (table_name,))
                    return None
                else:
                    MySQLOperator._log_tables.append(table_name)
        except Exception as e:
            LogOperator().writeLog('MySql create_log_table_if_not_exist error, ' + str(e))
            return None
        return table_name

    @staticmethod
    def get_all_log_table_names():
        rt = []
        try:
            sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s and TABLE_NAME like 'log_%%'"
            parameters = (mysql_config.get('database'),)
            ret = MySQLOperator._access.query('INFORMATION_SCHEMA', sql, parameters)
            if ret:
                rt = [x[0] for x in ret]
        except Exception as e:
            LogOperator().writeLog('MySql get_all_log_table_names error, ' + str(e))
        return rt