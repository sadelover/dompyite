from logic.MySQLOperator import MySQLOperator as mysql
import json
import numpy as np

def get_data_float(strPointName):
    return mysql.get_data_float(strPointName)

def get_data_bool(strPointName):
    nValue =  mysql.get_data_int(strPointName)
    if nValue>0:
        return True
    else:
        return False



def get_data_string(strPointName):
    return mysql.get_data_string(strPointName)


def get_data_int(strPointName):
    return mysql.get_data_int(strPointName)

def set_data_string(strPointName, strValue):
    return mysql.set_data_string(strPointName, strValue)

def set_data_float(strPointName, fValue):
    return mysql.set_data_string(strPointName, str(fValue))

def get_history_data(point, timeStart, timeEnd, timeFormat):
    return mysql.get_history_data(point, timeStart, timeEnd, timeFormat)