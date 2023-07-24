import logging
import os
from siteinterface import app
from siteinterface.BEOPDataAccess import BEOPDataAccess
from datetime import datetime


def fetchEnvImportTable(infoTable, tableName):
    """
    获取导入的表格
    """
    res = None
    try:
        staticFolder = app.static_folder
        tempFolder = os.path.join(staticFolder, "files")
        if not os.path.exists(tempFolder):
            os.mkdir(tempFolder)

        tempFolder = os.path.join(tempFolder, "temp")
        if not os.path.exists(tempFolder):
            os.mkdir(tempFolder)

        saveFilePath = os.path.join(tempFolder, tableName)
        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)
        infoTable.save(saveFilePath)

        res = saveFilePath

    except Exception as e:
        strLog = "ERROR in fetchInfoTable: %s" % e.__str__()
        print(strLog)
        logging.error(strLog)
    finally:
        return res

def noDuplicatePointsInEnvDetail(pointList, envid):
    """
    检查导入的点名在该场景ID下是否已存在于数据库中
    """
    res = False
    try:
        for point in pointList:
            rvConduct = BEOPDataAccess.getInstance().countPointNameInEnvDetail(envid, point)
            if rvConduct is None:
                return False
            if rvConduct and len(rvConduct):
                if len(rvConduct[0]):
                    if rvConduct[0][0] > 0:
                        return res
        res = True

    except Exception as e:
        strLog = "ERROR in checkIfPointsExistOnEnvid: %s" % e.__str__()
        logging.error(strLog)
    finally:
        return res

def valuesFromTableQualified(valueList):
    """
    检查导入的数据是否合格
    """
    res = False
    try:
        if not len(valueList):
            return res

        for value in valueList:
            if len(value) < 2:
                return res

            if isinstance(value[0], str):
                if not len(value[0]):
                    return res

            if isinstance(value[1], str):
                if not len(value[1]):
                    return res

        res = True

    except Exception as e:
        strLog = "ERROR in valuesFromTableQualified: %s" % e.__str__()
        logging.error(strLog)
    finally:
        return res

def envIdExistsInEnv(envid):
    """
    检查evnid是否已存在于env表中
    """
    res = False
    try:
        rvConduct = BEOPDataAccess.getInstance().envIdExistsInEnv(envid)
        if rvConduct and len(rvConduct):
            if len(rvConduct[0]):
                if rvConduct[0][0] > 0:
                    res = True

    except Exception as e:
        strLog = "ERROR in envIdExistsInDB: %s" % e.__str__()
        logging.error(strLog)

    finally:
        return res

def convertStrIntoInt(string):
    res = None
    try:
        res = int(string)
    except:
        pass
    finally:
        return res

def bubbleSort(dataList):
    try:
        if not len(dataList):
            return None

        n = len(dataList)
        for i in range(n):
            for j in range(0, n - i - 1):
                if dataList[j] > dataList[j+1]:
                    dataList[j], dataList[j+1] = dataList[j+1], dataList[j]
    except:
        pass
    finally:
        return dataList

def isValidDate(strDate, strFormat):
    res = False
    try:
        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res

def log_info_to_file(strLogFileName, strLogInfo):
    strLogPath = os.path.join(os.getcwd(), 'log')
    strLogFilePath = os.path.join(strLogPath, strLogFileName)

    tNow = datetime.now()
    with open(strLogFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S')+ '    ' + strLogInfo + '\n')


