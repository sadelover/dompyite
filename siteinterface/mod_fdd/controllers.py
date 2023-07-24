# -*- coding: utf-8 -*-
from siteinterface.mod_fdd import bp_fdd
from flask import request, jsonify
from siteinterface.BEOPSqliteAccess import *
from siteinterface.BEOPDataAccess import BEOPDataAccess
import logging
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
from siteinterface.RedisManager import RedisManager
import traceback
from siteinterface.utils import get_fault_view_en_name
from siteinterface.mod_fdd.utils import *
import json


def isValidDate(strDate, strFormat):
    res = False
    try:
        tTime = datetime.strptime(strDate, strFormat)
        res = True
    except:
        pass
    finally:
        return res

def get_worker_number(strNameEn):
    numList = re.findall(r"[0-9]+", strNameEn)
    if not len(numList):
        return -1
    return int(numList[0])


def getFaultGroupMembersOfAdmin(adminName):
    authDict = RedisManager.get("FaultAuthInfo")
    FaultPersonNameMap = RedisManager.get("FaultPersonNameMap")
    operationList = []
    maintainanceList = []
    unknownList = []

    if not authDict:
        return []

    adminGroup = authDict.get(adminName).get("group")
    nameReturned = []
    for name, infoDict in authDict.items():

        workGroup = infoDict.get("group")
        bSeated = False
        for group in workGroup:
            if group in adminGroup:
                if name.find("op") >= 0:
                    operationList.append({"name_en": name, "name_zh": FaultPersonNameMap.get(name)})
                    bSeated = True
                    break

                if name.find("man") >= 0:
                    maintainanceList.append({"name_en": name, "name_zh": FaultPersonNameMap.get(name)})
                    bSeated = True
                    break

        if not bSeated:
            unknownList.append({"name_en": name, "name_zh": FaultPersonNameMap.get(name)})

        if name not in nameReturned:
            nameReturned.append(name)

    for i in range(len(operationList)):
        for j in range(len(operationList)-i-1):
            if get_worker_number(operationList[j].get("name_en")) > get_worker_number(operationList[j+1].get("name_en")):
                operationList[j], operationList[j+1] = operationList[j+1], operationList[j]

    for i in range(len(maintainanceList)):
        for j in range(len(maintainanceList)-i-1):
            if get_worker_number(maintainanceList[j].get("name_en")) > get_worker_number(maintainanceList[j+1].get("name_en")):
                maintainanceList[j], maintainanceList[j+1] = maintainanceList[j+1], maintainanceList[j]

    for i in range(len(unknownList)):
        for j in range(len(unknownList)-i-1):
            if unknownList[j].get("name_en") > unknownList[j+1].get("name_en"):
                unknownList[j], unknownList[j + 1] = unknownList[j + 1], unknownList[j]

    res = operationList + maintainanceList + unknownList
    if adminName not in nameReturned:
        res.append({"name_en": adminName,
                    "name_zh": FaultPersonNameMap.get(adminName)})

    return res


# 遍历required views，筛选出符合的点
def match_the_point_views(viewsRequired, pointViewList):
    if not len(viewsRequired):
        return True

    for view in viewsRequired:
        if view not in pointViewList:
            return False
    return True

def match_the_category_required(categoryList, dPointView):
    if not len(categoryList):
        return True

    categoryOfPoint = dPointView.get("category", None)
    if categoryOfPoint is None:
        return True

    if categoryOfPoint in categoryList:
        return True
    return False


def match_the_medium_required(mediumList, dPointView):
    if not len(mediumList):
        return True

    mediumOfPoint = dPointView.get("medium", None)
    if mediumOfPoint is None:
        return True

    if mediumOfPoint in mediumList:
        return True
    return False

def match_the_position_required(positionList, dPointView):
    if not len(positionList):
        return True

    positionOfPoint = dPointView.get("position", None)
    if positionOfPoint is None:
        return True

    if positionOfPoint in positionList:
        return True
    return False

def match_the_status_required(statusList, nStatus):
    if not len(statusList):
        return True

    if nStatus in statusList:
        return True
    return False

def get_point_view_str(dPointView):
    dViews = {"category": "类型", "position": "位置", "medium": "介质"}
    infoList = []
    for viewEn, viewContent in dPointView.items():
        infoList.append("{content}({viewZh})".format(content=viewContent, viewZh=dViews.get(viewEn, "未知")))
    return ";".join(infoList) if len(infoList) else ""

@bp_fdd.route("/updateFaultPointsToRedis")
def update_fault_points_to_redis():
    rt = BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
    return jsonify(dict(err=0 if rt else 1, msg="", data=rt))

@bp_fdd.route("/updateFaultViewInfoToRedis")
def update_fault_view_info_to_redis():
    rt = BEOPSqliteAccess.getInstance().UpdateFaultViewInfoToRedis()
    return jsonify(dict(err=0 if rt else 1, msg="", data=rt))

@bp_fdd.route("/updateFaultAuthInfoToRedis")
def update_fault_auth_info_to_redis():
    rt = BEOPSqliteAccess.getInstance().UpdateFaultAuthInfoToRedis()
    return jsonify(dict(err=0 if rt else 1, msg="", data=rt))

@bp_fdd.route("/statistic", methods=["POST"])
def classify():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", "")
        yearMonth = rcv.get("yearMonth", "")
        viewZh = rcv.get("view", "")

        view = get_fault_view_en_name(viewZh)
        if view is None:
            return jsonify(dict(err=1, msg="维度字段为空", data={}))

        if not isinstance(userName, str) or not isinstance(yearMonth, str) or not isinstance(view, str):
            return jsonify(dict(err=1, msg="输入量必须为字符串", data={}))
        if not isValidDate(yearMonth, "%Y-%m"):
            return jsonify(dict(err=1, msg="输入的日期格式有误", data={}))

        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data={}))

        FaultViewInfo = RedisManager.get("FaultViewInfo")
        if not FaultViewInfo:
            return jsonify(dict(err=1, msg="Redis中未发现故障维度配置，请检查fdd_specy配置", data={}))

        if view not in FaultViewInfo.keys():
            return jsonify(dict(err=1, msg="所输入维度未在后台配置中发现，请检查fdd_specy配置", data={}))

        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="用户{userName}不在后台配置的权限列表中".format(userName=userName), data={}))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")

        tTime = datetime.strptime(yearMonth, "%Y-%m")
        strStartTime = "%s-%02d-01 00:00:00" % (tTime.year, tTime.month)
        tTimeStart = datetime.strptime(strStartTime, "%Y-%m-%d %H:%M:%S")
        t28ThisMonth = tTimeStart.replace(day=28)
        tNextMonth = t28ThisMonth + timedelta(days=5)
        tNextMonthFirstDay = tNextMonth.replace(day=1, hour=0, minute=0, second=0)
        strEndTime = tNextMonthFirstDay.strftime("%Y-%m-%d %H:%M:%S")

        # 从Mysql查取故障状态
        faultStatus = BEOPDataAccess.getInstance().getFaultStatusInfo(strStartTime, strEndTime)
        if faultStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="故障状态查询失败", data={}))

        # 获取Redis里面的点信息字典
        pointDict = RedisManager.get("FaultPointInfo")
        if not pointDict:
            BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
            pointDict = RedisManager.get("FaultPointInfo")
            if not pointDict:
                return jsonify(dict(err=1, msg="Redis中未发现故障点", data={}))

        # 生成结果字典
        result = {}
        subViewList = viewDict.get(view)
        for item in subViewList:
            result.update({item: dict(total=0, toBeAssigned=0, ongoing=0, toBeConfirmed=0, confirmed=0, pending=0,
                                      type=item, overdue=0, solved=0, overdueRate="", solveRate="", terminated=0)})

        # 遍历所有故障
        for orderId, infoList in faultStatus.get("data").items():

            pointName = infoList[0].get("fddName")

            # 判断故障点是否属于当前用户 START
            belongs = None
            for viewOfUser, subViewListOfUser in viewDict.items():
                pInfo = pointDict.get(pointName, None)
                if not pInfo:
                    continue
                pViews = pInfo.get("views", None)
                if not pViews:
                    continue
                subViewOfPoint = pViews.get(viewOfUser, None)

                if not subViewOfPoint:
                    continue
                if subViewOfPoint not in subViewListOfUser:
                    belongs = False
                    break
                belongs = True

            if not belongs:
                continue
            # 判断故障点是否属于当前用户 END

            # 获得工单的当前状态
            tTime = infoList[0].get("modifyTime")
            nStatus = infoList[0].get("status")
            tEstimatedTime = None
            for info in infoList:
                try:
                    if info.get("modifyTime") > tTime:
                        tTime = info.get("modifyTime")
                        nStatus = info.get("status")
                        if re.match("^.*estimatedTime.*$", info.get("opContent")):
                            strEstimatedTime = eval(info.get("opContent")).get("estimatedTime")
                            if isValidDate(strEstimatedTime, "%Y-%m-%d %H:%M:%S"):
                                tEstimatedTime = datetime.strptime(strEstimatedTime, "%Y-%m-%d %H:%M:%S")

                except Exception as e:
                    pass

            overdue = False
            if nStatus == 1 and tEstimatedTime:
                if datetime.now() >= tEstimatedTime:
                    overdue = True

            subViewOfPoint = pointDict.get(pointName).get("views").get(view, None)
            if not subViewOfPoint:
                continue

            strStatus = workOrderStatusMapEn.get(nStatus)

            if overdue:
                result[subViewOfPoint]["overdue"] += 1

            if nStatus == 3:
                result[subViewOfPoint]["solved"] += 1

            result[subViewOfPoint][strStatus] += 1
            result[subViewOfPoint]["total"] += 1

        # 计算逾期率和解决率
        for view, infoDict in result.items():
            if infoDict.get("total") > 0:
                infoDict["solveRate"] = "{0}%".format(round(100 * infoDict["solved"] / infoDict["total"], 1))
                infoDict["overdueRate"] = "{0}%".format(round(100 * infoDict["overdue"] / infoDict["total"], 1))

        return jsonify(dict(err=0, msg="获取成功", data=result))

    except Exception as e:
        logging.error("ERROR in /fdd/classify: %s" % e.__str__())
        return jsonify(dict(err=1, msg="获取失败:{err}".format(err=e.__str__()), data={}))

# 工单状态：0-待分派；1-分派（工单在进行中）；2-完成待审核；3-已审核；4-等待，暂停; 5-强制关闭
@bp_fdd.route("/query", methods=["POST"])
def process_query():
    try:
        rcv = request.get_json()
        categoryList = rcv.get("category", [])
        mediumList = rcv.get("medium", [])
        positionList = rcv.get("position", [])
        statusList = rcv.get("status", [])
        startTime = rcv.get("startTime", "")
        endTime = rcv.get("endTime", "")
        userName = rcv.get("userName", "")

        if not isinstance(categoryList, list):
            return jsonify(dict(err=1, msg="报警类型必须为列表", data=[]))
        if not isinstance(mediumList, list):
            return jsonify(dict(err=1, msg="介质类型必须为列表", data=[]))
        if not isinstance(positionList, list):
            return jsonify(dict(err=1, msg="位置必须为列表", data=[]))
        if not isinstance(statusList, list):
            return jsonify(dict(err=1, msg="状态必须为列表", data=[]))
        if not isinstance(startTime, str) or not isinstance(endTime, str):
            return jsonify(dict(err=1, msg="开始/终止时间必须为字符串", data=[]))
        if not isValidDate(startTime, "%Y-%m-%d %H:%M:%S") or not isValidDate(endTime, "%Y-%m-%d %H:%M:%S"):
            return jsonify(dict(err=1, msg="开始时间或结束时间格式有误", data=[]))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符串", data=[]))

        tStartTime = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
        tEndTime = datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")

        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data={}))

        dUserInfo = authDict.get(userName, {})
        if not dUserInfo:
            return jsonify(dict(err=1, msg="fdd_auth中未发现关于{userName}的权限配置".format(userName=userName), data={}))

        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="用户{userName}的角色定义（admin/executor）获取失败".format(userName=userName), data={}))

        FaultPersonNameMap = RedisManager.get("FaultPersonNameMap")

        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data={}))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")

        # 获取Redis里面的点信息字典
        pointDict = RedisManager.get("FaultPointInfo")
        if not pointDict:
            BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
            pointDict = RedisManager.get("FaultPointInfo")
            if not pointDict:
                return jsonify(dict(err=1, msg="Redis中未发现故障点", data={}))

        # 将查询时间范围内有增加过评论的工单id筛选出来
        nTargetOrderIdList = []
        dComment = BEOPDataAccess.getInstance().getCommentOfWorkOrder(None)
        for nOrderId, dCommentList in dComment.items():
            bCount = False
            for dCmdInfo in dCommentList:
                if dCmdInfo.get("createTime") >= tStartTime and dCmdInfo.get("createTime") <= tEndTime:
                    bCount = True
                    break

            if bCount:
                if nOrderId not in nTargetOrderIdList:
                    nTargetOrderIdList.append(nOrderId)

        # 将updateTime范围内的工单id查询返回
        nOrderIdListInUpdateTimeRange = BEOPDataAccess.getInstance().getFaultModifiedInTimeRange(startTime, endTime)
        if nOrderIdListInUpdateTimeRange == None:
            return jsonify(dict(err=1, msg="发生更新的工单id列表获取失败，请稍后再试", data=[]))

        if isinstance(nOrderIdListInUpdateTimeRange, list):
            nTargetOrderIdList.extend(nOrderIdListInUpdateTimeRange)

        nTargetOrderIdList = list(set(nTargetOrderIdList))

        faultInfoDict = BEOPDataAccess.getInstance().getFaultInfoOfCertainOrderId(nTargetOrderIdList)
        if faultInfoDict == None:
            return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

        result = []
        for orderId, infoList in faultInfoDict.items():
            pointName = infoList[0].get("fddName")

            if pointDict.get(pointName, None) is None:
                logging.error("/fdd/query:: {pointName} doesn't exist in domdb.4db".format(pointName=pointName))
                continue

            dPointView = pointDict.get(pointName).get("views")

            # 判断故障点是否属于当前用户 BEGIN
            belongs = None
            for viewOfUser, subViewListOfUser in viewDict.items():
                if pointDict.get(pointName).get("views", None) is None:
                    logging.error("/fdd/query:: %s doesn't have view info" % pointName)
                    continue

                subViewOfPoint = pointDict.get(pointName).get("views").get(viewOfUser, "")

                if not subViewOfPoint:
                    logging.error("/fdd/query:: subViewOfPoint是空(%s)" % subViewOfPoint)
                    continue

                if subViewOfPoint not in subViewListOfUser:
                    logging.error("/fdd/query:: subViewOfPoint(%s) not in subViewListOfUser:" % subViewOfPoint)
                    belongs = False
                    break

                belongs = True

            if not belongs:
                logging.error("/fdd/query:: not belongs %s" % belongs)
                continue

            # 判断故障点是否属于当前用户 END

            # 检查是否满足类型要求
            if not match_the_category_required(categoryList, dPointView):
                logging.error("/fdd/query:: 不满足类型要求")
                continue

            # 检查是否满足介质要求
            if not match_the_medium_required(mediumList, dPointView):
                logging.error("/fdd/query:: 不满足介质要求")
                continue

            # 检查是否满足位置要求
            if not match_the_position_required(positionList, dPointView):
                logging.error("/fdd/query:: 不满足位置要求")
                continue

            strView = get_point_view_str(dPointView)

            strCritical = pointDict.get(pointName).get("critical")

            strPosition = pointDict.get(pointName).get("views").get("位置", "")

            strGroup = pointDict.get(pointName).get("group")

            strDepartment = pointDict.get(pointName).get("department")

            strProcessor = ""
            for info in infoList:
                if isinstance(info.get("opContentData"), str):
                    if "toUserName" in info.get("opContentData"):
                        processorEn = eval(info.get("opContentData")).get("toUserName", "")
                        strProcessor = FaultPersonNameMap.get(processorEn, "")

            nStatus = infoList[0].get("status")
            tTarStatus = infoList[0].get("modifyTime")
            operatorEn = infoList[0].get("opUserName")

            strEstimatedTime = "无"
            tTarEstimatedTime = None

            strStartTime = "无"
            tTarStartTime = None

            nDurationSeconds = 0

            tCreateTime = infoList[0].get("modifyTime")
            strOrderName = infoList[0].get("name") if isinstance(infoList[0].get("name"), str) else ""

            strDetailWithHtml = infoList[0].get("detail") if isinstance(infoList[0].get("detail"), str) else ""

            strOwner = infoList[0].get("owner")
            strCreator = infoList[0].get("opUserName", "")
            strConclusion = ""

            imgNameList = []

            for info in infoList:
                if isinstance(info.get("opContentData"), str):
                    if "estimatedTime" in info.get("opContentData"):
                        if tTarEstimatedTime is None or info.get("modifyTime") > tTarEstimatedTime:
                            strEstimatedTime = eval(info.get("opContentData")).get("estimatedTime")
                            tTarEstimatedTime = info.get("modifyTime")

                if isinstance(info.get("opContentData"), str):
                    if "changeTo" in info.get("opContentData") and eval(info.get("opContentData")).get("changeTo") == 1:
                        if tTarStartTime is None or info.get("modifyTime") > tTarStartTime:
                            tTarStartTime = info.get("modifyTime")
                            strStartTime = info.get("modifyTime").strftime("%Y-%m-%d %H:%M:%S")

                if info.get("modifyTime") > tTarStatus:
                    nStatus = info.get("status")
                    operatorEn = info.get("opUserName")
                    tTarStatus = info.get("modifyTime")
                    strOwner = info.get("owner")

                    if isinstance(info.get("opContentData"), str):
                        if "duration" in info.get("opContentData") and eval(info.get("opContentData")).get("duration", None) is not None:
                            nDurationSeconds = eval(info.get("opContentData")).get("duration")

                        if "conclusion" in info.get("opContentData") and eval(info.get("opContentData")).get("conclusion", None) is not None:
                            strConclusion = eval(info.get("opContentData")).get("conclusion")

                    if nStatus == 0:
                        nDurationSeconds = 0

                if info.get("modifyTime") < tCreateTime:
                    strOrderName = info.get("name") if isinstance(info.get("name"), str) else ""
                    strDetailWithHtml = info.get("detail") if isinstance(info.get("detail"), str) else ""
                    tCreateTime = info.get("modifyTime")

                if info.get("opType") == -1:
                    strCreator = info.get("opUserName")

                if info.get("status", None) == 0:
                    image = info.get("img", None)
                    if isinstance(image, str):
                        imageList = image.split(",")
                        for iName in imageList:
                            if len(iName):
                                imgNameList.append(iName)

            # 检查当前故障点的状态是否符合所查询的状态列表
            if not match_the_status_required(statusList, nStatus):
                logging.error("/fdd/query:: 当前故障点的状态不满足查询的状态列表")
                continue

            # 获取故障启用禁用状态和提交时输入的总结内容
            faultLabelPoint = get_fault_label_point(pointName)
            pDataList, pDataDict = BEOPDataAccess.getInstance().getInputTable([faultLabelPoint])

            nEnabled = 1
            strSubmit = ""
            if faultLabelPoint in pDataDict.keys():
                strInfo = pDataDict.get(faultLabelPoint, "")

                jsonInfo = {}
                try:
                    jsonInfo = json.loads(strInfo)
                except:
                    pass

                dInfo = {} if not isinstance(jsonInfo, dict) else jsonInfo
                nEnabled = dInfo.get("Enabled", 1)

                reasonDict = dInfo.get("Reason", {})

                for strDate, strReason in reasonDict.items():
                    strSubmit += "{date}: {reason};\n".format(date=strDate, reason=strReason)

            if len(strSubmit):
                strDetailWithHtml += "总结:{0}".format(strSubmit)

            if len(strConclusion):
                strDetailWithHtml += "结论:{0}".format(strConclusion)

            strDuration = ""
            if nDurationSeconds > 0:
                strDuration = "{0} 小时".format(round(nDurationSeconds / 3600, 1)) if nDurationSeconds > 3600 else "{0} 分钟".format(
                    round(nDurationSeconds / 60, 1))

            bOverTime = 0
            if nDurationSeconds > 0 and isValidDate(strStartTime, "%Y-%m-%d %H:%M:%S") and isValidDate(strEstimatedTime, "%Y-%m-%d %H:%M:%S"):
                estimatedSeconds = (datetime.strptime(strEstimatedTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(strStartTime, "%Y-%m-%d %H:%M:%S")).total_seconds()
                bOverTime = 1 if nDurationSeconds > estimatedSeconds else 0

            nAllowSubmite = allow_submit(role, nStatus, strOwner, userName, strCreator)

            nMine = allow_assign(role, nStatus, strOwner, userName)

            nAllowEnable = allow_enable(role, pointName, MaintainanceFaultPointName)

            nAllowTernimate = allow_terminate(nStatus, role)

            nAllowPause = allow_pause(nStatus, role)

            nAllowAdminSubmit = allow_admin_submit(nStatus, role)

            nAllowEdit = allow_edit(nStatus, role)

            strOwnerCh = FaultPersonNameMap.get(strOwner, strOwner)

            commentList = descending_order_comment_by_create_time(dComment.get(orderId, []))

            strCommentDesc = "暂无评论"
            if len(commentList):
                latest = commentList[0]
                creatorEn = latest.get("creator", "")
                tPass = latest.get("createTime")
                timeTraceBackDesc = time_desc_trace_back(tPass)
                if timeTraceBackDesc != None:
                    strCommentDesc = "{userName}在{timeDesc}评论过".format(userName=FaultPersonNameMap.get(creatorEn, creatorEn),
                                                                    timeDesc=timeTraceBackDesc)

            strCreatorCh = FaultPersonNameMap.get(strCreator, "") if FaultPersonNameMap.get(strCreator, "") else strCreator
            result.append({
                "id": orderId,
                "name": strOrderName,
                "view": strView,
                "level": strCritical,
                "time": tCreateTime.strftime("%Y-%m-%d %H:%M:%S"),
                "detail": strDetailWithHtml,
                "position": strPosition,
                "group": strGroup,
                "department": strDepartment,
                "processor": strProcessor,
                "status": workOrderStatusMapZh.get(nStatus),
                "startTime": strStartTime,
                "estimatedTime": strEstimatedTime,
                "duration": strDuration,
                "operator": "系统" if operatorEn == "system" else FaultPersonNameMap.get(operatorEn, ""),
                "operatorEn": operatorEn,
                "enabled": nEnabled,
                "owner": strOwnerCh,
                "mine": nMine,
                "overTime": bOverTime,
                "allowEnable": nAllowEnable,
                "allowTerminate": nAllowTernimate,
                "allowPause": nAllowPause,
                "allowSubmit": nAllowSubmite,
                "allowAdminSubmit": nAllowAdminSubmit,
                "allowEdit": nAllowEdit,
                "commented": strCommentDesc,
                "imgList": imgNameList,
                "creatorCh": strCreatorCh,
                "creatorEn": strCreator,
                "conclusion": strConclusion
            })

        return jsonify(dict(err=0, msg="获取成功", data=result))

    except Exception as e:
        traceback.print_exc()
        logging.error("ERROR in /fdd/query: %s" % e.__str__())
        return jsonify(dict(err=1, msg="获取失败:{err}".format(err=e.__str__()), data={}))


@bp_fdd.route("/export", methods=["POST"])
def export_fdd_work_order():
    try:
        rcv = request.get_json()
        categoryList = rcv.get("category", [])
        mediumList = rcv.get("medium", [])
        positionList = rcv.get("position", [])
        statusList = rcv.get("status", [])
        startTime = rcv.get("startTime", "")
        endTime = rcv.get("endTime", "")
        userName = rcv.get("userName", "")

        if not isinstance(categoryList, list):
            return jsonify(dict(err=1, msg="报警类型必须为列表", data=[]))
        if not isinstance(mediumList, list):
            return jsonify(dict(err=1, msg="介质类型必须为列表", data=[]))
        if not isinstance(positionList, list):
            return jsonify(dict(err=1, msg="位置必须为列表", data=[]))
        if not isinstance(statusList, list):
            return jsonify(dict(err=1, msg="状态必须为列表", data=[]))
        if not isinstance(startTime, str) or not isinstance(endTime, str):
            return jsonify(dict(err=1, msg="开始/终止时间必须为字符串", data=[]))
        if not isValidDate(startTime, "%Y-%m-%d %H:%M:%S") or not isValidDate(endTime, "%Y-%m-%d %H:%M:%S"):
            return jsonify(dict(err=1, msg="开始时间或结束时间格式有误", data=[]))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符串", data=[]))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data={}))

        dUserInfo = authDict.get(userName, {})
        if not dUserInfo:
            return jsonify(dict(err=1, msg="fdd_auth中未发现关于{userName}的权限配置".format(userName=userName), data={}))

        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="用户{userName}的角色定义（admin/executor）获取失败".format(userName=userName), data={}))

        FaultPersonNameMap = RedisManager.get("FaultPersonNameMap")

        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data={}))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")

        # 获取Redis里面的点信息字典
        pointDict = RedisManager.get("FaultPointInfo")
        if not pointDict:
            BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
            pointDict = RedisManager.get("FaultPointInfo")
            if not pointDict:
                return jsonify(dict(err=1, msg="Redis中未发现故障点", data={}))

        # 从mysql获取fault信息
        faultInfo = BEOPDataAccess.getInstance().getFaultInfo(startTime=startTime, endTime=endTime)
        if faultInfo.get("code") > 0:
            return jsonify(dict(err=1, msg="从Mysql获取故障信息失败", data=[]))

        faultInfoDict = faultInfo.get("data")
        result = []
        for orderId, infoList in faultInfoDict.items():

            pointName = infoList[0].get("fddName")

            if pointDict.get(pointName, None) is None:
                logging.error("/fdd/export:: {pointName} doesn't exist in domdb.4db".format(pointName=pointName))
                continue

            dPointView = pointDict.get(pointName).get("views")

            # 判断故障点是否属于当前用户 BEGIN
            belongs = None
            for viewOfUser, subViewListOfUser in viewDict.items():
                if pointDict.get(pointName).get("views", None) is None:
                    logging.error("/fdd/export:: %s doesn't have view info" % pointName)
                    continue

                subViewOfPoint = pointDict.get(pointName).get("views").get(viewOfUser, "")
                if not subViewOfPoint:
                    continue

                if subViewOfPoint not in subViewListOfUser:
                    belongs = False
                    break

                belongs = True

            if not belongs:
                continue

            # 判断故障点是否属于当前用户 END

            # 检查是否满足类型要求
            if not match_the_category_required(categoryList, dPointView):
                continue

            # 检查是否满足介质要求
            if not match_the_medium_required(mediumList, dPointView):
                continue

            # 检查是否满足位置要求
            if not match_the_position_required(positionList, dPointView):
                continue

            strView = get_point_view_str(dPointView)

            strCritical = pointDict.get(pointName).get("critical")

            strPosition = pointDict.get(pointName).get("views").get("位置", "")

            strGroup = pointDict.get(pointName).get("group")

            strDepartment = pointDict.get(pointName).get("department")

            strProcessor = ""
            for info in infoList:
                if isinstance(info.get("opContentData"), str):
                    if "toUserName" in info.get("opContentData"):
                        processorEn = eval(info.get("opContentData")).get("toUserName", "")
                        strProcessor = FaultPersonNameMap.get(processorEn, "")

            nStatus = infoList[0].get("status")
            tTarStatus = infoList[0].get("modifyTime")
            operatorEn = infoList[0].get("opUserName")

            strEstimatedTime = "无"
            tTarEstimatedTime = None

            strStartTime = "无"
            tTarStartTime = None

            nDurationSeconds = 0

            tCreateTime = infoList[0].get("modifyTime")
            strOrderName = infoList[0].get("name")
            strDetailWithHtml = infoList[0].get("detail", "")
            strOwner = infoList[0].get("owner")
            strCreator = infoList[0].get("opUserName", "")
            strConclusion = ""

            for info in infoList:
                if isinstance(info.get("opContentData"), str):
                    if "estimatedTime" in info.get("opContentData"):
                        if tTarEstimatedTime is None or info.get("modifyTime") > tTarEstimatedTime:
                            strEstimatedTime = eval(info.get("opContentData")).get("estimatedTime")
                            tTarEstimatedTime = info.get("modifyTime")

                if isinstance(info.get("opContentData"), str):
                    if "changeTo" in info.get("opContentData") and eval(info.get("opContentData")).get("changeTo") == 1:
                        if tTarStartTime is None or info.get("modifyTime") > tTarStartTime:
                            tTarStartTime = info.get("modifyTime")
                            strStartTime = info.get("modifyTime").strftime("%Y-%m-%d %H:%M:%S")

                if info.get("modifyTime") > tTarStatus:
                    nStatus = info.get("status")
                    operatorEn = info.get("opUserName")
                    tTarStatus = info.get("modifyTime")
                    strOwner = info.get("owner")

                    if isinstance(info.get("opContentData"), str):
                        if "duration" in info.get("opContentData") and eval(info.get("opContentData")).get("duration", None) is not None:
                            nDurationSeconds = eval(info.get("opContentData")).get("duration")

                        if "conclusion" in info.get("opContentData") and eval(info.get("opContentData")).get("conclusion", None) is not None:
                            strConclusion = eval(info.get("opContentData")).get("conclusion")

                    if nStatus == 0:
                        nDurationSeconds = 0

                if info.get("modifyTime") < tCreateTime:
                    strOrderName = info.get("name")
                    strDetailWithHtml = info.get("detail", "")
                    tCreateTime = info.get("modifyTime")

                if info.get("opType") == -1:
                    strCreator = info.get("opUserName")

            # 检查当前故障点的状态是否符合所查询的状态列表
            if not match_the_status_required(statusList, nStatus):
                continue

            # 获取故障启用禁用状态和提交时输入的总结内容
            faultLabelPoint = get_fault_label_point(pointName)
            pDataList, pDataDict = BEOPDataAccess.getInstance().getInputTable([faultLabelPoint])

            nEnabled = 1
            strSubmit = ""
            if faultLabelPoint in pDataDict.keys():
                strInfo = pDataDict.get(faultLabelPoint, "")

                jsonInfo = {}
                try:
                    jsonInfo = json.loads(strInfo)
                except:
                    pass

                dInfo = {} if not isinstance(jsonInfo, dict) else jsonInfo
                nEnabled = dInfo.get("Enabled", 1)

                reasonDict = dInfo.get("Reason", {})

                for strDate, strReason in reasonDict.items():
                    strSubmit += "{date}: {reason};\n".format(date=strDate, reason=strReason)

            if len(strSubmit):
                strDetailWithHtml += "\n总结：\n" + strSubmit

            strDuration = ""
            if nDurationSeconds > 0:
                strDuration = "{0} 小时".format(round(nDurationSeconds / 3600, 1)) if nDurationSeconds > 3600 else "{0} 分钟".format(
                    round(nDurationSeconds / 60, 1))

            bOverTime = 0
            if nDurationSeconds > 0 and isValidDate(strStartTime, "%Y-%m-%d %H:%M:%S") and isValidDate(strEstimatedTime, "%Y-%m-%d %H:%M:%S"):
                estimatedSeconds = (datetime.strptime(strEstimatedTime, "%Y-%m-%d %H:%M:%S") - datetime.strptime(strStartTime, "%Y-%m-%d %H:%M:%S")).total_seconds()
                bOverTime = 1 if nDurationSeconds > estimatedSeconds else 0

            nAllowSubmite = allow_submit(role, nStatus, strOwner, userName, strCreator)

            nMine = allow_assign(role, nStatus, strOwner, userName)

            nAllowEnable = allow_enable(role, pointName, MaintainanceFaultPointName)

            nAllowTernimate = allow_terminate(nStatus, role)

            nAllowPause = allow_pause(nStatus, role)

            nAllowAdminSubmit = allow_admin_submit(nStatus, role)

            strDetail = get_detail_from_p_html(strDetailWithHtml)

            result.append({
                "id": orderId,
                "name": strOrderName,
                "view": strView,
                "level": strCritical,
                "time": tCreateTime.strftime("%Y-%m-%d %H:%M:%S"),
                "detail": strDetail,
                "position": strPosition,
                "group": strGroup,
                "department": strDepartment,
                "processor": strProcessor,
                "status": workOrderStatusMapZh.get(nStatus),
                "startTime": strStartTime,
                "estimatedTime": strEstimatedTime,
                "duration": strDuration,
                "operator": "系统" if operatorEn == "system" else FaultPersonNameMap.get(operatorEn, ""),
                "enabled": nEnabled,
                "owner": strOwner,
                "mine": nMine,
                "overTime": bOverTime,
                "allowEnable": nAllowEnable,
                "allowTerminate": nAllowTernimate,
                "allowPause": nAllowPause,
                "allowSubmit": nAllowSubmite,
                "allowAdminSubmit": nAllowAdminSubmit,
                "conclusion": strConclusion
            })

        excelFileName = insert_work_order_into_excel(result)
        if not excelFileName:
            return jsonify(dict(err=1, msg="导出失败", data=""))
        return jsonify(dict(err=0, msg="导出成功", data=excelFileName))

    except Exception as e:
        logging.error("ERROR in /fdd/export: %s" % e.__str__())
        return jsonify(dict(err=1, msg="导出失败：{err}".format(err=e.__str__()), data={}))

@bp_fdd.route("/enableFault", methods=["POST"])
def enable_fault():
    rcv = request.get_json()
    orderId = rcv.get("orderId", None)
    nEnable = rcv.get("enable", None)
    userName = rcv.get("userName", None)
    try:
        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=False))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))
        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))
        if nEnable is None:
            return jsonify(dict(err=1, msg="启用禁用不能为空", data=False))
        if nEnable not in [0, 1]:
            return jsonify(dict(err=1, msg="启用禁用必须为0或1", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="未发现权限配置", data=False))

        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data=False))

        role = authDict.get(userName).get("role")
        if role != "admin":
            return jsonify(dict(err=1, msg="当前用户不是管理员，无法执行冻结/禁用操作", data=False))

        fddNameAndCurrStatus = BEOPDataAccess.getInstance().getFddNameAndCurrentStatus(orderId)
        if fddNameAndCurrStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="获取当前状态及故障名称失败", data={}))

        curStatus = fddNameAndCurrStatus.get("data")[1]
        fddName = fddNameAndCurrStatus.get("data")[0]  # fddName: fault点名

        faultLabelPoint = get_fault_label_point(fddName)

        rt = BEOPDataAccess.getInstance().enableFault(faultLabelPoint, nEnable)

        if rt.get("code") > 0:
            return jsonify(dict(err=1, msg=rt.get("msg"), data=False))

        return jsonify(dict(err=0, msg="更新成功", data=True))

    except Exception as e:
        logging.error("ERROR in /fdd/editFault: %s" % e.__str__())
        return jsonify(dict(err=1, msg="编辑失败:{err}".format(err=e.__str__()), data=False))


@bp_fdd.route("/processFault", methods=["POST"])
def change_fault_status_and_assign():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", "")
        targetStatus = rcv.get("targetStatus", None)  # 目标状态  1-分派（工单在进行中）；2-完成待审核；3-已审核；4-等待，暂停; 5-强制关闭
        orderId = rcv.get("orderId", None)
        processor = rcv.get("processor", "")
        estimatedTime = rcv.get("estimatedTime", "")
        reason = rcv.get("reason", "")
        opType = rcv.get("opType", None)  # opType: 0-修改状态；1-修改预计完成时间

        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))
        if targetStatus is None:
            return jsonify(dict(err=1, msg="目标状态不能为空", data=False))
        if not isinstance(targetStatus, int):
            return jsonify(dict(err=1, msg="目标状态必须为整数", data=False))
        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))
        if not isinstance(processor, str):
            return jsonify(dict(err=1, msg="处理人必须为字符串", data=False))
        if not isinstance(estimatedTime, str):
            return jsonify(dict(err=1, msg="预计完成时间必须为字符串", data=False))
        if not isinstance(reason, str):
            if targetStatus == 3:
                reason = ""
            else:
                return jsonify(dict(err=1, msg="原因必须为字符串", data=False))
        if opType not in [0, 1]:
            return jsonify(dict(err=1, msg="操作类型有误", data=False))

        if len(estimatedTime):
            if not isValidDate(estimatedTime, "%Y-%m-%d %H:%M:%S"):
                return jsonify(dict(err=1, msg="预计完成时间格式有误", data=False))

            if datetime.strptime(estimatedTime, "%Y-%m-%d %H:%M:%S") < datetime.now():
                return jsonify(dict(err=1, msg="预计完成时间不能小于当前时间", data=False))

        orders = BEOPDataAccess.getInstance().getAllFaultOrderIds()
        if orders.get("code") > 0:
            return jsonify(dict(err=1, msg="现有工单id列表获取失败", data=False))

        orderIds = orders.get("data")
        if orderId not in orderIds:
            return jsonify(dict(err=1, msg="该工单不存在", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="未发现权限配置", data={}))

        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data={}))

        role = authDict.get(userName).get("role")

        fddNameAndCurrStatus = BEOPDataAccess.getInstance().getFddNameAndCurrentStatus(orderId)
        if fddNameAndCurrStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="获取当前状态及故障名称失败", data={}))

        curStatus = fddNameAndCurrStatus.get("data")[1] # 当前状态
        fddName = fddNameAndCurrStatus.get("data")[0]  # fddName: fault点名

        resCurFaultOwner = BEOPDataAccess.getInstance().getFaultOwner(orderId)
        if resCurFaultOwner.get("code") > 0:
            return jsonify(dict(err=1, msg="获取故障当前所属人失败", data={}))
        curFaultOwner = resCurFaultOwner.get("data")

        resFaultCreator = BEOPDataAccess.getInstance().getFaultCreator(orderId)
        if resFaultCreator.get("code") > 0:
            logging.error("ERROR in /fdd/processFault: fail to get fault creator: %s" % resFaultCreator.get("msg"))
        faultCreator = resFaultCreator.get("data")

        faultLabelPoint = get_fault_label_point(fddName)

        adminUserName = get_admin_of_executor(userName, authDict)

        if role == "admin":
            workers = getFaultGroupMembersOfAdmin(userName)
            workersEnNameList = [item.get("name_en") for item in workers]
            if len(processor) and processor not in workersEnNameList:
                return jsonify(dict(err=1, msg="所指派的处理人不在该admin管辖范围内", data={}))

            if targetStatus == 1 and curStatus in [0, 1] and opType == 0 and not len(processor):
                return jsonify(dict(err=1, msg="处理人不能为空", data=False))

            if targetStatus == 1 and curStatus in [0, 1] and opType == 0 and not len(estimatedTime):
                return jsonify(dict(err=1, msg="预计完成时间不能为空", data=False))

            if targetStatus == 1 and curStatus == 1 and opType == 1 and not isValidDate(estimatedTime, "%Y-%m-%d %H:%M:%S"):
                return jsonify(dict(err=1, msg="预计完成时间格式有误", data=False))

            if targetStatus == 1 and curStatus == 1 and opType == 0 and curFaultOwner == processor:
                return jsonify(dict(err=1, msg="该故障已分派给目标处理人{name}".format(name=processor), data=False))

            if targetStatus == 4 and not len(reason):
                return jsonify(dict(err=1, msg="工单暂停原因不能为空", data=False))

            # if targetStatus == 2:
            #     return jsonify(dict(err=1, msg="管理员无法将故障处理为提交待审核", data={}))

            if targetStatus not in [1, 3, 4, 5]:
                return jsonify(dict(err=1, msg="需设定的目标状态有误", data={}))

            if curStatus == 1 and targetStatus not in [1, 3, 4, 5]:
                return jsonify(dict(err=1, msg="无法修改为目标状态", data={}))

            if curStatus == 2 and targetStatus not in [3, 5]:
                return jsonify(dict(err=1, msg="无法修改为目标状态", data={}))

            if curStatus == 3 and targetStatus not in [5]:
                return jsonify(dict(err=1, msg="当前状态为已确认，无法进行其他修改", data={}))

            if curStatus == 4 and targetStatus not in [1, 3, 5]:
                return jsonify(dict(err=1, msg="无法修改为目标状态", data={}))
            if curStatus == 5:
                return jsonify(dict(err=1, msg="该操作无法执行，因该工单已被终止", data={}))

        elif role == "executor":
            if curFaultOwner != userName and not (curStatus == 0 and faultCreator == userName):
                return jsonify(dict(err=1, msg="该故障不属于当前用户，无权限处理", data={}))

            if targetStatus != 2:
                return jsonify(dict(err=1, msg="故障处理人无权限将故障状态修改为目标状态", data={}))

            if not len(reason):
                return jsonify(dict(err=1, msg="提交审核的总结内容不能为空", data=False))

        rt = BEOPDataAccess.getInstance().processFault(fddName, orderId, userName, curStatus, targetStatus, processor,
                                                       estimatedTime, reason, opType, faultLabelPoint, adminUserName, curFaultOwner, MaintainanceFaultPointName, faultCreator, role)

        if rt.get("code") > 0:
            return jsonify(dict(err=1, msg=rt.get("msg"), data=False))

        # 提交完结工单时（管理员）或提交工单待审核（执行人）输入的总结内容若不为空则写入评论区
        if isinstance(reason, str) and len(reason):
            if targetStatus in [3, 2]:
                nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("work_order_comment")
                nCommentId = nMaxId + 1
                BEOPDataAccess.getInstance().addCommentToWorkOrder(nCommentId, orderId, userName, reason, None)

        return jsonify(dict(err=0, msg="更新成功", data=True))

    except Exception as e:
        logging.error("ERROR in /fdd/changeFaultStatusAndAssign: %s" % e.__str__())
        return jsonify(dict(err=1, msg="更新失败:{err}".format(err=e.__str__()), data=[]))


@bp_fdd.route("/addFault", methods=["POST"])
def add_fault():
    try:
        rcv = request.get_json()
        fddName = rcv.get("fddName", None)
        detail = rcv.get("detail", "")

        if fddName is None:
            return jsonify(dict(err=1, msg="故障点名不能为空", data=False))
        if not isinstance(fddName, str):
            return jsonify(dict(err=1, msg="故障点名必须为字符串", data=False))
        if not isinstance(detail, str):
            return jsonify(dict(err=1, msg="故障详情必须为字符串", data=False))

        # 获取Redis里面的点信息字典
        pointDict = RedisManager.get("FaultPointInfo")
        if not pointDict:
            BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
            pointDict = RedisManager.get("FaultPointInfo")
            if not pointDict:
                return jsonify(dict(err=1, msg="Redis中未发现故障点", data={}))

        if fddName not in pointDict.keys():
            return jsonify(dict(err=1, msg="点表中未发现输入的故障点名", data={}))

        strOrderName = pointDict.get(fddName).get("description", "")

        orders = BEOPDataAccess.getInstance().getAllFaultOrderIds()
        if orders.get("code") > 0:
            return jsonify(dict(err=1, msg="现有工单id列表获取失败", data=False))
        orderIds = orders.get("data")
        newOrderId = max(orderIds) + 1 if len(orderIds) else 1

        rt = BEOPDataAccess.getInstance().addFault(fddName, newOrderId, strOrderName, detail)

        return jsonify(dict(err=rt.get("code"), msg=rt.get("msg"), data=rt.get("data")))

    except Exception as e:
        logging.error("ERROR in /fdd/addFault: %s" % e.__str__())
        return jsonify(dict(err=1, msg="添加失败：{err}".format(err=e.__str__()), data=False))


@bp_fdd.route("/getGroupMembersOfAdmin", methods=["POST"])
def get_group_members_of_admin():
    try:
        rcv = request.get_json()
        admin = rcv.get("admin", None)
        if admin is None:
            return jsonify(dict(err=1, msg="admin不能为空", data=False))
        if not isinstance(admin, str):
            return jsonify(dict(err=1, msg="admin必须为字符串", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="未发现权限配置", data={}))

        if admin not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data={}))

        if authDict.get(admin).get("role") != "admin":
            return jsonify(dict(err=1, msg="该用户角色不是admin", data={}))

        group = getFaultGroupMembersOfAdmin(admin)

        return jsonify(dict(err=0, msg="", data=group))

    except Exception as e:
        logging.error("ERROR in /fdd/getGroupMembersOfAdmin: %s" % e.__str__())
        return jsonify(dict(err=1, msg="获取失败:{err}".format(err=e.__str__()), data=[]))


@bp_fdd.route("/addMaintainanceFault", methods=["POST"])
def add_maintainance_fault():
    try:
        rcv = request.get_json()
        detail = rcv.get("detail", "")
        creator = rcv.get("creator", "")
        processor = rcv.get("processor", "")
        estimatedTime = rcv.get("estimatedTime", "")
        name = rcv.get("name", "")
        imgList = rcv.get("imgList", [])

        if not isinstance(creator, str):
            return jsonify(dict(err=1, msg="创建者必须为字符串", data=False))
        if not len(creator):
            return jsonify(dict(err=1, msg="创建者不能为空", data=False))
        if not isinstance(name, str):
            return jsonify(dict(err=1, msg="工单名称必须为字符串", data=False))
        if not len(name):
            return jsonify(dict(err=1, msg="工单名称不能为空", data=False))

        if detail:
            if not isinstance(detail, str):
                return jsonify(dict(err=1, msg="详情必须为字符串", data=False))
        if processor:
            if not isinstance(processor, str):
                return jsonify(dict(err=1, msg="处理人必须为字符串", data=False))
        if estimatedTime:
            if not isinstance(estimatedTime, str):
                return jsonify(dict(err=1, msg="预计完成时间必须为字符串", data=False))
            if not isValidDate(estimatedTime, "%Y-%m-%d %H:%M:%S"):
                return jsonify(dict(err=1, msg="预计完成时间格式有误", data=False))
            if datetime.strptime(estimatedTime, "%Y-%m-%d %H:%M:%S") < datetime.now():
                return jsonify(dict(err=1, msg="预计完成时间不能小于当前时间", data=False))

        # 获取Redis里面的点信息字典
        pointDict = RedisManager.get("FaultPointInfo")
        if not pointDict:
            BEOPSqliteAccess.getInstance().UpdateFaultPointsToRedis()
            pointDict = RedisManager.get("FaultPointInfo")
            if not pointDict:
                return jsonify(dict(err=1, msg="Redis中未发现故障点", data={}))

        if MaintainanceFaultPointName not in pointDict.keys():
            return jsonify(dict(err=1, msg="点表里面未发现虚拟点：{point}".format(point=MaintainanceFaultPointName), data={}))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="未发现权限配置", data={}))

        if not authDict.get(creator, None):
            return jsonify(dict(err=1, msg="权限配置中未发现用户名{name}".format(name=creator), data={}))

        if processor:
            if not authDict.get(processor, None):
                return jsonify(dict(err=1, msg="权限配置中未发现用户名{name}".format(name=processor), data={}))

        if "工单" not in authDict.get(creator).get("visable").get("category"):
            return jsonify(dict(err=1, msg="'工单'不在创建者的类型维度里面", data={}))

        orders = BEOPDataAccess.getInstance().getAllFaultOrderIds()
        if orders.get("code") > 0:
            return jsonify(dict(err=1, msg="现有工单id列表获取失败", data=False))

        orderIds = orders.get("data", [])
        newOrderId = 1
        if len(orderIds):
            newOrderId = max(orderIds) + 1

        adminUserName = get_admin_of_executor(creator, authDict)

        strImg = ""
        if len(imgList):
            strImg = ",".join(imgList)

        rt = BEOPDataAccess.getInstance().addMaintainanceFault(creator, processor, name, detail, estimatedTime, newOrderId, MaintainanceFaultPointName, adminUserName, strImg)

        return jsonify(dict(err=rt.get("code"), msg=rt.get("msg"), data=rt.get("data")))

    except Exception as e:
        strLog = "ERROR in /fdd/addMaintainanceFault: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="添加失败:{err}".format(err=e.__str__()), data=False))


@bp_fdd.route("/flow", methods=["POST"])
def process_fault():
    try:
        rcv = request.get_json()
        orderId = rcv.get("orderId", None)

        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))

        res = BEOPDataAccess().getInstance().getFaultInfo(orderId=orderId)

        if res.get("code") > 0:
            return jsonify(dict(err=1, msg="获取失败", data=[]))

        infoList = res.get("data").get(orderId)

        infoList = [info for info in infoList if info.get("opType") == 0]

        infoList = sorted(infoList, key=lambda item: item.get("modifyTime"))

        if not len(infoList):
            return jsonify(dict(err=0, msg="获取成功", data=dict(flow=[{"status":0, "name": "", "time": ""},
                                                                   {"status": 1, "name": "", "time": ""},
                                                                   {"status": 2, "name": "", "time": ""},
                                                                   {"status": 3, "name": "", "time": ""}], currentStatus=0)))

        NameMap = RedisManager.get("FaultPersonNameMap")

        assignTo = ""
        flowList = []
        curStatus = 0
        for info in infoList:
            strModifyTime = info.get("modifyTime").strftime("%Y-%m-%d %H:%M:%S")
            opNameEn = info.get("opUserName")
            curStatus = info.get("status")

            # 当status为1时：1-若动作信息中包含toUserName则生成分派动作的执行信息和接单的执行信息
            # 2-动作信息中不包含toUserName则只生成接单的执行信息
            if info.get("status") == 1:
                if eval(info.get("opContentData")).get("toUserName", None):
                    toNameEn = eval(info.get("opContentData")).get("toUserName")
                    assignTo = toNameEn

                    flowList.append(dict(status=0, name=NameMap.get(opNameEn, ""), time=strModifyTime))
                    flowList.append(dict(status=1, name=NameMap.get(toNameEn, ""), time=strModifyTime))

                else:
                    flowList.append(dict(status=1, name=NameMap.get(assignTo, ""), time=strModifyTime))

            # 当status为2,3,4时
            elif info.get("status") in [2, 3, 4]:
                flowList.append(dict(status=info.get("status"), name=NameMap.get(opNameEn, ""), time=strModifyTime))

        # 补齐各个状态
        for num in [0, 1, 2, 3]:
            exists = False
            for flow in flowList:
                if flow.get("status") == num:
                    exists = True
                    break
            if not exists:
                flowList.append(dict(status=num, name="", time=""))

        return jsonify(dict(err=0, msg="获取成功", data={"flow": flowList, "currentStatus": curStatus}))

    except Exception as exp:
        logging.error("ERROR in /fdd/flow: %s" % exp.__str__())
        return jsonify(dict(err=1, msg="获取失败:{err}".format(err=exp.__str__()), data={}))


@bp_fdd.route("/countUserPendingFault", methods=["POST"])
def count_user_pending_fault():
    try:
        rcv = request.get_json()
        authDict = RedisManager.get("FaultAuthInfo")
        if authDict is None:
            return jsonify(dict(err=1, msg="权限定义字典为空", data=None))

        userName = rcv.get("userName", None)
        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=None))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符串", data=None))
        if userName not in authDict.keys():
            return jsonify(dict(err=1, msg="该用户不在后台配置的权限列表中", data=None))

        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="获取当前用户的权限失败", data=None))

        rt = BEOPDataAccess.getInstance().countUserPendingFault(userName, role)

        if rt.get("code") > 0:
            return jsonify(dict(err=1, msg=rt.get("msg"), data=None))

        return jsonify(dict(err=0, msg=rt.get("msg"), data=rt.get("data")))
    except Exception as e:
        logging.error("ERROR in /fdd/countUserPendingFault: %s" % e.__str__())
        return jsonify(dict(err=1, msg="获取失败: %s" % e.__str__(), data=None))

@bp_fdd.route("/inspectWorkOrders")
def inspect_work_orders():
    rt = inspect_work_order()
    return jsonify(dict(err=rt.get("code"), msg=rt.get("msg"), data=rt.get("data")))

# 1-分派（工单在进行中）；2-完成待审核；3-已审核；4-等待，暂停; 5-强制关闭
@bp_fdd.route("/edit", methods=["POST"])
def edit_work_order():
    try:
        rcv = request.get_json()
        detail = rcv.get("detail", "")
        processor = rcv.get("processor", "")
        name = rcv.get("name", "")
        estimatedTime = rcv.get("estimatedTime", "")
        orderId = rcv.get("orderId", None)
        userName = rcv.get("userName", None)

        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=False))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))
        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))

        if detail is None:
            detail = ""
        if detail:
            if not isinstance(detail, str):
                return jsonify(dict(err=1, msg="详情必须为字符串", data=False))

        if name is None:
            name = ""
        if name:
            if not isinstance(name, str):
                return jsonify(dict(err=1, msg="工单名称必须为字符串", data=False))

        if processor is None:
            processor = ""
        if processor:
            if not isinstance(processor, str):
                return jsonify(dict(err=1, msg="处理人必须为字符串", data=False))

        if estimatedTime is None:
            estimatedTime = ""
        if estimatedTime:
            if not isinstance(estimatedTime, str):
                return jsonify(dict(err=1, msg="预计完成时间必须为字符串", data=False))
            if not isValidDate(estimatedTime, "%Y-%m-%d %H:%M:%S"):
                return jsonify(dict(err=1, msg="预计完成时间格式有误", data=False))
            if datetime.strptime(estimatedTime, "%Y-%m-%d %H:%M:%S") < datetime.now():
                return jsonify(dict(err=1, msg="预计完成时间不能小于当前时间", data=False))

        if not len(detail) and not len(name) and not len(processor) and not len(estimatedTime):
            return jsonify(dict(err=1, msg="所有的修改项都为空", data=False))

        authDict = RedisManager.get("FaultAuthInfo")
        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="用户{userName}的角色定义（admin/executor）获取失败".format(userName=userName), data={}))

        if role != "admin":
            return jsonify(dict(err=1, msg="当前用户不是admin，无权限修改", data=False))

        if len(processor):
            if processor not in authDict.keys():
                return jsonify(dict(err=1, msg="目标处理人不在后台配置的权限列表中", data=False))

        if len(processor):
            resCurFaultOwner = BEOPDataAccess.getInstance().getFaultOwner(orderId)
            if resCurFaultOwner.get("code") > 0:
                return jsonify(dict(err=1, msg="获取故障当前所属人失败", data=False))
            curFaultOwner = resCurFaultOwner.get("data")

            # 如果指派处理人已经是目标人则强行置空
            if curFaultOwner == processor:
                processor = ""

        if len(estimatedTime):
            resCurEstimatedTime = BEOPDataAccess.getInstance().getWorkOrderCurrentEstimatedTime(orderId)
            if resCurEstimatedTime.get("code") > 0:
                return jsonify(dict(err=1, msg="获取该故障的当前预计完成时间失败", data=False))

            # 如果预计完成时间已经是目标设置值则强行置空
            if resCurEstimatedTime.get("data") == datetime.strptime(estimatedTime, "%Y-%m-%d %H:%M:%S"):
                estimatedTime = ""

        resFddNameAndCurStatus = BEOPDataAccess.getInstance().getFddNameAndCurrentStatus(orderId)
        if resFddNameAndCurStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="获取工单当前状态失败", data=False))
        fddName = resFddNameAndCurStatus.get("data")[0]
        curStatus = resFddNameAndCurStatus.get("data")[1]

        if curStatus not in [0, 1, 4]:
            return jsonify(dict(err=1, msg="无法编辑，因当前工单状态不处于以下任何一个状态：待分派、进行中、等待", data=False))

        dRes = BEOPDataAccess.getInstance().editWorkOrder(orderId, name, detail, processor, estimatedTime, userName, fddName, curStatus)
        if dRes.get("err") > 0:
            return jsonify(dict(err=1, msg=",".join(dRes.get("msg")), data=False))
        return jsonify(dict(err=0, msg="修改成功", data=True))

    except Exception as e:
        logging.error("ERROR in /fdd/edit: %s" % e.__str__())
        dVersion = get_proc_version()
        return jsonify(dict(err=1, msg="编辑失败: %s" % e.__str__(), data=False))

@bp_fdd.route("/editUserPassword", methods=["POST"])
def edit_user_password():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", None)
        password = rcv.get("password", None)

        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=False))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))

        if not password:
            return jsonify(dict(err=1, msg="密码不能为空", data=False))
        if not isinstance(password, str):
            return jsonify(dict(err=1, msg="密码必须为字符", data=False))

        userList = BEOPDataAccess.getInstance().get_all_users()
        dUserInfo = {}
        for user in userList:
            if userName == user.get("username"):
                dUserInfo = user
                break

        if not dUserInfo:
            return jsonify(dict(err=1, msg="该用户名不存在", data=False))

        # validRes = BEOPDataAccess.getInstance().validate_user(userName, oldPassword)
        # if validRes.get("err") > 0:
        #     return jsonify(dict(err=1, msg="密码错误", data=False))

        dModifyData = {"userpwd": password}
        bSuc = BEOPDataAccess.getInstance().modify_user(dUserInfo.get("userid"), dModifyData)
        if not bSuc:
            return jsonify(dict(err=1, msg="修改失败", data=False))
        return jsonify(dict(err=0, msg="修改成功", data=True))
    except Exception as e:
        logging.error("ERROR in /fdd/editUserPassword: %s" % e.__str__())
        return jsonify(dict(err=1, msg="编辑失败: %s" % e.__str__(), data=False))


@bp_fdd.route("/editUserName", methods=["POST"])
def edit_user_name():
    try:
        rcv = request.get_json()
        oldNameEn = rcv.get("oldNameEn", None)
        newNameCh = rcv.get("newNameCh", None)

        if not oldNameEn:
            return jsonify(dict(err=1, msg="旧英文用户名不能为空", data=False))
        if not isinstance(oldNameEn, str):
            return jsonify(dict(err=1, msg="旧英文用户名必须为字符", data=False))
        if not newNameCh:
            return jsonify(dict(err=1, msg="新用户名不能为空", data=False))
        if not isinstance(newNameCh, str):
            return jsonify(dict(err=1, msg="新用户名必须为字符", data=False))

        if len(newNameCh) > 10:
            return jsonify(dict(err=1, msg="密码字符长度不能大于10", data=False))

        if newNameCh[0].isdigit():
            return jsonify(dict(err=1, msg="用户名首字符不能为数字", data=False))

        userList = BEOPDataAccess.getInstance().get_all_users()
        dUserInfo = {}
        for user in userList:
            if oldNameEn == user.get("username"):
                dUserInfo = user
                break

        if not dUserInfo:
            return jsonify(dict(err=1, msg="该用户不存在", data=False))

        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
           return jsonify(dict(err=1, msg="redis中未发现故障工单权限配置", data=False))

        if not authDict.get(oldNameEn, {}):
            return jsonify(dict(err=1, msg="故障工单权限配置中未发现该用户", data=False))

        dModifyData = {"userfullname": newNameCh}
        bSucMysqlSave = BEOPDataAccess.getInstance().modify_user(dUserInfo.get("userid"), dModifyData)

        authDict = RedisManager.get("FaultAuthInfo")
        bSucJsonSave = False
        if authDict:
            try:
                authDict[oldNameEn]["name_zh"] = newNameCh
                bSucFactory = BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', 'fdd_auth', authDict)
                bSucRedis = BEOPSqliteAccess.getInstance().UpdateFaultAuthInfoToRedis()
                bSucJsonSave = bSucFactory and bSucRedis
            except Exception as e:
                logging.error("ERROR in /fdd/editUserName: %s" % e.__str__())
                pass

        if bSucMysqlSave and bSucJsonSave:
            return jsonify(dict(err=0, msg="修改成功", data=True))

        return jsonify(dict(err=1, msg="修改失败", data=False))
    except Exception as e:
        logging.error("ERROR in /fdd/editUserName: %s" % e.__str__())
        return jsonify(dict(err=1, msg="编辑失败: %s" % e.__str__(), data=False))


@bp_fdd.route("/saveImgToLocal", methods=["POST"])
def save_img_to_local():
    try:
        fileList = []
        fileNameList = []
        for idx in range(1, 11):
            file = request.files.get("file%02d" % idx)
            if file is None or not isinstance(file.content_type, str):
                continue

            if file.filename in fileNameList:
                continue

            fileList.append(file)
            fileNameList.append(file.filename)

        if not len(fileList):
            return jsonify(dict(err=1, msg="未发现图片", data=""))

        for file in fileList:

            strFileName = file.filename

            extension = os.path.splitext(strFileName)[1]
            if not extension in [".jpg", ".png", ".jpeg", ".bmp", ".JPG", ".PNG", ".JPEG", ".BMP"]:
                return jsonify(dict(err=1, msg="只能上传图片文件（支持jpg, png, jpeg, bmp格式）", data=""))

        dResult = saveFddImgToLocal(fileList)

        return jsonify(dResult)

    except Exception as e:
        strLog = "ERROR in /fdd/saveImgToLocal: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="上传失败: %s" % e.__str__(), data=""))


@bp_fdd.route("/addCommentToWorkOrder", methods=["POST"])
def add_comment_to_work_order():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", None)
        orderId = rcv.get("orderId", None)
        content = rcv.get("content", None)
        imgNameList = rcv.get("imgList", [])

        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户英文名称必须为字符串", data=False))

        if not len(userName):
            return jsonify(dict(err=1, msg="用户英文名称不能为空", data=False))

        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单ID必须为整数", data=False))

        if content != None:
            if not isinstance(content, str):
                return jsonify(dict(err=1, msg="评论内容必须为字符串", data=False))
            if len(content) > 5000:
                return jsonify(dict(err=1, msg="评论内容过长", data=False))
            if not len(content):
                content = None

        if imgNameList != None:
            if not isinstance(imgNameList, list):
                return jsonify(dict(err=1, msg="图片名称列表必须为数组", data=False))
            if not len(imgNameList):
                imgNameList = None

        if content == None and imgNameList == None:
            return jsonify(dict(err=1, msg="评论内容和图片名称列表都为空", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data=False))

        dUserInfo = authDict.get(userName, {})
        if not dUserInfo:
            return jsonify(dict(err=1, msg="fdd_auth中未发现关于{userName}的权限配置".format(userName=userName), data=False))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")
        if not isinstance(viewDict, dict):
            return jsonify(dict(err=1, msg="用户权限信息必须为字符串，请查看项目现场factory中的fdd_auth配置下该用户的visable配置", data=False))

        nFaultTypeList = viewDict.get("category", [])
        if not len(nFaultTypeList):
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        if "工单" not in nFaultTypeList:
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        orders = BEOPDataAccess.getInstance().getAllFaultOrderIds()
        if orders.get("code") > 0:
            return jsonify(dict(err=1, msg="现有工单id列表获取失败", data=False))

        orderIds = orders.get("data")
        if orderId not in orderIds:
            return jsonify(dict(err=1, msg="该工单不存在", data=False))

        nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("work_order_comment")
        nCommentId = nMaxId + 1

        bSuc = BEOPDataAccess.getInstance().addCommentToWorkOrder(nCommentId, orderId, userName, content, imgNameList)

        if not bSuc:
            return jsonify(dict(err=1, msg="添加失败", data=False))
        return jsonify(dict(err=0, msg="添加成功", data=True))

    except Exception as e:
        strLog = "ERROR in /fdd/addCommentToWorkOrder: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="添加失败: %s" % e.__str__(), data=False))

@bp_fdd.route("/deleteCommentFromWorkOrder", methods=["POST"])
def delete_comment_from_work_order():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", None)
        commentId = rcv.get("id", None)         # 评论ID

        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户英文名称必须为字符串", data=False))
        if not len(userName):
            return jsonify(dict(err=1, msg="用户英文名称不能为空", data=False))
        if not isinstance(commentId, int):
            return jsonify(dict(err=1, msg="评论ID必须为整数", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data=False))

        dUserInfo = authDict.get(userName, {})
        if not dUserInfo:
            return jsonify(dict(err=1, msg="fdd_auth中未发现关于{userName}的权限配置".format(userName=userName), data=False))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")
        if not isinstance(viewDict, dict):
            return jsonify(dict(err=1, msg="用户权限信息必须为字符串，请查看项目现场factory中的fdd_auth配置下该用户的visable配置", data=False))

        nFaultTypeList = viewDict.get("category", [])
        if not len(nFaultTypeList):
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        if "工单" not in nFaultTypeList:
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        dComment = BEOPDataAccess.getInstance().getWorkOrderCommentDetail(commentId)
        if dComment == None:
            return jsonify(dict(err=1, msg="数据坤繁忙，请稍后再试", data=False))

        commentInfo = dComment.get(commentId, {})
        if not commentInfo:
            return jsonify(dict(err=1, msg="未发现评论信息", data=False))

        bSuc = BEOPDataAccess.getInstance().deleteCommentFromWorkOrder(commentId)
        if not bSuc:
            return jsonify(dict(err=1, msg="删除评论失败", data=False))

        imgList = commentInfo.get("imgList", [])
        if len(imgList):
            imgPathList = ["{ossDirectory}{imgName}".format(ossDirectory=OSS_FDD_IMG_DIR, imgName=imgName) for imgName in imgList]
            bSuc = OSSTool().delete_files(imgPathList)
            if not bSuc:
                return jsonify(dict(err=1, msg="删除评论中的图片失败", data=False))

        return jsonify(dict(err=0, msg="删除评论成功", data=True))

    except Exception as e:
        strLog = "ERROR in /fdd/deleteCommentFromWorkOrder: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="删除失败: %s" % e.__str__(), data=False))


@bp_fdd.route("/editCommentOfWorkOrder", methods=["POST"])
def edit_comment_of_work_order():
    try:
        rcv = request.get_json()
        userName = rcv.get("userName", None)
        commentId = rcv.get("id", None)           # 评论ID
        content = rcv.get("content", None)

        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户英文名称必须为字符串", data=False))
        if not len(userName):
            return jsonify(dict(err=1, msg="用户英文名称不能为空", data=False))
        if not isinstance(commentId, int):
            return jsonify(dict(err=1, msg="评论ID必须为整数", data=False))
        if not isinstance(content, str):
            return jsonify(dict(err=1, msg="评论内容必须为字符串", data=False))
        if not len(content):
            return jsonify(dict(err=1, msg="评论内容不能为空", data=False))
        if len(content) > 5000:
            return jsonify(dict(err=1, msg="评论内容过长", data=False))

        # 从redis获取权限列表
        authDict = RedisManager.get("FaultAuthInfo")
        if not authDict:
            return jsonify(dict(err=1, msg="Redis中未发现权限配置，请检查fdd_auth配置", data=False))

        dUserInfo = authDict.get(userName, {})
        if not dUserInfo:
            return jsonify(dict(err=1, msg="fdd_auth中未发现关于{userName}的权限配置".format(userName=userName), data=False))

        # 获取该用户的权限字典
        viewDict = authDict.get(userName).get("visable")
        if not isinstance(viewDict, dict):
            return jsonify(dict(err=1, msg="用户权限信息必须为字符串，请查看项目现场factory中的fdd_auth配置下该用户的visable配置", data=False))

        nFaultTypeList = viewDict.get("category", [])
        if not len(nFaultTypeList):
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        if "工单" not in nFaultTypeList:
            return jsonify(dict(err=1, msg="该用户无工单权限", data=False))

        bSuc = BEOPDataAccess.getInstance().editCommentOfWorkOrder(commentId, content)
        if not bSuc:
            return jsonify(dict(err=1, msg="修改评论失败", data=False))
        return jsonify(dict(err=0, msg="修改评论成功", data=True))

    except Exception as e:
        strLog = "ERROR in /fdd/editCommentOfWorkOrder: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="修改评论失败: %s" % e.__str__(), data=False))


@bp_fdd.route("/getWorkOrderFlow", methods=["POST"])
def get_work_order_flow():
    try:
        rcv = request.get_json()
        orderId = rcv.get("orderId", None)

        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data={}))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data={}))

        nameMap = RedisManager.get("FaultPersonNameMap")
        if not isinstance(nameMap, dict):
            nameMap = {}

        res = BEOPDataAccess().getInstance().getFaultInfo(orderId=orderId)

        if res.get("code") > 0:
            return jsonify(dict(err=1, msg="获取失败", data=[]))

        statusMap = {
            1: "进行中",
            2: "完成待审核",
            3: "已审核",
            4: "暂停",
            5: "强制关闭"
        }

        workOrderFlow = res.get("data").get(orderId, [])

        tCreateTime = workOrderFlow[0].get("modifyTime")
        workOrderName = workOrderFlow[0].get("name")
        workOrderDetail = workOrderFlow[0].get("detail", "")

        imgNameList = []

        creatorEn = ""
        creatorCh = ""
        createTime = ""

        flowList = []
        for item in workOrderFlow:
            tModTime = item.get("modifyTime")
            strModTime = tModTime.strftime("%Y-%m-%d %H:%M:%S")
            opType = item.get("opType")
            opUserEn = item.get("opUserName")
            opUserCh = nameMap.get(opUserEn) if nameMap.get(opUserEn, None) != None else opUserEn
            title = item.get("name")

            lContent = []
            if opType == -1:
                lContent.append(
                    "创建了工单，标题为{title}".format(userName=opUserCh, title=title)
                )
            else:
                opContentData = item.get("opContentData", None)
                if opContentData != None:

                    dOpContentData = eval(opContentData)

                    if dOpContentData.get("changeTo", None) != None:
                        changeToStatus = dOpContentData.get("changeTo")
                        lContent.append(
                            "将状态修改为{desc}".format(desc=statusMap.get(changeToStatus, "未知")))

                    if dOpContentData.get("toUserName", None) != None:
                        toUserNameEn = dOpContentData.get("toUserName")
                        toUserNameCh = nameMap.get(toUserNameEn) if nameMap.get(toUserNameEn, None) != None else toUserNameEn
                        lContent.append(
                            "将工单指派给{toUserName}".format(toUserName=toUserNameCh)
                        )

                    if dOpContentData.get("estimatedTime", None) != None:
                        estimatedTime = dOpContentData.get("estimatedTime")
                        lContent.append(
                            "将预计完成时间修改为{estimatedTime}".format(estimatedTime=estimatedTime)
                        )

                    if dOpContentData.get("conclusion", None) != None:
                        lContent.append(
                            "添加结论:{conc}".format(conc=dOpContentData.get("conclusion"))
                        )

            strContent = "{}".format(opUserCh)
            for nIndex, sContent in enumerate(lContent):
                if nIndex == 0:
                    strContent += sContent + ";"
                    continue

                strContent += "并且" + sContent + ";"

            strContent += "\n"

            flowList.append(dict(user=opUserCh,
                                 tTime=tModTime,
                                 strTime=strModTime,
                                 content=dict(detail=strContent),
                                 type="OPERATE"))

            if item.get("modifyTime") < tCreateTime:
                workOrderName = item.get("name")
                workOrderDetail = item.get("detail", "")
                tCreateTime = item.get("modifyTime")

            if item.get("status", None) == 0:
                image = item.get("img", None)
                if isinstance(image, str):
                    imageList = image.split(",")
                    for iName in imageList:
                        if len(iName):
                            imgNameList.append(iName)

            if item.get("opType", None) == -1:
                creatorEn = item.get("opUserName")
                creatorCh = nameMap.get(creatorEn, "")
                try:
                    createTime = item.get("modifyTime").strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass


        dComment = BEOPDataAccess().getInstance().getCommentOfWorkOrder(orderId)
        commentList = dComment.get(orderId, [])

        for item in commentList:
            opUserEn = item["creator"]
            opUserCh = nameMap.get(opUserEn) if nameMap.get(opUserEn, None) != None else opUserEn
            commentId = item["id"]
            commentContent = item["content"]
            tCreateTime = item["createTime"]
            strCreateTime = tCreateTime.strftime("%Y-%m-%d %H:%M:%S")
            flowList.append(dict(user=opUserEn,
                                 userCh=opUserCh,
                                 tTime=tCreateTime,
                                 strTime=strCreateTime,
                                 content=dict(commentId=commentId,detail=commentContent),
                                 imgNameList=item["imgNameList"],
                                 type="ADD_COMMENT"))

        # 按时间降序排序
        for i in range(len(flowList)):
            for j in range(len(flowList)-i-1):
                if flowList[j].get("tTime") > flowList[j+1].get("tTime"):
                    flowList[j], flowList[j+1] = flowList[j+1], flowList[j]

        return jsonify(dict(err=0, msg="", data=dict(flowList=flowList,
                                                     workOrderName=workOrderName,
                                                     workOrderDetail=workOrderDetail,
                                                     creatorEn=creatorEn,
                                                     creatorCh=creatorCh,
                                                     createTime=createTime,
                                                     imgList=imgNameList)))

    except Exception as e:
        strLog = "ERROR in /fdd/getWorkOrderFlow: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="获取失败: %s" % e.__str__(), data={}))


@bp_fdd.route("/addImgToWorkOrder", methods=["POST"])
def add_img_to_work_order():
    try:
        rcv = request.get_json()
        orderId = rcv.get("orderId", None)
        userName = rcv.get("userName", None)
        imgList = rcv.get("imgList", [])

        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=False))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))

        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))

        if not len(imgList):
            return jsonify(dict(err=1, msg="图片名称列表不能为空", data=False))

        authDict = RedisManager.get("FaultAuthInfo")
        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="用户{userName}的角色定义（admin/executor）获取失败".format(userName=userName), data={}))

        if role != "admin":
            return jsonify(dict(err=1, msg="当前用户不是admin，无权限修改", data=False))

        resFddNameAndCurStatus = BEOPDataAccess.getInstance().getFddNameAndCurrentStatus(orderId)
        if resFddNameAndCurStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="获取工单当前状态失败", data=False))

        curStatus = resFddNameAndCurStatus.get("data")[1]

        if curStatus not in [0, 1, 4]:
            return jsonify(dict(err=1, msg="无法添加图片，因当前工单状态不处于以下任何一个状态：待分派、进行中、等待", data=False))

        bSuc = BEOPDataAccess.getInstance().addImgToFddWorkOrder(orderId, imgList)
        if bSuc:
            return jsonify(dict(err=0, msg="添加图片成功", data=True))
        return jsonify(dict(err=1, msg="添加图片失败", data=False))
    except Exception as e:
        strLog = "ERROR in /fdd/addImgToWorkOrder: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="添加失败: %s" % e.__str__(), data=False))


@bp_fdd.route("/removeImgFromWorkOrder", methods=["POST"])
def remove_img_from_work_order():
    try:
        rcv = request.get_json()
        orderId = rcv.get("orderId", None)
        userName = rcv.get("userName", None)
        imgList = rcv.get("imgList", [])

        if not userName:
            return jsonify(dict(err=1, msg="用户名不能为空", data=False))
        if not isinstance(userName, str):
            return jsonify(dict(err=1, msg="用户名必须为字符", data=False))

        if orderId is None:
            return jsonify(dict(err=1, msg="工单号不能为空", data=False))
        if not isinstance(orderId, int):
            return jsonify(dict(err=1, msg="工单号必须为整数", data=False))

        if not len(imgList):
            return jsonify(dict(err=1, msg="图片名称列表不能为空", data=False))

        authDict = RedisManager.get("FaultAuthInfo")
        role = authDict.get(userName).get("role", None)
        if not role:
            return jsonify(dict(err=1, msg="用户{userName}的角色定义（admin/executor）获取失败".format(userName=userName), data={}))

        if role != "admin":
            return jsonify(dict(err=1, msg="当前用户不是admin，无权限修改", data=False))

        resFddNameAndCurStatus = BEOPDataAccess.getInstance().getFddNameAndCurrentStatus(orderId)
        if resFddNameAndCurStatus.get("code") > 0:
            return jsonify(dict(err=1, msg="获取工单当前状态失败", data=False))

        curStatus = resFddNameAndCurStatus.get("data")[1]

        if curStatus not in [0, 1, 4]:
            return jsonify(dict(err=1, msg="无法删除图片，因当前工单状态不处于以下任何一个状态：待分派、进行中、等待", data=False))

        bSuc = BEOPDataAccess.getInstance().removeImgFromWorkOrder(orderId, imgList)
        if bSuc:
            return jsonify(dict(err=0, msg="添加图片成功", data=True))
        return jsonify(dict(err=1, msg="删除图片失败", data=False))
    except Exception as e:
        strLog = "ERROR in /fdd/removeImgFromWorkOrder: %s" % e.__str__()
        logging.error(strLog)
        return jsonify(dict(err=1, msg="删除失败: %s" % e.__str__(), data=False))

@bp_fdd.route("/import", methods=["POST"])
def import_fdd_work_order():
    file = request.files.get("file")
    if not file:
        return jsonify(dict(err=1, msg="文件有误", data=False))

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    FaultPersonNameMapChEn = RedisManager.get("FaultPersonNameMapChEn")

    fileName = file.filename

    name = os.path.splitext(fileName)[0]
    ext = os.path.splitext(fileName)[1]

    filePath = os.path.join(tempDir, "{name}_{time}{ext}".format(name=name, time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"), ext=ext))
    if os.path.exists(filePath):
        os.remove(filePath)

    file.stream.read()
    file.stream.seek(0)

    file.save(filePath)
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="保存导入的表格失败", data=False))

    book = xlrd.open_workbook(filePath)
    sheet = book.sheet_by_index(0)
    nrows = sheet.nrows

    fddPointName = "dom_system_maintainance_fault"
    paramList = []
    for rowx in range(nrows):
        if rowx == 0:
            continue

        values = sheet.row_values(rowx)
        opUserName = FaultPersonNameMapChEn.get(values[14], None)
        opType = -1
        orderId = values[0]
        modifyTime = values[6]
        detail = values[2]
        status = 0
        createTime = values[6]
        title = values[1]
        ownUser = FaultPersonNameMapChEn.get(values[8], None)

        if opUserName == None:
            continue
        if not isValidDate(modifyTime, "%Y-%m-%d %H:%M:%S"):
            continue

        paramList.append(
            (fddPointName, opUserName, opType, orderId, modifyTime, detail, status, createTime, title, ownUser)
        )

    bSuc = BEOPDataAccess.getInstance().importFddWorkOrderByExcel(paramList)
    if os.path.exists(filePath):
        os.remove(filePath)

    return jsonify(dict(err=0, msg="", data=bSuc))


"""
某用户访问（点击）了某个工单一次则计一条记录
"""
@bp_fdd.route("/addVisit", methods=["POST"])
def add_work_order_visit():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    userName = rcv.get("userName", None)
    orderId = rcv.get("orderId", None)
    if not isinstance(userName, str):
        return jsonify(dict(err=1, msg="用户名必须为字符串", data=False))
    if not len(userName):
        return jsonify(dict(err=1, msg="用户名不能为空", data=False))

    userId = BEOPDataAccess.getInstance().get_user_id_by_name(userName)
    if userId == None:
        return jsonify(dict(err=1, msg="该用户不存在于现场用户列表中", data=False))

    if not isinstance(orderId, int):
        return jsonify(dict(err=1, msg="工单ID必须为整数", data=False))

    orders = BEOPDataAccess.getInstance().getAllFaultOrderIds()
    if orders.get("code") > 0:
        return jsonify(dict(err=1, msg="现有工单id列表获取失败", data=False))

    orderIds = orders.get("data")
    if orderId not in orderIds:
        return jsonify(dict(err=1, msg="该工单不存在", data=False))

    bSuc, msg = BEOPDataAccess.getInstance().addFddWorkOrderUserVisitRecord(userId, orderId)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))


"""
获取工单的更新（包括工单状态更新和评论的增加和修改）
"""
@bp_fdd.route("/getWorkOrderUpdate", methods=["POST"])
def get_work_order_update():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    userName = rcv.get("userName", None)
    beginTime = rcv.get("beginTime", None)

    if not isinstance(userName, str):
        return jsonify(dict(err=1, msg="用户名必须为字符串", data=[]))
    if not len(userName):
        return jsonify(dict(err=1, msg="用户名不能为空", data=[]))

    userId = BEOPDataAccess.getInstance().get_user_id_by_name(userName)
    if userId == None:
        return jsonify(dict(err=1, msg="该用户不存在于现场用户列表中", data=[]))

    tBeginTime = datetime.now() - timedelta(days=7)
    if isValidDate(beginTime, "%Y-%m-%d %H:%M:%S"):
        tBeginTime = datetime.strptime(beginTime, "%Y-%m-%d %H:%M:%S")
        if tBeginTime >= datetime.now():
            return jsonify(dict(err=1, msg="查询起始时间必须小于当前时间", data=[]))

    # 查询工单的更新记录
    dWorkOrderUpdate, msg = BEOPDataAccess.getInstance().getFaultUpdate(tBeginTime.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userName)
    if dWorkOrderUpdate == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    # 查询用户访问记录  {orderId: latestVisitTimeStamp}
    dVisitRecord, msg = BEOPDataAccess.getInstance().getWorkOrderUserVisitRecord(userId, tBeginTime.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if dVisitRecord == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    # 查询工单的评论更新       {orderId: latestCommentTimeStamp}
    dWorkOrderComment = {}
    commentDataList, msg = BEOPDataAccess.getInstance().getFaultCommentUpdate(tBeginTime.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userName)
    if commentDataList == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    for comment in commentDataList:
        nOrderId = comment.get("orderId")
        tCommentCreateTime = datetime.strptime(comment.get("createTime"), "%Y-%m-%d %H:%M:%S")
        if nOrderId not in dWorkOrderComment.keys():
            dWorkOrderComment.update({nOrderId: tCommentCreateTime})
        else:
            if tCommentCreateTime > dWorkOrderComment.get(nOrderId):
                dWorkOrderComment.update({nOrderId: tCommentCreateTime})

    # 工单名称与创建时间  {orderId: {}}
    dOrderCreateTimeTitle, msg = BEOPDataAccess.getInstance().getWorkOrderCreateTimeAndTitle()
    if dOrderCreateTimeTitle == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    # 比较工单更新
    dStat = {}
    for nOrderId, dTemp in dWorkOrderUpdate.items():
        bCount = False
        tVisitTime = dVisitRecord.get(nOrderId, None)

        if tVisitTime == None:
            bCount = True
        else:
            if isinstance(tVisitTime, datetime):
                if dTemp.get("tModifyTime") > tVisitTime:  # 若工单更新时间大于用户最近一次访问时间
                    bCount = True

        if bCount:
            dStat.update({nOrderId: dict(orderId=nOrderId,
                                         createTime=dOrderCreateTimeTitle.get(nOrderId, {}).get("createTime", ""),
                                         name=dOrderCreateTimeTitle.get(nOrderId, {}).get("name", ""))})

    # 比较评论更新
    for nOrderId, tCommentTime in dWorkOrderComment.items():
        bCount = False
        tVisitTime = dVisitRecord.get(nOrderId, None)

        if tVisitTime == None:
            bCount = True
        else:
            if isinstance(tCommentTime, datetime):
                if tCommentTime > tVisitTime:  # 若工单被评论时间大于用户最近一次访问时间
                    bCount = True

        if bCount:
            dStat.update({nOrderId: dict(orderId=nOrderId,
                                         createTime=dOrderCreateTimeTitle.get(nOrderId, {}).get("createTime", ""),
                                         name=dOrderCreateTimeTitle.get(nOrderId, {}).get("name", ""))})

    statList = []
    for wo in dStat.values():
        statList.append(wo)

    return jsonify(dict(err=0, msg="", data=statList))


@bp_fdd.route("/initFddFaultConfig")
def init_fdd_fault_config():
    if not BEOPSqliteAccess.getInstance().pointExists("dom_system_maintainance_fault"):
        nMaxId = BEOPSqliteAccess.getInstance().getMaxIdInTable("list_point")
        insertList = [[str(nMaxId+1), 'dom_system_maintainance_fault', 'vpoint', '', '', '0', '', 'fault', '{"critical": 1, "group": "运行组"}', "类型|工单".encode("gbk"),
                       '', '', '', '', '', '', '0', '0', '0', '0', '2', '', '', '', '', '2']]
        dResult = BEOPSqliteAccess.getInstance().insertPointList(insertList)
        if not dResult.get("success", False):
            return jsonify(dict(err=1, msg="添加故障工单点名失败(dom_system_maintainance_fault)", data=False))

        BEOPSqliteAccess.getInstance().updateAllPointInfoIntoRedis()
        BEOPDataAccess.getInstance().operateUnit01ForVpointAddDel("dom_system_maintainance_fault", 1)

    dStdFddAuth = {
          "admin": {
            "group": [
              "运行组",
              "维修组"
            ],
            "name_zh": "能源站主管",
            "role": "admin",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "man1": {
            "group": [
              "维修组"
            ],
            "name_zh": "维修岗1号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "man2": {
            "group": [
              "维修组"
            ],
            "name_zh": "维修岗2号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "man3": {
            "group": [
              "维修组"
            ],
            "name_zh": "维修岗3号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "man4": {
            "group": [
              "维修组"
            ],
            "name_zh": "维修岗4号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "op1": {
            "group": [
              "运行组"
            ],
            "name_zh": "运行岗1号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "op2": {
            "group": [
              "运行组"
            ],
            "name_zh": "运行岗2号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "op3": {
            "group": [
              "运行组"
            ],
            "name_zh": "运行岗3号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          },
          "op4": {
            "group": [
              "运行组"
            ],
            "name_zh": "运行岗4号",
            "role": "executor",
            "visable": {
              "类型": [
                "通讯故障",
                "安全故障",
                "效率报警",
                "跑冒滴漏",
                "硬件故障",
                "工单"
              ]
            }
          }
        }

    dStdFddSpecy = {
        "group": [{
            "children": [{
                "name": "通讯故障"
            },
            {
                "name": "效率报警"
            },
            {
                "name": "跑冒滴漏"
            },
            {
                "name": "安全故障"
            },
            {
                "name": "硬件故障"
            },
            {
                "name": "工单"
            }],
            "name": "类型"
        }]
    }

    fddSpecy = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig("fdd_specy")
    dCurFddSpecy = {}
    try:
        dCurFddSpecy = json.loads(fddSpecy)
    except:
        pass

    if not dCurFddSpecy:
        bSuc = BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', "fdd_specy", dStdFddSpecy)
        if not bSuc:
            return jsonify(dict(err=1, msg="fdd_spec初始化失败", data=False))
        BEOPSqliteAccess.getInstance().UpdateFaultViewInfoToRedis()

    fddAuth = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig("fdd_auth")
    dCurFddAuth = {}
    try:
        dCurFddAuth = json.loads(fddAuth)
    except:
        pass

    if not dCurFddAuth:
        bSuc = BEOPSqliteAccess.getInstance().saveLocalConfig('domdb.4db', "fdd_auth", dStdFddAuth)
        if not bSuc:
            return jsonify(dict(err=1, msg="fdd_spec初始化失败", data=False))
        BEOPSqliteAccess.getInstance().UpdateFaultAuthInfoToRedis()

    return jsonify(dict(err=0, msg="故障工单初始化配置成功", data=True))


@bp_fdd.route("/getWorkOrderMembers")
def get_work_order_members():
    try:
        if RedisManager.is_alive():
            FaultAuthInfo = RedisManager.get("FaultAuthInfo")
        else:
            faultAuth = BEOPSqliteAccess.getInstance().getValueByKeyInLocalConfig("fdd_auth")
            if not isinstance(faultAuth, str):
                return False

            infoDict = json.loads(faultAuth)

            FaultAuthInfo = {}
            for nameEn, dInfo in infoDict.items():
                visable = dInfo.get("visable")
                visableDict = {}
                for viewZh, itemList in visable.items():
                    if not is_english_word(viewZh):
                        viewEn = get_fault_view_en_name(viewZh)
                    else:
                        viewEn = viewZh
                    if not viewEn:
                        continue
                    visableDict.update({viewEn: itemList})
                FaultAuthInfo.update({nameEn: dict(visable=visableDict,
                                                   group=dInfo.get("group"),
                                                   role=dInfo.get("role"),
                                                   name_zh=dInfo.get("name_zh"))})

        if not isinstance(FaultAuthInfo, dict):
            return jsonify(dict(err=1, msg="工单权限配置有误，请检查", data=[]))

        memberList = []
        for nameEn, dMemberInfo in FaultAuthInfo.items():
            memberList.append(dict(nameEn=nameEn,
                                   nameCh=dMemberInfo.get("name_zh", ""),
                                   role=dMemberInfo.get("role", ""),
                                   group=dMemberInfo.get("group", ""),
                                   visable=dMemberInfo.get("visable", {})))

        for i in range(len(memberList)):
            for j in range(len(memberList)-i-1):
                if memberList[j].get("nameEn") > memberList[j+1].get("nameEn"):
                    memberList[j], memberList[j+1] = memberList[j+1], memberList[j]

        return jsonify(dict(err=0, msg="", data=memberList))

    except Exception as e:
        return jsonify(dict(err=1, msg="工单权限配置解析失败:{err}".format(err=e.__str__()), data=[]))