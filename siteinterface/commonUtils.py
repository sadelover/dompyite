# -*- encoding=utf-8 -*-
__author__ = 'huangzhijun'
import os, sys, imp, time, inspect, re, glob
import pdfkit
from flask import render_template
from datetime import datetime, timedelta, date
import calendar as cal
import string
import json
from configparser import ConfigParser
import uuid
import logging
from siteinterface.processManager import ProcessManager
import subprocess
import struct
import chardet
import requests
from siteinterface.OSSTool import OSSTool
from siteinterface import app


class MyConf(ConfigParser):
    def __init__(self):
        ConfigParser.__init__(self, defaults=None)

    def optionxform(self, strOption):
        return strOption


def validate_string(tmp,name):
    if tmp is None or not isinstance(tmp, str):
        msg = json.dumps(dict(err=1, msg='%s must be a str or value' % (name)), ensure_ascii=False)
    else:
        msg = None

    return msg

def validate_number(tmp,name):
    if tmp is None or not  str(tmp).isdigit():
        msg = json.dumps(dict(err=1, msg='%s must be a number or value' % (name)), ensure_ascii=False)
    else:
        msg = None

    return msg

#限制为0和1的数字
def validate_restricted_number(tmp,name):
    if tmp is None:
        msg = json.dumps(dict(err=1, msg='%s must be 0 or 1' % (name)), ensure_ascii=False)
    else:
        if tmp == 0 or tmp == 1:
            msg = None
        else:
            msg = json.dumps(dict(err=1, msg='%s must be 0 or 1' % (name)), ensure_ascii=False)
    return msg

#把时间格式03：30 转成 3.5 03：00 转成3
def timeToInt(timeStr):
    timeStr1 = timeStr.strip()
    if timeStr1 is None or timeStr1 == "":
        return 0

    curtime = time.strptime(timeStr1, '%H:%M')
    minutesStr = time.strftime("%M", curtime)
    num = 0
    if int(minutesStr) >= 30:
        num = 0.5
    return int(time.strftime("%H", curtime)) + num

#把时间格式3.5 转成  03：00 转成3 转成03：00
def intToTime(timeStr):
    timeStr1 = timeStr.strip()
    if timeStr1 is None or timeStr1 =="":
        return ""

    timeNum= ""
    if "." in timeStr:
        nums=timeStr.split('.')
        if(nums[1] == '5'):
            timeNum = "%s:%s" %(nums[0].zfill(2),"30")
        else:
            timeNum = "%s:%s" % (nums[0].zfill(2), "00")
    else:
        timeNum = timeStr.zfill(5)

    return timeNum


def time_get_first_day_of_next_month(flag_time):
    nYear = flag_time.year
    nMonth = flag_time.month+1
    if nMonth>12:
        nYear+=1
        nMonth = 1
    flag_time_new = datetime(nYear, nMonth, 1,0,0,0)

    return flag_time_new


def time_get_today_begin():
    tNow = datetime.now()
    tBegin = tNow.replace(hour=0, minute=0, second=0)
    return tBegin


def time_get_today_end():
    tNow = datetime.now()
    tEnd = tNow.replace(hour=23, minute=59, second=59)
    return tEnd


def time_get_first_day_of_next_year(flag_time):
    nYear = flag_time.year + 1
    flag_time_new = datetime(nYear, 1,1,0,0,0)

    return flag_time_new

def time_get_first_day_of_one_month_this_year(nMonth, flag_time):
    flag_time_new = flag_time.replace(month=nMonth, day=1, hour=0, minute=0, second=0)

    return flag_time_new

def time_get_first_day_of_next_month_this_year(nMonth, flag_time):
    nYear = flag_time.year
    if nMonth>=12:
        nYear+=1
        nMonth = 1
    else:
        nMonth+=1
    flag_time_new = flag_time.replace(year=nYear, month=nMonth, day=1, hour=0, minute=0, second=0)

    return flag_time_new

def time_get_first_day_of_this_month(flag_time):
    flag_time_new = flag_time.replace(day=1,hour=0, minute=0,second=0)

    return flag_time_new

def numericItemToInt(itemInput):
    res = None
    try:
        if isinstance(itemInput, bytes):
            res = int(float(itemInput))
        elif isinstance(itemInput, float):
            res = int(itemInput)
        elif isinstance(itemInput, str):
            res = int(float(itemInput))
        else:
            res = itemInput
    except:
        pass
    finally:
        return res

def to_time_format_string(timeStr,format):
    if timeStr is None or timeStr == "":
        return timeStr
    else:
        return timeStr.strftime(format)

def get_number_format(strValue):
    rvValue = strValue
    try:
        rvValue = float(rvValue)
    except:
        pass

    return rvValue


# 资产管理标准模板设备信息
# `cn_name`, `en_name`, `ui_type`, `group_num`, `sort_num`, `project_id`
standardAssetTmplDef = {
            "冷机": [["名称", "name", 1, 1, 1, 0],
                   ["标识", "identity", 1, 1, 2, 0],
                   ["品牌", "brand", 1, 1, 3, 0],
                    ["型号", "model", 1, 1, 4, 0],
                   ["制冷量(ton)", "capacity", 1, 1, 5, 0],
                   ["额定电压(V)", "ratingVoltage", 1, 1, 6, 0],
                   ["额定功率(kW)", "ratingPower", 1, 1, 7, 0],
                   ["额定电流(A)", "ratedCurrent", 1, 1, 8, 0],
                   ["使用电压范围(V)", "voltageRange", 1, 1, 9, 0],
                   ["最小承载电流(A)", "minLoadCurrent", 1, 1, 10, 0],
                   ["制冷剂名称", "refrigerant", 1, 1, 11, 0],
                   ["制冷剂理论充注量(kg)", "refrigerantWeight", 1, 1, 12, 0],
                   ["机组总质量(kg)", "weight", 1, 1, 13, 0],
                    ["制造日期", "productionDate", 1, 1, 12, 0],
                    ["制冷剂侧设计压力（高压）(kPa)", "refrigerantDesignPressureHigh", 1, 1, 14, 0],
                    ["制冷剂侧设计压力（低压）(kPa)", "refrigerantDesignPressureLow", 1, 1, 15, 0],
                    ["冷凝器最大工作压力(kPa)", "condMaxPressure", 1, 1, 16, 0],
                    ["蒸发器最大工作压力(kPa)", "evapMaxPressure", 1, 1, 17, 0],
                    ["蒸发器水流量(m3/h)", "evapChWFlowRate", 1, 1, 18, 0],
                    ["蒸发器额定压降(bar)", "evapDP", 1, 1, 19, 0],
                    ["蒸发器最小流量(m3/h)", "evapChWFlowMin", 1, 1, 20, 0],
                    ["蒸发器最大流量(m3/h)", "evapChWFlowMax", 1, 1, 21, 0],
                    ["蒸发器污垢系数(m2-deg C/kw)", "evapScalingFactor", 1, 1, 22, 0],
                    ["冷凝器水流量(m3/h)", "condCWFlowRate", 1, 1, 23, 0],
                    ["冷凝器额定压降(bar)", "condDP", 1, 1, 24, 0],
                    ["冷凝器最小流量(m3/h)", "condCWFlowMin", 1, 1, 25, 0],
                    ["冷凝器最大流量(m3/h)", "condCWFlowMax", 1, 1, 26, 0],
                    ["冷凝器污垢系数(m2-deg C/kw)", "condScalingFactor", 1, 1, 27, 0]
                   ],
            "水泵": [
                ["名称", "name", 1, 1, 1, 0],
                ["标识", "identity", 1, 1, 2, 0],
                ["品牌", "brand", 1, 1, 3, 0],
                ["流量(m3/h)", "flow", 1, 1, 4, 0],
                ["扬程(m)", "head", 1, 1, 5, 0],
                ["泵效率", "efficiency", 1, 1, 6, 0],
                ["转速(rpm)", "speed", 1, 1, 7, 0],
                ["最大压力(bar)", "maxPressure", 1, 1, 8, 0],
                ["最高温度(℃)", "maxTemp", 1, 1, 9, 0]
            ],
            "冷却塔": [
                ["名称", "name", 1, 1, 1, 0],
                ["标识", "identity", 1, 1, 2, 0],
                ["品牌", "brand", 1, 1, 3, 0],
                ["冷却能力(kcal/h)", "coolingCapacity", 1, 1, 4, 0],
                ["处理水量(m3/h)", "cwflow", 1, 1, 5, 0],
                ["入口温度(℃)", "enterTemp", 1, 1, 6, 0],
                ["出口温度(℃)", "leaveTemp", 1, 1, 7, 0],
                ["外气湿球温度(℃)", "outdoorWetTemp", 1, 1, 8, 0],
                ["风机电机电压(V)", "fanVoltage", 1, 1, 9, 0],
                ["风机电机满频频率(Hz)", "fanFrequency", 1, 1, 10, 0],
                ["风机电机功率(kW)", "fanPower", 1, 1, 11, 0],
                ["散水泵电机电压(V)", "pumpVoltage", 1, 1, 12, 0],
                ["散水泵电机满频频率(Hz)", "pumpFrequency", 1, 1, 13, 0],
                ["散水泵电机功率(kW)", "pumpPower", 1, 1, 14, 0]
            ],
            "空压机": [
                ["名称", "name", 1, 1, 1, 0],
                ["标识", "identity", 1, 1, 2, 0],
                ["品牌", "brand", 1, 1, 3, 0],
                ["型号", "model", 1, 1, 4, 0],
                ["额定工作压力(MPa)", "ratingPressure", 1, 1, 5, 0],
                ["最大工作压力(MPa)", "maxPressure", 1, 1, 6, 0],
                ["排气量(L/s)", "airExhaustVolumePerSecond", 1, 1, 7, 0],
                ["额定轴功率(kW)", "ratingShaftPower", 1, 1, 8, 0],
                ["启动轴转速(r/min)", "startupShaftSpeed", 1, 1, 9, 0],
                ["净重(kg)", "weight", 1, 1, 10, 0],
                ["外形尺寸(长X宽X高)", "weight", 1, 1, 11, 0],
                ["制造日期", "productionDate", 1, 1, 12, 0],
                ["吸气量(m3/min)", "intakeCapacity", 1, 1, 12, 0],
                ["吸气压力(MPa)", "intakePressure", 1, 1, 13, 0],
                ["排气压力(MPa)", "dischargePressure", 1, 1, 14, 0],
                ["额定转速(rpm)", "ratingSpeed", 1, 1, 15, 0],
                ["吸气温度(℃)", "intakeTemperature", 1, 1, 16, 0],
            ],
            "干燥机": [
                ["名称", "name", 1, 1, 1, 0],
                ["标识", "identity", 1, 1, 2, 0],
                ["品牌", "brand", 1, 1, 3, 0],
                ["型号", "model", 1, 1, 4, 0],
                ["处理气量(Nm3/min)", "volume", 1, 1, 5, 0],
                ["工作压力(MPa)", "operatingPressure", 1, 1, 6, 0],
                ["露点温度(℃)", "dewpointTemperature", 1, 1, 7, 0],
                ["加热功率(kW)", "heaterPower", 1, 1, 8, 0],
                ["干燥剂", "desiccant", 1, 1, 9, 0],
                ["干燥机充注量", "desiccantWeight", 1, 1, 10, 0]
            ],
            "空调箱": [
                ["名称", "name", 1, 1, 1, 0],
                ["标识", "identity", 1, 1, 2, 0],
                ["品牌", "brand", 1, 1, 3, 0],
                ["型号", "model", 1, 1, 4, 0],
                ["额定风量(m3/h)", "ratingAirVolume", 1, 1, 5, 0],
                ["供冷量(kW)", "coolingCapacity", 1, 1, 6, 0],
                ["供热量(kW)", "heatingCapacity", 1, 1, 7, 0],
                ["机组全静压(Pa)", "totalStaticPressure", 1, 1, 8, 0],
                ["机外静压(Pa)", "externalStaticPressure", 1, 1, 9, 0],
                ["机组电压(V)", "voltage", 1, 1, 10, 0],
                ["机组段数", "sectionNumber", 1, 1, 11, 0],
                ["机组重量(kg)", "weight", 1, 1, 12, 0],
                ["采用标准", "standard", 1, 1, 13, 0],
                ["外形尺寸", "size", 1, 1, 14, 0],
                ["电机功率(kW)", "size", 1, 1, 15, 0]]
        }


def assign_vpoint_recalculation_task(taskList):
    if not len(taskList):
        return True

    try:
        dTask = {}
        for task in taskList:
            if not task.get("point", "") or not task.get("time", ""):
                continue

            strKey = "{pointName}@@@{time}".format(pointName=task.get("point"), time=task.get("time"))
            dTask.update(
                {strKey: task.get("value")}
            )

        coreDir = os.path.dirname(os.getcwd())
        domJobsDir = os.path.join(coreDir, "domJobs")
        if not os.path.exists(domJobsDir):
            return None

        siteinterfaceDir = os.path.join(domJobsDir, "siteinterface")
        if not os.path.exists(siteinterfaceDir):
            os.mkdir(siteinterfaceDir)

        staticDir = os.path.join(siteinterfaceDir, "static")
        if not os.path.exists(staticDir):
            os.mkdir(staticDir)

        queueDir = os.path.join(staticDir, "queue")
        if not os.path.exists(queueDir):
            os.mkdir(queueDir)

        strFileName = "reCalculation_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        jsonFilePath = os.path.join(queueDir, strFileName)

        dJson = {}
        if os.path.exists(jsonFilePath):
            with open(jsonFilePath, "r", encoding="UTF8") as oFile:
                dJson = json.load(oFile)

        dJson.update(dTask)

        if os.path.exists(jsonFilePath):
            os.remove(jsonFilePath)

        with open(jsonFilePath, "w", encoding="UTF8") as oFile:
            json.dump(dJson, oFile)

        return True

    except Exception as e:
        logging.error("ERROR in assign_vpoint_recalculation_task: %s" % e.__str__())
        return False

def is_english_word(word):
    bIs = True
    for char in word:
        if (char >= u'\u0041' and char <= u'\u005a') or (char >= u'\u0061' and char <= u'\u007a'):
            bIs = True
        else:
            bIs = False
            break
    return bIs

def is_one_number(tar):
    try:
        n = float(tar)
        return True
    except:
        return False

def find_next_nearest_time_in_5_seconds(tTime):
    try:
        tProtect = (tTime + timedelta(minutes=2)).replace(second=0)
        tCur = tTime
        while True:
            if tCur.second % 5 == 0:
                return tCur

            tCur += timedelta(seconds=1)

            if tCur > tProtect:
                return tProtect

    except Exception as e:
        print(e.__str__())

def find_last_nearest_time_in_5_seconds(tTime):
    try:
        tProtect = (tTime - timedelta(minutes=2)).replace(second=0)
        tCur = tTime
        while True:
            if tCur.second % 5 == 0:
                return tCur

            tCur -= timedelta(seconds=1)

            if tCur < tProtect:
                return tProtect
    except Exception as e:
        print(e.__str__())

def update_mysql_my_ini_config(myIniPath, innodb_file_per_table, tmp_table_size, max_heap_table_size):
    if innodb_file_per_table == None and tmp_table_size == None and max_heap_table_size == None:
        return True

    try:
        conf = MyConf()
        conf.read(myIniPath)
        if conf.has_section("mysqld"):
            if innodb_file_per_table != None:
                conf["mysqld"].update({"innodb_file_per_table": str(innodb_file_per_table)})

            if tmp_table_size != None:
                conf["mysqld"].update({"tmp_table_size": "{num}M".format(num=tmp_table_size)})

            if max_heap_table_size != None:
                conf["mysqld"].update({"max_heap_table_size": "{num}M".format(num=max_heap_table_size)})

            with open(myIniPath, "w") as file:
                conf.write(file)

        return True
    except Exception as e:
        print(e.__str__())
        return False

def get_mysql_my_ini_config(myIniPath):
    conf = MyConf()
    res = {}
    if not os.path.exists(myIniPath):
        return {}

    conf.read(myIniPath)

    if conf.has_section("client"):
        if conf.has_option("client", "port"):
            res.update({"port": conf["client"]["port"]})

    if conf.has_section("mysql"):
        if conf.has_option("mysql", "default-character-set"):
            res.update({"default-character-set": conf["mysql"]["default-character-set"]})

    if conf.has_section("mysqld"):
        if conf.has_option("mysqld", "default-storage-engine"):
            res.update({"default-storage-engine": conf["mysqld"]["default-storage-engine"]})

        if conf.has_option("mysqld", "max_connections"):
            res.update({"max_connections": conf["mysqld"]["max_connections"]})

        if conf.has_option("mysqld", "innodb_file_per_table"):
            res.update({"innodb_file_per_table": conf["mysqld"]["innodb_file_per_table"]})

        if conf.has_option("mysqld", "tmp_table_size"):
            res.update({"tmp_table_size": conf["mysqld"]["tmp_table_size"]})

        if conf.has_option("mysqld", "max_heap_table_size"):
            res.update({"max_heap_table_size": conf["mysqld"]["max_heap_table_size"]})

    return res


class ConfigIniManager:
    def __init__(self):
        self.strFilePath = self.get_config_filePath()
        self.conf = MyConf()
        self.dAll = {
            "mysql": ["dbip"],
            "data": ["decimal"],
            "projectdb": ["dbFileName"],
            "cloud": ["projectname", "fileUploadServer"],
            "log": ["level"],
            "host": ["domhost"]
        }

    def get_config_filePath(self):
        filePath = os.path.join(os.getcwd(), "config.ini")
        if not os.path.exists(filePath):
            return None
        return filePath

    def get_content_of_option(self, strOption):
        content = None
        sectionName = None
        for key, optionList in self.dAll.items():
            if strOption in optionList:
                sectionName = key
                break

        if sectionName == None:
            return None

        if not self.strFilePath:
            return None

        self.conf.read(self.strFilePath)
        if self.conf.has_section(sectionName):
            if self.conf.has_option(sectionName, strOption):
                content = self.conf[sectionName][strOption]
        return content

    def set_content_of_options(self, name, value):
        nameList = []
        valueList = []
        try:
            if isinstance(name, str) and isinstance(value, str):
                nameList = [name]
                valueList = [value]
            elif isinstance(name, str) and is_one_number(value):
                nameList = [name]
                valueList = [value]
            elif isinstance(name, list) and isinstance(value, list):
                if len(name) == len(value):
                    nameList = name
                    valueList = value

            if not len(nameList):
                return False

            dSet = {}
            for sectionName, optionList in self.dAll.items():
                for idx, name in enumerate(nameList):
                    if name in optionList:
                        dSet.update({sectionName: {name: str(valueList[idx])}})

            if not self.strFilePath:
                return None

            self.conf.read(self.strFilePath)

            for key, value in dSet.items():
                self.conf[key].update(value)

            with open(self.strFilePath, "w") as fo:
                self.conf.write(fo)

            return True
        except Exception as e:
            print(e.__str__())
            return False


"""
现有的完整的进程列表
hostType: 0-无需添加驻守(domhost默认驻守)；1-需要添加驻守
seconds: 在线升级时的等待秒数
vsrc: core服务器上进程版本的存放位置
vkey: redis中的进程当前版本查询键
logOpType: log操作类型（0-不可只通过操作config.ini控制日志打印开关；1-可通过操作config.ini控制日志打印开关）
sttSrc: 启动时间(startupTime)的存放位置
sttKey: 启动时间(startupTime)在redis中的查询键
"""
allProcList = [{"name": "dompysite", "vsrc": "self", "vkey": "", "hostType": 0, "seconds": 60*8, "logOpType": 1, "sttSrc": "redis", "sttKey": "StartupTimeDompysite"},
                {"name": "domcore", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0, "sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic01", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic02", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0, "sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic03", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic04", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domlogic05", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domhost", "vsrc": "redis", "vkey": "VersionDomhost", "hostType": 0, "seconds": 60*2, "logOpType": 1, "sttSrc": "redis",  "sttKey": "StartupTimeDomhost"},
                {"name": "domModbusClientCore", "vsrc": "redis", "vkey": "VersionDomModbusClientCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomModbusClientCore"},
                {"name": "domCloudSync", "vsrc": "redis", "vkey": "VersionDomCloudSync", "hostType": 0, "seconds": 60*2, "logOpType": 1, "sttSrc": "redis", "sttKey": "StartupTimeDomCloudSync"},
                {"name": "domKNXCore", "vsrc": "redis", "vkey": "VersionDomKNXCore", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomKNXCore"},
                {"name": "domKNXMonitor", "vsrc": "redis", "vkey": "VersionDomKNXMonitor", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomKNXMonitor"},
                {"name": "domBacnetCore", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domBacnetCore1", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domBacnetCore2", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domBacnetCore3", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domBacnetCore4", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domBacnetCore5", "vsrc": "redis", "vkey": "VersionDomBacnetCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomBacnetCore"},
                {"name": "domABSLCCore", "vsrc": "redis", "vkey": "VersionDomABSLCCore", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomABSLCCore"},
                {"name": "domDLT645Core", "vsrc": "redis", "vkey": "VersionDomDLT645Core", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomDLT645Core"},
                {"name": "domOPCUACore", "vsrc": "redis", "vkey": "VersionDomOPCUACore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomOPCUACore"},
                {"name": "domLogixCore", "vsrc": "redis", "vkey": "VersionDomLogixCore", "hostType": 0, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomLogixCore"},
                {"name": "domJobs", "vsrc": "redis", "vkey": "VersionDomJobs", "hostType": 0, "seconds": 60*2, "logOpType": 1, "sttSrc": "redis","sttKey": "StartupTimeDomJobs"},
                {"name": "domModbusServer", "vsrc": "redis", "vkey": "VersionDomModbusServer", "hostType": 1, "seconds": 60*6, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomModbusServer"},
                {"name": "domObixCore", "vsrc": "redis", "vkey": "VersionDomObixCore", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": "StartupTimeDomObixCore"},
                {"name": "domSiemenseTCPCore", "vsrc": "unit01", "vkey": "", "hostType": 0, "seconds": 60*2, "logOpType": 0,"sttSrc": "unit01", "sttKey": ""},
                {"name": "domCloudMQTTCenter", "vsrc": "redis", "vkey": "VersionDomCloudMQTTCenter", "hostType": 1, "seconds": 60*2, "logOpType": 1,"sttSrc": "redis", "sttKey": ""},
                {"name": "domDCIMDataDriver", "vsrc": "redis", "vkey": "VersionDomDCIMDataDriver", "hostType": 1, "seconds": 60*2, "logOpType": 0,"sttSrc": "redis", "sttKey": "StartupTimeDomDCIMDataDriver"},
                {"name": "redis", "vsrc": "", "vkey": "", "hostType": 0, "seconds": 0},
                {"name": "omsite", "vsrc": "", "vkey": "", "hostType": 0, "seconds": 0},
                {"name": "domUpdate", "vsrc": "redis", "vkey": "VersionDomUpdate", "hostType": 0, "seconds": 0, "logOpType": 1, "sttSrc": "redis", "sttKey": "StartupTimeDomUpdate"},
                {"name": "domOPCUAServer", "vsrc": "redis", "vkey": "VersionDomOPCUAServer", "hostType": 1, "seconds": 60*3, "logOpType": 0, "sttSrc": "redis", "sttKey": "StartupTimeDomOPCUAServer"}]


def find_ip_list(tar):
    if not isinstance(tar, str):
        return []

    matchList = re.findall(r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)", tar)
    return matchList

def is_ip(tar):
    if re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", tar):
        return True
    return False

def is_digit(tar):
    try:
        n = float(tar)
        return True
    except:
        return False

def is_int_digit(tar):
    try:
        n = int(tar)
        return True
    except:
        return False

def get_network_segment(strIp):
    if not isinstance(strIp, str):
        return None
    les = strIp.split(".")

    if len(les) != 4:
        return None
    return ".".join(les[0:3])

# 获取服务器网卡信息
def get_server_adapters():
    interfList = subprocess.check_output(['ipconfig']).decode('gbk').split('\n')
    lineList = []
    for intref in interfList:
        if intref == "\r":
            continue

        data = intref.replace("\r", "")
        lineList.append(data)

    dAdapters = {}
    dRouter = {}

    curAdapterName = None
    for line in lineList:

        # 寻找路由IP
        if line.find("默认网关") >= 0:
            matchList = find_ip_list(line)
            if len(matchList):
                seg = get_network_segment(matchList[0])
                dRouter.update({seg: matchList[0]})

        if not line.startswith(" "):
            line = line.strip()
            if line.endswith(":"):
                line = line[:-1]
            curAdapterName = line
            continue

        if line.startswith(" "):
            matchList = find_ip_list(line)
            if len(matchList) and line.find("IPv4") >= 0:
                if curAdapterName != None:
                    dAdapters.update({matchList[0]: {"adapterName": curAdapterName, "routerIp": None}})

    for ip, dInfo in dAdapters.items():
        seg = get_network_segment(ip)
        if dRouter.get(seg, None):
            dInfo.update({"routerIp": dRouter[seg]})
        else:
            dInfo.update({"routerIp": "未知"})

    return dAdapters

def is_time_string(tar, format):
    if not isinstance(tar, str):
        return False

    try:
        tTime = datetime.strptime(tar, format)
        return True
    except:
        return False

def ping_ip(strIP):
    result = os.system('ping %s' % strIP)
    if result == 0:
        return True
    return False

def get_energy_management_node_info(dNode):
    if not isinstance(dNode, dict):
        return []

    if not dNode:
        return []

    if dNode.get("children", []):
        les = []
        for dChild in dNode.get("children"):
            infoList = get_energy_management_node_info(dChild)
            les.extend(infoList)
        return les
    else:
        gatewayId = dNode.get("gatewayId")
        meterId = dNode.get("meterId")
        name = dNode.get("name")
        no = dNode.get("no")
        return [dict(gatewayId=gatewayId, meterId=meterId, name=name, no=no)]

"""
{"gatewayId": {"meterId": {}}}
"""
def analysis_energy_management_structure(dEMConfig):
    dStruct = {}
    infoList = get_energy_management_node_info(dEMConfig)
    for info in infoList:
        if info["gatewayId"].startswith("modbusTCP:"):
            continue

        if info["gatewayId"] not in dStruct.keys():
            dStruct.update({info["gatewayId"]: {}})

        dGateway = dStruct[info["gatewayId"]]
        if info["meterId"] not in dGateway.keys():
            dGateway.update({info["meterId"]: {}})

        dMeter = dGateway[info["meterId"]]
        dMeter.update(dict(gatewayId=info["gatewayId"], meterId=info["meterId"], name=info["name"], no=info["no"]))
    return dStruct


def shutdown_processes(exceptProcNameList):
    if len(exceptProcNameList):
        excNameList = [item.replace(".exe", "").lower() for item in exceptProcNameList]
    else:
        excNameList = []

    for dProc in allProcList:
        if dProc.get("name", None) == None:
            continue

        if not isinstance(dProc.get("name"), str):
            continue

        if not len(dProc.get("name", "")):
            continue

        if dProc.get("name").lower() not in excNameList:
            continue

        try:
            procNameWithExt = "{procName}.exe".format(procName=dProc.get("name"))
            if ProcessManager.getInstance().findProcess(procNameWithExt):
                print("shutting down: {name}".format(name=procNameWithExt))
                ProcessManager.getInstance().killProcess(procNameWithExt)
                time.sleep(0.1)
        except:
            pass


"""
删除nSeconds之前的过期文件
"""
def remove_files_specified_seconds_ago(walkDir, nSeconds):
    for root, dirs, files in os.walk(walkDir):
        for file in files:
            timeList = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}", file)
            if not len(timeList):
                continue

            strTime = timeList[0]
            tTime = datetime.strptime(strTime, "%Y-%m-%d-%H-%M-%S")

            if (datetime.now() - tTime).total_seconds() > nSeconds:
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass



"""
检查编码类型：
0- bytes ch utf8
1- bytes ch gbk
2- bytes en
3- str
-2- 其他数据类型（非bytes、非str)
-1- 不明
"""
def check_encoding(tar):
    if type(tar) not in [str, bytes]:
        return -2

    if isinstance(tar, str):
        return 3

    if isinstance(tar, bytes):
        try:
            tentative = tar.decode("gbk")
        except:
            try:
                tentative = tar.decode("utf8")
            except:
                return -1

        if tentative >= u"\u4e00" and tentative <= u"\u9fff":  # 是汉字
            det = chardet.detect(tar)
            if isinstance(det, dict):
                if det.get("confidence", 0) > 0:
                    strEnco = det.get("encoding", "").lower()
                    if re.match(r"^iso-[0-9]*.*$", strEnco):
                        return 1

                    if strEnco in ["gb2312"]:
                        return 1

                    if strEnco in ["utf-8", "utf8"]:
                        return 0

                    if det.get("encoding", "").lower() == "utf-8":
                        return 0
        else:
            return 2

    return -1

def check_bytes_encoding(tar):
    rt = chardet.detect(tar)
    if not isinstance(rt, dict):
        return None
    strEncoding = rt.get("encoding", "")
    if isinstance(strEncoding, str):
        strEncoding = strEncoding.replace("-", "").lower()
        if strEncoding == "utf8":
            return 0
        elif strEncoding == "gbk":
            return 1
    return None

def get_cloud_user_info(userId):
    headers = {"Content-Type": "application/json"}
    postData = {"userId": userId}
    rsp = None
    try:
        rsp = requests.post("http://47.100.17.99/api/mobile/getUserInfo", data=json.dumps(postData), headers=headers, timeout=15)
        if rsp.status_code != 200:
            return []
    except:
        return []

    try:
        dData = json.loads(rsp.text)
        userInfoList = dData.get("data", {}).get("userInfo", [])
        return userInfoList
    except:
        return []

def cloud_verification(userName, password):
    post_data = {'name': userName, 'pwd': password}

    try:
        headers = {'content-type': 'application/json'}
        r = requests.post('http://47.100.17.99/api/login/2', data=json.dumps(post_data), headers=headers, timeout=300)
        if r.status_code != 200:
            return False, {}

        rvdata = json.loads(r.text)
        return rvdata.get("status", False), rvdata.get("userProfile", {})
    except:
        return False, {}

def update_template_info_to_cloud(fileNameWithExt, version, nType, userId, description):
    headers = {"Content-Type": "application/json"}
    postData = {"fileName": fileNameWithExt, "version": version, "type": nType, "userId": userId, "description": description}

    try:
        rsp = requests.post("http://47.100.17.99/api/refreshTemplateInfo", data=json.dumps(postData), headers=headers,
                            timeout=15)
        if rsp.status_code != 200:
            return False
    except:
        return False

    try:
        dData = json.loads(rsp.text)
        bSuc = dData.get("data", False)
        return bSuc
    except:
        return False

def get_all_process_name_list():
    continuousProcessNameList = ['domKNXMonitor', 'dompysite', 'domJobs',
                                 'domOPCUACore', 'domKNXCore', 'domDCIMDataDriver',
                                 'domDLT645Core', 'domBacnetCore', 'domABSLCCore', 'domlogic', 'domSiemenseTCPCore',
                                 'domUpdate', 'domModbusClientCore', 'domcore', 'domModbusServer', 'domCloudSync',
                                 'domhost', 'domLogixCore', 'domObixCore']

    discontinousProcessNameList = ["domBackupMysql", "domUpload"]

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    lfPath = os.path.join(tempDir, "update_{time}.json".format(time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")))
    if os.path.exists(lfPath):
        try:
            os.remove(lfPath)
        except:
            pass

    bDownload = OSSTool().download("update/update.json", lfPath)
    if not bDownload or not os.path.exists(lfPath):
        strLog = "下载update.json失败，返回默认列表"
        logging.error(strLog)
        print(strLog)

        return continuousProcessNameList, discontinousProcessNameList

    with open(lfPath, "r", encoding="UTF8", errors="ignore") as fo:
        try:
            dJson = json.load(fo)
        except:
            dJson = {}

    if not isinstance(dJson, dict) or not dJson:
        try:
            os.remove(lfPath)
        except:
            pass
        return continuousProcessNameList, discontinousProcessNameList

    continuousProcessNameList.clear()
    discontinousProcessNameList.clear()
    for key, value in dJson.items():
        if isinstance(value, dict) and value.get("runType", "") == "discontinuous" and value.get("version", None):
            discontinousProcessNameList.append(key)
        elif isinstance(value, dict) and value.get("runType", "") == "continous" and value.get("version", None):
            continuousProcessNameList.append(key)
        elif isinstance(value, str) and re.match(r"^[0-9]*\.[0-9]*\.[0-9]*$", value):
            continuousProcessNameList.append(key)

    try:
        os.remove(lfPath)
    except:
        pass

    return continuousProcessNameList, discontinousProcessNameList


def convert_version(strVersion):
    try:
        if not isinstance(strVersion, str):
            return None

        strVersion = strVersion.replace("V", "").replace("v", "")

        if not re.match(r"^([0-9]*|\.)*$", strVersion):
            return None

        nList = strVersion.split(".")
        nList.reverse()

        nVersion = 0
        scale = 1
        for n in nList:
            nVersion += int(n) * scale
            scale = scale * 100

        return nVersion
    except Exception as e:
        return None

# 页面类型映射
def get_page_type_num(strPageType):
    dMap = {"fullscreen": 0, "floating": 1}
    return dMap.get(strPageType, None)

# 页面类型映射
def get_page_type_str(nPageType):
    dMap = {0: "fullscreen", 1: "floating"}
    return dMap.get(nPageType)

def update_template_file_to_mainService(templateName):
    headers = {"Content-Type": "application/json"}
    postData = {"templateName": templateName}

    try:
        rsp = requests.post("http://47.100.17.99/api/template/updateTemplateFileFromOSS", data=json.dumps(postData), headers=headers,
                            timeout=3)
        if rsp.status_code != 200:
            return False, "status_code不为200"
    except:
        return True, "mainService解压模板文件中的图片和动画需要一定时间"

    try:
        dData = json.loads(rsp.text)
        bSuc = dData.get("data", False)
        return bSuc, ""
    except:
        return False, "上传组态模板文件至mainService失败"

"""
遍历磁盘上的标注按钮图片，分析并整理出每种风格下的图片名称（不带图片后缀）
fileNameList: ["red", "redover", "reddown", "reddisabled", "green", "greenover", "greendown", "greendisabled", "yellow", "yellowover", "yellowdown", "yellowdisabled"]

dStyle:
{
    "red": {
        "comm": "red",
        "over": "redover",
        "down": "reddown",
        "disabled": "reddisabled"
    },
    "green": {
        "comm": "green",
        "over": "greenover",
        "down": "greendown",
        "disabled": "greendisabled"
    },
    "yellow": {
        "comm": "yellow",
        "over": "yellowover",
        "down": "yellowdown",
        "disabled": "yellowdisabled"
    }
}
"""
def get_standard_button_image_from_static():
    imagesDir = os.path.join(app.static_folder, "images")
    if not os.path.exists(imagesDir):
        return None, None

    buttonDir = os.path.join(imagesDir, "button")
    if not os.path.exists(buttonDir):
        return None, None

    fileNameList = []
    dStyle = {}
    for root, dirs, fileNames in os.walk(buttonDir):
        for fileName in fileNames:
            if not fileName.endswith(".png"):
                continue

            strTemp = os.path.splitext(fileName)[0]
            if strTemp not in fileNameList:
                fileNameList.append(strTemp)

            if strTemp.find("disabled") == -1 and strTemp.find("down") == -1 and strTemp.find("over") == -1:
                if strTemp not in dStyle.keys():
                    dStyle.update({strTemp: dict(comm=strTemp)})

            elif strTemp.find("disabled") >= 0:
                styleName = strTemp.replace("disabled", "")
                if len(styleName):
                    if styleName not in dStyle.keys():
                        dStyle.update({styleName: dict(comm=styleName)})
                    dStyle[styleName].update({"disabled": strTemp})

            elif strTemp.find("down") >= 0:
                styleName = strTemp.replace("down", "")
                if len(styleName):
                    if styleName not in dStyle.keys():
                        dStyle.update({styleName: dict(comm=styleName)})
                    dStyle[styleName].update({"down": strTemp})

            elif strTemp.find("over") >= 0:
                styleName = strTemp.replace("over", "")
                if len(styleName):
                    if styleName not in dStyle.keys():
                        dStyle.update({styleName: dict(comm=styleName)})
                    dStyle[styleName].update({"over": strTemp})

    for styleName, dStyleInfo in dStyle.items():
        if dStyleInfo.get("comm", None) == None or dStyleInfo.get("disabled", None) == None or dStyleInfo.get("down", None) == None or dStyleInfo.get("over", None) == None:
            return 0, 0
    return fileNameList, dStyle

def get_dom_image_lib_category():

    categoryMap = {1: '冷机', 2: '水泵', 3: '冷却塔', 4: '空调箱', 5: '阀门', 6: '管道弯头', 7: '按钮', 8: '图表', 9: '布局', 10: '图标', 11: '其他'}

    nMin = min(list(categoryMap.keys()))
    nMax = max(list(categoryMap.keys()))

    les = []

    for i in range(nMin, nMax+1):
        les.append(dict(no=i, name=categoryMap.get(i)))

    return categoryMap, les

def isValidDate(strDate, strFormat):
    res = False
    try:
        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res


