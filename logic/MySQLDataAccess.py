# -*- encoding=utf-8 -*-
__author__ = 'yan'

import mysql.connector
from logic.LogOperator import LogOperator
from siteinterface import app

#mysql数据库执行类
class MySQLDataAccess(object):
    """description of class"""

    def __init__(self, *args, **kwargs):
        try:
            self._connection = None
            if kwargs:
                self.user = kwargs.get('user', 'root')
                if not self.user:
                    raise Exception('key user is missing')
                self.password = kwargs.get('password', 'RNB.beop-2013')
                if not self.password:
                    raise Exception('key password is missing')
                self.host = kwargs.get('host', 'localhost')
                if not self.host:
                    raise Exception('key host is missing')
                self.pool_name = kwargs.get('pool_name', 'syncdata')
                if not self.pool_name:
                    raise Exception('key pool_name is missing')
                self.pool_size = kwargs.get('pool_size', 2)
                if not self.pool_size:
                    raise Exception('key pool_size is missing')
                self.database = kwargs.get('database', app.config['DATABASE'])
                if not self.database:
                    raise Exception('key database is missing')
        except Exception as e:
            LogOperator().writeLog('MySql init error, ' + str(e))
    
    def get_connection(self, dbname):
        con = None
        try:
            con = mysql.connector.connect(
                    user = self.user,
                    password = self.password,
                    host = self.host,
                    pool_name = self.pool_name,
                    pool_size = self.pool_size,
                    database = self.database)
            if con:
                con.database = dbname
        except Exception as e:
            if con:
                con.close()
            LogOperator().writeLog('MySql connection error, ' + str(e))
        return con

    def release(self, con, cur):
        try:
            if cur:
                cur.close()
            if con:
                con.close()
        except Exception as e:
            LogOperator().writeLog('MySql release error, ' + str(e))
        

    def query(self, dbname, strQuery, parameter=()):
        """
            query interface
        """

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
            con.commit()
        except Exception as e:
            LogOperator().writeLog('MySql query error, ' + str(e))
        finally:
            self.release(con, cur)
        return rv

    def update(self, dbname, strQuery, parameter=()):
        """
            update and insert interface
        """
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
            LogOperator().writeLog('MySql update error, ' + str(e))
        finally:
            self.release(con, cur)
        return rt


        
            


