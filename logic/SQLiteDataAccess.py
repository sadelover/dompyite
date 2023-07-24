# -*- encoding=utf-8 -*-
__author__ = 'murphy'

import sqlite3
from logic.LogOperator import LogOperator


# sqlite数据库执行类
class SQLiteDataAccess(object):
    """description of class"""

    def __init__(self, *args, **kwargs):
        try:
            self._connection = None
        except Exception as e:
            LogOperator().writeLog('Sqlite init error, ' + str(e))

    def get_connection(self, dbname):
        con = None
        try:
            con = sqlite3.connect(dbname)
            #con.execute('PRAGMA key = ""')
            #con.commit()
        except Exception as e:
            if con is not None:
                con.close()
            LogOperator().writeLog('Sqlite connect error, ' + str(e))
        return con

    def release(self, con, cur):
        try:
            if cur is not None:
                cur.close()
            if con is not None:
                con.close()
        except Exception as e:
            LogOperator().writeLog('Sqlite release error, ' + str(e))

    def query(self, dbname, strQuery, parameter=()):
        con = None
        cur = None
        rv = []
        try:
            con = self.get_connection(dbname)
            if con is None:
                LogOperator().writeLog('con is None: %s, %s', dbname, strQuery)
                return rv
            cur = con.cursor()
            if len(parameter) > 0:
                cur.execute(strQuery, parameter)
            else:
                cur.execute(strQuery)
            rv = cur.fetchall()
        except Exception as e:
            LogOperator().writeLog('Sqlite query error, ' + str(e))
        finally:
            self.release(con, cur)
        return rv

    def update(self, dbname, strQuery, parameter=()):
        con = None
        cur = None
        rt = False
        try:
            con = self.get_connection(dbname)
            if con is None:
                LogOperator().writeLog('con is None: %s, %s', dbname, strQuery)
            else:
                cur = con.cursor()
                if len(parameter) > 0:
                    cur.execute(strQuery, parameter)
                else:
                    cur.execute(strQuery)
                con.commit()
                rt = True
        except Exception as e:
            LogOperator().writeLog('Sqlite update error, ' + str(e))
        finally:
            self.release(con, cur)
        return rt
