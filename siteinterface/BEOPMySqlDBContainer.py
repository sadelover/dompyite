# -*- coding: utf-8 -*-

"""
Routes and views for the flask application.
"""

from . import app
from flask import g, json
from math import floor, ceil
import os, sys
import mysql.connector
from math import floor, ceil
from datetime import datetime,timedelta
import time
import logging
import mysql.connector.locales.eng.client_error
import traceback
from mysql.connector import errors


g_mysql_last_pool_exhaust_time = {}


def mysql_log_info(strFileName, strLog):
    strLogDir = os.path.join(os.getcwd(), "log")
    if not os.path.exists(strLogDir):
        os.mkdir(strLogDir)

    hisDataLogDir = os.path.join(strLogDir, "mysql")
    if not os.path.exists(hisDataLogDir):
        os.mkdir(hisDataLogDir)

    logFilePath = os.path.join(hisDataLogDir, strFileName)

    tNow = datetime.now()
    with open(logFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S') + '    ' + strLog + '\n')


class BEOPMySqlDBContainer:

    def __init__(self, strPoolName=None, strDBUserName='root'):
        if strPoolName is None:
            self._strPoolName = app.config['DB_POOL_NAME']
        else:
            self._strPoolName = strPoolName

        self._strDBUserName = strDBUserName
        self._strDBUserPwd = app.config['PASSWORD']
        if self._strDBUserName!="root":
            self._strDBUserPwd = 'DOM.cloud-2016'


    def get_db(self, dbname):
        db = None
        bNeedRetryRoot = False
        try:
            db = mysql.connector.connect(
                    user=self._strDBUserName,
                    password=self._strDBUserPwd,
                    host=app.config['HOST'], #数据库地址
                    pool_name= self._strPoolName,
                    pool_size= app.config['INIT_CONNECTIONS_POOL'],
                    database='')

        except errors.PoolError as PoolErr:
            if PoolErr.__str__().find("exhausted") > 0:
                strLog = "MYSQL POOL EXHAUSTED !!!(poolName: {poolName}, userName: {userName})".format(poolName=self._strPoolName,
                                                                                                       userName=self._strDBUserName)
                print(strLog)
                logging.error(strLog)
                g_mysql_last_pool_exhaust_time.update(dict(last=datetime.now()))
                if db:
                    db.close()
                return None

        except Exception as e:
            if e.__str__().find('Access denied')>=0 and app.config['USERNAME']!="root":
                bNeedRetryRoot = True
            else:
                strError = 'Error Exception in get_db(poolname:%s):%s'%(self._strPoolName, e.__str__())
                print(strError)
                logging.error(strError)
                if db:
                    db.close()
                return None

        if bNeedRetryRoot:
            self._strDBUserName = "root"
            self._strDBUserPwd = "RNB.beop-2013"
            try:
                db = mysql.connector.connect(
                    user=self._strDBUserName,
                    password=self._strDBUserPwd,
                    host=app.config['HOST'],
                    pool_name=self._strPoolName,
                    pool_size=app.config['INIT_CONNECTIONS_POOL'],
                    database='')

            except Exception as e:
                    strError = 'Error Exception in get_db(poolname:%s):%s' % (self._strPoolName, e.__str__())
                    print(strError)
                    logging.error(strError)
                    if db:
                        db.close()
                    return None

        try:
            setResult = db.set_database(dbname)
            return db
        except Exception as e:
            logging.error(e)
            db.set_database(app.config['DATABASE'])
            db.close()
            return None

    def release_db(self, db, cur):
        if cur is not None:
            cur.close()
        if db is not None:
            db.close()

    def test_db_connection_is_living(self, dbName, ):
        #print(dbName + ' :  ' + strQuery)
        db = None
        cur = None
        rv = False
        print('test db connection is living')
        try:
            db = self.get_db(dbName)
            # 是否连接成功
            if db is None:
                rv = False
            else:
                rv = True

        except mysql.connector.Error as e:
            strError = 'mysql error occured when test db connection is living. Exception:%s' % ( e.__str__())
            print(strError)
            logging.error(strError)
            rv  = False
        except Exception as e:
            strError = 'mysql error occured when test db connection is living: %s. Exception:%s' % ( e.__str__())
            print(strError)
            logging.error(strError)
            rv = False
        finally:
            self.release_db(db, cur)
            return rv

    def op_db_query(self, dbName, strQuery, parameter=()):
        db = None
        cur = None
        rv = []
        print(strQuery)
        try:
            db = self.get_db(dbName)
            # 是否连接成功
            if db is None:
                logging.error('beoplog: op_db_query self._db is None: %s, %s', dbName, strQuery)
                rv = None
                return rv

            cur = db.cursor()
            if len(parameter) > 0:
                cur.execute(strQuery, parameter)
            else:
                cur.execute(strQuery)
            rv = cur.fetchall()
            db.commit()

        except mysql.connector.Error as e:
            strError = 'mysql error occured when query: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            logging.error(strError)
            rv  = None

        except Exception as e:
            strError = 'mysql error occured when query: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            logging.error(strError)
            rv = None
        finally:
            self.release_db(db, cur)
            return rv


    def op_db_update(self, dbName, strQuery, parameter=()):
        db = None
        cur = None
        print(strQuery)
        try:
            db = self.get_db(dbName)
            if db is None:
                return False
            cur= db.cursor()
            if len(parameter)>0:
                cur.execute(strQuery, parameter)
            else:
                cur.execute(strQuery)
            db.commit()
        except Exception as e:
            strError = 'mysql error occured when execute: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            print(parameter)
            logging.error(strError)

            return False
        finally:
            self.release_db(db, cur)
        return True

    def op_db_transaction_update_many(self, dbName, queryList, paramList):
        db = None
        cur = None
        rt = False
        print(queryList)
        try:
            db = self.get_db(dbName)
            if db is None:
                return False
            cur = db.cursor()
            for idx, strQuery in enumerate(queryList):
                if len(paramList[idx])>0:
                    if isinstance(paramList[idx][0], tuple):
                        cur.executemany(strQuery, paramList[idx])
                    else:
                        cur.execute(strQuery, paramList[idx])
                else:
                    cur.execute(strQuery)
            db.commit()
            rt = True
        except Exception as e:
            strErr = "ERROR in mysql query(op_db_transaction_update): %s. queryList:%s. paramList:%s" % (e.__str__(), str(queryList), str(paramList))
            logging.error(strErr)
            #db.rollback()
        finally:
            self.release_db(db, cur)
            return rt

    def op_db_update_many(self, dbName, strQuery, parameter):
        db = None
        cur = None
        print(strQuery)
        try:
            db = self.get_db(dbName)
            if db is None:
                return False
            cur= db.cursor()
            if cur is None:
                return False
            if len(parameter)>0:
                cur.executemany(strQuery, parameter)
            else:
                cur.execute(strQuery)
            db.commit()
        except Exception as e:
            strError = 'mysql error occured when execute: %s *** %s, Exception:%s' % (strQuery, str(parameter), e.__str__())
            print(strError)
            print(parameter)
            logging.error(strError)

            return False
        finally:
            self.release_db(db, cur)
        return True

    def op_db_insert(self, dbName, strQuery, parameter=()):
        db = None
        cur = None
        lastrowid = None
        print(strQuery)
        try:
            db = self.get_db(dbName)
            cur= db.cursor()
            if len(parameter)>0:
                cur.execute(strQuery, parameter)
            else:
                cur.execute(strQuery)
            db.commit()
        except Exception as e:
            strError = 'mysql error occured when execute: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            print(parameter)
            logging.error(strError)

            return {
                'success': False,
                'lastrowid': None
            }
        finally:
            lastrowid = cur.lastrowid
            self.release_db(db, cur)
        return {
            'success': True,
            'lastrowid': lastrowid
        }

    def op_db_delete(self, dbName, strQuery):
        #print(dbName + ' :  ' + strQuery)
        db = None
        cur = None
        rv = []
        print(strQuery)
        try:
            db = self.get_db(dbName)
            # 是否连接成功
            if db is None:
                logging.error('beoplog: op_db_query self._db is None: %s, %s', dbName, strQuery)
                return rv
            cur = db.cursor()
            if len(strQuery) > 0:
                cur.execute(strQuery)
            db.commit()
        except mysql.connector.Error as e:
            strError = 'mysql error occured when delete: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            logging.error(strError)
        except Exception as e:
            strError = 'mysql error occured when delete: %s. Exception:%s' % (strQuery, e.__str__())
            print(strError)
            logging.error(strError)
        finally:
            self.release_db(db, cur)
            return rv

    def op_db_update_with_id(self, dbName, strQuery, parameter=()):
        # print(dbName + ' :  ' + strQuery)
        # print(parameter)
        db = None
        cur = None
        new_id = -1
        try:
            db = self.get_db(dbName)
            if db is None:
                strError = 'error: get db failed :' + dbName
                print(strError)
                logging.error(strError)
            else:
                cur = db.cursor()
                if len(parameter) > 0:
                    cur.execute(strQuery, parameter)
                else:
                    cur.execute(strQuery)
                new_id = cur.lastrowid
                db.commit()
        except mysql.connector.Error as e:
            strError = 'mysql error occured when execute: %s.' % strQuery
            print(strError)
            logging.error(strError)
            print(e)
            logging.error(e)
        finally:
            self.release_db(db, cur)
            return new_id