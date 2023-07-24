# -*- coding: utf-8 -*-

__author__ = 'golding'

from siteinterface import app
from math import floor, ceil
import os, sys
from math import floor, ceil
from datetime import datetime,timedelta
import time
import logging
import threading
from siteinterface.BEOPDataAccess import *
from siteinterface.BEOPSqliteAccess import *

class BEOPDataBufferController:
    _dataRealtime = dict()
    _lock = threading.Lock()
    __instance = None
    _pointList = []

    def __init__(self):
        self.initPointList()
        if BEOPDataAccess.getInstance().getServerOption('sitemode')=='0':
            self.initWriteInputTable()

    @classmethod
    def getInstance(self):
        if(self.__instance == None):
            self.__instance = BEOPDataBufferController()
        return self.__instance

    def initPointList(self):
        self._pointList = BEOPSqliteAccess.getInstance('BEOPDataBufferController::initPointList').getPointListFromS3db('beop') #'beop' need to be modified as the s3db name in the path

    def initWriteInputTable(self):
        return

    def setValue(self, pointName, pointValue):
        if self._lock.acquire(30):
            self._dataRealtime[pointName] = [datetime.now(), pointValue]

        else:
            strError = 'ERROR: wait lock timeout'
            logging.error(strError)
            return False

    def getValue(self, pointName):
        rv = None
        if self._lock.acquire(30):
            if pointName in self._dataRealtime.keys():
                rv = self._dataRealtime[pointName][1]
            self._lock.release()
        else:
            strError = 'ERROR: wait lock timeout'
            logging.error(strError)
        return rv

    def getValues(self):
        rv = None
        if self._lock.acquire(30):
            rv = self._dataRealtime
            self._lock.release()
        else:
            strError = 'ERROR: wait lock timeout'
            logging.error(strError)

        return rv

    def isThirdPartySetValueEnabled(self):
        if 'ThirdPartyWriteEnable' in self._dataRealtime.keys():
            if self._dataRealtime['ThirdPartyWriteEnable'] =='1':
                return True
        return False
