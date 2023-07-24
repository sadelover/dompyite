from siteinterface.mod_calendar import bp_calendar
from siteinterface import app
from flask import request, jsonify
from logic.StandardPointName import *
from openpyxl import Workbook
import os
from datetime import datetime
import traceback
from .. BEOPMySqlDBContainer import BEOPMySqlDBContainer
from siteinterface.BEOPSqliteAccess import *
from siteinterface.BEOPDataAccess import BEOPDataAccess
import logging
import xlrd
from siteinterface.utils import send_alert_to_cloud_center, get_proj_name

def isValidDate(strDate, strFormat):
    res = False
    try:
        if not isinstance(strDate, str):
            return res

        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res

def get_last_day_of_this_month(curDate):
    res = None
    try:
        if not isinstance(curDate, datetime):
            return None

        tNextMonth = curDate.replace(day=28) + timedelta(days=4)
        firstDayOfNextMonth = tNextMonth.replace(day=1)
        res = firstDayOfNextMonth - timedelta(days=1)
    except:
        pass
    finally:
        return res

def modeIdExistsInMode(modeId):
    """
    检查modeId是否已存在于mode表中
    """
    res = False
    try:
        rvConduct = BEOPDataAccess.getInstance().modeIdExistsInMode(modeId)
        if rvConduct is None:
            return None

        if rvConduct and len(rvConduct):
            if len(rvConduct[0]):
                if rvConduct[0][0] > 0:
                    res = True

    except Exception as e:
        strLog = "ERROR in modeIdExistsInMode: %s" % e.__str__()
        logging.error(strLog)

    finally:
        return res

@bp_calendar.route("/getCalendarWithWeather", methods=["POST"])
def get_calendar_with_weather():
    try:
        rcv = request.get_json()
        year = rcv.get("year") if rcv.get("year") else None
        month = rcv.get("month") if rcv.get("month") else None

        if not year:
            return jsonify(dict(err=1, msg="年不能为空", data=[]))

        if not month:
            return jsonify(dict(err=1, msg="月不能为空", data=[]))

        timeFormat = "%Y-%m-%d"

        strTimeStart = "%s-%02d-01" % (year, month)

        tTimeStart = datetime.strptime("%s-%02d-01" % (year, month), timeFormat)

        tTimeEnd = get_last_day_of_this_month(datetime.strptime("%s-%02d-01" % (year, month), timeFormat))

        strTimeEnd = tTimeEnd.strftime(timeFormat)

        weatherDict = BEOPDataAccess.getInstance().getCalendarWithWeather(strTimeStart, strTimeEnd)

        if weatherDict is None:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试", data=[]))

        if not weatherDict:
            return jsonify(dict(err=1, msg="无日历数据", data=[]))

        dataList = list()
        curDate = tTimeStart
        while curDate <= tTimeEnd:

            strCurDate = curDate.strftime("%Y-%m-%d")

            weatherInfo = weatherDict.get(strCurDate) if weatherDict.get(strCurDate) else {}

            dataList.append({
                "day": curDate.day,
                "weather": weatherInfo
            })

            curDate = curDate + timedelta(days=1)

        return jsonify(dict(err=0, data=dataList, msg="获取成功"))

    except Exception as e:
        strLog = "ERROR in /calendar/getMonthWeatherData: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="获取失败: %s" % e.__str__(), data=[]))

@bp_calendar.route("/addModeToCalendar", methods=["POST"])
def add_mode_to_calendar():
    try:
        rcv = request.get_json()
        date = rcv.get("date") if rcv.get("date") else None
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        type = rcv.get("type") if rcv.get("type") is not None else None
        creator = rcv.get("creator") if rcv.get("creator") else None
        now = datetime.now()
        dateToday = datetime.strptime(now.strftime("%Y-%m-%d"), "%Y-%m-%d")

        strSource = rcv.get("source", "")
        strIP = request.remote_addr
        strLog = '[IMPORTANT]addModeToCalendar: 来自IP:%s, 用户:%s, date:%s, type:%s  modeId:%s' % (
        strIP, strSource, date, type, modeId)
        logging.error(strLog)

        if strSource:
            bReadOnly = BEOPDataAccess.getInstance().is_user_read_only(strSource)
            if bReadOnly:
                return json.dumps(dict(err=1, msg='user has no write priority', data={}), ensure_ascii=False)

        if date is None:
            return jsonify(dict(err=1, msg="日期不能为空"))

        if not isValidDate(date, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="日期格式有误"))

        tDate = datetime.strptime(date, "%Y-%m-%d")

        if tDate < dateToday:
            return jsonify(dict(err=1, msg="今日之前的模式不可编辑"))

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为整数"))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在"))

        if type is None:
            return jsonify(dict(err=1, msg="模式类型不能为空"))

        if not isinstance(type, int):
            return jsonify(err=1, msg="模式类型必须为整数")

        if not creator:
            return jsonify(dict(err=1, msg="创建者不能为空"))
        if not isinstance(creator, str):
            return jsonify(err=1, msg="创建者名称必须为字符串")

        rvConduct = BEOPDataAccess.getInstance().getModeById(modeId)
        if rvConduct is None:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试"))

        if not len(rvConduct[1]):
            strMsg = "IP为{ip}的用户正在执行模式绑定(项目:{proj},模式ID:{modeId})，但该模式内容为空".format(ip=strIP,
                                                                                   proj=get_proj_name(), modeId=modeId)
            send_alert_to_cloud_center(get_proj_name(), strMsg)

        result = BEOPDataAccess.getInstance().insertIntoModeCalendar(date, modeId, creator, type)
        try:
            BEOPDataAccess.getInstance().appendOperationLog(strSource, '从地址%s发起模式修改'%(strIP))
        except:
            pass

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=result.get("data")))
        else:
            return jsonify(dict(err=0, msg=result.get("msg"), data=result.get("data")))

    except Exception as e:
        strLog = "ERROR in /calendar/addModeToCalendar: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="保存失败: %s" % e.__str__(), data=False))

@bp_calendar.route("/batchAddModeToCalendar", methods=["POST"])
def batch_add_mode_to_calendar():
    try:
        rcv = request.get_json()
        year = rcv.get("year") if rcv.get("year") is not None else None
        month = rcv.get("month") if rcv.get("month") is not None else None
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        type = rcv.get("type") if rcv.get("type") is not None else None
        creator = rcv.get("creator") if rcv.get("creator") else None
        strSource = rcv.get("source", "")
        nWeekdayList = rcv.get('weekdayList', [])
        if len(nWeekdayList)==0:
            nWeekdayList = [0,1,2,3,4,5,6]
        strIP = request.remote_addr

        strLog = '[IMPORTANT]batchAddModeToCalendar: 来自IP:%s, 用户:%s, year:%s,  month:%s,  modeId:%s'%(strIP, strSource, year, month, modeId)
        logging.error(strLog)

        if strSource:
            bReadOnly = BEOPDataAccess.getInstance().is_user_read_only(strSource)
            if bReadOnly:
                return json.dumps(dict(err=1, msg='user has no write priority', data={}), ensure_ascii=False)

        now = datetime.now()
        today = now.day
        thisYear = now.year
        thisMonth = now.month

        if year is None:
            return jsonify(dict(err=1, msg="年不能为空"))

        if not isinstance(year, int):
            return jsonify(dict(err=1, msg="年必须为整数"))

        if month is None:
            return jsonify(dict(err=1, msg="月不能为空"))

        if not isinstance(month, int):
            return jsonify(dict(err=1, msg="月必须为整数"))

        if year < thisYear:
            return jsonify(dict(err=1, msg="无法编辑去年的日程"))

        if year == thisYear and month < thisMonth:
            return jsonify(dict(err=1, msg="无法编辑本月之前的日程"))

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为整数"))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在"))

        if type is None:
            return jsonify(dict(err=1, msg="模式类型不能为空"))

        if not isinstance(type, int):
            return jsonify(err=1, msg="模式ID必须为整数")

        if not creator:
            return jsonify(dict(err=1, msg="创建者不能为空"))

        if not isinstance(creator, str):
            return jsonify(err=1, msg="创建者名称必须为字符串")

        fromDay = 1
        if year == thisYear and month == thisMonth:
            fromDay = today

        lastDate = get_last_day_of_this_month(datetime.strptime("%s-%02d-01" % (year, month), "%Y-%m-%d"))
        toDay = lastDate.day

        rvConduct = BEOPDataAccess.getInstance().getModeById(modeId)
        if rvConduct is None:
            return jsonify(dict(err=1, msg="数据库繁忙，请重试"))

        if not len(rvConduct[1]):
            strMsg = "IP为{ip}的用户正在执行批量模式绑定(项目:{proj},模式ID:{modeId})，但该模式内容为空".format(ip=strIP,
                                                                                   proj=get_proj_name(), modeId=modeId)
            send_alert_to_cloud_center(get_proj_name(), strMsg)

        result = BEOPDataAccess.getInstance().batchInsertIntoModeCalendar(year, month, fromDay, toDay, modeId, creator, type, nWeekdayList)

        try:
            BEOPDataAccess.getInstance().appendOperationLog(strSource, '从地址%s发起模式批量绑定'%(strIP))
        except:
            pass

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=result.get("data")))

        return jsonify(dict(err=0, msg=result.get("msg"), data=result.get("data")))

    except Exception as e:
        strLog = "ERROR in /calendar/batchAddModeToCalendar: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="保存失败: %s" % e.__str__(), data=[]))

@bp_calendar.route("/getCalendarWithMode", methods=["POST"])
def get_calendar_with_mode():
    try:
        rcv = request.get_json()
        year = rcv.get("year") if rcv.get("year") else None
        month = rcv.get("month") if rcv.get("month") else None
        type = rcv.get("type") if rcv.get("type") is not None else None

        if type is not None:
            if not isinstance(type, int):
                return jsonify(dict(err=1, msg="type必须是一个整数"))

        if not year:
            return jsonify(dict(err=1, msg="年不能为空", data=[]))

        if not month:
            return jsonify(dict(err=1, msg="月不能为空", data=[]))

        strTimeStart = "%s-%02d-01" % (year, month)

        tTimeStart = datetime.strptime("%s-%02d-01" % (year, month), "%Y-%m-%d")

        tTimeEnd = get_last_day_of_this_month(datetime.strptime("{0}-{1}-01".format(year, month), "%Y-%m-%d"))

        strTimeEnd = tTimeEnd.strftime("%Y-%m-%d")

        result = BEOPDataAccess.getInstance().getCalendarWithMode(strTimeStart, strTimeEnd, type)

        if result["code"] == 1:
            return jsonify(dict(err=1, msg=result["msg"], data=result.get("data")))

        if result["code"] == 2:
            return jsonify(dict(err=0, msg=result["msg"], data=result.get("data")))

        dataList = []
        curDate = tTimeStart
        dataDict = result.get("data")[0]
        weatherDict = result.get("data")[1]
        while curDate <= tTimeEnd:
            strCurDate = curDate.strftime("%Y-%m-%d")

            lInfo = dataDict.get(strCurDate) if dataDict.get(strCurDate) else []
            weather = weatherDict.get(strCurDate) if weatherDict.get(strCurDate) else {}
            dataList.append({
                "day": curDate.day,
                "mode": lInfo,
                "weather": weather
            })

            curDate = curDate + timedelta(days=1)

        return jsonify(dict(err=0, msg="获取成功", data=dataList))

    except Exception as e:
        strLog = "ERROR in /calendar/getCalendarWithMode: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="保存失败: %s" % e.__str__(), data=[]))

@bp_calendar.route("/removeModeFromCalendar", methods=["POST"])
def remove_mode_from_calendar():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId") if rcv.get("modeId") is not None else None
        date = rcv.get("date") if rcv.get("date") else None
        strSource = rcv.get("source", "")
        strIP = request.remote_addr

        strLog = '[IMPORTANT]removeModeFromCalendar: 来自IP:%s, 用户:%s, date:%s, modeId:%s'%(strIP, strSource, date, modeId)
        logging.error(strLog)

        if strSource:
            bReadOnly = BEOPDataAccess.getInstance().is_user_read_only(strSource)
            if bReadOnly:
                return json.dumps(dict(err=1, msg='user has no write priority', data={}), ensure_ascii=False)

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空"))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为整数"))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在"))

        if not isValidDate(date, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="日期格式有误"))

        result = BEOPDataAccess.getInstance().removeModeFromCalendar(modeId, date)

        try:
            BEOPDataAccess.getInstance().appendOperationLog(strSource, '从地址%s发起模式解除'%(strIP))
        except:
            pass

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=False))
        else:
            return jsonify(dict(err=0, msg=result.get("msg"), data=True))

    except Exception as e:
        strLog = "ERROR in /calendar/removeModeFromCalendar: %s" % e.__str__()
        logging.error(strLog)

        return jsonify(dict(err=1, msg="删除失败: %s" % e.__str__(), data=False))

@bp_calendar.route("/batchRemoveModeFromCalendar", methods=["POST"])
def batch_remove_mode_from_calendar():
    try:
        rcv = request.get_json()
        modeId = rcv.get("modeId", None)
        strFrom = rcv.get("from", "")
        strTo = rcv.get("to", "")
        strSource = rcv.get("source", "")
        strIP = request.remote_addr

        strLog = '[IMPORTANT]batchRemoveModeFromCalendar: 来自IP:%s, 用户:%s, date:%s, modeId:%s' % (strIP, strSource, date, modeId)
        logging.error(strLog)

        if strSource:
            bReadOnly = BEOPDataAccess.getInstance().is_user_read_only(strSource)
            if bReadOnly:
                return json.dumps(dict(err=1, msg='user has no write priority', data={}), ensure_ascii=False)

        if modeId is None:
            return jsonify(dict(err=1, msg="模式ID不能为空", data=False))

        if not isinstance(modeId, int):
            return jsonify(dict(err=1, msg="模式ID必须为整数", data=False))

        if not modeIdExistsInMode(modeId):
            return jsonify(dict(err=1, msg="模式ID不存在", data=False))

        if not len(strFrom) or not len(strTo):
            return jsonify(dict(err=1, msg="开始、结束日期不能为空", data=False))

        if not isValidDate(strFrom, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="开始日期格式有误", data=False))

        if not isValidDate(strTo, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="结束日期格式有误", data=False))

        tFrom = datetime.strptime(strFrom, "%Y-%m-%d")
        tTo = datetime.strptime(strTo, "%Y-%m-%d")
        if tFrom < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="今天之前的模式无法解绑", data=False))

        if tFrom > tTo:
            return jsonify(dict(err=1, msg="开始日期不能大于结束日期", data=False))

        result = BEOPDataAccess.getInstance().batchRemoveModeFromCalendar(modeId, tFrom, tTo)

        try:
            BEOPDataAccess.getInstance().appendOperationLog(strSource, '从地址%s发起模式批量解除'%(strIP))
        except:
            pass

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=False))
        return jsonify(dict(err=0, msg=result.get("msg"), data=True))

    except Exception as e:
        strLog = "ERROR in /calendar/batchRemoveModeFromCalendar: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="解绑失败: %s" % e.__str__(), data=False))


@bp_calendar.route("/batchRemoveModeFromCalendarThisMonth", methods=["POST"])
def batch_remove_mode_from_calendar_this_month():
    try:
        rcv = request.get_json()
        nType = rcv.get("type", None)
        strDate = rcv.get("date", "")

        strSource = rcv.get("source", "")
        strIP = request.remote_addr

        strLog = '[IMPORTANT]batchRemoveModeFromCalendarThisMonth: 来自IP:%s, 用户:%s, date:%s, modeId:%s' % (strIP, strSource, strDate, nType)
        logging.error(strLog)

        if strSource:
            bReadOnly = BEOPDataAccess.getInstance().is_user_read_only(strSource)
            if bReadOnly:
                return json.dumps(dict(err=1, msg='user has no write priority', data={}), ensure_ascii=False)

        # if nType is None:
        #     return jsonify(dict(err=1, msg="类型不能为空", data=False))

        if nType is not None:
            if not isinstance(nType, int):
                return jsonify(dict(err=1, msg="类型必须为整数", data=False))

        if not len(strDate):
            return jsonify(dict(err=1, msg="日期不能为空", data=False))

        if not isValidDate(strDate, "%Y-%m"):
            return jsonify(dict(err=1, msg="日期格式有误", data=False))

        tDate = datetime.strptime(strDate, "%Y-%m")
        tFrom = tDate.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        tTo = (time_get_first_day_of_next_month(tDate) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
        if tFrom < datetime.now():
            tFrom = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        result = BEOPDataAccess.getInstance().batchRemoveModeFromCalendarThisMonth(nType, tFrom, tTo)

        try:
            BEOPDataAccess.getInstance().appendOperationLog(strSource, '从地址%s发起模式批量解除'%(strIP))
        except:
            pass

        if result.get("code") > 0:
            return jsonify(dict(err=1, msg=result.get("msg"), data=False))
        return jsonify(dict(err=0, msg=result.get("msg"), data=True))

    except Exception as e:
        strLog = "ERROR in /calendar/batchRemoveModeFromCalendarThisMonth: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="解绑失败: %s" % e.__str__(), data=False))


@bp_calendar.route("/getModeOfTypeOnCertainDate", methods=["POST"])
def get_mode_of_type_on_certain_date():
    rcv = request.get_json()
    nType = rcv.get("type", None)
    date = rcv.get("date", "")

    if nType is None:
        return jsonify(dict(err=1, msg="类型不能为空", data={}))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="类型必须为整数", data={}))
    if not date:
        return jsonify(dict(err=1, msg="日期不能为空", data={}))
    if not isinstance(date, str):
        return jsonify(dict(err=1, msg="日期必须为字符串", data={}))
    if not isValidDate(date, "%Y-%m-%d"):
        return jsonify(dict(err=1, msg="日期格式有误", data={}))

    res = BEOPDataAccess.getInstance().getModeOfTypeOnCertainDate(nType, date)
    if res.get("code") > 0:
        return jsonify(dict(err=1, msg=res.get("msg"), data={}))
    return jsonify(dict(err=0, msg="获取成功", data=res.get("data")))

