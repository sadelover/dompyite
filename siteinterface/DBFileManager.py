
from siteinterface import app
from flask import g, json
from math import floor, ceil
import os, sys,shutil
import mysql.connector
from math import floor, ceil
from datetime import datetime,timedelta
import time
import logging


class DBFileManager:
    __instance = None

    def __init__(self):
        pass

    @classmethod
    def getInstance(self):
        if(self.__instance == None):
            self.__instance = DBFileManager()
        return self.__instance

    @classmethod
    def removeAllDBFile(cls):
        #tofix
        return None

    @classmethod
    def getTempDBFilePath(cls,):
        #tofix
        currentPath = os.getcwd()
        tempPath = os.path.join(currentPath , 'tempDBFile')
        try:
            os.mkdir(tempPath)
        except:
            pass
        return tempPath

    @classmethod
    def moveDBFromTempToMain(cls,corePath):
        currentPath = os.getcwd()
        tempPath = os.path.join(currentPath, 'tempDBFile')
        tempFilePath = os.path.join(tempPath, app.config['DB_FILE_NAME'])
        coreFilePath = os.path.join(corePath, app.config['DB_FILE_NAME'])

        shutil.copy(tempFilePath,coreFilePath)
        os.remove(tempFilePath)
        os.rmdir(tempPath)
        return True

    @classmethod
    def deleteDB(cls,corePath):
        DBFilePath = []
        for files in os.listdir(corePath):
            if os.path.splitext(files)[1] == '.4db':
                DBFilePath.append(os.path.join(corePath, files))
        for i in range(0,DBFilePath.__len__()):
            try:
                os.remove(DBFilePath[i])
            except Exception as e:
                print(e)

        return True