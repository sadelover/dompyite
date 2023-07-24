from flask import request, json, jsonify
from siteinterface.mod_page import bp_page
from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
import re
from siteinterface.mod_page.utils import *
from siteinterface.commonUtils import get_page_type_str, get_page_type_num, is_int_digit, convert_version, get_dom_image_lib_category
import random
import string
from siteinterface.RedisManager import RedisManager
from siteinterface.utils import isValidDate, get_int_from_rgb, get_hex_from_rgb
from datetime import datetime
import os
from siteinterface import app
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface.mod_page.utils import nPageEditMinsTimeOut, strPageEditLockKey, get_current_locked_page_map, search_template_by_point_keyword_from_cloud, execute_backup_domdb
import shutil
import uuid


@bp_page.route('/addPageGroup', methods=['POST'])
def add_page_group():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    name = rcv.get("name", None)
    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="页面组名称必须为字符串", data=False))
    if not len(name):
        return jsonify(dict(err=1, msg="页面组名称不能为空", data=False))
    if len(name) > 30:
        return jsonify(dict(err=1, msg="页面组名称长度不能超过30个字符", data=False))
    if not re.match(r"^[a-zA-Z0-9\u4e00-\u9fa5_-]*$", name):
        return jsonify(dict(err=1, msg="页面组名称中不能包含空格和特殊字符", data=False))

    nMaxId = BEOPSqliteAccess.getInstance().getMaxIdInTable("list_pagegroup")
    nMaxSortNum, msg = BEOPSqliteAccess.getInstance().getMaxSortNumOfPageGroup()

    if nMaxSortNum == None:
        return jsonify(dict(err=1, msg="添加分组失败:{msg}".format(msg=msg), data=False))

    bSuc, msg = BEOPSqliteAccess.getInstance().addPageGroup(nMaxId+1, name, nMaxSortNum+1)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))


@bp_page.route("/deletePageGroup", methods=['POST'])
def delete_page_group():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nGroupId = rcv.get("groupId", None)
    if not isinstance(nGroupId, int):
        return jsonify(dict(err=1, msg="页面分组ID不能为空且必须为整数", data=False))

    # 若存在页面锁则判断一次当前组中是否存在被锁住的页面
    dLockedPageMap = get_current_locked_page_map()
    if dLockedPageMap and isinstance(dLockedPageMap, dict):
        dLockedPage = None

        groupList, dPageGroup, msg = BEOPSqliteAccess.getInstance().getPageInfo()
        if not isinstance(groupList, list):
            return jsonify(dict(err=1, msg=msg, data=False))

        if isinstance(dPageGroup, dict):
            dPageGroupInfo = dPageGroup.get(nGroupId, {})
            pageList = dPageGroupInfo.get("pageList", [])
            if isinstance(pageList, list) and len(pageList):
                for dPage in pageList:
                    if isinstance(dPage, dict):
                        if dPage.get("pageId", None) != None:
                            strPageId = str(dPage.get("pageId"))
                            if dLockedPageMap.get(strPageId, None) != None:
                                dLockedPage = dLockedPageMap.get(strPageId)
                                break

        if dLockedPage != None:
            return jsonify(dict(err=1, msg="删除组失败，原因：当前该组中的页面(pageId:{pageId})被用户{userName}(userId:{userId})编辑占用，请先释放本组内所有页面的锁".format(pageId=dLockedPage.get("pageId"),
                                                                                                                         userName=dLockedPage.get("userName"),
                                                                                                                         userId=dLockedPage.get("userId")), data=False))

    bSuc, msg = BEOPSqliteAccess.getInstance().deletePageGroup(nGroupId)

    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

"""
修改组名称
"""
@bp_page.route('/updatePageGroup', methods=['POST'])
def update_page_group():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    name = rcv.get("name", None)
    nGroupId = rcv.get("groupId", None)

    if not isinstance(nGroupId, int):
        return jsonify(dict(err=1, msg="页面分组ID不能为空且必须为整数", data=False))
    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="页面分组名称必须为字符串", data=False))
    if not len(name):
        return jsonify(dict(err=1, msg="页面分组名称不能为空", data=False))
    if len(name) > 30:
        return jsonify(dict(err=1, msg="页面组名称长度不能超过30个字符", data=False))
    if not re.match(r"^[a-zA-Z0-9\u4e00-\u9fa5_-]*$", name):
        return jsonify(dict(err=1, msg="页面组名称中不能包含空格和特殊字符", data=False))

    bSuc, msg = BEOPSqliteAccess.getInstance().updatePageGroup(nGroupId, name)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_page.route('/getPageGroup', methods=['POST'])
def get_page_group():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nGroupId = rcv.get("groupId", None)
    if nGroupId != None:
        if not isinstance(nGroupId, int):
            return jsonify(dict(err=1, msg="页面分组ID不能为空且必须为整数", data=[]))

    dataList, msg = BEOPSqliteAccess.getInstance().getPageGroup(nGroupId)
    return jsonify(dict(err=0, msg=msg, data=dataList))

@bp_page.route("/addPage", methods=['POST'])
def add_page():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    name = rcv.get("name", None)
    nPageType = rcv.get("type", 0)   # 0-固定页面fullscreen  1-浮动页面 floating
    nWidth = rcv.get("width", 1920)
    nHeight = rcv.get("height", 955)
    nDisplay = rcv.get("display", 1)  # 是否显示在置顶菜单 0-不显示  1-显示
    nMinAuth = rcv.get("minAuth", 0)  # 页面最低权限要求    0-访客  1-操作员  2-管理员  3-调试维修员
    nGroupId = rcv.get("groupId", None)

    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="页面名称必须为字符串", data=False))
    if not len(name):
        return jsonify(dict(err=1, msg="页面名称不能为空", data=False))
    if len(name) > 30:
        return jsonify(dict(err=1, msg="页面名称长度不能超过30个字符", data=False))

    if nPageType not in [0, 1]:
        return jsonify(dict(err=1, msg="页面类型必须为0(固定页面)或1(浮动页面)", data=False))
    if not isinstance(nWidth, int):
        return jsonify(dict(err=1, msg="页面宽度必须为整数", data=False))
    if not isinstance(nHeight, int):
        return jsonify(dict(err=1, msg="页面高度必须为整数", data=False))
    if nWidth > 1920 or nWidth < 0:
        return jsonify(dict(err=1, msg="页面宽度必须在0-1920之间", data=False))
    if nHeight > 955 or nHeight < 0:
        return jsonify(dict(err=1, msg="页面高度必须在0-955之间", data=False))
    if nPageType == 0:
        if not ((nWidth == 1920 and nHeight == 955) or (nWidth == 1366 and nHeight == 680)):
            return jsonify(dict(err=1, msg="固定页面类型的高宽比仅支持1920*955 和 1366*680", data=False))

    if nDisplay not in [0, 1]:
        return jsonify(dict(err=1, msg="是否显示在置顶菜单必须为0或1", data=False))
    if nMinAuth not in [0, 1, 2, 3]:
        return jsonify(dict(err=1, msg="页面最低权限要求必须为0或1或2或3", data=False))

    if not isinstance(nGroupId, int):
        return jsonify(dict(err=1, msg="组ID必须为整数", data=False))

    nPageGroupList, strMsg = BEOPSqliteAccess.getInstance().getPageGroup(nGroupId)
    if not len(nPageGroupList):
        return jsonify(dict(err=1, msg="该页面组(ID:{id})不存在".format(id=nGroupId), data=False))

    nMaxId = BEOPSqliteAccess.getInstance().getMaxIdInTable("list_page")
    if not isinstance(nMaxId, int):
        return jsonify(dict(err=1, msg="获取最大页面ID失败", data=False))

    nNewPageId = nMaxId + 1
    pageList, msgGetPageList = BEOPSqliteAccess.getInstance().getAllPageOrderByShowOrder()
    if pageList == None:
        return jsonify(dict(err=1, msg=msgGetPageList, data=False))

    needUpdateShowOrderList = []
    bFoundGroup = False
    nPossibleShowOrderPrior = None # 可能的showOrder的前一个showOrder
    nShowOrderToSet = None
    for page in pageList:
        if not bFoundGroup:
            if page.get("groupId") == nGroupId:
                bFoundGroup = True
                nPossibleShowOrderPrior = page.get("order")
                continue

        if not bFoundGroup:
            continue

        # 已找到分组
        # 若发现继续是该分组则记下showOrder 检查下一个
        if nShowOrderToSet == None:
            if page.get("groupId") == nGroupId:
                nPossibleShowOrderPrior = page.get("order")
                continue

        # 发现已是下一个分组，则上一个showOrder就是需要放置的showOrder
        if nShowOrderToSet == None:
            nShowOrderToSet = nPossibleShowOrderPrior + 1

        # 已确定需要放置的showOrder则从当前页面开始所有页面showOrder加1
        if nShowOrderToSet != None:
            needUpdateShowOrderList.append(
                (page.get("order") + 1, page.get("id"))
            )

    if nShowOrderToSet == None:
        if isinstance(nPossibleShowOrderPrior, int):
            nShowOrderToSet = nPossibleShowOrderPrior + 1
        else:
            if len(pageList):
                nShowOrderToSet = pageList[-1].get("order") + 1
            else:
                nShowOrderToSet = 1

    bSuc, msg = BEOPSqliteAccess.getInstance().addPage(name, nNewPageId, nPageType, nWidth, nHeight, nDisplay, nMinAuth, nShowOrderToSet, nGroupId, needUpdateShowOrderList)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))


@bp_page.route("/deletePage", methods=['POST'])
def delete_page():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nPageId = rcv.get("id", None)
    token = rcv.get("token", None)
    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面ID必须为整数", data=False))

    strPageId = str(nPageId)

    if token != None:
        if not isinstance(token, str):
            return jsonify(dict(err=1, msg="token必须为字符串", data=False))
        if not len(token):
            return jsonify(dict(err=1, msg="token不能为空", data=False))

    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict):
        dEditLock = {}

    dPageEditLock = dEditLock.get(strPageId, {})
    if not isinstance(dPageEditLock, dict):
        dPageEditLock = {}

    # 页面被锁住且当前用户就是权限占用用户则可以直接删除
    if dPageEditLock:
        bLocked = False
        if dPageEditLock.get("lock", 0) == 1:
            tActiveTime = None
            try:
                tActiveTime = datetime.strptime(dPageEditLock.get("activeTime", ""), "%Y-%m-%d %H:%M:%S")
            except:
                pass

            if isinstance(tActiveTime, datetime):
                if (datetime.now() - tActiveTime).total_seconds() < nPageEditMinsTimeOut * 60:
                    if dPageEditLock.get("token", None) != token:
                        bLocked = True

        if bLocked:
            return jsonify(dict(err=1,
                                msg="该页面(pageId:{pageId})目前被用户{userName}(userId:{userId})编辑占用，无法删除".format(
                                    pageId=nPageId,
                                    userName=dPageEditLock.get("userName", ""),
                                    userId=dPageEditLock.get("userId", ""))))

        else:
            bSuc, msg = BEOPSqliteAccess.getInstance().deletePage(nPageId)
            if bSuc:
                if strPageId in dEditLock.keys():
                    del dEditLock[strPageId]
                    RedisManager.set(strPageEditLockKey, dEditLock)
                BEOPSqliteAccess.getInstance().deleteElementsFromPage(nPageId)

            return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

    else:
        bSuc, msg = BEOPSqliteAccess.getInstance().deletePage(nPageId)
        if bSuc:
            if strPageId in dEditLock.keys():
                del dEditLock[strPageId]
                RedisManager.set(strPageEditLockKey, dEditLock)
            BEOPSqliteAccess.getInstance().deleteElementsFromPage(nPageId)
        return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))


@bp_page.route('/updatePageInfo', methods=['POST'])
def update_page_info():
    errMsgList = []
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nPageId = rcv.get("id", None)
    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面ID必须为整数", data=False))

    name = rcv.get("name", None)
    nPageType = rcv.get("type", None)  # 0-固定页面fullscreen  1-浮动页面 floating
    nWidth = rcv.get("width", None)
    nHeight = rcv.get("height", None)
    nDisplay = rcv.get("display", None)  # 是否显示在置顶菜单 0-不显示  1-显示
    nMinAuth = rcv.get("minAuth", None)  # 页面最低权限要求    0-访客  1-操作员  2-管理员  3-调试维修员
    bgcolor1 = rcv.get("bgcolor1", None)
    bgcolor2 = rcv.get("bgcolor2", None)
    nGroupId = rcv.get("groupId", None)

    if name != None:
        if not isinstance(name, str):
            return jsonify(dict(err=1, msg="页面名称必须为字符串", data=False))
        if not len(name):
            return jsonify(dict(err=1, msg="页面名称不能为空", data=False))
        if len(name) > 30:
            return jsonify(dict(err=1, msg="页面名称长度不能超过30个字符", data=False))

    if nPageType != None:
        if nPageType not in [0, 1]:
            return jsonify(dict(err=1, msg="页面类型必须为0(固定页面)或1(浮动页面)", data=False))

        if nWidth == None or nHeight == None:
            return jsonify(dict(err=1, msg="修改页面类型后需同时传入页面高宽", data=False))

    if nWidth != None or nHeight != None:
        if nPageType == None:
            return jsonify(dict(err=1, msg="页面高宽修改时需同时传入页面类型", data=False))

    if isinstance(nWidth, int):
        if not isinstance(nHeight, int):
            return jsonify(dict(err=1, msg="页面的高宽需同步修改，高度也需要传入", data=False))

    if isinstance(nHeight, int):
        if not isinstance(nWidth, int):
            return jsonify(dict(err=1, msg="页面的高宽需同步修改，宽度也需要传入", data=False))

    if isinstance(nWidth, int) and isinstance(nHeight, int):
        if not isinstance(nWidth, int):
            return jsonify(dict(err=1, msg="页面宽度必须为整数", data=False))
        if not isinstance(nHeight, int):
            return jsonify(dict(err=1, msg="页面高度必须为整数", data=False))
        if nWidth > 1920 or nWidth < 0:
            return jsonify(dict(err=1, msg="页面宽度必须在0-1920之间", data=False))
        if nHeight > 955 or nHeight < 0:
            return jsonify(dict(err=1, msg="页面高度必须在0-955之间", data=False))

        if nPageType != None:
            nTarPageType = nPageType
        else:
            dPageTypeInfo = BEOPSqliteAccess.getInstance().getPageType(nPageId)
            strPageType = dPageTypeInfo.get("pageType", None)
            nTarPageType = get_page_type_num(strPageType)

        if nTarPageType == 0:
            if not ((nWidth == 1920 and nHeight == 955) or (nWidth == 1366 and nHeight == 680)):
                return jsonify(dict(err=1, msg="固定页面类型的高宽比仅支持1920*955 和 1366*680", data=False))

    if nDisplay != None:
        if nDisplay not in [0, 1]:
            return jsonify(dict(err=1, msg="是否显示在置顶菜单必须为0或1", data=False))

    if nMinAuth != None:
        if nMinAuth not in [0, 1, 2, 3]:
            return jsonify(dict(err=1, msg="页面最低权限要求必须为0或1或2或3", data=False))

    if bgcolor1 != None:
        if not isinstance(bgcolor1, dict):
            return jsonify(dict(err=1, msg="背景颜色1必须为字典", data=False))

    if bgcolor2 != None:
        if not isinstance(bgcolor2, dict):
            return jsonify(dict(err=1, msg="背景颜色2必须为字典", data=False))

    # 移动页面到另一个分组时目标分组id判断一次
    if nGroupId != None:
        if not isinstance(nGroupId, int):
            return jsonify(dict(err=1, msg="分组id必须为整数", data=False))
        groupList, msg = BEOPSqliteAccess.getInstance().getPageGroup()
        if groupList == None:
            return jsonify(dict(err=1, msg="分组列表获取失败: {msg}".format(msg=msg), data=False))

        nGroupIdList = []
        for group in groupList:
            if not isinstance(group.get("id"), int):
                continue
            nGroupIdList.append(group.get("id"))
        if nGroupId not in nGroupIdList:
            return jsonify(dict(err=1, msg="移动至的目标分组id不存在", data=False))

    if name == None and nPageType == None and nWidth == None and nHeight == None and nDisplay == None and nMinAuth == None and bgcolor1 == None and bgcolor2 == None and nGroupId == None:
        return jsonify(dict(err=1, msg="未发现修改项", data=False))

    strPageType = None
    if nPageType != None:
        strPageType = get_page_type_str(nPageType)

    nBgColor1 = None
    nBgColor2 = None
    if isinstance(bgcolor1, dict):
        nBgColor1 = get_int_from_rgb(bgcolor1.get("r", 0), bgcolor1.get("g", 0), bgcolor1.get("b", 0))

    if isinstance(bgcolor2, dict):
        nBgColor2 = get_int_from_rgb(bgcolor2.get("r", 0), bgcolor2.get("g", 0), bgcolor2.get("b", 0))

    bSuc1, msgUpdagePageInfo = BEOPSqliteAccess.getInstance().updatePageInfo(nPageId, name, strPageType, nWidth, nHeight, nDisplay, nMinAuth, nBgColor1, nBgColor2)

    # 修改分组
    bSuc2 = False
    if nGroupId != None:
        pageList, msgGetPageList = BEOPSqliteAccess.getInstance().getAllPageOrderByShowOrder()
        if pageList != None:
            nPageIdList = []
            nCurGroupId = None
            nCurOrder = None
            for page in pageList:
                nPageIdList.append(page.get("id"))
                if page.get("id") == nPageId:
                    nCurGroupId = page.get("groupId")
                    nCurOrder = page.get("order")

            if nPageId in nPageIdList:
                if nCurGroupId != nGroupId:
                    if isinstance(nCurOrder, int):
                        nOldIndex = nCurOrder - 1
                        transit = pageList.pop(nOldIndex)

                        nNewIndex = None
                        for idx, page in enumerate(pageList):
                            if page.get("groupId") == nGroupId:
                                nNewIndex = idx
                                break

                        if nNewIndex == None:  # 若未找到groupId为nTarGroupId的分组，则说明目标分组中无任何页面
                            pageList.append(transit)
                        else:
                            pageList.insert(nNewIndex, transit)  # 将元素插入指定索引

                        orderTplList = []
                        for idx, page in enumerate(pageList):
                            orderTplList.append(
                                (idx + 1, page.get("id"))
                            )

                        bSuc2, msgMovePage = BEOPSqliteAccess.getInstance().movePageToOtherGroup(nPageId, nGroupId, orderTplList)
                        if not bSuc2:
                            errMsgList.append(msgMovePage)
                    else:
                        errMsgList.append("该页面的排序号有误")
                else:
                    errMsgList.append("移动至的分组id就是该页面当前所在的分组({grpId})".format(grpId=nGroupId))

            else:
                errMsgList.append("页面id不存在")

        else:
            errMsgList.append("页面移动失败，原因：页面列表获取失败({msg})".format(msg=msgGetPageList))

    # 更新页面缓存  (2023-07-07 debugtool编辑页面后暂时不将页面内容存入debugtool专用缓存)
    if bSuc1:
        # rvContent1 = BEOPSqliteAccess.getInstance().getPlantDebugTool(nPageId)
        # if rvContent1 != None:
        #     RedisManager.set_4db_page_content_DebugTool(nPageId, rvContent1)

        rvContent2 = BEOPSqliteAccess.getInstance().getPlant("", nPageId)
        if rvContent2 != None:
            RedisManager.set_4db_page_content(nPageId, rvContent2)

    msgFinal = ""
    if not bSuc1:
        msgFinal += msgUpdagePageInfo + ";"
    if nGroupId != None:
        if len(errMsgList):
            msgFinal += ";".join(errMsgList)

    if nGroupId != None:
        bSucFinal = bSuc1 and bSuc2
    else:
        bSucFinal = bSuc1

    return jsonify(dict(err=1 if not bSucFinal else 0, msg=msgFinal, data=bSucFinal))


@bp_page.route('/getPageInfo', methods=['POST'])
def get_page():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nPageId = rcv.get("pageId", None)
    if nPageId != None:
        if not isinstance(nPageId, int):
            return jsonify(dict(err=1, msg="页面ID必须为整数", data=[]))

    groupList, dPageGroup, msg = BEOPSqliteAccess.getInstance().getPageInfo(nPageId)
    if groupList == None:
        return jsonify(dict(err=1, msg=msg, data=[]))
    return jsonify(dict(err=0, msg=msg, data=groupList))


@bp_page.route('/updatePageContent', methods=['POST'])
def update_page_content():
    # typeTag: 元素识别符号  text, button, image
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    # 组态编辑权限验证
    nPageId = rcv.get("pageId", None)
    token = rcv.get("token", None)
    if not isinstance(token, str):
        return jsonify(dict(err=1, msg="token必须为字符串", data=False))
    if not len(token):
        return jsonify(dict(err=1, msg="token不能为空", data=False))
    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="pageId必须为整数", data=False))

    strPageId = str(nPageId)

    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict) or dEditLock == None:
        dEditLock = {}

    dPageEditLock = dEditLock.get(strPageId, {})
    if not isinstance(dPageEditLock, dict):
        dPageEditLock = {}

    if not dPageEditLock.get("token", ""):
        return jsonify(dict(err=1, msg="该页面(pageId:{pageId})不存在组态编辑权限锁，请先尝试获取".format(pageId=nPageId), data=False))

    if dPageEditLock.get("token", "") != token:
        return jsonify(dict(err=1, msg="该页面(pageId:{pageId})的组态编辑权限正在被用户{userName}(id:{userId})占用，您暂时无法编辑该页面的组态".format(
            userName=dPageEditLock.get("userName", ""),
            pageId=nPageId,
            userId=dPageEditLock.get("userId", "")), data=""))

    addList = rcv.get("addList", [])
    removeList = rcv.get("removeList", [])
    updateList = rcv.get("updateList", [])

    if not len(addList) and not len(removeList) and not len(updateList):
        return jsonify(dict(err=1, msg="增加、删除和修改列表均为空", data=False))

    nPageIdList, msg = BEOPSqliteAccess.getInstance().getPageIdList()
    if nPageIdList == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    if nPageId not in nPageIdList:
        return jsonify(dict(err=1, msg="页面id{pageId}不存在".format(pageId=nPageId), data=False))

    nTextIdListOfPage, msg = BEOPSqliteAccess.getInstance().getTextIdListOfOnePage(nPageId)
    if nTextIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nCustIdListOfPage, msg = BEOPSqliteAccess.getInstance().getCustomControlsIdListOfOnePage(nPageId)
    if nCustIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nButtonIdListOfPage, msg = BEOPSqliteAccess.getInstance().getButtonIdListOfOnePage(nPageId)
    if nButtonIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nCheckboxIdListOfPage, msg = BEOPSqliteAccess.getInstance().getCheckboxIdListOfOnePage(nPageId)
    if nCheckboxIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nImageIdListOfPage, msg = BEOPSqliteAccess.getInstance().getImageIdListOfOnePage(nPageId)
    if nImageIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    dAllImages, imgList, msg = BEOPSqliteAccess.getInstance().getElementFromDomLibImage()
    if dAllImages == None:
        return jsonify(dict(err=1, msg="从lib_image获取现有图片信息失败", data=False))

    dAllImagesDomdb, imgList, msg = BEOPSqliteAccess.getInstance().getElementFromLibImage()
    if dAllImages == None:
        return jsonify(dict(err=1, msg="从domdb.4db的lib_image表获取现有图片信息失败", data=False))

    dAllAnimations, msg = BEOPSqliteAccess.getInstance().getAnimationMapFromDomImgLib()
    if dAllAnimations == None:
        return jsonify(dict(err=1, msg="从dom图库获取所有动画失败：%s" % msg, data=False))

    # 最新标准按键风格类型
    dBtnImgStyleType, msg = BEOPSqliteAccess.getInstance().getStandardButtonImageInfo()
    if not isinstance(dBtnImgStyleType, dict):
        return jsonify(dict(err=1, msg=msg, data=False))

    if not dBtnImgStyleType:
        return jsonify(dict(err=1, msg="未获取到后台静态图片文件信息，请先升级后台", data=False))

    nLineIdListOfPage, msg = BEOPSqliteAccess.getInstance().getLineIdListOfOnePage(nPageId)
    if nLineIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nSysEquipIdListOfPage, msg = BEOPSqliteAccess.getInstance().getSysEquipIdListOfOnePage(nPageId)
    if nSysEquipIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nRectangleIdListOfPage, msg = BEOPSqliteAccess.getInstance().getRectangleIdListOfOnePage(nPageId)
    if nSysEquipIdListOfPage == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    imagesDir = os.path.join(app.static_folder, "images")
    if not os.path.exists(imagesDir):
        os.mkdir(imagesDir)
    plantDir = os.path.join(imagesDir, "plant")
    if not os.path.exists(plantDir):
        os.mkdir(plantDir)
    projectDir = os.path.join(plantDir, "project")
    if not os.path.exists(projectDir):
        os.mkdir(projectDir)

    # text容器
    addTextList = []
    removeTextList = []
    updateTextList = []
    addTextParamList = []
    removeTextParamList = []
    addTextIdList = []         # 用于查重text id

    # 自定义组件容器
    addCustList = []
    removeCustList = []
    updateCustList = []
    addCustParamList = []
    addCustIdList = []
    removeCustParamList = []

    # 按键容器
    addButtonList = []
    removeButtonList = []
    updateButtonList = []
    addButtonParamList = []
    addButtonIdList = []
    removeButtonParamList = []

    # checkbox容器
    addCheckboxList = []
    removeCheckboxList = []
    updateCheckboxList = []
    addCheckboxParamList = []
    addCheckboxIdList = []
    removeCheckboxParamList = []

    # image
    addImageList = []
    removeImageList = []
    updateImageList = []
    addImageParamList = []
    addImageIdList = []
    removeImageParamList = []

    addImageEventParamList = []
    updateImageEventContentParamList = []
    updateImageBindContentParamList = []

    # pipeLine容器
    addLineList = []
    removeLineList = []
    updateLineList = []
    addLineParamList = []
    addLineIdList = []
    removeLineParamList = []

    # 标准设备容器
    addSysEquipList = []
    removeSysEquipList = []
    updateSysEquipList = []
    addSysEquipParamList = []
    addSysEquipIdList = []
    removeSysEquipParamList = []

    # 矩形框容器
    addRectangleList = []
    removeRectangleList = []
    updateRectangleList = []
    addRectangleParamList = []
    addRectangleIdList = []
    removeRectangleParamList = []

    # 新增text
    for item in addList:
        if not isinstance(item, dict):
            continue

        if item.get("typeTag") == "text":
            font = item.get("font", "微软雅黑")
            size = item.get("fontSize", 16)
            color = item.get("color", dict(r=0, g=0, b=0))    # 字体颜色（十进制）
            border_color = item.get("border_color", dict(r=255, g=255, b=255))
            initialvalue = item.get("text", "Static Text")
            xpos = item.get("x", 0)
            ypos = item.get("y", 0)
            height = item.get("height", 25)
            width = item.get("width", 100)
            showMode = item.get("showMode", 1)   #  0-枚举模式  1- 值模式 2-时间模式   3-字符串模式  4-按间隔加减修改值模式  5-值模式带单位显示
            layer = item.get("layer", 4)
            align = item.get("align", 0)
            dataComId = item.get("idCom", "")
            bindstring = item.get("bindString", "0:关闭|1:开启")
            dataComTime = item.get("dataComTime", "")
            dataComTimeArrayPoint = item.get("dataComTimeArrayPoint", "")
            unitproperty01 = item.get("backgroudFrameStyle", "0")  # 背景框样式
            unitproperty02 = item.get("sensorType", 0)  # 类型   0-无需配置；1-温度；2-湿度；3-SP
            unitproperty05 = item.get("bindScript", "")  # 自定义语法
            hideScript = item.get("hideScript", "")   # 隐藏判断脚本
            decimalplace = item.get("decimalplace", 0)
            nTextId = item.get("id", None)
            unit = item.get("unit", "")

            if not isinstance(font, str):
                return jsonify(dict(err=1, msg="新增text的字体类型必须为字符串", data=False))
            if not len(font):
                return jsonify(dict(err=1, msg="新增text的字体类型不能是空字符串", data=False))

            if not isinstance(size, int):
                return jsonify(dict(err=1, msg="新增text的字体大小必须为整数", data=False))
            if size < 5 or size > 100:
                return jsonify(dict(err=1, msg="新增text的字体大小必须在5-100之间", data=False))

            if not isinstance(color, dict):
                return jsonify(dict(err=1, msg="新增text的颜色必须为字典", data=False))
            if not isinstance(color.get("r", None), int):
                return jsonify(dict(err=1, msg="新增text的颜色r必须为整数", data=False))
            if not isinstance(color.get("g", None), int):
                return jsonify(dict(err=1, msg="新增text的颜色g必须为整数", data=False))
            if not isinstance(color.get("b", None), int):
                return jsonify(dict(err=1, msg="新增text的颜色b必须为整数", data=False))
            if color.get("r") < 0 or color.get("r") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))
            if color.get("g") < 0 or color.get("g") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))
            if color.get("b") < 0 or color.get("b") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))

            if not isinstance(border_color, dict):
                return jsonify(dict(err=1, msg="新增text的边框颜色必须为字典", data=False))
            if not isinstance(border_color.get("r", None), int):
                return jsonify(dict(err=1, msg="新增text的边框颜色r必须为整数", data=False))
            if not isinstance(border_color.get("g", None), int):
                return jsonify(dict(err=1, msg="新增text的边框颜色g必须为整数", data=False))
            if not isinstance(border_color.get("b", None), int):
                return jsonify(dict(err=1, msg="新增text的边框颜色b必须为整数", data=False))
            if border_color.get("r") < 0 or border_color.get("r") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))
            if border_color.get("g") < 0 or border_color.get("g") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))
            if border_color.get("b") < 0 or border_color.get("b") > 255:
                return jsonify(dict(err=1, msg="rgb颜色范围为0-255", data=False))

            if not isinstance(initialvalue, str):
                return jsonify(dict(err=1, msg="新增text的初始值必须为字符串", data=False))
            if not len(initialvalue):
                return jsonify(dict(err=1, msg="新增text的初始值不能为空字符串", data=False))

            if not isinstance(xpos, int):
                return jsonify(dict(err=1, msg="新增text的横坐标初始值必须为整数", data=False))
            if not isinstance(ypos, int):
                return jsonify(dict(err=1, msg="新增text的纵坐标初始值必须为整数", data=False))

            if not isinstance(height, int):
                return jsonify(dict(err=1, msg="新增text的高度初始值必须为整数", data=False))
            if height < 0 or height > 955:
                return jsonify(dict(err=1, msg="新增text的高度超限", data=False))
            if not isinstance(width, int):
                return jsonify(dict(err=1, msg="新增text的宽度初始值必须为整数", data=False))
            if width < 0 or width > 1920:
                return jsonify(dict(err=1, msg="新增text的宽度超限", data=False))

            if not isinstance(showMode, int):
                return jsonify(dict(err=1, msg="新增text的显示模式必须为整数", data=False))
            if showMode not in [0, 1, 2, 3, 4, 5]:
                return jsonify(dict(err=1, msg="新增text的显示模式必须为0-5之间的整数", data=False))

            if not isinstance(layer, int):
                return jsonify(dict(err=1, msg="新增text的图层必须为整数", data=False))
            if layer < 0 or layer > 9:
                return jsonify(dict(err=1, msg="新增text的图层必须在0-9之间", data=False))

            if not isinstance(align, int):
                return jsonify(dict(err=1, msg="新增text的对齐必须为整数", data=False))
            if align < 0 or align > 8:
                return jsonify(dict(err=1, msg="新增text的对齐必须为0-8之间的整数", data=False))

            if not isinstance(dataComId, str):
                return jsonify(dict(err=1, msg="新增text的非时间变量点名必须为字符串", data=False))

            if not isinstance(bindstring, str):
                return jsonify(dict(err=1, msg="新增text的非时间变量点名必须为字符串", data=False))
            if showMode == 0 and not len(bindstring):
                return jsonify(dict(err=1, msg="新增text在枚举模式下必须要绑定枚举量对应的字符串", data=False))

            if not isinstance(dataComTime, str):
                return jsonify(dict(err=1, msg="新增text的时间变量点名必须为字符串", data=False))
            if not isinstance(dataComTimeArrayPoint, str):
                return jsonify(dict(err=1, msg="新增text的时间序列点名必须为字符串", data=False))

            if not is_int_digit(unitproperty01):
                return jsonify(dict(err=1, msg="新增text的背景框样式必须为整数或整数字符串", data=False))
            nUnitproperty01 = int(unitproperty01)
            if nUnitproperty01 < 0 or nUnitproperty01 > 10:
                return jsonify(dict(err=1, msg="新增text的背景框样式必须为0-10之间的整数或整数字符串", data=False))

            if not isinstance(unitproperty02, int):
                return jsonify(dict(err=1, msg="新增text的传感器类型必须为整数", data=False))
            if unitproperty02 < 0 or unitproperty02 > 3:
                return jsonify(dict(err=1, msg="新增text的传感器类型必须为0-3之间的整数", data=False))

            if not isinstance(unitproperty05, str):
                return jsonify(dict(err=1, msg="新增text的自定义语法必须为字符串", data=False))

            if not isinstance(hideScript, str):
                return jsonify(dict(err=1, msg="新增text的隐藏脚本必须为字符串", data=False))

            if not isinstance(decimalplace, int):
                return jsonify(dict(err=1, msg="新增text的小数位必须为整数", data=False))

            if decimalplace < 0 or decimalplace > 4:
                return jsonify(dict(err=1, msg="新增text的小数位必须为0-4的整数", data=False))

            if not isinstance(nTextId, int):
                return jsonify(dict(err=1, msg="新增text的id必须为整数", data=False))
            if nTextId < 0:
                return jsonify(dict(err=1, msg="新增text的id不能小于0", data=False))

            if not isinstance(unit, str):
                return jsonify(dict(err=1, msg="新增text单位必须为字符串", data=False))

            istransparent = 0
            transparence = 0
            borderType = 1

            nColor = get_int_from_rgb(color.get("r"), color.get("g"), color.get("b"))
            nBorderColor = get_int_from_rgb(border_color.get("r"), border_color.get("g"), border_color.get("b"))

            addTextParamList.append(
                (nPageId, nTextId, font.encode("gbk"), size, nColor, nBorderColor, initialvalue.encode("gbk"),
                 decimalplace, istransparent, xpos, ypos, height, width, dataComId.encode("gbk"), showMode, transparence, borderType,
                 layer, align, bindstring.encode("gbk"), dataComTime.encode("gbk"), dataComTimeArrayPoint.encode("gbk"), nUnitproperty01, unitproperty02, unitproperty05.encode("gbk"),
                 hideScript.encode("gbk"), unit.encode("gbk"))
            )

            if nTextId in nTextIdListOfPage:
                return jsonify(dict(err=1, msg="新增text中发现与页面(pageId: {pageId})中已有text重复的id(id:{id})".format(id=nTextId, pageId=nPageId), data=False))

            if nTextId in addTextIdList:
                return jsonify(dict(err=1, msg="新增text中发现重复的id(id:{id})".format(id=nTextId), data=False))

            addTextIdList.append(nTextId)

        # 新增自定义组件
        elif item.get("typeTag") == "customControls":
            nCustId = item.get("id", None)
            xpos = item.get("x", 0)
            ypos = item.get("y", 0)
            height = item.get("height", 418)
            width = item.get("width", 756)
            layer = item.get("layer", 4)
            strConfig = item.get("config", "{}")

            if not isinstance(nCustId, int):
                return jsonify(dict(err=1, msg="新增自定义组件的id必须为整数", data=False))
            if nCustId < 0:
                return jsonify(dict(err=1, msg="新增自定义组件的id不能小于0", data=False))

            if not isinstance(xpos, int):
                return jsonify(dict(err=1, msg="新增自定义组件的横坐标初始值必须为整数", data=False))
            if not isinstance(ypos, int):
                return jsonify(dict(err=1, msg="新增自定义组件的纵坐标初始值必须为整数", data=False))
            if not isinstance(height, int):
                return jsonify(dict(err=1, msg="新增自定义组件的高度初始值必须为整数", data=False))
            if height < 0 or height > 955:
                return jsonify(dict(err=1, msg="新增自定义组件的高度超限", data=False))
            if not isinstance(width, int):
                return jsonify(dict(err=1, msg="新增自定义组件的宽度初始值必须为整数", data=False))
            if width < 0 or width > 1920:
                return jsonify(dict(err=1, msg="新增自定义组件的宽度超限", data=False))
            if not isinstance(layer, int):
                return jsonify(dict(err=1, msg="新增自定义组件的图层必须为整数", data=False))
            if layer < 0 or layer > 9:
                return jsonify(dict(err=1, msg="新增自定义组件的图层必须在0-9之间", data=False))

            if not isinstance(strConfig, str):
                return jsonify(dict(err=1, msg="新增自定义组件的配置内容必须为字符串", data=False))
            if not len(strConfig):
                return jsonify(dict(err=1, msg="新增自定义组件的配置内容不能为空", data=False))

            try:
                dCustJson = json.loads(strConfig)
            except:
                return jsonify(dict(err=1, msg="新增自定义组件的配置内容必须为json格式", data=False))

            addCustParamList.append(
                (xpos, ypos, width, height, layer, nCustId, nPageId, "generalComponent", strConfig.encode("gbk"))
            )

            if nCustId in nCustIdListOfPage:
                return jsonify(dict(err=1, msg="新增自定义组件中发现与页面(pageId: {pageId})中已有自定义组件重复的id(id:{id})".format(id=nCustId, pageId=nPageId), data=False))

            if nCustId in addCustIdList:
                return jsonify(dict(err=1, msg="新增自定义组件中发现重复的id(id:{id})".format(id=nCustId), data=False))

            addCustIdList.append(nCustId)
        # 新增button
        elif item.get("typeTag") == "button":
            nBtnId = item.get("id", None)
            preCheckScript = item.get("PreCheckScript", "")  # 按键点击后的预检脚本
            preCheckScriptDescription = item.get("PreCheckScriptDescription", "")  #按键点击后的预检脚本提示
            strStyle = item.get("style", None) # 风格类型
            link = item.get("link", -1)
            nX = item.get("x", 0)
            nY = item.get("y", 0)
            width = item.get("width", 82)
            height = item.get("height", 43)
            layer = item.get("layer", 4)
            setValue = item.get("setValue", None)
            setPoint = item.get("idCom", None)
            textContent = item.get("text", None)
            fontColor = item.get("fontColor", dict(r=0, g=0, b=0))
            fontSize = item.get("fontSize", 16)
            description = item.get("description", "")
            relation = item.get("relation", [])    # 按键有效性判断逻辑
            relationType = item.get("relatType", "0")
            downloadEnableCondition = item.get("downloadEnableCondition", "")
            downloadURL = item.get("downloadURL", "")
            hideScript = item.get("hideScript", "")

            if not isinstance(nBtnId, int):
                return jsonify(dict(err=1, msg="新增按键的id必须为整数", data=False))
            if nBtnId < 0:
                return jsonify(dict(err=1, msg="新增按键的id不能小于0", data=False))

            if not isinstance(preCheckScript, str):
                return jsonify(dict(err=1, msg="新增按键点击后的预检脚本必须为字符串", data=False))
            if not isinstance(preCheckScriptDescription, str):
                return jsonify(dict(err=1, msg="新增按键点击后的预检脚本提示必须为字符串", data=False))

            if not isinstance(strStyle, str):
                return jsonify(dict(err=1, msg="新增按键风格类型必须为字符串", data=False))
            if not len(strStyle):
                return jsonify(dict(err=1, msg="新增按键风格类型不能为空", data=False))
            if strStyle not in dBtnImgStyleType.keys():
                return jsonify(dict(err=1, msg="新增按键风格{strStyle}不存在".format(strStyle=strStyle), data=False))

            if not isinstance(link, int):
                return jsonify(dict(err=1, msg="新增按键点击时的跳转页面id必须为整数", data=False))
            if link not in nPageIdList and link != -1:
                return jsonify(dict(err=1, msg="新增按键点击时的跳转页面id({id})不存在".format(id=link), data=False))
            if link == nPageId:
                return jsonify(dict(err=1, msg="新增按键点击时的跳转页面id({id})不能等于本页面id".format(id=link), data=False))

            if not isinstance(nX, int):
                return jsonify(dict(err=1, msg="新增按键的横坐标初始值必须为整数", data=False))
            if not isinstance(nY, int):
                return jsonify(dict(err=1, msg="新增按键的纵坐标初始值必须为整数", data=False))

            if not isinstance(height, int):
                return jsonify(dict(err=1, msg="新增按键的高度初始值必须为整数", data=False))
            if height < 0 or height > 955:
                return jsonify(dict(err=1, msg="新增按键的高度超限", data=False))
            if not isinstance(width, int):
                return jsonify(dict(err=1, msg="新增按键的宽度初始值必须为整数", data=False))
            if width < 0 or width > 1920:
                return jsonify(dict(err=1, msg="新增按键的宽度超限", data=False))

            if not isinstance(layer, int):
                return jsonify(dict(err=1, msg="新增按键的图层必须为整数", data=False))
            if layer < 0 or layer > 9:
                return jsonify(dict(err=1, msg="新增按键的图层必须在0-9之间", data=False))

            if not isinstance(setValue, str) and not isinstance(setValue, float) and not isinstance(setValue, int):
                return jsonify(dict(err=1, msg="新增按键点击后的写值内容必须为字符串或浮点或整数", data=False))

            if not isinstance(setPoint, str):
                return jsonify(dict(err=1, msg="新增按键点击后的写值点必须为字符串", data=False))

            if not isinstance(textContent, str):
                return jsonify(dict(err=1, msg="新增按键的文本内容必须为字符串", data=False))

            if not isinstance(fontColor, dict):
                return jsonify(dict(err=1, msg="新增按键的颜色必须为字典", data=False))
            if not isinstance(fontColor.get("r", None), int):
                return jsonify(dict(err=1, msg="新增按键的颜色r必须为整数", data=False))
            if not isinstance(fontColor.get("g", None), int):
                return jsonify(dict(err=1, msg="新增按键的颜色g必须为整数", data=False))
            if not isinstance(fontColor.get("b", None), int):
                return jsonify(dict(err=1, msg="新增按键的颜色b必须为整数", data=False))
            if not isinstance(fontSize, int):
                return jsonify(dict(err=1, msg="新增按键的字体大小必须为整数", data=False))
            if fontSize < 5 or fontSize > 100:
                return jsonify(dict(err=1, msg="新增按键的字体大小必须在5-100之间", data=False))

            if not isinstance(description, str):
                return jsonify(dict(err=1, msg="新增按键点击之后的操作记录描述文本必须为字符串", data=False))

            relationList = []
            if not isinstance(relation, list):
                return jsonify(dict(err=1, msg="新增按键有效性判断逻辑必须为数组", data=False))
            if len(relation):
                for oneRelation in relation:
                    pointName = oneRelation.get("point", "")
                    if not pointName:
                        return jsonify(dict(err=1, msg="新增按键的有效性判断中缺少点名", data=False))
                    logical = oneRelation.get("type", 0)
                    if not is_int_digit(logical):
                        return jsonify(dict(err=1, msg="新增按键的有效性判断的逻辑判断符必须未整数或整数字符串", data=False))

                    if int(logical) not in [0, 1, 2, 3, 4, 5]:
                        return jsonify(dict(err=1, msg="新增按键的有效性判断的逻辑判断符必须在0-5之间", data=False))

                    pointValue = oneRelation.get("value", None)
                    if pointValue == None:
                        return jsonify(dict(err=1, msg="新增按键的有效性判断中缺少点值", data=False))
                    relationList.append("{pointName}|{logical}|{pointValue}".format(pointName=pointName, logical=logical, pointValue=pointValue))

            if not isinstance(relationType, str):
                return jsonify(dict(err=1, msg="新增按键有效性判断逻辑类型必须为字符串", data=False))
            if relationType not in ["0", "1"]:
                return jsonify(dict(err=1, msg="新增按键有效性判断逻辑类型必须为0或1", data=False))
            if not isinstance(downloadEnableCondition, str):
                return jsonify(dict(err=1, msg="新增按键下载使能内容必须为字符串", data=False))
            if not isinstance(downloadURL, str):
                return jsonify(dict(err=1, msg="新增按键下载文件标识必须为字符串", data=False))
            if not isinstance(hideScript, str):
                return jsonify(dict(err=1, msg="新增按键隐藏脚本必须为字符串", data=False))

            nFontColor = get_int_from_rgb(fontColor.get("r"), fontColor.get("g"), fontColor.get("b"))
            dPreCheck = {"PreCheckScript" : preCheckScript,"PreCheckScriptDescription" : preCheckScriptDescription}
            nType = 0
            elementtype = 50
            strButtonValidation = ",".join(relationList)

            comm = dBtnImgStyleType.get(strStyle, {}).get("comm", None)
            over = dBtnImgStyleType.get(strStyle, {}).get("over", None)
            down = dBtnImgStyleType.get(strStyle, {}).get("down", None)
            disable = dBtnImgStyleType.get(strStyle, {}).get("disabled", None)

            if not isinstance(comm, int) or not isinstance(over, int) or not isinstance(down, int) or not isinstance(disable, int):
                return jsonify(dict(err=1, msg="新增按键的各风格图片id有误，请先升级后台", data=False))

            addButtonParamList.append(
                (nPageId, nBtnId, json.dumps(dPreCheck).encode("gbk"), nType, comm, over, down, disable, link, nX, nY, width,
                 height, layer, elementtype, str(setValue).encode("gbk"), setPoint.encode("gbk"), textContent.encode("gbk"),
                 nFontColor, fontSize, description.encode("gbk"), strButtonValidation.encode("gbk"), relationType.encode("gbk"),
                 downloadEnableCondition.encode("gbk"), downloadURL.encode("gbk"), hideScript.encode("gbk"), strStyle.encode("gbk"))
            )

            if nBtnId in nButtonIdListOfPage:
                return jsonify(dict(err=1, msg="新增按键中发现与页面(pageId: {pageId})中已有按键重复的id(id:{id})".format(id=nBtnId, pageId=nPageId), data=False))

            if nBtnId in addButtonIdList:
                return jsonify(dict(err=1, msg="新增按键中发现重复的id(id:{id})".format(id=nBtnId), data=False))

            addButtonIdList.append(nBtnId)

        # 新增checkbox
        elif item.get("typeTag") == "checkbox":
            nCheckBoxId = item.get("id", None)
            nX = item.get("x", 0)
            nY = item.get("y", 0)
            width = item.get("width", 18)
            height = item.get("height", 18)
            layer = item.get("layer", 9)
            nType = item.get("type", 0)  # 0-单选 1-多选
            fontColor = item.get("fontColor", dict(r=0, g=0, b=0))
            fontSize = item.get("fontSize", 14)
            setValue = item.get("setValue", 1)
            unsetValue = item.get("unsetValue", "")
            idCom = item.get("idCom", "")
            strText = item.get("text", "")
            idGroup = item.get("idGroup", 0)
            strExpression = item.get("expression", "")
            desc = item.get("desc", "")

            if not isinstance(nCheckBoxId, int):
                return jsonify(dict(err=1, msg="新增checkbox的id必须为整数", data=False))
            if nCheckBoxId < 0:
                return jsonify(dict(err=1, msg="新增checkbox的id不能小于0", data=False))

            if not isinstance(nX, int):
                return jsonify(dict(err=1, msg="新增checkbox的横坐标初始值必须为整数", data=False))
            if not isinstance(nY, int):
                return jsonify(dict(err=1, msg="新增checkbox的纵坐标初始值必须为整数", data=False))

            if not isinstance(height, int):
                return jsonify(dict(err=1, msg="新增checkbox的高度初始值必须为整数", data=False))
            if height < 0 or height > 955:
                return jsonify(dict(err=1, msg="新增checkbox的高度超限", data=False))
            if not isinstance(width, int):
                return jsonify(dict(err=1, msg="新增checkbox的宽度初始值必须为整数", data=False))
            if width < 0 or width > 1920:
                return jsonify(dict(err=1, msg="新增checkbox的宽度超限", data=False))

            if not isinstance(layer, int):
                return jsonify(dict(err=1, msg="新增checkbox的图层必须为整数", data=False))
            if layer < 0 or layer > 9:
                return jsonify(dict(err=1, msg="新增checkbox的图层必须在0-9之间", data=False))

            if not is_int_digit(nType):
                return jsonify(dict(err=1, msg="新增checkbox的类型必须为整数或整数字符串", data=False))
            if int(nType) not in [0, 1]:
                return jsonify(dict(err=1, msg="新增checkbox的类型必须为0或1", data=False))

            if not isinstance(fontColor, dict):
                return jsonify(dict(err=1, msg="新增checkbox的颜色必须为字典", data=False))
            if not isinstance(fontColor.get("r", None), int):
                return jsonify(dict(err=1, msg="新增checkbox的颜色r必须为整数", data=False))
            if not isinstance(fontColor.get("g", None), int):
                return jsonify(dict(err=1, msg="新增checkbox的颜色g必须为整数", data=False))
            if not isinstance(fontColor.get("b", None), int):
                return jsonify(dict(err=1, msg="新增checkbox的颜色b必须为整数", data=False))

            if not is_int_digit(fontSize):
                return jsonify(dict(err=1, msg="新增checkbox的字体大小必须为整数或整数字符串", data=False))
            if int(fontSize) < 5 or int(fontSize) > 100:
                return jsonify(dict(err=1, msg="新增checkbox的字体大小必须在5-100之间", data=False))

            if not isinstance(setValue, str) and not isinstance(setValue, float) and not isinstance(setValue, int):
                return jsonify(dict(err=1, msg="新增checkbox的选中赋值必须为字符串或浮点或整数", data=False))
            if not isinstance(unsetValue, str) and not isinstance(unsetValue, float) and not isinstance(unsetValue, int):
                return jsonify(dict(err=1, msg="新增checkbox的非选中赋值必须为字符串或浮点或整数", data=False))

            if not isinstance(idCom, str):
                return jsonify(dict(err=1, msg="新增checkbox的绑定点位必须为字符串", data=False))
            if not isinstance(strText, str):
                return jsonify(dict(err=1, msg="新增checkbox的选项名称必须为字符串", data=False))
            if not is_int_digit(idGroup):
                return jsonify(dict(err=1, msg="新增checkbox的组号必须为整数或整数字符串", data=False))
            if not isinstance(strExpression, str):
                return jsonify(dict(err=1, msg="新增checkbox的有效状态属性必须为字符串", data=False))
            if not isinstance(desc, str):
                return jsonify(dict(err=1, msg="新增checkbox的选项描述必须为字符串", data=False))

            strUnsetValue = ""
            try:
                strUnsetValue = str(unsetValue)
            except:
                pass

            nFontColor = get_int_from_rgb(fontColor.get("r"), fontColor.get("g"), fontColor.get("b"))
            addCheckboxParamList.append(
                (nX, nY, width, height, layer, nCheckBoxId, nPageId, str(nType).encode("gbk"), str(nFontColor).encode("gbk"), str(fontSize).encode("gbk"),
                 str(setValue).encode("gbk"), strUnsetValue.encode("gbk"), idCom.encode("gbk"), strText.encode("gbk"), str(idGroup).encode("gbk"),
                 strExpression.encode("gbk"), desc.encode("gbk"))
            )

            if nCheckBoxId in nCheckboxIdListOfPage:
                return jsonify(dict(err=1, msg="新增checkbox中发现与页面(pageId: {pageId})中已有checkbox重复的id(id:{id})".format(id=nCheckBoxId, pageId=nPageId), data=False))

            if nCheckBoxId in addCheckboxIdList:
                return jsonify(dict(err=1, msg="新增checkbox中发现重复的id(id:{id})".format(id=nCheckBoxId), data=False))

            addCheckboxIdList.append(nCheckBoxId)

        # 新增图片
        elif item.get("typeTag") == "image":
            nImageId = item.get("id", None)
            nX = item.get("x", 0)
            nY = item.get("y", 0)
            width = item.get("width", 82)
            height = item.get("height", 43)
            layer = item.get("layer", 4)
            bindPoint = item.get("idCom", "")
            rotateAngle = item.get("rotate", 0)
            pictureId = item.get("idPicture", None)
            bindType = item.get("bindType", 0)
            elementName = item.get("name", "")
            hideScript = item.get("hideScript", "")
            bindEnumList = item.get("bindEnumList", [])
            eventBindPoint = item.get("eventBindPoint", "")  # 绑定事件点
            eventEquipType = item.get("eventEquipType", 0)  # 事件设备类型
            eventType = item.get("eventType", 0)   # 事件类型
            eventEquipName = item.get("eventEquipName", "")  # 事件设备名称
            eventInnerLink = item.get("eventInnerLink", -1) # 事件跳转内部页面id
            eventOuterLink = item.get("eventOuterLink", "")
            nPictureFromDomLib = item.get("fromDomLib", 0)   # 图片是否来自图库(DOMImageLib.4db) 1-是  0-否
            customName = item.get("customName", "")

            if not isinstance(nImageId, int):
                return jsonify(dict(err=1, msg="新增图片的id必须为整数", data=False))
            if nImageId < 0:
                return jsonify(dict(err=1, msg="新增图片的id不能小于0", data=False))

            if not isinstance(nX, int):
                return jsonify(dict(err=1, msg="新增图片的横坐标初始值必须为整数", data=False))
            if not isinstance(nY, int):
                return jsonify(dict(err=1, msg="新增图片的纵坐标初始值必须为整数", data=False))

            if not isinstance(height, int):
                return jsonify(dict(err=1, msg="新增图片的高度初始值必须为整数", data=False))
            if height < 0 or height > 955:
                return jsonify(dict(err=1, msg="新增图片的高度超限", data=False))
            if not isinstance(width, int):
                return jsonify(dict(err=1, msg="新增图片的宽度初始值必须为整数", data=False))
            if width < 0 or width > 1920:
                return jsonify(dict(err=1, msg="新增图片的宽度超限", data=False))

            if not isinstance(layer, int):
                return jsonify(dict(err=1, msg="新增图片的图层必须为整数", data=False))
            if layer < 0 or layer > 9:
                return jsonify(dict(err=1, msg="新增图片的图层必须在0-9之间", data=False))
            if not isinstance(bindPoint, str):
                return jsonify(dict(err=1, msg="新增图片绑点必须为字符串", data=False))
            if not isinstance(rotateAngle, int) and not isinstance(rotateAngle, float):
                return jsonify(dict(err=1, msg="新增图片的旋转角度必须为浮点或整数", data=False))

            if not isinstance(pictureId, int):
                return jsonify(dict(err=1, msg="新增图片的id必须为整数", data=False))

            if nPictureFromDomLib == 1:
                if pictureId not in dAllImages.keys():
                    return jsonify(dict(err=1, msg="新增图片的id不存在于图库中", data=False))
            else:
                if pictureId not in dAllImagesDomdb.keys():
                    return jsonify(dict(err=1, msg="新增图片的id不存在于domdb.4db中", data=False))

            if not is_int_digit(bindType):
                return jsonify(dict(err=1, msg="新增图片的绑点判断类型（点/脚本)必须为整数或整数字符串", data=False))
            if int(bindType) not in [0, 1]:
                return jsonify(dict(err=1, msg="新增图片的绑点判断类型（点/脚本)必须为0或1", data=False))
            if not isinstance(elementName, str):
                return jsonify(dict(err=1, msg="新增图片元素名称必须为字符串", data=False))
            if not isinstance(hideScript, str):
                return jsonify(dict(err=1, msg="新增图片的隐藏脚本必须为字符串", data=False))

            if not isinstance(bindEnumList, list):
                return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量配置必须为列表", data=False))

            if nPictureFromDomLib == 1:
                nPicId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(pictureId)
                if nPicId == None:
                    return jsonify(dict(err=1, msg="新增图片时将图片插入lib_image失败:%s" % msg, data=False))
            else:
                nPicId = pictureId

            strBindEnumList = []
            for bindEnum in bindEnumList:
                if bindEnum.get("value", None) == None:
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量点值不能为空", data=False))
                if not is_int_digit(bindEnum.get("value")):
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量点值必须为整数或整数字符串", data=False))
                if bindEnum.get("id", None) == None:
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量图片id不能为空", data=False))
                if not isinstance(bindEnum.get("id"), int):
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量图片id必须为整数", data=False))

                if not isinstance(bindEnum.get("interval", None), int):
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量时间间隔必须为整数", data=False))

                nEnumType = bindEnum.get("type", 0)  # 0-图片  1-动画
                if nEnumType not in [0, 1]:
                    return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量对象类型必须为0或1", data=False))

                if nEnumType == 0:
                    if bindEnum.get("id") not in dAllImages.keys():
                        return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量图片id不存在:{id}".format(id=bindEnum.get("id")), data=False))
                elif nEnumType == 1:
                    if bindEnum.get("id") not in dAllAnimations.keys():
                        return jsonify(dict(err=1, msg="新增动画的绑点对应的枚举量动画id不存在:{id}".format(id=bindEnum.get("id")), data=False))

                nFrame = 1  # 帧（图片：1  动画：动画中包含的图片数量）
                nBindEnumItemId = None

                if nEnumType == 0:
                    nBindEnumItemId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(bindEnum.get("id"))
                    if nBindEnumItemId == None:
                        return jsonify(dict(err=1, msg="新增图片时将枚举量图片存入domdb.4db时失败:%s" % msg, data=False))

                elif nEnumType == 1:
                    nBindEnumItemId, nFrame, msg = BEOPSqliteAccess.getInstance().copyAnimationFromDomLibImage(bindEnum.get("id"))
                    if nBindEnumItemId == None:
                        return jsonify(dict(err=1, msg="新增图片时将枚举量动画存入domdb.4db时失败:%s" % msg, data=False))

                strBindEnumList.append("{value},{id},{frame},{interval}".format(value=bindEnum.get("value"), id=nBindEnumItemId, frame=nFrame, interval=bindEnum.get("interval", 0)))

            if len(strBindEnumList) > 20:
                return jsonify(dict(err=1, msg="新增图片的绑点对应的枚举量数量最大不能超过20个", data=False))

            if not isinstance(eventBindPoint, str):
                return jsonify(dict(err=1, msg="新增图片的绑定事件点名必须为字符串", data=False))
            if not is_int_digit(eventEquipType):
                return jsonify(dict(err=1, msg="新增图片的绑定事件设备类型必须为整数或整数字符串", data=False))
            if int(eventEquipType) < 0 or int(eventEquipType) > 12:
                return jsonify(dict(err=1, msg="新增图片的绑定事件设备类型范围必须为0-12", data=False))
            if not is_int_digit(eventType):
                return jsonify(dict(err=1, msg="新增图片的绑定事件的类型必须为整数或整数字符串", data=False))
            if int(eventType) < 0 or int(eventType) > 5:
                return jsonify(dict(err=1, msg="新增图片的绑定事件类型范围必须为0-5", data=False))
            if not isinstance(eventEquipName, str):
                return jsonify(dict(err=1, msg="新增图片的绑定事件设备名称必须为字符串", data=False))
            if not isinstance(eventInnerLink, int):
                return jsonify(dict(err=1, msg="新增图片的绑定事件跳转页面id必须为整数", data=False))
            if eventInnerLink not in nPageIdList and eventInnerLink != -1:
                return jsonify(dict(err=1, msg="新增图片的绑定事件跳转页面id不存在:{id}".format(id=eventInnerLink), data=False))
            if not isinstance(eventOuterLink, str):
                return jsonify(dict(err=1, msg="新增图片的绑定事件跳转外部链接必须为字符串", data=False))

            if not isinstance(customName, str):
                return jsonify(dict(err=1, msg="新增图片的用户自定义名称必须为字符串", data=False))

            mElementType = 49
            nLink = 0
            nElementSubType = 0
            strIsFromAnimation = "1"
            addImageParamList.append(
                (nPageId, mElementType, nImageId, nX, nY, width, height, layer, nLink, bindPoint.encode("gbk"), rotateAngle,
                 nElementSubType, elementName.encode("gbk"), nPicId, strIsFromAnimation.encode("gbk"), str(bindType).encode("gbk"), hideScript.encode("gbk"), customName.encode("gbk"))
            )

            strEventContent = "{eventBindPoint},{eventEquipType},{eventType},1,{eventInnerLink},-99,{eventEquipName},{eventOuterLink}".format(eventBindPoint=eventBindPoint,
                                                                                                                                              eventEquipType=str(eventEquipType),
                                                                                                                                              eventType=str(eventType),
                                                                                                                                              eventInnerLink=eventInnerLink,
                                                                                                                                              eventEquipName=eventEquipName,
                                                                                                                                              eventOuterLink=eventOuterLink)
            strBindContent = "|".join(strBindEnumList)
            addImageEventParamList.append(
                (nPageId, nImageId, strEventContent.encode("gbk"), strBindContent.encode("gbk"))
            )

            if nImageId in nImageIdListOfPage:
                return jsonify(dict(err=1, msg="新增图片中发现与页面(pageId: {pageId})中已有图片重复的id(id:{id})".format(id=nImageId, pageId=nPageId), data=False))

            if nImageId in addImageIdList:
                return jsonify(dict(err=1, msg="新增图片中发现重复的id(id:{id})".format(id=nImageId), data=False))

            addImageIdList.append(nImageId)

        # 新增管道
        elif item.get("typeTag") == "line":
            nLineId = item.get("id", None)
            nDirection = item.get("direction", 0)  # 0-正向  1-反向
            dColor = item.get("color", dict(r=255, g=128, b=192))
            nStartX = item.get("startX", 0)
            nStartY = item.get("startY", 0)
            nEndX = item.get("endX", 50)
            nEndY = item.get("endY", 50)
            nWidth = item.get("width", 14)
            nLayer = item.get("layer", 4)
            nLogic = item.get("logic", 0)
            idlist = item.get("idCom", "")
            nWaterType = item.get("waterType", 0)
            nDenSity = item.get("denSity", 0)
            nSpeed = item.get("speed", 0)
            nWaterShape = item.get("waterShape", 1)

            if not isinstance(nLineId, int):
                return jsonify(dict(err=1, msg="新增管道id必须为整数", data=False))
            if nLineId < 0:
                return jsonify(dict(err=1, msg="新增管道id不能是负数", data=False))

            if not is_int_digit(nDirection):
                return jsonify(dict(err=1, msg="新增管道的水流方向必须为整数或整数字符串", data=False))
            nDirection = int(nDirection)
            if nDirection not in [0, 1]:
                return jsonify(dict(err=1, msg="新增管道的水流方向必须为0或1", data=False))

            if dColor.get("r") < 0 or dColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增管道rgb颜色范围为0-255", data=False))
            if dColor.get("g") < 0 or dColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增管道rgb颜色范围为0-255", data=False))
            if dColor.get("b") < 0 or dColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增管道rgb颜色范围为0-255", data=False))

            if not isinstance(nStartX, int):
                return jsonify(dict(err=1, msg="新增管道的起点坐标必须为整数", data=False))
            if not isinstance(nStartY, int):
                return jsonify(dict(err=1, msg="新增管道的起点坐标必须为整数", data=False))
            if not isinstance(nEndX, int):
                return jsonify(dict(err=1, msg="新增管道的终点坐标必须为整数", data=False))
            if not isinstance(nEndY, int):
                return jsonify(dict(err=1, msg="新增管道的终点坐标必须为整数", data=False))

            if not is_int_digit(nWidth):
                return jsonify(dict(err=1, msg="新增管道的宽度必须为整数或整数字符串", data=False))
            nWidth = int(nWidth)
            if nWidth > 14 or nWidth < 1:
                return jsonify(dict(err=1, msg="新增管道的宽度必须在1-14", data=False))

            if not isinstance(nLayer, int):
                return jsonify(dict(err=1, msg="新增管道的图层必须为整数", data=False))
            if nLayer < 0 or nLayer > 9:
                return jsonify(dict(err=1, msg="新增管道的图层必须在0-9之间", data=False))

            if not is_int_digit(nLogic):
                return jsonify(dict(err=1, msg="新增管道的水流逻辑关系必须为整数或整数字符串", data=False))
            nLogic = int(nLogic)
            if nLogic not in [0, 1, 2]:
                return jsonify(dict(err=1, msg="新增管道的水流逻辑关系必须为0或1或2", data=False))

            if not isinstance(idlist, str):
                return jsonify(dict(err=1, msg="新增管道水流动画绑点必须为字符串", data=False))

            if not is_int_digit(nWaterType):
                return jsonify(dict(err=1, msg="新增管道的水流类型必须为字符串或整数字符串", data=False))
            nWaterType = int(nWaterType)
            if nWaterType < 0 or nWaterType > 15:
                return jsonify(dict(err=1, msg="新增管道的水流类型必须在0-15", data=False))

            if not is_int_digit(nDenSity):
                return jsonify(dict(err=1, msg="新增管道的水流密度必须为整数或整数字符串", data=False))
            nDenSity = int(nDenSity)
            if nDenSity < 0 or nDenSity > 4:
                return jsonify(dict(err=1, msg="新增管道的水流密度必须必须在0-4", data=False))

            if not is_int_digit(nSpeed):
                return jsonify(dict(err=1, msg="新增管道的水流速度必须为整数或整数字符串", data=False))
            nSpeed = int(nSpeed)
            if nSpeed < 0 or nSpeed > 2:
                return jsonify(dict(err=1, msg="新增管道的水流速度必须必须在0-2", data=False))

            if not is_int_digit(nWaterShape):
                return jsonify(dict(err=1, msg="新增管道的水流形状必须为整数或整数字符串", data=False))
            nWaterShape = int(nWaterShape)
            if nWaterShape not in [0, 1]:
                return jsonify(dict(err=1, msg="新增管道的水流形状必须为0或1", data=False))

            nInnerColor = get_int_from_rgb(dColor.get("r"), dColor.get("g"), dColor.get("b"))
            nOuterColor = 4194432
            coordinator = "({startX},{startY});({endX},{endY});".format(startX=nStartX, startY=nStartY, endX=nEndX, endY=nEndY)
            nUnitproperty02 = "0".encode("gbk")

            addLineParamList.append(
                (nPageId, nLineId, nDirection, nInnerColor, nOuterColor, coordinator.encode("gbk"), nWidth, nLayer, nLogic, idlist.encode("gbk"),
                 str(nWaterType).encode("gbk"), nUnitproperty02, str(nDenSity).encode("gbk"), str(nSpeed).encode("gbk"), str(nWaterShape).encode("gbk"))
            )

            if nLineId in nLineIdListOfPage:
                return jsonify(dict(err=1, msg="新增管道中发现与页面(pageId: {pageId})中已有管道重复的id(id:{id})".format(id=nLineId,
                                                                                                            pageId=nPageId), data=False))

            if nLineId in addLineIdList:
                return jsonify(dict(err=1, msg="新增管道中发现重复的id(id:{id})".format(id=nLineId), data=False))

            addLineIdList.append(nLineId)

        # 新增标准设备
        elif item.get("typeTag") == "systemEquipment":
            nSysEquipId = item.get("id", None)
            nX = item.get("x", 300)
            nY = item.get("y", 300)
            nWidth = item.get("width", 120)
            nHeight = item.get("height", 120)
            nLayer = item.get("layer", 4)
            nEntranceGroupId = item.get("entranceGroupId", None)
            nEntrancePageId = item.get("entrancePageId", None)
            templateName = item.get("templateName", None)
            placeHolder = item.get("placeHolder", None)
            templateFileName = item.get("templateFileName", None)
            customName = item.get("customName", "")

            if not isinstance(nSysEquipId, int):
                return jsonify(dict(err=1, msg="新增标准设备id必须为整数", data=False))
            if nSysEquipId < 0:
                return jsonify(dict(err=1, msg="新增标准设备id不能是负数", data=False))
            if not isinstance(nX, int):
                return jsonify(dict(err=1, msg="新增增标准设备的坐标必须为整数", data=False))
            if not isinstance(nY, int):
                return jsonify(dict(err=1, msg="新增增标准设备的坐标必须为整数", data=False))
            if not isinstance(nWidth, int):
                return jsonify(dict(err=1, msg="新增增标准设备的宽度必须为整数", data=False))
            if nWidth < 0 or nWidth > 1920:
                return jsonify(dict(err=1, msg="新增增标准设备的宽度必须在0-1920", data=False))
            if not isinstance(nHeight, int):
                return jsonify(dict(err=1, msg="新增增标准设备的高度必须为整数", data=False))
            if nHeight < 0 or nHeight > 955:
                return jsonify(dict(err=1, msg="新增增标准设备的高度必须在0-955", data=False))

            if not isinstance(nLayer, int):
                return jsonify(dict(err=1, msg="新增标准设备的图层必须为整数", data=False))
            if nLayer < 0 or nLayer > 9:
                return jsonify(dict(err=1, msg="新增标准设备的图层必须在0-9之间", data=False))

            if not isinstance(nEntranceGroupId, int):
                return jsonify(dict(err=1, msg="新增标准设备的入口页面分组id必须为整数", data=False))
            if not isinstance(nEntrancePageId, int):
                return jsonify(dict(err=1, msg="新增标准设备的入口页面id必须为整数", data=False))

            if not isinstance(templateName, str):
                return jsonify(dict(err=1, msg="新增标准设备的模板名称必须为字符串", data=False))
            if not len(templateName):
                return jsonify(dict(err=1, msg="新增标准设备的模板名称不能为空", data=False))

            if not isinstance(placeHolder, list):
                return jsonify(dict(err=1, msg="新增标准设备的占位符必须为数组", data=False))
            if not isinstance(templateFileName, str):
                return jsonify(dict(err=1, msg="新增标准设备的模板文件名称必须为字符串", data=False))
            if not len(templateFileName):
                return jsonify(dict(err=1, msg="新增标准设备的模板文件名称不能为空", data=False))

            if not isinstance(customName, str):
                return jsonify(dict(err=1, msg="新增标准设备的用户自定义名称必须为字符串", data=False))

            addSysEquipParamList.append(
                (nX, nY, nWidth, nHeight, nLayer, nSysEquipId, nPageId, "0".encode("gbk"), "0".encode("gbk"), str(nEntranceGroupId).encode("gbk"),
                 str(nEntrancePageId).encode("gbk"), templateName.encode("gbk"), str(placeHolder).encode("gbk"), templateFileName.encode("gbk"), "0".encode("gbk"), "".encode("gbk"), customName.encode("gbk"))
            )

            if nSysEquipId in nSysEquipIdListOfPage:
                return jsonify(dict(err=1, msg="新增标准设备中发现与页面(pageId: {pageId})中已有标准设备重复的id(id:{id})".format(id=nSysEquipId,
                                                                                                            pageId=nPageId), data=False))

            if nSysEquipId in addSysEquipIdList:
                return jsonify(dict(err=1, msg="新增标准设备中发现重复的id(id:{id})".format(id=nSysEquipId), data=False))

            addSysEquipIdList.append(nSysEquipId)

        # 新增矩形框
        elif item.get("typeTag") == "rectangle":
            nRectId = item.get("id", None)
            nX = item.get("x", 300)
            nY = item.get("y", 300)
            nWidth = item.get("width", 120)
            nHeight = item.get("height", 120)
            nLayer = item.get("layer", 4)
            dFrameColor = item.get("color", dict(r=255, g=255, b=25))  # 边框颜色
            frameTrans = item.get("frameTrans", 100)    # 边框透明度
            frameLineWidth = item.get("lineWidth", 1)  # 边框线宽
            nFillOrNot = item.get("fillOrNot", 0)  # 是否填充 0，1
            dFillColor = item.get("fillColor", dict(r=255, g=255, b=255))
            fillTrans = item.get("fillTrans", 100)  # 填充透明度
            nRoundOrNot = item.get("roundOrNot", 1)  # 是否有圆角
            roundYPox = item.get("roundYPox", 10)  #圆角高度
            roundXPox = item.get("roundXPox", 10)  #圆角宽度
            rectStyle = item.get("rectStyle", 0)
            titleColor = item.get("titleColor", dict(r=255, g=255, b=255))
            titleTrans = item.get("titleTrans", 100)
            titleSize = item.get("titleSize", 14)
            bodyColor = item.get("bodyColor", dict(r=255, g=255, b=255))
            bodySize = item.get("bodySize", 14)
            bodyTrans = item.get("bodyTrans", 100)
            descColor = item.get("descColor", dict(r=255, g=255, b=255))
            descSize = item.get("descSize", 14)
            descTrans = item.get("descTrans", 100)
            descOrNot = item.get("descOrNot", 1)
            bindPointList = item.get("pointList", [])
            title = item.get("title", "")

            if not isinstance(nRectId, int):
                return jsonify(dict(err=1, msg="新增矩形框id必须为整数", data=False))
            if nRectId < 0:
                return jsonify(dict(err=1, msg="新增矩形框id不能是负数", data=False))
            if not isinstance(nX, int):
                return jsonify(dict(err=1, msg="新增矩形框的坐标必须为整数", data=False))
            if not isinstance(nY, int):
                return jsonify(dict(err=1, msg="新增矩形框的坐标必须为整数", data=False))
            if not isinstance(nWidth, int):
                return jsonify(dict(err=1, msg="新增矩形框的宽度必须为整数", data=False))
            if nWidth < 0 or nWidth > 1920:
                return jsonify(dict(err=1, msg="新增矩形框的宽度必须在0-1920", data=False))
            if not isinstance(nHeight, int):
                return jsonify(dict(err=1, msg="新增矩形框的高度必须为整数", data=False))
            if nHeight < 0 or nHeight > 955:
                return jsonify(dict(err=1, msg="新增矩形框的高度必须在0-955", data=False))

            if not isinstance(nLayer, int):
                return jsonify(dict(err=1, msg="新增矩形框的图层必须为整数", data=False))
            if nLayer < 0 or nLayer > 9:
                return jsonify(dict(err=1, msg="新增矩形框的图层必须在0-9之间", data=False))

            if dFrameColor.get("r") < 0 or dFrameColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增矩形框rgb颜色范围为0-255", data=False))
            if dFrameColor.get("g") < 0 or dFrameColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增矩形框rgb颜色范围为0-255", data=False))
            if dFrameColor.get("b") < 0 or dFrameColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增矩形框rgb颜色范围为0-255", data=False))

            if not isinstance(frameTrans, int) and not isinstance(frameTrans, float):
                return jsonify(dict(err=1, msg="新增矩形框的边框透明度必须为数字", data=False))
            if frameTrans < 0.0 or frameTrans > 100.0:
                return jsonify(dict(err=1, msg="新增矩形框的边框透明度必须在0-100", data=False))

            if not isinstance(frameLineWidth, int):
                return jsonify(dict(err=1, msg="新增矩形框的边框透线宽必须为整数", data=False))
            if frameLineWidth < 0 or frameLineWidth > 14:
                return jsonify(dict(err=1, msg="新增矩形框的边框透线宽必须在0-14", data=False))

            if nFillOrNot not in [0,1]:
                return jsonify(dict(err=1, msg="新增矩形框的是否填充必须为整数0或1", data=False))

            if dFillColor.get("r") < 0 or dFillColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增矩形框填充色范围为0-255", data=False))
            if dFillColor.get("g") < 0 or dFillColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增矩形框填充色范围为0-255", data=False))
            if dFillColor.get("b") < 0 or dFillColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增矩形框填充色范围为0-255", data=False))

            if not isinstance(fillTrans, int) and not isinstance(fillTrans, float):
                return jsonify(dict(err=1, msg="新增矩形框的填充透明度必须为数字", data=False))
            if fillTrans < 0.0 or fillTrans > 100.0:
                return jsonify(dict(err=1, msg="新增矩形框的填充透明度必须在0-100", data=False))

            if nRoundOrNot not in [0,1]:
                return jsonify(dict(err=1, msg="新增矩形框的是否为圆角必须为整数0或1", data=False))

            if not isinstance(roundYPox, int):
                return jsonify(dict(err=1, msg="新增矩形框的圆角高度必须为整数", data=False))
            if roundYPox < 0 or roundYPox > 100:
                return jsonify(dict(err=1, msg="新增矩形框的圆角宽度必须在0-100", data=False))
            if not isinstance(roundXPox, int):
                return jsonify(dict(err=1, msg="新增矩形框的圆角宽度必须为整数", data=False))
            if roundXPox < 0 or roundXPox > 100:
                return jsonify(dict(err=1, msg="新增矩形框的圆角宽度必须在0-100", data=False))

            if not isinstance(rectStyle, int):
                return jsonify(dict(err=1, msg="新增矩形框的样式必须为整数", data=False))
            if rectStyle < 0 or rectStyle > 10:
                return jsonify(dict(err=1, msg="新增矩形框的样式必须在0-10", data=False))

            if titleColor.get("r") < 0 or titleColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增矩形框标题颜色范围为0-255", data=False))
            if titleColor.get("g") < 0 or titleColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增矩形框标题颜色范围为0-255", data=False))
            if titleColor.get("b") < 0 or titleColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增矩形框标题颜色范围为0-255", data=False))

            if not isinstance(titleSize, int):
                return jsonify(dict(err=1, msg="新增矩形框的标题字号必须为整数", data=False))

            if not isinstance(titleTrans, int) and not isinstance(titleTrans, float):
                return jsonify(dict(err=1, msg="新增矩形框的标题透明度必须为数字", data=False))
            if titleTrans < 0.0 or titleTrans > 100.0:
                return jsonify(dict(err=1, msg="新增矩形框的标题透明度必须在0-100", data=False))

            if bodyColor.get("r") < 0 or bodyColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增矩形框正文颜色范围为0-255", data=False))
            if bodyColor.get("g") < 0 or bodyColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增矩形框正文颜色范围为0-255", data=False))
            if bodyColor.get("b") < 0 or bodyColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增矩形框正文颜色范围为0-255", data=False))

            if not isinstance(bodySize, int):
                return jsonify(dict(err=1, msg="新增矩形框的正文字号必须为整数", data=False))

            if not isinstance(bodyTrans, int) and not isinstance(bodyTrans, float):
                return jsonify(dict(err=1, msg="新增矩形框的正文透明度必须为数字", data=False))
            if bodyTrans < 0.0 or bodyTrans > 100.0:
                return jsonify(dict(err=1, msg="新增矩形框的正文透明度必须在0-100", data=False))

            if descColor.get("r") < 0 or descColor.get("r") > 255:
                return jsonify(dict(err=1, msg="新增矩形框描述颜色范围为0-255", data=False))
            if descColor.get("g") < 0 or descColor.get("g") > 255:
                return jsonify(dict(err=1, msg="新增矩形框描述颜色范围为0-255", data=False))
            if descColor.get("b") < 0 or descColor.get("b") > 255:
                return jsonify(dict(err=1, msg="新增矩形框描述颜色范围为0-255", data=False))

            if not isinstance(descSize, int):
                return jsonify(dict(err=1, msg="新增矩形框的描述字号必须为整数", data=False))

            if not isinstance(descTrans, int) and not isinstance(descTrans, float):
                return jsonify(dict(err=1, msg="新增矩形框的注释透明度必须为数字", data=False))
            if descTrans < 0.0 or descTrans > 100.0:
                return jsonify(dict(err=1, msg="新增矩形框的注释透明度必须在0-100", data=False))

            if descOrNot not in [0,1]:
                return jsonify(dict(err=1, msg="新增矩形框的是否显示描述必须为整数0或1", data=False))

            if not isinstance(title, str):
                return jsonify(dict(err=1, msg="新增矩形框的标题必须为字符串", data=False))

            strBinddPointItemList = []
            if isinstance(bindPointList, list) and len(bindPointList):
                for dBindPoint in bindPointList:
                    nFromDomLib = dBindPoint.get("fromDomLib", 1)

                    if not isinstance(dBindPoint.get("point"), str):
                        return jsonify(dict(err=1, msg="新增矩形框的枚举量绑点必须为字符串", data=False))
                    if not len(dBindPoint.get("point")):
                        return jsonify(dict(err=1, msg="新增矩形框的枚举量绑点不能为空字符串", data=False))
                    if not isinstance(dBindPoint.get("id"), int):
                        return jsonify(dict(err=1, msg="新增矩形框的枚举量图片id必须为整数", data=False))

                    if nFromDomLib == 1:
                        if dBindPoint.get("id") not in dAllImages.keys():
                            return jsonify(dict(err=1, msg="新增矩形框的枚举量图片id不存在于图库中:{id}".format(id=dBindPoint.get("id")), data=False))
                    else:
                        if dBindPoint.get("id") not in dAllImagesDomdb.keys():
                            return jsonify(dict(err=1, msg="新增矩形框的枚举量图片id不存在于domdb.4db中:{id}".format(id=dBindPoint.get("id")), data=False))

                    if not isinstance(dBindPoint.get("decimal"), int):
                        return jsonify(dict(err=1, msg="新增矩形框的枚举量小数位必须为整数", data=False))

                    if nFromDomLib == 1:
                        nBindItemId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(dBindPoint.get("id"))
                        if nBindItemId == None:
                            return jsonify(dict(err=1, msg="新增矩形框的枚举量图片在转移至domdb.4db时失败:%s" % msg, data=False))
                    else:
                        nBindItemId = dBindPoint.get("id")

                    strBinddPointItemList.append("{point},{nBindItemId},{decimal}".format(point=dBindPoint.get("point"), nBindItemId=nBindItemId, decimal=dBindPoint.get("decimal")))

            strContentArea = ""
            if len(strBinddPointItemList):
                strContentArea = "|".join(strBinddPointItemList)

            strHexFrameColor = get_hex_from_rgb(dFrameColor.get("r"), dFrameColor.get("g"), dFrameColor.get("b"))
            strFrameColorTrans = "#{color}#{trans}".format(color=strHexFrameColor, trans=str(int(frameTrans / 100)))

            strHexFillColor = get_hex_from_rgb(dFillColor.get("r"), dFillColor.get("g"), dFillColor.get("b"))
            strFillColorTrans = "#{color}#{trans}".format(color=strHexFillColor, trans=str(int(fillTrans / 100)))

            strHexTitleColor = get_hex_from_rgb(titleColor.get("r"), titleColor.get("g"), titleColor.get("b"))
            strTitleColorTransSize = "#{color}#{trans},{size}".format(color=strHexTitleColor, trans=str(int(titleTrans / 100)), size=titleSize)

            strHexBodyColor = get_hex_from_rgb(bodyColor.get("r"), bodyColor.get("g"), bodyColor.get("b"))
            strBodyColorTransSize = "#{color}#{trans},{size}".format(color=strHexBodyColor, trans=str(int(bodyTrans / 100)), size=bodySize)

            strHexDescColor = get_hex_from_rgb(descColor.get("r"), descColor.get("g"), descColor.get("b"))
            strDescColorTransSize = "#{color}#{trans},{size}".format(color=strHexDescColor, trans=str(int(descTrans / 100)), size=descSize)

            addRectangleParamList.append(
                (nX, nY, nWidth,nHeight, nLayer, nRectId, nPageId, 'rectangle', strFrameColorTrans.encode("gbk"), str(frameLineWidth).encode("gbk"), str(nFillOrNot).encode("gbk"),
                 strFillColorTrans.encode("gbk"), str(nRoundOrNot).encode("gbk"), str(roundYPox).encode("gbk"), str(roundXPox).encode("gbk"), str(rectStyle).encode("gbk"), strTitleColorTransSize,
                 strBodyColorTransSize, strDescColorTransSize, str(descOrNot).encode("gbk"), strContentArea.encode("gbk"), title.encode("gbk"))
            )

            if nRectId in nRectangleIdListOfPage:
                return jsonify(
                    dict(err=1, msg="新增矩形框中发现与页面(pageId: {pageId})中已有矩形框重复的id(id:{id})".format(id=nRectId, pageId=nPageId), data=False))

            if nRectId in addRectangleIdList:
                return jsonify(dict(err=1, msg="新增矩形框中发现重复的id(id:{id})".format(id=nRectId), data=False))

            addRectangleIdList.append(nRectId)


    if len(addTextParamList):
        sqlInsertText = "INSERT INTO list_text (pageid, id, font, size, color, border_color, initialvalue, decimalplace, istransparent, xpos, ypos, height, width, dataComId, showMode, transparence, borderType," \
                        "layer, align, bindstring, dataComTime, dataComTimeArrayPoint, unitproperty01, unitproperty02, unitproperty05, hideScript, unitproperty04) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"

        addTextList.append(sqlInsertText)
        addTextList.append(addTextParamList)

    if len(addCustParamList):
        strInsertCust = "INSERT INTO list_unit19 (x, y, width, height, layer, id, pageid, unitproperty01, unitproperty02) VALUES (?,?,?,?,?,?,?,?,?)"
        addCustList.append(strInsertCust)
        addCustList.append(addCustParamList)

    if len(addButtonParamList):
        sqlInsertButton = "INSERT INTO list_button (pageid, id, name, type, comm, over, down, disable, link, x, y, width, height, layer, elementtype, settingvalue, " \
                          "settingpoint, textcontent, textcolor, textsize, description, unitproperty01, unitproperty02, unitproperty04,unitproperty05, hideScript, sourceType) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addButtonList.append(sqlInsertButton)
        addButtonList.append(addButtonParamList)

    if len(addCheckboxParamList):
        sqlInsertCheckbox = "INSERT INTO list_unit07 (x, y, width, height, layer, id, pageid, unitproperty01,unitproperty02,unitproperty03, unitproperty04, unitproperty05, unitproperty06, unitproperty07, " \
                            "unitproperty08, unitproperty09, unitproperty10) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addCheckboxList.append(sqlInsertCheckbox)
        addCheckboxList.append(addCheckboxParamList)

    if len(addImageParamList):
        sqlInsertImage = "INSERT INTO page_contain_elements (pageid, elementtype, elementid, x, y, width, hight, layer, link," \
                         " DataComId, rotateAngle, elementSubType, elementName, pictureid, unitproperty02, unitproperty03, hideScript, unitproperty04) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addImageList.append(sqlInsertImage)
        addImageList.append(addImageParamList)

    if len(addLineParamList):
        sqlInsertLine = "INSERT INTO list_line (pageid, id, style, innerColor, outerColor, PointList, pipeWidth, layer, logic, idlist, " \
                        "unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addLineList.append(sqlInsertLine)
        addLineList.append(addLineParamList)

    if len(addSysEquipParamList):
        sqlInsertSysEquip = "INSERT INTO list_unit13 (x, y, width, height, layer, id, pageid, unitproperty01, unitproperty02, " \
                            "unitproperty03, unitproperty04, unitproperty05, unitproperty06, unitproperty07, unitproperty08, unitproperty09, unitproperty10) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addSysEquipList.append(sqlInsertSysEquip)
        addSysEquipList.append(addSysEquipParamList)

    if len(addRectangleIdList):
        strInsertRectangle = "INSERT INTO list_unit19 (x, y, width, height, layer, id, pageid, unitproperty01, unitproperty02, unitproperty03, unitproperty04, unitproperty05, unitproperty06," \
                             "unitproperty07, unitproperty08, unitproperty09, unitproperty10, unitproperty11, unitproperty12, unitproperty13, unitproperty14, unitproperty15) VALUES (?,?,?,?,?," \
                             "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        addRectangleList.append(strInsertRectangle)
        addRectangleList.append(addRectangleParamList)

    # 删除
    for item in removeList:
        if not isinstance(item, dict):
            continue

        if item.get("typeTag") == "text":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="text的id必须为整数", data=False))
            removeTextParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "customControls":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的自定义组件的id必须为整数", data=False))
            removeCustParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "button":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的按键的id必须为整数", data=False))
            removeButtonParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "checkbox":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的checkbox的id必须为整数", data=False))
            removeCheckboxParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "image":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的image的id必须为整数", data=False))
            removeImageParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "line":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的管道id必须为整数", data=False))
            removeLineParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "systemEquipment":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的标准设备id必须为整数", data=False))
            removeSysEquipParamList.append((item.get("id"), nPageId))

        elif item.get("typeTag") == "rectangle":
            if not isinstance(item.get("id"), int):
                return jsonify(dict(err=1, msg="需删除的矩形框id必须为整数", data=False))
            removeRectangleParamList.append((item.get("id"), nPageId))

    if len(removeTextParamList):
        sqlDeleteText = "DELETE FROM list_text WHERE id =? AND pageid=?"
        removeTextList.append(sqlDeleteText)
        removeTextList.append(removeTextParamList)

    if len(removeCustParamList):
        strDeleteCust = "DELETE FROM list_unit19 WHERE id=? AND pageid=? AND unitproperty01='generalComponent'"
        removeCustList.append(strDeleteCust)
        removeCustList.append(removeCustParamList)

    if len(removeButtonParamList):
        strDeleteButton = "DELETE FROM list_button WHERE id=? AND pageid=?"
        removeButtonList.append(strDeleteButton)
        removeButtonList.append(removeButtonParamList)

    if len(removeCheckboxParamList):
        strDeleteCheckbox = "DELETE FROM list_unit07 WHERE id=? AND pageid =?"
        removeCheckboxList.append(strDeleteCheckbox)
        removeCheckboxList.append(removeCheckboxParamList)

    if len(removeImageParamList):
        strDeleteImage = "DELETE FROM page_contain_elements WHERE elementtype=49 AND elementid=? AND pageid=?"
        removeImageList.append(strDeleteImage)
        removeImageList.append(removeImageParamList)

    if len(removeLineParamList):
        strDeleteLine = "DELETE FROM list_line WHERE id=? AND pageid=?"
        removeLineList.append(strDeleteLine)
        removeLineList.append(removeLineParamList)

    if len(removeSysEquipParamList):
        strDeleteSysEquip = "DELETE FROM list_unit13 WHERE id=? AND pageid=?"
        removeSysEquipList.append(strDeleteSysEquip)
        removeSysEquipList.append(removeSysEquipParamList)

    # 删除矩形框
    if len(removeRectangleParamList):
        strDeleteRectangle = "DELETE FROM list_unit19 WHERE id=? AND pageid=? AND unitproperty01='rectangle'"
        removeRectangleList.append(strDeleteRectangle)
        removeRectangleList.append(removeRectangleParamList)

    # 修改text
    for item in updateList:
        if not isinstance(item, dict):
            continue

        if item.get("typeTag") == "text":
            nTextId = item.get("id", None)
            font = item.get("font", None)
            size = item.get("fontSize", None)
            color = item.get("color", None)
            border_color = item.get("border_color", None)
            initialvalue = item.get("text", None)
            xpos = item.get("x", None)
            ypos = item.get("y", None)
            height = item.get("height", None)
            width = item.get("width", None)
            showMode = item.get("showMode", None)  # 0-枚举模式  1- 值模式 2-时间模式   3-字符串模式  4-按间隔加减修改值模式  5-值模式带单位显示
            layer = item.get("layer", None)
            align = item.get("align", None)
            dataComId = item.get("idCom", None)
            bindstring = item.get("bindString", None)
            dataComTime = item.get("dataComTime", None)
            dataComTimeArrayPoint = item.get("dataComTimeArrayPoint", None)
            unitproperty01 = item.get("backgroudFrameStyle", None)  # 背景框样式
            unitproperty02 = item.get("sensorType", None)  # 类型   0-无需配置；1-温度；2-湿度；3-SP
            unitproperty05 = item.get("bindScript", None)  # 自定义语法
            hideScript = item.get("hideScript", None)  # 隐藏判断脚本
            decimalplace = item.get("decimalplace", None)
            unit = item.get("unit", None)

            if not isinstance(nTextId, int):
                return jsonify(dict(err=1, msg="待修改的text id必须为整数", data=False))

            if font != None:
                if not isinstance(font, str):
                    return jsonify(dict(err=1, msg="待修改text的字体类型必须为字符串", data=False))
                if not len(font):
                    return jsonify(dict(err=1, msg="待修改text的字体类型不能是空字符串", data=False))

            if size != None:
                if not isinstance(size, int):
                    return jsonify(dict(err=1, msg="待修改text的字体大小必须为整数", data=False))
                if size < 5 or size > 100:
                    return jsonify(dict(err=1, msg="待修改text的字体大小必须在5-100之间", data=False))

            if color != None:
                if not isinstance(color, dict):
                    return jsonify(dict(err=1, msg="待修改text的颜色必须为字典", data=False))
                if not isinstance(color.get("r", None), int):
                    return jsonify(dict(err=1, msg="待修改text的颜色r必须为整数", data=False))
                if not isinstance(color.get("g", None), int):
                    return jsonify(dict(err=1, msg="待修改text的颜色g必须为整数", data=False))
                if not isinstance(color.get("b", None), int):
                    return jsonify(dict(err=1, msg="待修改text的颜色b必须为整数", data=False))
                if color.get("r") < 0 or color.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))
                if color.get("g") < 0 or color.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))
                if color.get("b") < 0 or color.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))

            if border_color != None:
                if not isinstance(border_color, dict):
                    return jsonify(dict(err=1, msg="待修改text的边框颜色必须为字典", data=False))
                if not isinstance(border_color.get("r", None), int):
                    return jsonify(dict(err=1, msg="待修改text的边框颜色r必须为整数", data=False))
                if not isinstance(border_color.get("g", None), int):
                    return jsonify(dict(err=1, msg="待修改text的边框颜色g必须为整数", data=False))
                if not isinstance(border_color.get("b", None), int):
                    return jsonify(dict(err=1, msg="待修改text的边框颜色b必须为整数", data=False))
                if border_color.get("r") < 0 or border_color.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))
                if border_color.get("g") < 0 or border_color.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))
                if border_color.get("b") < 0 or border_color.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改字体rgb颜色范围为0-255", data=False))

            if initialvalue != None:
                if not isinstance(initialvalue, str):
                    return jsonify(dict(err=1, msg="待修改text的初始值必须为字符串", data=False))
                if not len(initialvalue):
                    return jsonify(dict(err=1, msg="待修改text的初始值不能为空字符串", data=False))

            if xpos != None:
                if not isinstance(xpos, int):
                    return jsonify(dict(err=1, msg="待修改text的横坐标初始值必须为整数", data=False))

            if ypos != None:
                if not isinstance(ypos, int):
                    return jsonify(dict(err=1, msg="待修改text的纵坐标初始值必须为整数", data=False))

            if height != None:
                if not isinstance(height, int):
                    return jsonify(dict(err=1, msg="待修改text的高度初始值必须为整数", data=False))
                if height < 0 or height > 955:
                    return jsonify(dict(err=1, msg="待修改text的高度超限", data=False))

            if width != None:
                if not isinstance(width, int):
                    return jsonify(dict(err=1, msg="待修改text的宽度初始值必须为整数", data=False))
                if width < 0 or width > 1920:
                    return jsonify(dict(err=1, msg="待修改text的宽度超限", data=False))

            if showMode != None:
                if not isinstance(showMode, int):
                    return jsonify(dict(err=1, msg="待修改text的显示模式必须为整数", data=False))
                if showMode not in [0, 1, 2, 3, 4, 5]:
                    return jsonify(dict(err=1, msg="待修改text的显示模式必须为0-5之间的整数", data=False))

            if layer != None:
                if not isinstance(layer, int):
                    return jsonify(dict(err=1, msg="待修改text的图层必须为整数", data=False))
                if layer < 0 or layer > 9:
                    return jsonify(dict(err=1, msg="待修改text的图层必须在0-9之间", data=False))

            if align != None:
                if not isinstance(align, int):
                    return jsonify(dict(err=1, msg="待修改text的对齐必须为整数", data=False))
                if align < 0 or align > 8:
                    return jsonify(dict(err=1, msg="待修改text的对齐必须为0-8之间的整数", data=False))

            if dataComId != None:
                if not isinstance(dataComId, str):
                    return jsonify(dict(err=1, msg="待修改text的非时间变量点名必须为字符串", data=False))

            if bindstring != None:
                if not isinstance(bindstring, str):
                    return jsonify(dict(err=1, msg="待修改text的非时间变量点名必须为字符串", data=False))
                if showMode != None:
                    if showMode == 0 and not len(bindstring):
                        return jsonify(dict(err=1, msg="待修改text在枚举模式下必须要绑定枚举量对应的字符串", data=False))

            if dataComTime != None:
                if not isinstance(dataComTime, str):
                    return jsonify(dict(err=1, msg="待修改text的时间变量点名必须为字符串", data=False))

            if dataComTimeArrayPoint != None:
                if not isinstance(dataComTimeArrayPoint, str):
                    return jsonify(dict(err=1, msg="待修改text的时间序列点名必须为字符串", data=False))

            nUnitproperty01 = None
            if unitproperty01 != None:
                if not is_int_digit(unitproperty01):
                    return jsonify(dict(err=1, msg="待修改text的背景框样式必须为整数或整数字符串", data=False))
                nUnitproperty01 = int(unitproperty01)
                if nUnitproperty01 < 0 or nUnitproperty01 > 10:
                    return jsonify(dict(err=1, msg="待修改text的背景框样式必须为0-10之间的整数或整数字符串", data=False))

            if unitproperty02 != None:
                if not isinstance(unitproperty02, int):
                    return jsonify(dict(err=1, msg="待修改text的传感器类型必须为整数", data=False))
                if unitproperty02 < 0 or unitproperty02 > 3:
                    return jsonify(dict(err=1, msg="待修改text的传感器类型必须为0-3之间的整数", data=False))

            if unitproperty05 != None:
                if not isinstance(unitproperty05, str):
                    return jsonify(dict(err=1, msg="待修改text的自定义语法必须为字符串", data=False))

            if hideScript != None:
                if not isinstance(hideScript, str):
                    return jsonify(dict(err=1, msg="待修改text的隐藏脚本必须为字符串", data=False))

            if decimalplace != None:
                if not isinstance(decimalplace, int):
                    return jsonify(dict(err=1, msg="待修改text的小数位必须为整数", data=False))

                if decimalplace < 0 or decimalplace > 4:
                    return jsonify(dict(err=1, msg="待修改text的小数位必须为0-4的整数", data=False))

            if unit != None:
                if not isinstance(unit, str):
                    return jsonify(dict(err=1, msg="待修改text的单位必须为字符串", data=False))

            if font == None and size == None and color == None and border_color == None and initialvalue == None and xpos == None and \
                ypos == None and height == None and width == None and showMode == None and layer == None and align == None and dataComId == None and \
                bindstring == None and dataComTime == None and dataComTimeArrayPoint == None and nUnitproperty01 == None and unitproperty02 == None and \
                unitproperty05 == None and hideScript == None and decimalplace == None and unit == None:
                continue

            sqlList = []
            updateTextParamList = []
            sqlUpdateText = "UPDATE list_text SET "

            if font != None:
                sqlList.append("font=?")
                updateTextParamList.append(font.encode("gbk"))
            if size != None:
                sqlList.append("size=?")
                updateTextParamList.append(size)
            if color != None:
                nColor = get_int_from_rgb(color.get("r"), color.get("g"), color.get("b"))
                sqlList.append("color=?")
                updateTextParamList.append(nColor)
            if border_color != None:
                nBorderColor = get_int_from_rgb(border_color.get("r"), border_color.get("g"), border_color.get("b"))
                sqlList.append("border_color=?")
                updateTextParamList.append(nBorderColor)
            if initialvalue != None:
                sqlList.append("initialvalue=?")
                updateTextParamList.append(initialvalue.encode("gbk"))
            if xpos != None:
                sqlList.append("xpos=?")
                updateTextParamList.append(xpos)
            if ypos != None:
                sqlList.append("ypos=?")
                updateTextParamList.append(ypos)
            if height != None:
                sqlList.append("height=?")
                updateTextParamList.append(height)
            if width != None:
                sqlList.append("width=?")
                updateTextParamList.append(width)
            if dataComId != None:
                sqlList.append("dataComId=?")
                updateTextParamList.append(dataComId.encode("gbk"))
            if showMode != None:
                sqlList.append("showMode=?")
                updateTextParamList.append(showMode)
            if layer != None:
                sqlList.append("layer=?")
                updateTextParamList.append(layer)
            if align != None:
                sqlList.append("align=?")
                updateTextParamList.append(align)
            if bindstring != None:
                sqlList.append("bindstring=?")
                updateTextParamList.append(bindstring.encode("gbk"))
            if dataComTime != None:
                sqlList.append("dataComTime=?")
                updateTextParamList.append(dataComTime.encode("gbk"))
            if dataComTimeArrayPoint != None:
                sqlList.append("dataComTimeArrayPoint=?")
                updateTextParamList.append(dataComTimeArrayPoint.encode("gbk"))
            if unitproperty01 != None:
                sqlList.append("unitproperty01=?")
                updateTextParamList.append(nUnitproperty01)
            if unitproperty02 != None:
                sqlList.append("unitproperty02=?")
                updateTextParamList.append(unitproperty02)
            if unitproperty05 != None:
                sqlList.append("unitproperty05=?")
                updateTextParamList.append(unitproperty05.encode("gbk"))
            if decimalplace != None:
                sqlList.append("decimalplace=?")
                updateTextParamList.append(decimalplace)
            if hideScript != None:
                sqlList.append("hideScript=?")
                updateTextParamList.append(hideScript.encode("gbk"))
            if unit != None:
                sqlList.append("unitproperty04=?")
                updateTextParamList.append(unit.encode("gbk"))

            sqlUpdateText += ",".join(sqlList)
            sqlUpdateText += " WHERE id=? AND pageid=?"
            updateTextParamList.append(nTextId)
            updateTextParamList.append(nPageId)

            updateTextList.append(
                (sqlUpdateText, updateTextParamList)
            )
        # 修改自定义组件
        elif item.get("typeTag") == "customControls":
            nCustId = item.get("id", None)
            xpos = item.get("x", 0)
            ypos = item.get("y", 0)
            height = item.get("height", 418)
            width = item.get("width", 756)
            layer = item.get("layer", 4)
            strConfig = item.get("config", "{}")

            if not isinstance(nCustId, int):
                return jsonify(dict(err=1, msg="待修改的自定义组件id必须为整数", data=False))

            if xpos != None:
                if not isinstance(xpos, int):
                    return jsonify(dict(err=1, msg="待修改自定义组件的横坐标初始值必须为整数", data=False))

            if ypos != None:
                if not isinstance(ypos, int):
                    return jsonify(dict(err=1, msg="待修改自定义组件的纵坐标初始值必须为整数", data=False))

            if height != None:
                if not isinstance(height, int):
                    return jsonify(dict(err=1, msg="待修改自定义组件的高度初始值必须为整数", data=False))
                if height < 0 or height > 955:
                    return jsonify(dict(err=1, msg="待修改自定义组件的高度超限", data=False))

            if width != None:
                if not isinstance(width, int):
                    return jsonify(dict(err=1, msg="待修改自定义组件的宽度初始值必须为整数", data=False))
                if width < 0 or width > 1920:
                    return jsonify(dict(err=1, msg="待修改自定义组件的宽度超限", data=False))

            if layer != None:
                if not isinstance(layer, int):
                    return jsonify(dict(err=1, msg="待修改自定义组件的图层必须为整数", data=False))
                if layer < 0 or layer > 9:
                    return jsonify(dict(err=1, msg="待修改自定义组件的图层必须在0-9之间", data=False))

            if strConfig != None:
                if not isinstance(strConfig, str):
                    return jsonify(dict(err=1, msg="待修改自定义组件的配置内容必须为字符串", data=False))
                if not len(strConfig):
                    return jsonify(dict(err=1, msg="待修改自定义组件的配置内容不能为空", data=False))
                try:
                    dConfigJson = json.loads(strConfig)
                except:
                    return jsonify(dict(err=1, msg="待修改自定义组件的配置内容必须为json格式", data=False))

            if xpos == None and ypos == None and height == None and width == None and layer == None and strConfig == None:
                continue

            sqlList = []
            updateCustParamList = []
            sqlUpdateCust = "UPDATE list_unit19 SET "

            if xpos != None:
                sqlList.append("x=?")
                updateCustParamList.append(xpos)
            if ypos != None:
                sqlList.append("y=?")
                updateCustParamList.append(ypos)
            if height != None:
                sqlList.append("height=?")
                updateCustParamList.append(height)
            if width != None:
                sqlList.append("width=?")
                updateCustParamList.append(width)
            if layer != None:
                sqlList.append("layer=?")
                updateCustParamList.append(layer)
            if strConfig != None:
                sqlList.append("unitproperty02=?")
                updateCustParamList.append(strConfig.encode("gbk"))

            sqlUpdateCust += ",".join(sqlList)
            sqlUpdateCust += " WHERE id=? AND pageid=? AND unitproperty01='generalComponent'"
            updateCustParamList.append(nCustId)
            updateCustParamList.append(nPageId)

            updateCustList.append(
                (sqlUpdateCust, updateCustParamList)
            )

        # 修改button
        elif item.get("typeTag") == "button":
            nBtnId = item.get("id", None)
            preCheckScript = item.get("PreCheckScript", None)  # 按键点击后的预检脚本
            preCheckScriptDescription = item.get("PreCheckScriptDescription", None)  # 按键点击后的预检脚本提示
            strStyle = item.get("style", None)
            link = item.get("link", -1)
            nX = item.get("x", None)
            nY = item.get("y", None)
            width = item.get("width", None)
            height = item.get("height", None)
            layer = item.get("layer", None)
            setValue = item.get("setValue", None)
            setPoint = item.get("idCom", None)
            textContent = item.get("text", None)
            fontColor = item.get("fontColor", None)
            fontSize = item.get("fontSize", 16)
            description = item.get("description", "")
            relation = item.get("relation", [])  # 按键有效性判断逻辑
            relationType = item.get("relatType", "0")
            downloadEnableCondition = item.get("downloadEnableCondition", "")
            downloadURL = item.get("downloadURL", "")
            hideScript = item.get("hideScript", "")

            if not isinstance(nBtnId, int):
                return jsonify(dict(err=1, msg="待修改按键的id必须为整数", data=False))

            if preCheckScript != None or preCheckScriptDescription != None:
                if not isinstance(preCheckScript, str) or not isinstance(preCheckScriptDescription, str):
                    return jsonify(dict(err=1, msg="待修改按键的按键点击后的预检脚本及提示脚本必须为字符串", data=False))

            if strStyle != None:
                if not isinstance(strStyle, str):
                    return jsonify(dict(err=1, msg="待修改按键风格必须为字符串", data=False))
                if not len(strStyle):
                    return jsonify(dict(err=1, msg="待修改按键风格不能为空", data=False))
                if strStyle not in dBtnImgStyleType.keys():
                    return jsonify(dict(err=1, msg="待修改按键风格{strStyle}不存在".format(strStyle=strStyle), data=False))

            if link != None:
                if not isinstance(link, int):
                    return jsonify(dict(err=1, msg="待修改按键点击后跳转的页面id必须为整数", data=False))
                if link not in nPageIdList and link != -1:
                    return jsonify(dict(err=1, msg="待修改按键点击后跳转的页面id不存在", data=False))
                if link == nPageId:
                    return jsonify(dict(err=1, msg="待修改按键点击时的跳转页面id({id})不能等于本页面id".format(id=link), data=False))

            if nX != None:
                if not isinstance(nX, int):
                    return jsonify(dict(err=1, msg="待修改的按键的横坐标初始值必须为整数", data=False))

            if nY != None:
                if not isinstance(nY, int):
                    return jsonify(dict(err=1, msg="待修改按键的纵坐标初始值必须为整数", data=False))

            if height != None:
                if not isinstance(height, int):
                    return jsonify(dict(err=1, msg="待修改按键的高度初始值必须为整数", data=False))
                if height < 0 or height > 955:
                    return jsonify(dict(err=1, msg="待修改按键的高度超限", data=False))

            if width != None:
                if not isinstance(width, int):
                    return jsonify(dict(err=1, msg="待修改按键的宽度初始值必须为整数", data=False))
                if width < 0 or width > 1920:
                    return jsonify(dict(err=1, msg="待修改按键的宽度超限", data=False))

            if layer != None:
                if not isinstance(layer, int):
                    return jsonify(dict(err=1, msg="待修改按键的图层必须为整数", data=False))
                if layer < 0 or layer > 9:
                    return jsonify(dict(err=1, msg="待修改按键的图层必须在0-9之间", data=False))

            if setValue != None:
                if not isinstance(setValue, str) and not isinstance(setValue, float) and not isinstance(setValue, int):
                    return jsonify(dict(err=1, msg="待修改按键点击后的写值内容必须为字符串或整数或浮点", data=False))
            if setPoint != None:
                if not isinstance(setPoint, str):
                    return jsonify(dict(err=1, msg="待修改按键点击后的写值点必须为字符串", data=False))

            if textContent != None:
                if not isinstance(textContent, str):
                    return jsonify(dict(err=1, msg="待修改按键的文本内容必须为字符串", data=False))

            if fontColor != None:
                if not isinstance(fontColor, dict):
                    return jsonify(dict(err=1, msg="待修改按键的颜色必须为字典", data=False))
                if not isinstance(fontColor.get("r", None), int):
                    return jsonify(dict(err=1, msg="待修改按键的颜色r必须为整数", data=False))
                if not isinstance(fontColor.get("g", None), int):
                    return jsonify(dict(err=1, msg="待修改按键的颜色g必须为整数", data=False))
                if not isinstance(fontColor.get("b", None), int):
                    return jsonify(dict(err=1, msg="待修改按键的颜色b必须为整数", data=False))

            if fontSize != None:
                if not isinstance(fontSize, int):
                    return jsonify(dict(err=1, msg="待修改按键的字体大小必须为整数", data=False))
                if fontSize < 5 or fontSize > 100:
                    return jsonify(dict(err=1, msg="待修改按键的字体大小必须在5-100之间", data=False))

            if description != None:
                if not isinstance(description, str):
                    return jsonify(dict(err=1, msg="待修改按键点击之后的操作记录描述文本必须为字符串", data=False))

            relationList = []
            if relation != None:
                if not isinstance(relation, list):
                    return jsonify(dict(err=1, msg="待修改按键有效性判断逻辑必须为数组", data=False))
                if len(relation):
                    for oneRelation in relation:
                        pointName = oneRelation.get("point", "")
                        if not pointName:
                            return jsonify(dict(err=1, msg="待修改按键的有效性判断中缺少点名", data=False))
                        logical = oneRelation.get("type", 0)
                        if not is_int_digit(logical):
                            return jsonify(dict(err=1, msg="待修改按键的有效性判断的逻辑判断符必须为整数或整数字符串", data=False))

                        if int(logical) not in [0, 1, 2, 3, 4, 5]:
                            return jsonify(dict(err=1, msg="待修改按键的有效性判断的逻辑判断符必须在0-5之间", data=False))

                        pointValue = oneRelation.get("value", None)
                        if pointValue == None:
                            return jsonify(dict(err=1, msg="待修改按键的有效性判断中缺少点值", data=False))
                        relationList.append("{pointName}|{logical}|{pointValue}".format(pointName=pointName, logical=logical,pointValue=pointValue))

            if relationType != None:
                if not isinstance(relationType, str):
                    return jsonify(dict(err=1, msg="待修改按键有效性判断逻辑类型必须为字符串", data=False))
                if relationType not in ["0", "1"]:
                    return jsonify(dict(err=1, msg="待修改按键有效性判断逻辑类型必须为0或1", data=False))
            if downloadEnableCondition != None:
                if not isinstance(downloadEnableCondition, str):
                    return jsonify(dict(err=1, msg="待修改按键下载使能内容必须为字符串", data=False))
            if downloadURL != None:
                if not isinstance(downloadURL, str):
                    return jsonify(dict(err=1, msg="待修改按键下载文件标识必须为字符串", data=False))
            if hideScript != None:
                if not isinstance(hideScript, str):
                    return jsonify(dict(err=1, msg="待修改按键隐藏脚本必须为字符串", data=False))

            if preCheckScript == None and preCheckScriptDescription == None and comm == None and over == None and down == None and disable == None \
                    and link == None and nX == None and nY == None and height == None and width == None and layer == None and setValue == None and \
                    setPoint == None and textContent == None and fontColor == None and fontSize == None and description == None and relation == None and \
                    relationType == None and downloadEnableCondition == None and downloadURL == None and hideScript == None:
                continue

            sqlList = []
            updateButtonParamList = []
            sqlUpdateButton = "UPDATE list_button SET "
            if preCheckScript != None or preCheckScriptDescription != None:
                dPreCheck = {"PreCheckScript": preCheckScript, "PreCheckScriptDescription": preCheckScriptDescription}
                sqlList.append("name=?")
                updateButtonParamList.append(json.dumps(dPreCheck).encode("gbk"))

            if strStyle != None:
                nComm = dBtnImgStyleType.get(strStyle, {}).get("comm", None)
                nOver = dBtnImgStyleType.get(strStyle, {}).get("over", None)
                nDown = dBtnImgStyleType.get(strStyle, {}).get("down", None)
                nDisabled = dBtnImgStyleType.get(strStyle, {}).get("disabled", None)

                if not isinstance(nComm, int) or not isinstance(nOver, int) or not isinstance(nDown, int) or not isinstance(nDisabled, int):
                    return jsonify(dict(err=1, msg="待修改按键各风格图片id有误，请先升级后台", data=False))

                sqlList.append("comm=?")
                updateButtonParamList.append(nComm)

                sqlList.append("over=?")
                updateButtonParamList.append(nOver)

                sqlList.append("down=?")
                updateButtonParamList.append(nDown)

                sqlList.append("disable=?")
                updateButtonParamList.append(nDisabled)

                sqlList.append("sourceType=?")
                updateButtonParamList.append(strStyle.encode("gbk"))

            if link != None:
                sqlList.append("link=?")
                updateButtonParamList.append(link)
            if nX != None:
                sqlList.append("x=?")
                updateButtonParamList.append(nX)
            if nY != None:
                sqlList.append("y=?")
                updateButtonParamList.append(nY)
            if width != None:
                sqlList.append("width=?")
                updateButtonParamList.append(width)
            if height != None:
                sqlList.append("height=?")
                updateButtonParamList.append(height)
            if layer != None:
                sqlList.append("layer=?")
                updateButtonParamList.append(layer)
            if setValue != None:
                sqlList.append("settingvalue=?")
                updateButtonParamList.append(str(setValue).encode("gbk"))
            if setPoint != None:
                sqlList.append("settingpoint=?")
                updateButtonParamList.append(setPoint.encode("gbk"))
            if textContent != None:
                sqlList.append("textcontent=?")
                updateButtonParamList.append(textContent.encode("gbk"))
            if fontColor != None:
                nFontColor = get_int_from_rgb(fontColor.get("r"), fontColor.get("g"), fontColor.get("b"))
                sqlList.append("textcolor=?")
                updateButtonParamList.append(nFontColor)
            if fontSize != None:
                sqlList.append("textsize=?")
                updateButtonParamList.append(fontSize)
            if description != None:
                sqlList.append("description=?")
                updateButtonParamList.append(description.encode("gbk"))
            if relation != None:
                sqlList.append("unitproperty01=?")
                updateButtonParamList.append(",".join(relationList).encode("gbk"))
            if relationType != None:
                sqlList.append("unitproperty02=?")
                updateButtonParamList.append(relationType.encode("gbk"))
            if downloadEnableCondition != None:
                sqlList.append("unitproperty04=?")
                updateButtonParamList.append(downloadEnableCondition.encode("gbk"))
            if downloadURL != None:
                sqlList.append("unitproperty05=?")
                updateButtonParamList.append(downloadURL.encode("gbk"))
            if hideScript != None:
                sqlList.append("hideScript=?")
                updateButtonParamList.append(hideScript.encode("gbk"))

            sqlUpdateButton += ",".join(sqlList)
            sqlUpdateButton += " WHERE id=? AND pageid=?"
            updateButtonParamList.append(nBtnId)
            updateButtonParamList.append(nPageId)

            updateButtonList.append(
                (sqlUpdateButton, updateButtonParamList)
            )

        # 修改checkbox
        elif item.get("typeTag") == "checkbox":
            nCheckBoxId = item.get("id", None)
            nX = item.get("x", None)
            nY = item.get("y", None)
            width = item.get("width", None)
            height = item.get("height", None)
            layer = item.get("layer", None)
            nType = item.get("type", None)  # 0-单选 1-多选
            fontColor = item.get("fontColor", None)
            fontSize = item.get("fontSize", None)
            setValue = item.get("setValue", None)
            unsetValue = item.get("unsetValue", None)
            idCom = item.get("idCom", None)
            strText = item.get("text", None)
            idGroup = item.get("idGroup", None)
            strExpression = item.get("expression", None)
            desc = item.get("desc", None)

            if not isinstance(nCheckBoxId, int):
                return jsonify(dict(err=1, msg="待修改checkbox的id必须为整数", data=False))

            if nX != None:
                if not isinstance(nX, int):
                    return jsonify(dict(err=1, msg="待修改的checkbox的横坐标初始值必须为整数", data=False))

            if nY != None:
                if not isinstance(nY, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的纵坐标初始值必须为整数", data=False))

            if height != None:
                if not isinstance(height, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的高度初始值必须为整数", data=False))
                if height < 0 or height > 955:
                    return jsonify(dict(err=1, msg="待修改checkbox的高度超限", data=False))

            if width != None:
                if not isinstance(width, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的宽度初始值必须为整数", data=False))
                if width < 0 or width > 1920:
                    return jsonify(dict(err=1, msg="待修改checkbox的宽度超限", data=False))

            if layer != None:
                if not isinstance(layer, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的图层必须为整数", data=False))
                if layer < 0 or layer > 9:
                    return jsonify(dict(err=1, msg="待修改checkbox的图层必须在0-9之间", data=False))

            if nType != None:
                if not is_int_digit(nType):
                    return jsonify(dict(err=1, msg="待修改checkbox的类型必须为整数或整数字符串", data=False))
                if int(nType) not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改checkbox的类型必须为0或1", data=False))

            if fontColor != None:
                if not isinstance(fontColor, dict):
                    return jsonify(dict(err=1, msg="待修改checkbox的颜色必须为字典", data=False))
                if not isinstance(fontColor.get("r", None), int):
                    return jsonify(dict(err=1, msg="待修改checkbox的颜色r必须为整数", data=False))
                if not isinstance(fontColor.get("g", None), int):
                    return jsonify(dict(err=1, msg="待修改checkbox的颜色g必须为整数", data=False))
                if not isinstance(fontColor.get("b", None), int):
                    return jsonify(dict(err=1, msg="待修改checkbox的颜色b必须为整数", data=False))

            if fontSize != None:
                if not is_int_digit(fontSize):
                    return jsonify(dict(err=1, msg="待修改checkbox的字体大小必须为整数或整数字符串", data=False))
                if int(fontSize) < 5 or int(fontSize) > 100:
                    return jsonify(dict(err=1, msg="待修改checkbox的字体大小必须在5-100之间", data=False))

            if setValue != None:
                if not isinstance(setValue, str) and not isinstance(setValue, float) and not isinstance(setValue, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的选中赋值必须为字符串或浮点或整数", data=False))
            if unsetValue != None:
                if not isinstance(unsetValue, str) and not isinstance(unsetValue, float) and not isinstance(unsetValue, int):
                    return jsonify(dict(err=1, msg="待修改checkbox的非选中赋值必须为字符串或浮点或整数", data=False))

            if idCom != None:
                if not isinstance(idCom, str):
                    return jsonify(dict(err=1, msg="待修改checkbox的绑定点位必须为字符串", data=False))
            if strText != None:
                if not isinstance(strText, str):
                    return jsonify(dict(err=1, msg="待修改checkbox的选项名称必须为字符串", data=False))
            if idGroup != None:
                if not is_int_digit(idGroup):
                    return jsonify(dict(err=1, msg="待修改checkbox的组号必须为整数或整数字符串", data=False))

            if strExpression != None:
                if not isinstance(strExpression, str):
                    return jsonify(dict(err=1, msg="待修改checkbox的有效状态属性必须为字符串", data=False))

            if desc != None:
                if not isinstance(desc, str):
                    return jsonify(dict(err=1, msg="待修改checkbox的选项描述必须为字符串", data=False))

            if nX == None and nY == None and height == None and width == None and layer == None and nType == None and fontColor == None and fontSize == None and setValue == None \
                and unsetValue == None and idCom == None and strText == None and idGroup == None and strExpression == None and desc == None:
                continue

            sqlList = []
            updateCheckboxParamList = []
            sqlUpdateCheckbox = "UPDATE list_unit07 SET "

            if nX != None:
                sqlList.append("x=?")
                updateCheckboxParamList.append(nX)
            if nY != None:
                sqlList.append("y=?")
                updateCheckboxParamList.append(nY)
            if height != None:
                sqlList.append("height=?")
                updateCheckboxParamList.append(height)
            if width != None:
                sqlList.append("width=?")
                updateCheckboxParamList.append(width)
            if layer != None:
                sqlList.append("layer=?")
                updateCheckboxParamList.append(layer)
            if nType != None:
                sqlList.append("unitproperty01=?")
                updateCheckboxParamList.append(str(nType).encode("gbk"))
            if fontColor != None:
                nFontColor = get_int_from_rgb(fontColor.get("r"), fontColor.get("g"), fontColor.get("b"))
                sqlList.append("unitproperty02=?")
                updateCheckboxParamList.append(str(nFontColor).encode("gbk"))
            if fontSize != None:
                sqlList.append("unitproperty03=?")
                updateCheckboxParamList.append(str(fontSize).encode("gbk"))
            if setValue != None:
                sqlList.append("unitproperty04=?")
                updateCheckboxParamList.append(str(setValue).encode("gbk"))
            if unsetValue != None:
                sqlList.append("unitproperty05=?")
                updateCheckboxParamList.append(str(unsetValue).encode("gbk"))
            if idCom != None:
                sqlList.append("unitproperty06=?")
                updateCheckboxParamList.append(str(idCom).encode("gbk"))
            if strText != None:
                sqlList.append("unitproperty07=?")
                updateCheckboxParamList.append(str(strText).encode("gbk"))
            if idGroup != None:
                sqlList.append("unitproperty08=?")
                updateCheckboxParamList.append(str(idGroup).encode("gbk"))
            if strExpression != None:
                sqlList.append("unitproperty09=?")
                updateCheckboxParamList.append(str(strExpression).encode("gbk"))
            if desc != None:
                sqlList.append("unitproperty10=?")
                updateCheckboxParamList.append(str(desc).encode("gbk"))

            sqlUpdateCheckbox += ",".join(sqlList)
            sqlUpdateCheckbox += " WHERE id=? AND pageid=?"
            updateCheckboxParamList.append(nCheckBoxId)
            updateCheckboxParamList.append(nPageId)

            updateCheckboxList.append(
                (sqlUpdateCheckbox, updateCheckboxParamList)
            )

        # 修改图片
        elif item.get("typeTag") == "image":
            nImageId = item.get("id", None)
            nX = item.get("x", None)
            nY = item.get("y", None)
            width = item.get("width", None)
            height = item.get("height", None)
            layer = item.get("layer", None)
            bindPoint = item.get("idCom", None)
            rotateAngle = item.get("rotate", None)
            pictureId = item.get("idPicture", None)
            bindType = item.get("bindType", None)
            elementName = item.get("name", None)
            hideScript = item.get("hideScript", None)
            bindEnumList = item.get("bindEnumList", None)
            eventBindPoint = item.get("eventBindPoint", None)  # 绑定事件点
            eventEquipType = item.get("eventEquipType", None)  # 事件设备类型
            eventType = item.get("eventType", None)  # 事件类型
            eventEquipName = item.get("eventEquipName", None)  # 事件设备名称
            eventInnerLink = item.get("eventInnerLink", None)  # 事件跳转内部页面id
            eventOuterLink = item.get("eventOuterLink", None)
            nFromDomLib = item.get("fromDomLib", 0)   # 图片是否来自图库(DOMImageLib.4db) 1-是  0-否
            customName = item.get("customName", None)

            nPicId = None

            if not isinstance(nImageId, int):
                return jsonify(dict(err=1, msg="待修改图片的id必须为整数", data=False))

            if nX != None:
                if not isinstance(nX, int):
                    return jsonify(dict(err=1, msg="待修改图片的横坐标初始值必须为整数", data=False))
            if nY != None:
                if not isinstance(nY, int):
                    return jsonify(dict(err=1, msg="待修改图片的纵坐标初始值必须为整数", data=False))

            if height != None:
                if not isinstance(height, int):
                    return jsonify(dict(err=1, msg="待修改图片的高度初始值必须为整数", data=False))
                if height < 0 or height > 955:
                    return jsonify(dict(err=1, msg="待修改图片的高度超限", data=False))
            if width != None:
                if not isinstance(width, int):
                    return jsonify(dict(err=1, msg="待修改图片的宽度初始值必须为整数", data=False))
                if width < 0 or width > 1920:
                    return jsonify(dict(err=1, msg="待修改图片的宽度超限", data=False))

            if layer != None:
                if not isinstance(layer, int):
                    return jsonify(dict(err=1, msg="待修改图片的图层必须为整数", data=False))
                if layer < 0 or layer > 9:
                    return jsonify(dict(err=1, msg="待修改图片的图层必须在0-9之间", data=False))
            if bindPoint != None:
                if not isinstance(bindPoint, str):
                    return jsonify(dict(err=1, msg="待修改图片绑点必须为字符串", data=False))

            if rotateAngle != None:
                if not isinstance(rotateAngle, int) and not isinstance(rotateAngle, float):
                    return jsonify(dict(err=1, msg="待修改图片的旋转角度必须为浮点或整数", data=False))

            if pictureId != None:
                if not isinstance(pictureId, int):
                    return jsonify(dict(err=1, msg="待修改图片的id必须为整数", data=False))

                if nFromDomLib == 1:
                    if pictureId not in dAllImages.keys():
                        return jsonify(dict(err=1, msg="待修改图片的id不存在于图库中", data=False))
                else:
                    if pictureId not in dAllImagesDomdb.keys():
                        return jsonify(dict(err=1, msg="待修改图片的id不存在于domdb.4db中", data=False))

                if nFromDomLib == 1:
                    nPicId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(pictureId)
                    if nPicId == None:
                        return jsonify(dict(err=1, msg="待修改图片时将图片插入lib_image失败:%s" % msg, data=False))
                else:
                    nPicId = pictureId

            if bindType != None:
                if not is_int_digit(bindType):
                    return jsonify(dict(err=1, msg="待修改图片的绑点判断类型（点/脚本)必须为整数或整数字符串", data=False))
                if int(bindType) not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改图片的绑点判断类型（点/脚本)必须为整数0或1", data=False))

            if elementName != None:
                if not isinstance(elementName, str):
                    return jsonify(dict(err=1, msg="待修改图片元素名称必须为字符串", data=False))
            if hideScript != None:
                if not isinstance(hideScript, str):
                    return jsonify(dict(err=1, msg="待修改图片的隐藏脚本必须为字符串", data=False))

            strBindEnumList = []
            if bindEnumList != None:
                if not isinstance(bindEnumList, list):
                    return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量配置必须为列表", data=False))

                for bindEnum in bindEnumList:
                    if bindEnum.get("fromDomLib", None) not in [0, 1]:
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量id来源不能为空且只能为0或1", data=False))

                    # 0-表示元素已存在于domdb.4db中无需从DOMImageLib.4db获取,且bindEnum.get("id")为nBindEnumItemId
                    # 1-表示需要从DOMImageLib.4db获取
                    nFromDomLib = bindEnum.get("fromDomLib")

                    if bindEnum.get("value", None) == None:
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量点值不能为空", data=False))
                    if not is_int_digit(bindEnum.get("value")):
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量点值必须为整数或整数字符串", data=False))
                    if bindEnum.get("id", None) == None:
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量图片id不能为空", data=False))
                    if not isinstance(bindEnum.get("id"), int):
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量图片id必须为整数", data=False))

                    if not isinstance(bindEnum.get("interval", None), int):
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量时间间隔必须为整数", data=False))

                    nEnumType = bindEnum.get("type", 0)  # 0-图片  1-动画
                    if nEnumType not in [0, 1]:
                        return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量对象类型必须为0或1", data=False))

                    # 只有需要从DOMImageLib.4db获取时才判断是否存在于图库中
                    if nFromDomLib:
                        if nEnumType == 0:
                            if bindEnum.get("id") not in dAllImages.keys():
                                return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量图片id不存在:{id}".format(id=bindEnum.get("id")), data=False))
                        elif nEnumType == 1:
                            if bindEnum.get("id") not in dAllAnimations.keys():
                                return jsonify(dict(err=1, msg="待修改动画的绑点对应的枚举量动画id不存在:{id}".format(id=bindEnum.get("id")), data=False))

                    nFrame = 1  # 帧（图片-1  动画-动画中包含的图片数量）
                    nBindEnumItemId = None

                    if nEnumType == 0:

                        # 只有需要从DOMImageLib.4db中获取时才执行一次搬运
                        # bindEnum.get("id"): 当nFromDomLib=1时（需要从DomImageLib.4db搬运过来）则为图库（DomImageLib.4db中的图片id), 当当nFromDomLib=1时（无需搬运）则为domdb.4db中的图片id
                        # nBindEnumItemId: domdb.4db中的图片id或动画id
                        if nFromDomLib == 1:
                            nBindEnumItemId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(bindEnum.get("id"))
                            if nBindEnumItemId == None:
                                return jsonify(dict(err=1, msg="待修改图片时将枚举量图片存入domdb.4db时失败:%s" % msg, data=False))
                        else:
                            nBindEnumItemId = bindEnum.get("id")

                    elif nEnumType == 1:
                        if nFromDomLib == 1: # 只有需要从DOMImageLib.4db中获取时才执行一次搬运
                            nBindEnumItemId, nFrame, msg = BEOPSqliteAccess.getInstance().copyAnimationFromDomLibImage(bindEnum.get("id"))  # bindEnum.get("id"):  存在于dodmb.4db lib_image表中的图片id
                            if nBindEnumItemId == None:
                                return jsonify(dict(err=1, msg="待修改图片时将枚举量动画存入domdb.4db时失败:%s" % msg, data=False))
                        else:
                            nBindEnumItemId = bindEnum.get("id")
                            nStatus, value, nId, nFrame, nInterval, msg = BEOPSqliteAccess.getInstance().getBindContentOnElement(nPageId, nImageId, nBindEnumItemId)
                            if nStatus != 1:
                                return jsonify(dict(err=1, msg="待修改图片时将枚举量动画存入domdb.4db时失败:%s" % msg, data=False))

                    strBindEnumList.append("{value},{id},{frame},{interval}".format(value=bindEnum.get("value"), id=nBindEnumItemId,
                                                                 frame=nFrame, interval=bindEnum.get("interval", 0)))

            if len(strBindEnumList) > 20:
                return jsonify(dict(err=1, msg="待修改图片的绑点对应的枚举量数量最大不能超过20个", data=False))

            if eventBindPoint != None:
                if not isinstance(eventBindPoint, str):
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件点名必须为字符串", data=False))

            if eventEquipType != None:
                if not is_int_digit(eventEquipType):
                    return jsonify(dict(err=1, msg="新增图片的绑定事件设备类型必须为整数或整数字符串", data=False))
                if int(eventEquipType) < 0 or int(eventEquipType) > 12:
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件设备类型范围必须为0-12", data=False))
            if eventType != None:
                if not is_int_digit(eventType):
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件的类型必须为整数或整数字符串", data=False))
                if int(eventType) < 0 or int(eventType) > 5:
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件类型范围必须为0-5", data=False))

            if eventEquipName != None:
                if not isinstance(eventEquipName, str):
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件设备名称必须为字符串", data=False))

            if eventInnerLink != None:
                if not isinstance(eventInnerLink, int):
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件跳转页面id必须为整数", data=False))
                if eventInnerLink not in nPageIdList and eventInnerLink != -1:
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件跳转页面id不存在:{id}".format(id=eventInnerLink), data=False))

            if eventOuterLink != None:
                if not isinstance(eventOuterLink, str):
                    return jsonify(dict(err=1, msg="待修改图片的绑定事件跳转外部链接必须为字符串", data=False))

            if customName != None:
                if not isinstance(customName, str):
                    return jsonify(dict(err=1, msg="待修改图片的用户自定义名称必须为字符串", data=False))

            if nX == None and nY == None and width == None and height == None and layer == None and bindPoint == None and rotateAngle == None and pictureId ==None \
                    and bindType == None and elementName == None and hideScript == None and bindEnumList == None and eventBindPoint == None and eventEquipType == None and \
                    eventType == None and eventEquipName == None and eventInnerLink == None and eventOuterLink == None and customName == None:
                continue

            sqlList = []
            updateImageParamList = []
            sqlUpdateImage = "UPDATE page_contain_elements SET "

            if nX != None:
                sqlList.append("x=?")
                updateImageParamList.append(nX)
            if nY != None:
                sqlList.append("y=?")
                updateImageParamList.append(nY)
            if width != None:
                sqlList.append("width=?")
                updateImageParamList.append(width)
            if height != None:
                sqlList.append("hight=?")
                updateImageParamList.append(height)
            if layer != None:
                sqlList.append("layer=?")
                updateImageParamList.append(layer)
            if bindPoint != None:
                sqlList.append("DataComId=?")
                updateImageParamList.append(bindPoint.encode("gbk"))
            if rotateAngle != None:
                sqlList.append("rotateAngle=?")
                updateImageParamList.append(rotateAngle)
            if pictureId != None:
                sqlList.append("pictureid=?")
                updateImageParamList.append(nPicId)
            if bindType != None:
                sqlList.append("unitproperty03=?")
                updateImageParamList.append(str(bindType).encode("gbk"))
            if elementName != None:
                sqlList.append("elementName=?")
                updateImageParamList.append(elementName.encode("gbk"))
            if hideScript != None:
                sqlList.append("hideScript=?")
                updateImageParamList.append(hideScript.encode("gbk"))
            if customName != None:
                sqlList.append("unitproperty04=?")
                updateImageParamList.append(customName.encode("gbk"))

            if eventBindPoint != None or eventEquipType != None or eventType != None or eventInnerLink != None or eventEquipName != None or eventOuterLink != None:
                updateImageEventContentParamList.append(
                    (nPageId, nImageId, eventBindPoint, eventEquipType, eventType, "1", eventInnerLink, "-99", eventEquipName, eventOuterLink)
                )

            if bindEnumList != None:
                strBindContent = "|".join(strBindEnumList)
                updateImageBindContentParamList.append(
                    (nPageId, nImageId, strBindContent.encode("gbk"))
                )

            if len(sqlList):
                sqlUpdateImage += ",".join(sqlList)
                sqlUpdateImage += " WHERE elementtype=49 AND elementid=? AND pageid=?"
                updateImageParamList.append(nImageId)
                updateImageParamList.append(nPageId)

                updateImageList.append(
                    (sqlUpdateImage, updateImageParamList)
                )

        # 修改管道
        elif item.get("typeTag") == "line":
            nLineId = item.get("id", None)
            nDirection = item.get("direction", None)  # 0-正向  1-反向
            dColor = item.get("color", None)
            nStartX = item.get("startX", None)
            nStartY = item.get("startY", None)
            nEndX = item.get("endX", None)
            nEndY = item.get("endY", None)
            nWidth = item.get("width", None)
            nLayer = item.get("layer", None)
            nLogic = item.get("logic", None)
            idlist = item.get("idCom", None)
            nWaterType = item.get("waterType", None)
            nDenSity = item.get("denSity", None)
            nSpeed = item.get("speed", None)
            nWaterShape = item.get("waterShape", None)

            if not isinstance(nLineId, int):
                return jsonify(dict(err=1, msg="待修改的管道 id必须为整数", data=False))

            if nDirection != None:
                if not is_int_digit(nDirection):
                    return jsonify(dict(err=1, msg="待修改管道的水流方向必须为整数或整数字符串", data=False))
                nDirection = int(nDirection)
                if nDirection not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改管道的水流方向必须为0或1", data=False))

            if dColor != None:
                if not isinstance(dColor, dict):
                    return jsonify(dict(err=1, msg="待修改管道的颜色必须为字典", data=False))
                if not isinstance(dColor.get("r", None), int):
                    return jsonify(dict(err=1, msg="待修改管道的颜色r必须为整数", data=False))
                if not isinstance(dColor.get("g", None), int):
                    return jsonify(dict(err=1, msg="待修改管道的颜色g必须为整数", data=False))
                if not isinstance(dColor.get("b", None), int):
                    return jsonify(dict(err=1, msg="待修改管道的颜色b必须为整数", data=False))
                if dColor.get("r") < 0 or dColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改管道rgb颜色范围为0-255", data=False))
                if dColor.get("g") < 0 or dColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改管道rgb颜色范围为0-255", data=False))
                if dColor.get("b") < 0 or dColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改管道rgb颜色范围为0-255", data=False))

            if nStartX != None or nStartY != None or nEndX != None or nEndY != None:
                if not isinstance(nStartX, int) or not isinstance(nStartY, int) or not isinstance(nEndX, int) or not isinstance(nEndY, int):
                    return jsonify(dict(err=1, msg="待修改管道起点和终点的坐标必须为整数", data=False))

            if nWidth != None:
                if not is_int_digit(nWidth):
                    return jsonify(dict(err=1, msg="待修改管道的宽度必须为整数或整数字符串", data=False))
                nWidth = int(nWidth)
                if nWidth > 14 or nWidth < 1:
                    return jsonify(dict(err=1, msg="待修改管道的宽度必须在1-14", data=False))

            if nLayer != None:
                if not isinstance(nLayer, int):
                    return jsonify(dict(err=1, msg="待修改管道的图层必须为整数", data=False))
                if nLayer < 0 or nLayer > 9:
                    return jsonify(dict(err=1, msg="待修改管道的图层必须在0-9之间", data=False))

            if nLogic != None:
                if not is_int_digit(nLogic):
                    return jsonify(dict(err=1, msg="待修改管道的水流逻辑关系必须为整数或整数字符串", data=False))
                nLogic = int(nLogic)
                if nLogic not in [0, 1, 2]:
                    return jsonify(dict(err=1, msg="待修改管道的水流逻辑关系必须为0或1或2", data=False))

            if idlist != None:
                if not isinstance(idlist, str):
                    return jsonify(dict(err=1, msg="待修改管道水流动画绑点必须为字符串", data=False))

            if nWaterType != None:
                if not is_int_digit(nWaterType):
                    return jsonify(dict(err=1, msg="待修改管道的水流类型必须为字符串或整数字符串", data=False))
                nWaterType = int(nWaterType)
                if nWaterType < 0 or nWaterType > 15:
                    return jsonify(dict(err=1, msg="待修改管道的水流类型必须在0-15", data=False))

            if nDenSity != None:
                if not is_int_digit(nDenSity):
                    return jsonify(dict(err=1, msg="待修改管道的水流密度必须为整数或整数字符串", data=False))
                nDenSity = int(nDenSity)
                if nDenSity < 0 or nDenSity > 4:
                    return jsonify(dict(err=1, msg="待修改管道的水流密度必须必须在0-4", data=False))

            if nSpeed != None:
                if not is_int_digit(nSpeed):
                    return jsonify(dict(err=1, msg="待修改管道的水流速度必须为整数或整数字符串", data=False))
                nSpeed = int(nSpeed)
                if nSpeed < 0 or nSpeed > 2:
                    return jsonify(dict(err=1, msg="待修改管道的水流速度必须必须在0-2", data=False))

            if nWaterShape != None:
                if not is_int_digit(nWaterShape):
                    return jsonify(dict(err=1, msg="待修改管道的水流形状必须为整数或整数字符串", data=False))
                nWaterShape = int(nWaterShape)
                if nWaterShape not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改管道的水流形状必须为0或1", data=False))

            if nDirection == None and dColor == None and nStartX == None and nStartY == None and nEndX == None and nEndY == None and nWidth == None \
                and nLayer == None and nLogic == None and idlist == None and nWaterType == None and nDenSity == None and nSpeed == None and nWaterShape == None:
                continue

            sqlList = []
            updateLineParamList = []
            sqlUpdateLine = "UPDATE list_line SET "

            if nDirection != None:
                sqlList.append("style=?")
                updateLineParamList.append(nDirection)
            if dColor != None:
                nInnerColor = get_int_from_rgb(dColor.get("r"), dColor.get("g"), dColor.get("b"))
                sqlList.append("innerColor=?")
                updateLineParamList.append(nInnerColor)
            if nStartX != None or nStartY != None or nEndX != None or nEndY != None:
                coordinator = "({startX},{startY});({endX},{endY});".format(startX=nStartX, startY=nStartY, endX=nEndX, endY=nEndY)
                sqlList.append("PointList=?")
                updateLineParamList.append(coordinator.encode("gbk"))

            if nWidth != None:
                sqlList.append("pipeWidth=?")
                updateLineParamList.append(nWidth)

            if nLayer != None:
                sqlList.append("layer=?")
                updateLineParamList.append(nLayer)

            if nLogic != None:
                sqlList.append("logic=?")
                updateLineParamList.append(nLogic)

            if idlist != None:
                sqlList.append("idlist=?")
                updateLineParamList.append(idlist.encode("gbk"))
            if nWaterType != None:
                sqlList.append("unitproperty01=?")
                updateLineParamList.append(str(nWaterType).encode("gbk"))
            if nDenSity != None:
                sqlList.append("unitproperty03=?")
                updateLineParamList.append(str(nDenSity).encode("gbk"))
            if nSpeed != None:
                sqlList.append("unitproperty04=?")
                updateLineParamList.append(str(nSpeed).encode("gbk"))
            if nWaterShape != None:
                sqlList.append("unitproperty05=?")
                updateLineParamList.append(str(nWaterShape).encode("gbk"))

            sqlUpdateLine += ",".join(sqlList)
            sqlUpdateLine += " WHERE id=? AND pageid=?"
            updateLineParamList.append(nLineId)
            updateLineParamList.append(nPageId)

            updateLineList.append(
                (sqlUpdateLine, updateLineParamList)
            )

        # 修改标准设备
        elif item.get("typeTag") == "systemEquipment":
            nSysEquipId = item.get("id", None)
            nX = item.get("x", 300)
            nY = item.get("y", 300)
            nWidth = item.get("width", 120)
            nHeight = item.get("height", 120)
            nLayer = item.get("layer", 4)
            nEntranceGroupId = item.get("entranceGroupId", None)
            nEntrancePageId = item.get("entrancePageId", None)
            templateName = item.get("templateName", None)
            placeHolder = item.get("placeHolder", None)
            templateFileName = item.get("templateFileName", None)
            customName = item.get("customName", None)

            if not isinstance(nSysEquipId, int):
                return jsonify(dict(err=1, msg="待修改的标准设备id必须为整数", data=False))

            if nX != None:
                if not isinstance(nX, int):
                    return jsonify(dict(err=1, msg="待修改的标准设备坐标必须为整数", data=False))
            if nY != None:
                if not isinstance(nY, int):
                    return jsonify(dict(err=1, msg="待修改的标准设备坐标必须为整数", data=False))
            if nWidth != None:
                if not isinstance(nWidth, int):
                    return jsonify(dict(err=1, msg="待修改的标准设备的宽度必须为整数", data=False))
            if nHeight != None:
                if not isinstance(nHeight, int):
                    return jsonify(dict(err=1, msg="待修改的标准设备的高度必须为整数", data=False))
            if nLayer != None:
                if not isinstance(nLayer, int):
                    return jsonify(dict(err=1, msg="待修改标准设备的图层必须为整数", data=False))
                if nLayer < 0 or nLayer > 9:
                    return jsonify(dict(err=1, msg="待修改标准设备的图层必须在0-9之间", data=False))
            if nEntranceGroupId != None:
                if not isinstance(nEntranceGroupId, int):
                    return jsonify(dict(err=1, msg="待修改标准设备的入口页面所在groupid必须为整数", data=False))
            if nEntrancePageId != None:
                if not isinstance(nEntrancePageId, int):
                    return jsonify(dict(err=1, msg="待修改标准设备的入口页面id必须为整数", data=False))
            if templateName != None:
                if not isinstance(templateName, str):
                    return jsonify(dict(err=1, msg="待修改标准设备的入口页面id必须为字符串", data=False))
                if not len(templateName):
                    return jsonify(dict(err=1, msg="待修改标准设备的入口页面id不能为空字符串", data=False))

            if placeHolder != None:
                if not isinstance(placeHolder, list):
                    return jsonify(dict(err=1, msg="待修改标准设备的占位符必须为数组", data=False))
            if templateFileName != None:
                if not isinstance(templateFileName, str):
                    return jsonify(dict(err=1, msg="待修改标准设备的模板文件名必须为字符串", data=False))
                if not len(templateFileName):
                    return jsonify(dict(err=1, msg="待修改标准设备的模板文件名不能为字符串", data=False))

            if customName != None:
                if not isinstance(customName, str):
                    return jsonify(dict(err=1, msg="待修改标准设备的用户自定义名称必须为字符串", data=False))

            if nX == None and nY == None and nWidth == None and nHeight == None and nLayer == None and nEntranceGroupId == None and \
                nEntrancePageId == None and templateName == None and placeHolder == None and templateFileName == None and customName == None:
                continue

            sqlList = []
            updateSysEquipParamList = []
            sqlUpdateSysEquip = "UPDATE list_unit13 SET "

            if nX != None:
                sqlList.append("x=?")
                updateSysEquipParamList.append(nX)
            if nY != None:
                sqlList.append("y=?")
                updateSysEquipParamList.append(nY)
            if nWidth != None:
                sqlList.append("width=?")
                updateSysEquipParamList.append(nWidth)
            if nHeight != None:
                sqlList.append("height=?")
                updateSysEquipParamList.append(nHeight)
            if nLayer != None:
                sqlList.append("layer=?")
                updateSysEquipParamList.append(nLayer)
            if nEntranceGroupId != None:
                sqlList.append("unitproperty03=?")
                updateSysEquipParamList.append(str(nEntranceGroupId).encode("gbk"))
            if nEntrancePageId != None:
                sqlList.append("unitproperty04=?")
                updateSysEquipParamList.append(str(nEntrancePageId).encode("gbk"))
            if templateName != None:
                sqlList.append("unitproperty05=?")
                updateSysEquipParamList.append(templateName.encode("gbk"))
            if placeHolder != None:
                sqlList.append("unitproperty06=?")
                updateSysEquipParamList.append(str(placeHolder).encode("gbk"))
            if templateFileName != None:
                sqlList.append("unitproperty07=?")
                updateSysEquipParamList.append(templateFileName.encode("gbk"))
            if customName != None:
                sqlList.append("unitproperty10=?")
                updateSysEquipParamList.append(customName.encode("gbk"))

            sqlUpdateSysEquip += ",".join(sqlList)
            sqlUpdateSysEquip += " WHERE id=? AND pageid=?"
            updateSysEquipParamList.append(nSysEquipId)
            updateSysEquipParamList.append(nPageId)

            updateSysEquipList.append(
                (sqlUpdateSysEquip, updateSysEquipParamList)
            )

        # 修改矩形框
        elif item.get("typeTag") == "rectangle":
            nRectId = item.get("id", None)
            nX = item.get("x", None)
            nY = item.get("y", None)
            nWidth = item.get("width", None)
            nHeight = item.get("height", None)
            nLayer = item.get("layer", None)
            dFrameColor = item.get("color", None)  # 边框颜色
            frameTrans = item.get("frameTrans", None)  # 边框透明度
            frameLineWidth = item.get("lineWidth", None)  # 边框线宽
            nFillOrNot = item.get("fillOrNot", None)  # 是否填充 0，1
            dFillColor = item.get("fillColor", None)
            fillTrans = item.get("fillTrans", None)  # 填充透明度
            nRoundOrNot = item.get("roundOrNot", None)  # 是否有圆角
            roundYPox = item.get("roundYPox", None)  # 圆角高度
            roundXPox = item.get("roundXPox", None)  # 圆角宽度
            rectStyle = item.get("rectStyle", None)
            titleColor = item.get("titleColor", None)
            titleTrans = item.get("titleTrans", None)
            titleSize = item.get("titleSize", None)
            bodyColor = item.get("bodyColor", None)
            bodySize = item.get("bodySize", None)
            bodyTrans = item.get("bodyTrans", None)
            descColor = item.get("descColor", None)
            descSize = item.get("descSize", None)
            descTrans = item.get("descTrans", None)
            descOrNot = item.get("descOrNot", None)
            bindPointList = item.get("pointList", None)
            title = item.get("title", None)

            if not isinstance(nRectId, int):
                return jsonify(dict(err=1, msg="待修改矩形框id必须为整数", data=False))
            if nRectId < 0:
                return jsonify(dict(err=1, msg="待修改矩形框id不能是负数", data=False))

            if nX != None:
                if not isinstance(nX, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的坐标必须为整数", data=False))

            if nY != None:
                if not isinstance(nY, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的坐标必须为整数", data=False))

            if nWidth != None:
                if not isinstance(nWidth, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的宽度必须为整数", data=False))
                if nWidth < 0 or nWidth > 1920:
                    return jsonify(dict(err=1, msg="待修改矩形框的宽度必须在0-1920", data=False))
            if nHeight != None:
                if not isinstance(nHeight, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的高度必须为整数", data=False))
                if nHeight < 0 or nHeight > 955:
                    return jsonify(dict(err=1, msg="待修改矩形框的高度必须在0-955", data=False))
            if nLayer != None:
                if not isinstance(nLayer, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的图层必须为整数", data=False))
                if nLayer < 0 or nLayer > 9:
                    return jsonify(dict(err=1, msg="待修改矩形框的图层必须在0-9之间", data=False))

            if dFrameColor != None:
                if dFrameColor.get("r") < 0 or dFrameColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框rgb颜色范围为0-255", data=False))
                if dFrameColor.get("g") < 0 or dFrameColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框rgb颜色范围为0-255", data=False))
                if dFrameColor.get("b") < 0 or dFrameColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框rgb颜色范围为0-255", data=False))
                if frameTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框的透明度不能为空", data=False))

            if frameTrans != None:
                if not isinstance(frameTrans, int) and not isinstance(frameTrans, float):
                    return jsonify(dict(err=1, msg="待修改矩形框的边框透明度必须为数字", data=False))
                if frameTrans < 0.0 or frameTrans > 100.0:
                    return jsonify(dict(err=1, msg="待修改矩形框的边框透明度必须在0-100", data=False))
                if dFrameColor == None:
                    return jsonify(dict(err=1, msg="待修改矩形框rgb颜色不能为空", data=False))

            if frameLineWidth != None:
                if not isinstance(frameLineWidth, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的边框透线宽必须为整数", data=False))
                if frameLineWidth < 0 or frameLineWidth > 14:
                    return jsonify(dict(err=1, msg="待修改矩形框的边框透线宽必须在0-14", data=False))

            if nFillOrNot != None:
                if nFillOrNot not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改矩形框的是否填充必须为整数0或1", data=False))

            if dFillColor != None:
                if dFillColor.get("r") < 0 or dFillColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框填充色范围为0-255", data=False))
                if dFillColor.get("g") < 0 or dFillColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框填充色范围为0-255", data=False))
                if dFillColor.get("b") < 0 or dFillColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框填充色范围为0-255", data=False))
                if fillTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框的填充透明度不能为空", data=False))

            if fillTrans != None:
                if not isinstance(fillTrans, int) and not isinstance(fillTrans, float):
                    return jsonify(dict(err=1, msg="待修改矩形框的填充透明度必须为数字", data=False))
                if fillTrans < 0.0 or fillTrans > 100.0:
                    return jsonify(dict(err=1, msg="待修改矩形框的填充透明度必须在0-100", data=False))
                if dFillColor == None:
                    return jsonify(dict(err=1, msg="待修改矩形框填充色不能为空", data=False))

            if nRoundOrNot != None:
                if nRoundOrNot not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改矩形框的是否为圆角必须为整数0或1", data=False))

            if roundYPox != None:
                if not isinstance(roundYPox, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的圆角高度必须为整数", data=False))
                if roundYPox < 0 or roundYPox > 100:
                    return jsonify(dict(err=1, msg="待修改矩形框的圆角宽度必须在0-100", data=False))

            if roundXPox != None:
                if not isinstance(roundXPox, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的圆角宽度必须为整数", data=False))
                if roundXPox < 0 or roundXPox > 100:
                    return jsonify(dict(err=1, msg="待修改矩形框的圆角宽度必须在0-100", data=False))

            if rectStyle != None:
                if not isinstance(rectStyle, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的样式必须为整数", data=False))
                if rectStyle < 0 or rectStyle > 10:
                    return jsonify(dict(err=1, msg="待修改矩形框的样式必须在0-10", data=False))

            if titleColor != None:
                if titleColor.get("r") < 0 or titleColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框标题颜色范围为0-255", data=False))
                if titleColor.get("g") < 0 or titleColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框标题颜色范围为0-255", data=False))
                if titleColor.get("b") < 0 or titleColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框标题颜色范围为0-255", data=False))
                if titleSize == None or titleTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框的字号和透明度不能为空", data=False))

            if titleSize != None:
                if not isinstance(titleSize, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的标题字号必须为整数", data=False))
                if titleColor == None or titleTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框的标题颜色和透明度不能为空", data=False))

            if titleTrans != None:
                if not isinstance(titleTrans, int) and not isinstance(titleTrans, float):
                    return jsonify(dict(err=1, msg="待修改矩形框的标题透明度必须为数字", data=False))
                if titleTrans < 0.0 or titleTrans > 100.0:
                    return jsonify(dict(err=1, msg="待修改矩形框的标题透明度必须在0-100", data=False))
                if titleColor == None or titleSize == None:
                    return jsonify(dict(err=1, msg="待修改矩形框的标题颜色和字号不能为空", data=False))

            if bodyColor != None:
                if bodyColor.get("r") < 0 or bodyColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框正文颜色范围为0-255", data=False))
                if bodyColor.get("g") < 0 or bodyColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框正文颜色范围为0-255", data=False))
                if bodyColor.get("b") < 0 or bodyColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框正文颜色范围为0-255", data=False))
                if bodySize == None or bodyTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框正文字号和透明度不能为空", data=False))

            if bodySize != None:
                if not isinstance(bodySize, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的正文字号必须为整数", data=False))
                if bodyColor == None or bodyTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框正文颜色和透明度不能为空", data=False))

            if bodyTrans != None:
                if not isinstance(bodyTrans, int) and not isinstance(bodyTrans, float):
                    return jsonify(dict(err=1, msg="待修改矩形框的正文透明度必须为数字", data=False))
                if bodyTrans < 0.0 or bodyTrans > 100.0:
                    return jsonify(dict(err=1, msg="待修改矩形框的正文透明度必须在0-100", data=False))
                if bodyColor == None or bodySize == None:
                    return jsonify(dict(err=1, msg="待修改矩形框正文颜色和字号不能为空", data=False))

            if descColor != None:
                if descColor.get("r") < 0 or descColor.get("r") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框描述颜色范围为0-255", data=False))
                if descColor.get("g") < 0 or descColor.get("g") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框描述颜色范围为0-255", data=False))
                if descColor.get("b") < 0 or descColor.get("b") > 255:
                    return jsonify(dict(err=1, msg="待修改矩形框描述颜色范围为0-255", data=False))
                if descSize == None or descTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框描述字号和透明度不能为空", data=False))

            if descSize != None:
                if not isinstance(descSize, int):
                    return jsonify(dict(err=1, msg="待修改矩形框的描述字号必须为整数", data=False))
                if descColor == None or descTrans == None:
                    return jsonify(dict(err=1, msg="待修改矩形框描述字体颜色和透明度不能为空", data=False))

            if descTrans != None:
                if not isinstance(descTrans, int) and not isinstance(descTrans, float):
                    return jsonify(dict(err=1, msg="待修改矩形框的注释透明度必须为数字", data=False))
                if descTrans < 0.0 or descTrans > 100.0:
                    return jsonify(dict(err=1, msg="待修改矩形框的注释透明度必须在0-100", data=False))
                if descSize == None or descColor == None:
                    return jsonify(dict(err=1, msg="待修改矩形框描述字号和透明度不能为空", data=False))

            if descOrNot != None:
                if descOrNot not in [0, 1]:
                    return jsonify(dict(err=1, msg="待修改矩形框的是否显示描述必须为整数0或1", data=False))

            if title != None:
                if not isinstance(title, str):
                    return jsonify(dict(err=1, msg="待修改矩形框的标题必须为字符串", data=False))

            strBinddPointItemList = []
            if bindPointList != None:
                if isinstance(bindPointList, list) and len(bindPointList):
                    for dBindPoint in bindPointList:
                        nFromDomLib = dBindPoint.get("fromDomLib", 1)

                        if not isinstance(dBindPoint.get("point"), str):
                            return jsonify(dict(err=1, msg="待修改矩形框的枚举量绑点必须为字符串", data=False))
                        if not len(dBindPoint.get("point")):
                            return jsonify(dict(err=1, msg="待修改矩形框的枚举量绑点不能为空字符串", data=False))
                        if not isinstance(dBindPoint.get("id"), int):
                            return jsonify(dict(err=1, msg="待修改矩形框的枚举量图片id必须为整数", data=False))

                        if nFromDomLib == 1:
                            if dBindPoint.get("id") not in dAllImages.keys():
                                return jsonify(dict(err=1, msg="待修改矩形框的枚举量图片id不存在于图库中:{id}".format(id=dBindPoint.get("id")), data=False))
                        else:
                            if dBindPoint.get("id") not in dAllImagesDomdb.keys():
                                return jsonify(dict(err=1, msg="待修改矩形框的枚举量图片id不存在于domdb.4db中:{id}".format(id=dBindPoint.get("id")), data=False))

                        if not isinstance(dBindPoint.get("decimal"), int):
                            return jsonify(dict(err=1, msg="待修改矩形框的枚举量小数位必须为整数", data=False))

                        if nFromDomLib == 1:
                            nBindItemId, msg = BEOPSqliteAccess.getInstance().copyImgFromDomLibImage(dBindPoint.get("id"))
                            if nBindItemId == None:
                                return jsonify(dict(err=1, msg="待修改矩形框的枚举量图片在转移至domdb.4db时失败:%s" % msg, data=False))
                        else:
                            nBindItemId = dBindPoint.get("id")

                        strBinddPointItemList.append("{point},{nBindItemId},{decimal}".format(point=dBindPoint.get("point"), nBindItemId=nBindItemId, decimal=dBindPoint.get("decimal")))

            if nX == None and nY == None and nWidth == None and nHeight == None and nLayer == None and dFrameColor == None and frameTrans == None and frameLineWidth == None and \
                nFillOrNot == None and dFillColor == None and fillTrans == None and nRoundOrNot == None and roundYPox == None and roundXPox == None and rectStyle == None and titleColor == None \
                and titleSize == None and titleTrans == None and bodyColor == None and bodySize == None and bodyTrans == None and descColor == None and descSize == None and descTrans == None and \
                descOrNot == None and title == None and bindPointList == None:
                continue

            sqlList = []
            updateRectangleParamList = []
            sqlUpdateRectangle = "UPDATE list_unit19 SET "

            if nX != None:
                sqlList.append("x=?")
                updateRectangleParamList.append(nX)
            if nY != None:
                sqlList.append("y=?")
                updateRectangleParamList.append(nY)
            if nWidth != None:
                sqlList.append("width=?")
                updateRectangleParamList.append(nWidth)
            if nHeight != None:
                sqlList.append("height=?")
                updateRectangleParamList.append(nHeight)
            if nLayer != None:
                sqlList.append("layer=?")
                updateRectangleParamList.append(nLayer)
            if dFrameColor != None:
                strHexFrameColor = get_hex_from_rgb(dFrameColor.get("r"), dFrameColor.get("g"), dFrameColor.get("b"))
                strFrameColorTrans = "#{color}#{trans}".format(color=strHexFrameColor, trans=str(int(frameTrans / 100)))
                sqlList.append("unitproperty02=?")
                updateRectangleParamList.append(strFrameColorTrans.encode("gbk"))
            if frameLineWidth != None:
                sqlList.append("unitproperty03=?")
                updateRectangleParamList.append(str(frameLineWidth).encode("gbk"))
            if nFillOrNot != None:
                sqlList.append("unitproperty04=?")
                updateRectangleParamList.append(str(nFillOrNot).encode("gbk"))
            if dFillColor != None:
                strHexFillColor = get_hex_from_rgb(dFillColor.get("r"), dFillColor.get("g"), dFillColor.get("b"))
                strFillColorTrans = "#{color}#{trans}".format(color=strHexFillColor, trans=str(int(fillTrans / 100)))
                sqlList.append("unitproperty05=?")
                updateRectangleParamList.append(strFillColorTrans.encode("gbk"))
            if nRoundOrNot != None:
                sqlList.append("unitproperty06=?")
                updateRectangleParamList.append(str(nRoundOrNot).encode("gbk"))
            if roundYPox != None:
                sqlList.append("unitproperty07=?")
                updateRectangleParamList.append(str(roundYPox).encode("gbk"))
            if roundXPox != None:
                sqlList.append("unitproperty08=?")
                updateRectangleParamList.append(str(roundXPox).encode("gbk"))
            if rectStyle != None:
                sqlList.append("unitproperty09=?")
                updateRectangleParamList.append(str(rectStyle).encode("gbk"))
            if titleColor != None:
                strHexTitleColor = get_hex_from_rgb(titleColor.get("r"), titleColor.get("g"), titleColor.get("b"))
                strTitleColorTransSize = "#{color}#{trans},{size}".format(color=strHexTitleColor,
                                                                           trans=str(int(titleTrans / 100)), size=titleSize)
                sqlList.append("unitproperty10=?")
                updateRectangleParamList.append(strTitleColorTransSize.encode("gbk"))

            if bodyColor != None:
                strHexBodyColor = get_hex_from_rgb(bodyColor.get("r"), bodyColor.get("g"), bodyColor.get("b"))
                strBodyColorTransSize = "#{color}#{trans},{size}".format(color=strHexBodyColor,
                                                                          trans=str(int(bodyTrans / 100)), size=bodySize)
                sqlList.append("unitproperty11=?")
                updateRectangleParamList.append(strBodyColorTransSize.encode("gbk"))

            if descColor != None:
                strHexDescColor = get_hex_from_rgb(descColor.get("r"), descColor.get("g"), descColor.get("b"))
                strDescColorTransSize = "#{color}#{trans},{size}".format(color=strHexDescColor,
                                                                          trans=str(int(descTrans / 100)), size=descSize)
                sqlList.append("unitproperty12=?")
                updateRectangleParamList.append(strDescColorTransSize.encode("gbk"))
            if descOrNot != None:
                sqlList.append("unitproperty13=?")
                updateRectangleParamList.append(str(descOrNot).encode("gbk"))
            if bindPointList != None:
                sqlList.append("unitproperty14=?")
                updateRectangleParamList.append("|".join(strBinddPointItemList).encode("gbk"))
            if title != None:
                sqlList.append("unitproperty15=?")
                updateRectangleParamList.append(title.encode("utf8"))

            sqlUpdateRectangle += ",".join(sqlList)
            sqlUpdateRectangle += " WHERE id=? AND pageid=? AND unitproperty01='rectangle'"
            updateRectangleParamList.append(nRectId)
            updateRectangleParamList.append(nPageId)

            updateRectangleList.append(
                (sqlUpdateRectangle, updateRectangleParamList)
            )

    # 页面内的所有元素最终一起处理
    bSuc, msg = BEOPSqliteAccess.getInstance().updatePageContent(nPageId, addTextList, removeTextList, updateTextList,
                                                                 addCustList, removeCustList, updateCustList,
                                                                 addButtonList, removeButtonList, updateButtonList,
                                                                 addCheckboxList, removeCheckboxList, updateCheckboxList,
                                                                 addImageList, removeImageList, updateImageList,
                                                                 addImageEventParamList, updateImageEventContentParamList, updateImageBindContentParamList,
                                                                 addLineList, removeLineList, updateLineList,
                                                                 addSysEquipList, removeSysEquipList, updateSysEquipList,
                                                                 addRectangleList, removeRectangleList, updateRectangleList)

    # 更新页面缓存 （2023-07-07 debugtool编辑后页面内容暂时不存入debugtool专用的redis缓存)
    if bSuc:
        # rvContent1 = BEOPSqliteAccess.getInstance().getPlantDebugTool(nPageId)
        # if rvContent1 != None:
        #     RedisManager.set_4db_page_content_DebugTool(nPageId, rvContent1)

        rvContent2 = BEOPSqliteAccess.getInstance().getPlant("", nPageId)
        if rvContent2 != None:
            RedisManager.set_4db_page_content(nPageId, rvContent2)

    bSucBackup, backupMsg = execute_backup_domdb()
    msg = ""
    if not bSucBackup:
        msg += backupMsg
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))


@bp_page.route("/acquireLock", methods=["POST"])
def acquire_lock():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nPageId = rcv.get("pageId", None)
    userId = rcv.get("userId", None)
    strMacAddr = rcv.get("macAddress", None)

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=""))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=""))

    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面ID必须为整数", data=""))
    pageIdList, msg = BEOPSqliteAccess.getInstance().getPageIdList(pageId=nPageId)
    if pageIdList == None:
        return jsonify(dict(err=1, msg="查询页面id列表失败", data=""))

    if not len(pageIdList):
        return jsonify(dict(err=1, msg="该页面不存在(id:{id})不存在".format(id=nPageId), data=""))

    if strMacAddr != None:
        if not isinstance(strMacAddr, str):
            return jsonify(dict(err=1, msg="mac地址必须为字符串", data=""))

    strPageId = str(nPageId)
    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict) or dEditLock == None:
        dEditLock = {}

    dPageEditLock = dEditLock.get(strPageId, {})
    if not isinstance(dPageEditLock, dict) or dPageEditLock == None:
        dPageEditLock = {}

    strActiveTime = dPageEditLock.get("activeTime", None)
    tActiveTime = None
    if isValidDate(strActiveTime, "%Y-%m-%d %H:%M:%S"):
        tActiveTime = datetime.strptime(strActiveTime, "%Y-%m-%d %H:%M:%S")

    if isinstance(tActiveTime, datetime):
        if (datetime.now() - tActiveTime).total_seconds() > nPageEditMinsTimeOut * 60:
            dPageEditLock.update(dict(lock=0, token="", userId=None, userName=""))

    if dPageEditLock.get("lock", 0) == 1:
        if dPageEditLock.get("userId", "") == userId:
            if strMacAddr != None and dPageEditLock.get("macAddress", None) != None:
                if strMacAddr == dPageEditLock.get("macAddress", ""):
                    return jsonify(dict(err=0, msg="您拥有此电脑在该页面的组态编辑权限", data=dPageEditLock.get("token", "")))
                else:
                    return jsonify(dict(err=1, msg="您拥有此电脑在该页面的组态编辑权限，但传入的mac地址错误", data=""))

            return jsonify(dict(err=0, msg="您已在一台电脑上获取了该页面的组态编辑权限，请继续使用那台电脑进行组态编辑", data=""))
        else:
            return jsonify(dict(err=1, msg="该页面(pageId:{pageId})的组态编辑权限正在被用户{userName}(id:{userId})占用，您暂时无法获得该项目组态的编辑权限".format(userName=dPageEditLock.get("userName", ""),
                                                                                                             userId=dPageEditLock.get("userId", ""), pageId=nPageId), data=""))

    strToken = "".join(random.sample(string.ascii_letters + string.digits, 32))
    dPageEditLock.update(dict(token=strToken,
                          activeTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          lock=1,
                          userId=userId,
                          userName=dUserInfo.get("username", "")))

    if isinstance(strMacAddr, str):
        if len(strMacAddr):
            dPageEditLock.update({"macAddress": strMacAddr})

    dEditLock.update({strPageId: dPageEditLock})
    RedisManager.set(strPageEditLockKey, dEditLock)

    return jsonify(dict(err=0, msg="获取编辑权限成功", data=strToken))


@bp_page.route("/releaseLock", methods=["POST"])
def release_lock():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    token = rcv.get("token", None)
    nPageId = rcv.get("pageId", None)

    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面ID必须为整数", data=""))
    pageIdList, msg = BEOPSqliteAccess.getInstance().getPageIdList(pageId=nPageId)
    if pageIdList == None:
        return jsonify(dict(err=1, msg="查询页面id列表失败", data=""))

    if not len(pageIdList):
        return jsonify(dict(err=1, msg="该页面不存在(pageId:{pageId})不存在".format(pageId=nPageId), data=""))

    if not isinstance(token, str):
        return jsonify(dict(err=1, msg="token必须为字符串", data=False))
    if not len(token):
        return jsonify(dict(err=1, msg="token不能为空", data=False))

    strPageId = str(nPageId)
    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict) or dEditLock == None:
        dEditLock = {}

    dPageEditLock = dEditLock.get(strPageId, {})
    if not isinstance(dPageEditLock, dict) or dPageEditLock == None:
        dPageEditLock = {}

    if dPageEditLock.get("lock", 0) == 0:
        return jsonify(dict(err=0, msg="该页面(pageId:{pageId})组态未处于编辑占用状态".format(pageId=nPageId), data=True))

    if dPageEditLock.get("token", "") == token:
        dPageEditLock.update(dict(lock=0, token="", userId=None, userName="", macAddress=""))
        dEditLock.update({strPageId: dPageEditLock})
        RedisManager.set(strPageEditLockKey, dEditLock)
        return jsonify(dict(err=0, msg="您已成功解除该页面(pageId:{pageId})的组态编辑权限".format(pageId=nPageId), data=True))
    else:
        strActiveTime = dPageEditLock.get("activeTime", "")
        tActiveTime = None
        if isValidDate(strActiveTime, "%Y-%m-%d %H:%M:%S"):
            tActiveTime = datetime.strptime(strActiveTime, "%Y-%m-%d %H:%M:%S")

        if isinstance(tActiveTime, datetime):
            if (datetime.now() - tActiveTime).total_seconds() > nPageEditMinsTimeOut * 60:
                dPageEditLock.update(dict(lock=0, token="", userId=None, userName="", macAddress=""))
                dEditLock.update({strPageId: dPageEditLock})
                RedisManager.set(strPageEditLockKey, dEditLock)
                return jsonify(dict(err=0, msg="该页面(pageId:{pageId})的组态的编辑占用状态超时，已解除占用".format(pageId=nPageId), data=True))

        return jsonify(dict(err=1, msg="该页面(pageId:{pageId})的组态编辑权限正在被用户{userName}(id:{userId})占用，您暂时无法对权限锁进行操作".format(
            userName=dPageEditLock.get("userName", ""),
            pageId=nPageId,
            userId=dPageEditLock.get("userId", "")), data=""))


@bp_page.route("/activateLock", methods=["POST"])
def activate_lock():
    if not RedisManager.is_alive():
        return jsonify(dict(err=1, msg="Redis未安装或未在运行，请先完善后台安装", data=""))

    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    token = rcv.get("token", None)
    nPageId = rcv.get("pageId", None)
    if not isinstance(token, str):
        return jsonify(dict(err=1, msg="token必须为字符串", data=False))

    if not len(token):
        return jsonify(dict(err=1, msg="token不能为空", data=False))

    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面ID必须为整数", data=""))

    pageIdList, msg = BEOPSqliteAccess.getInstance().getPageIdList(pageId=nPageId)
    if pageIdList == None:
        return jsonify(dict(err=1, msg="查询页面id列表失败", data=""))

    if not len(pageIdList):
        return jsonify(dict(err=1, msg="该页面不存在(pageId:{pageId})不存在".format(pageId=nPageId), data=""))

    strPageId = str(nPageId)
    dEditLock = RedisManager.get(strPageEditLockKey)
    if not isinstance(dEditLock, dict) or dEditLock == None:
        dEditLock = {}

    dPageEditLock = dEditLock.get(strPageId, {})
    if not isinstance(dPageEditLock, dict) or dPageEditLock == None:
        dPageEditLock = {}

    if not dPageEditLock.get("token", ""):
        return jsonify(dict(err=1, msg="该页面(pageId:{pageId})组态的编辑权限未处于占用状态，请先尝试获取编辑权限".format(pageId=nPageId), data=False))

    if dPageEditLock.get("token", "") != token:
        return jsonify(dict(err=1, msg="该页面(pageId:{pageId})的组态编辑权限正在被用户{userName}(id:{userId})占用，您暂时无法对权限锁进行操作".format(
            userName=dPageEditLock.get("userName", ""),
            pageId=nPageId,
            userId=dPageEditLock.get("userId", "")), data=""))

    if dPageEditLock.get("token", "") == token and dPageEditLock.get("lock", 0) == 1:
        dPageEditLock.update(dict(lock=1, activeTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        dEditLock.update({strPageId: dPageEditLock})
        RedisManager.set(strPageEditLockKey, dEditLock)
        return jsonify(dict(err=0, msg="页面(pageId:{pageId})编辑权限的心跳续存成功".format(pageId=nPageId), data=True))

    return jsonify(dict(err=1, msg="该页面(pageId:{pageId})组态的编辑权限无法续存心跳，可能占用状态已被解除，请重新尝试获取".format(pageId=nPageId), data=False))

@bp_page.route("/addElementToLibImageAnimation", methods=["POST"])
def add_image_to_lib_image_animation():
    fileList = []
    nMaxId, msg = BEOPSqliteAccess.getInstance().getMaxIdInDomImgLibTable("lib_image_animation")
    if nMaxId == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nId = nMaxId + 1

    animationName = request.form.get("name")
    if animationName != None:
        if not isinstance(animationName, str):
            return jsonify(dict(err=1, msg="动画名称不能为空", data=False))
        if not len(animationName):
            return jsonify(dict(err=1, msg="动画名称不能为空", data=False))

    if not isinstance(animationName, str):
        animationName = uuid.uuid4().hex

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    categoryMap, les = get_dom_image_lib_category()

    cate = request.form.get("category")
    if is_int_digit(cate):
        nCate = int(cate)
        if nCate not in categoryMap.keys():
            nCate = 11
    else:
        nCate = 11

    nImgIdList = []
    for i in range(20):
        key = "file{n:02d}".format(n=i+1)
        file = request.files.get(key)
        if file == None:
            continue

        fileName = file.filename
        fileNameSplit = os.path.splitext(fileName)
        fileNameNew = "{name}_{time}{ext}".format(name=fileNameSplit[0],
                                                  time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                                                  ext=fileNameSplit[1])
        if fileNameSplit[1].lower() != ".png":
            return jsonify(dict(err=1, msg="只支持.png格式的图片", data=False))

        filePath = os.path.join(tempDir, fileNameNew)
        if os.path.exists(filePath):
            try:
                os.remove(filePath)
            except:
                pass

        file.save(filePath)
        if not os.path.exists(filePath):
            return jsonify(dict(err=1, msg="发现无效图片，保存失败", data=False))
        fileList.append(dict(path=filePath, nId=nId, name=fileName))
        nImgIdList.append(nId)
        nId += 1

    if not len(fileList):
        return jsonify(dict(err=1, msg="必须传入图片", data=False))

    bSuc, msg = BEOPSqliteAccess.getInstance().addElementToDomLibImageAnimation(animationName, fileList, nCate)
    if bSuc:
        imagesDir = os.path.join(app.static_folder, "images")
        if not os.path.exists(imagesDir):
            os.mkdir(imagesDir)
        domImgLibDir = os.path.join(imagesDir, "dom-img-lib")
        if not os.path.exists(domImgLibDir):
            os.mkdir(domImgLibDir)

        for oFile in fileList:
            destPath = os.path.join(domImgLibDir, "animation_{name}.png".format(name=oFile.get("nId")))
            try:
                os.remove(destPath)
            except:
                pass
            shutil.copy2(oFile.get("path"), destPath)

    for oFile in fileList:
        try:
            os.remove(oFile.get("path"))
        except:
            pass

    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_page.route("/deleteElementFromLibImage", methods=["POST"])
def delete_element_from_lib_image():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nId = rcv.get("id", None)
    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="图片id必须为整数", data=False))
    bSuc, msg = BEOPSqliteAccess.getInstance().deleteElementFromDomLibImage(nId)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_page.route("/deleteElementFromLibImageAnimation", methods=["POST"])
def delete_element_from_lib_image_animation():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nId = rcv.get("id", None)
    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="动画id必须为整数", data=False))
    bSuc, msg = BEOPSqliteAccess.getInstance().deleteElementFromLibImageAnimation(nId)
    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_page.route("/addElementToLibImage", methods=["POST"])
def add_image_to_lib_image():
    file = request.files.get("file")
    if file == None:
        return jsonify(dict(err=1, msg="文件不能为空", data=False))

    fileName = file.filename
    fileNameSplit = os.path.splitext(fileName)
    fileNameNew = "{name}_{time}{ext}".format(name=fileNameSplit[0],
                                              time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                                              ext=fileNameSplit[1])

    if fileNameSplit[1].lower() != ".png":
        return jsonify(dict(err=1, msg="只支持.png格式的图片", data=False))

    categoryMap, les = get_dom_image_lib_category()

    cate = request.form.get("category")
    if is_int_digit(cate):
        nCate = int(cate)
        if nCate not in categoryMap.keys():
            nCate = 11
    else:
        nCate = 11

    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    filePath = os.path.join(tempDir, fileNameNew)
    if os.path.exists(filePath):
        try:
            os.remove(filePath)
        except:
            pass

    file.save(filePath)

    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="未发现有效的图片文件", data=False))

    strFileType = fileNameSplit[1].replace(".", "")

    with open(filePath, "rb") as f:
        fileBinary = f.read()

    if fileBinary == None:
        try:
            os.remove(filePath)
        except:
            pass
        return jsonify(dict(err=1, msg="将图片文件转换为二进制失败", data=False))

    nMaxId, msg = BEOPSqliteAccess.getInstance().getMaxIdInDomImgLibTable("lib_image")
    if nMaxId == None:
        return jsonify(dict(err=1, msg=msg, data=False))

    nId = nMaxId + 1
    bSuc, msg = BEOPSqliteAccess.getInstance().addElementToDomImgLib(nId, fileName, fileBinary, strFileType, nCate)
    if bSuc:
        BEOPSqliteAccess.getInstance().releaseImgFromDomImageLib(nId)

    try:
        os.remove(filePath)
    except:
        pass

    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))

@bp_page.route("/getElementFromLibImageAnimation", methods=["POST"])
def get_image_from_lib_image_animation():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    keyword = rcv.get("keyword", None)
    if keyword != None:
        if not isinstance(keyword, str):
            return jsonify(dict(err=1, msg="图片名称关键词必须为字符串", data=[]))
        if not len(keyword):
            return jsonify(dict(err=1, msg="图片名称关键词不能为空", data=[]))

    categoryMap, les = get_dom_image_lib_category()

    imgList, msg = BEOPSqliteAccess.getInstance().getElementFromDomLibImageAnimation(keyword)
    if imgList == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    for i in range(len(imgList)):
        for j in range(len(imgList)-i-1):
            if imgList[j].get("id") < imgList[j+1].get("id"):
                imgList[j], imgList[j+1] = imgList[j+1], imgList[j]
    return jsonify(dict(err=0, msg="", data=imgList))

@bp_page.route("/getElementFromLibImage", methods=["POST"])
def get_image_from_lib_image():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    keyword = rcv.get("keyword", None)
    if keyword != None:
        if not isinstance(keyword, str):
            return jsonify(dict(err=1, msg="图片名称关键词必须为字符串", data=[]))
        if not len(keyword):
            return jsonify(dict(err=1, msg="图片名称关键词不能为空", data=[]))

    categoryMap, les = get_dom_image_lib_category()

    dImgs, imgList, msg = BEOPSqliteAccess.getInstance().getElementFromDomLibImage(keyword)
    if imgList == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    dStat = {}
    for img in imgList:
        if img.get("specy") not in dStat.keys():
            dStat.update({img.get("specy"): []})

        dStat[img.get("specy")].append(img)

    dataList = []
    for nCate, itemList in dStat.items():
        for i in range(len(itemList)):
            for j in range(len(itemList)-i-1):
                if itemList[j].get("id") < itemList[j+1].get("id"):
                    itemList[j], itemList[j+1] = itemList[j+1], itemList[j]
        dataList.append(dict(categoryId=nCate, categoryName=categoryMap.get(nCate, ""), itemList=itemList))

    return jsonify(dict(err=0, msg="", data=dataList))

@bp_page.route("/searchTemplateByPointKeyword", methods=["POST"])
def search_template_by_point_keyword():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    keyword = rcv.get("keyword", None)
    if not isinstance(keyword, str):
        return jsonify(dict(err=1, msg="关键词必须为字符串", data=[]))
    if not len(keyword):
        return jsonify(dict(err=1, msg="关键词不能为空", data=[]))

    # 首先从云端获取模板信息，dTemplateFromCloud作为汇总字典
    dTemplateFromCloud, msg = search_template_by_point_keyword_from_cloud(keyword)

    templateDir = os.path.join(app.static_folder, "template")
    if not os.path.exists(templateDir):
        return jsonify(dict(err=0, msg="", data=dTemplateFromCloud))

    ignoreFileNameList = ["best.4db"]

    for root, dirs, fileNames in os.walk(templateDir):
        for fileName in fileNames:

            if not fileName.endswith(".4db"):
                continue

            if fileName in ignoreFileNameList:
                continue

            filePath = os.path.join(root, fileName)

            # 模板名称与占位符键值对
            dTemplateNamePlaceHolderMap, strLocalVersion, msg = BEOPSqliteAccess.getInstance().getTemplateNamePlaceHolderMap(filePath)
            if dTemplateNamePlaceHolderMap == None:
                continue

            # 模板详情页面id列表
            pageIdList, msg = BEOPSqliteAccess.getInstance().getPageIdsContainPointsOfKeyword(filePath, keyword)
            if not isinstance(pageIdList, list):
                continue

            if not len(pageIdList):
                continue

            # 入口页面id列表
            nEntrancePageIdList, msg = BEOPSqliteAccess.getInstance().getEntrancePageIdList(filePath, pageIdList)
            if not isinstance(nEntrancePageIdList, list):
                continue

            if not len(nEntrancePageIdList):
                continue

            # 页面id与页面名称键值对
            dPageIdNameMap, msg = BEOPSqliteAccess.getInstance().getPageIdNameMap(filePath, nEntrancePageIdList)
            if dPageIdNameMap == None:
                continue

            if not dPageIdNameMap:
                continue

            bOnlyExistsLocally = False
            for nEntrancePageId in nEntrancePageIdList:

                # 获取页面名称（模板名称）
                strPageName = dPageIdNameMap.get(nEntrancePageId, "")
                if not strPageName:
                    continue

                # 若无对应的占位符字典则认为不是模板
                dPlaceHolder = dTemplateNamePlaceHolderMap.get(strPageName, None)
                if not dPlaceHolder:
                    continue

                if fileName not in dTemplateFromCloud.keys():
                    bOnlyExistsLocally = True
                    dTemplateFromCloud.update({fileName: dict(version=strLocalVersion, templateList=[], desc="")})

                dTemplateFromCloud[fileName]["templateList"].append(dict(templateName=strPageName,
                                              placeHolder=dPlaceHolder))

            if bOnlyExistsLocally:
                dTemplateFromCloud[fileName].update({"desc": "本地自有，不存在于云端"})
            else:
                dTemplateFromCloud[fileName].update({"desc": "本地版本为最新"})
                nLocalVersion = convert_version(strLocalVersion)
                strCloudVersion = dTemplateFromCloud.get(fileName, {}).get("version", "")
                nCloudVersion = convert_version(strCloudVersion)

                if isinstance(nLocalVersion, int) and isinstance(nCloudVersion, int):
                    if nCloudVersion > nLocalVersion:
                        dTemplateFromCloud[fileName].update({"desc": "需同步云端版本"})

    return jsonify(dict(err=0, msg="", data=dTemplateFromCloud))



"""
获取core服务器磁盘上所有组态模板文件中的标准设备
"""
@bp_page.route("/getStandardEquipmentOfAllTemplateFiles")
def get_standard_equipment_of_all_template_files():
    templateDir = os.path.join(app.static_folder, "template")
    if not os.path.exists(templateDir):
        return jsonify(dict(err=1, msg="模板文件夹不存在", data=[]))

    dResAll = {}
    for root, dirs, fileNames in os.walk(templateDir):
        for fileName in fileNames:
            if not fileName.endswith(".4db"):
                continue

            templateFileName = fileName.replace(".4db", "")
            templateFilePath = os.path.join(templateDir, "{name}.4db".format(name=templateFileName))

            dTemplateNamePlaceHolderMap, strLocalVersion, msg = BEOPSqliteAccess.getInstance().getTemplateNamePlaceHolderMap(templateFilePath)
            if dTemplateNamePlaceHolderMap == None:
                return jsonify(dict(err=1, msg=msg, data=[]))

            stdEquipNameList = []
            for stdEquipName, dPlaceHolder in dTemplateNamePlaceHolderMap.items():
                if stdEquipName.startswith("bsd"):  # 过滤佰诗得模板
                    continue
                if stdEquipName.find("模板") >= 0:
                    continue

                stdEquipNameList.append(stdEquipName)

            # 标准设备名称与跳转进入的模板页面id键值对
            dStdEquipNameLinkDetailPageIdMap, msg = BEOPSqliteAccess.getInstance().getStdEquipEntrancePageNameAndTemplatePageId(templateFilePath, stdEquipNameList)
            if dStdEquipNameLinkDetailPageIdMap == None:
                return jsonify(dict(err=1, msg=msg, data=[]))

            dPageGroup = {}
            for stdEquipName, dDetailInfo in dStdEquipNameLinkDetailPageIdMap.items():
                strGroupName = dDetailInfo.get("groupName", "")
                if not strGroupName:
                    continue

                if strGroupName not in dPageGroup.keys():
                    dPageGroup.update({strGroupName: []})

                dPageGroup[strGroupName].append(dict(stdEquipName=stdEquipName,
                                                     placeHolder=dTemplateNamePlaceHolderMap.get(stdEquipName, {}),
                                                     detailPageId=dDetailInfo.get("detailPageId", None),
                                                     groupId=dDetailInfo.get("groupId", ""),
                                                     entrancePageId=dDetailInfo.get("entrancePageId", ""),
                                                     elementId=dDetailInfo.get("elementId", ""),
                                                     entrancePictureId=dDetailInfo.get("entrancePictureId")))

            resEquipList = []
            for strGroupName, stdEquipList in dPageGroup.items():
                for i in range(len(stdEquipList)):
                    for j in range(len(stdEquipList)-i-1):
                        if stdEquipList[j].get("stdEquipName") < stdEquipList[j+1].get("stdEquipName"):
                            stdEquipList[j], stdEquipList[j+1] = stdEquipList[j+1], stdEquipList[j]

                resEquipList.append(dict(groupName=strGroupName,
                                         stdEquipList=stdEquipList))

            for i in range(len(resEquipList)):
                for j in range(len(resEquipList)-i-1):
                    if resEquipList[j].get("groupName") < resEquipList[j+1].get("groupName"):
                        resEquipList[j], resEquipList[j+1] = resEquipList[j+1], resEquipList[j]

            if not len(resEquipList):
                continue

            dResAll.update({fileName: resEquipList})

    return jsonify(dict(err=0, msg="", data=dResAll))

"""
获取一个模板内的所有标准设备列表
"""
@bp_page.route("/getStandardEquipmentOfTemplateFile", methods=["POST"])
def get_standard_equipment_of_template_file():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    templateFileName = rcv.get("templateFileName", None)
    if not isinstance(templateFileName, str):
        return jsonify(dict(err=1, msg="模板文件名称不能为空且必须为字符串", data=[]))
    if templateFileName.endswith(".4db"):
        templateFileName = templateFileName.replace(".4db", "")

    templateDir = os.path.join(app.static_folder, "template")
    if not os.path.exists(templateDir):
        return jsonify(dict(err=1, msg="模板文件夹不存在", data=[]))

    templateFilePath = os.path.join(templateDir, "{name}.4db".format(name=templateFileName))
    if not os.path.exists(templateFilePath):
        return jsonify(dict(err=1, msg="模板文件{name}.4db不存在".format(name=templateFileName), data=[]))

    dTemplateNamePlaceHolderMap, strLocalVersion, msg = BEOPSqliteAccess.getInstance().getTemplateNamePlaceHolderMap(templateFilePath)
    if dTemplateNamePlaceHolderMap == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    stdEquipNameList = []
    for stdEquipName, dPlaceHolder in dTemplateNamePlaceHolderMap.items():
        if stdEquipName.startswith("bsd"):  # 过滤佰诗得模板
            continue
        if stdEquipName.find("模板") >= 0:
            continue

        stdEquipNameList.append(stdEquipName)

    # 标准设备名称与跳转进入的模板页面id键值对
    dStdEquipNameLinkDetailPageIdMap, msg = BEOPSqliteAccess.getInstance().getStdEquipEntrancePageNameAndTemplatePageId(templateFilePath, stdEquipNameList)
    if dStdEquipNameLinkDetailPageIdMap == None:
        return jsonify(dict(err=1, msg=msg, data=[]))

    dPageGroup = {}
    for stdEquipName, dDetailInfo in dStdEquipNameLinkDetailPageIdMap.items():
        strGroupName = dDetailInfo.get("groupName", "")
        if not strGroupName:
            continue

        if strGroupName not in dPageGroup.keys():
            dPageGroup.update({strGroupName: []})

        dPageGroup[strGroupName].append(dict(stdEquipName=stdEquipName,
                                             placeHolder=dTemplateNamePlaceHolderMap.get(stdEquipName, {}),
                                             detailPageId=dDetailInfo.get("detailPageId", None),
                                             groupId=dDetailInfo.get("groupId", ""),
                                             entrancePageId=dDetailInfo.get("entrancePageId", ""),
                                             elementId=dDetailInfo.get("elementId", ""),
                                             entrancePictureId=dDetailInfo.get("entrancePictureId")))

    resEquipList = []
    for strGroupName, stdEquipList in dPageGroup.items():
        for i in range(len(stdEquipList)):
            for j in range(len(stdEquipList)-i-1):
                if stdEquipList[j].get("stdEquipName") < stdEquipList[j+1].get("stdEquipName"):
                    stdEquipList[j], stdEquipList[j+1] = stdEquipList[j+1], stdEquipList[j]

        resEquipList.append(dict(groupName=strGroupName,
                                 stdEquipList=stdEquipList))

    for i in range(len(resEquipList)):
        for j in range(len(resEquipList)-i-1):
            if resEquipList[j].get("groupName") < resEquipList[j+1].get("groupName"):
                resEquipList[j], resEquipList[j+1] = resEquipList[j+1], resEquipList[j]

    return jsonify(dict(err=0, msg="", data=resEquipList))


@bp_page.route("/movePageUpDown", methods=["POST"])
def move_page_up_down():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nPageId = rcv.get("pageId", None)
    nDirection = rcv.get("direction", 0)  # 0下调，1上调

    if nDirection not in [0, 1]:
        return jsonify(dict(err=1, msg="方向(direction)必须为0或1", data=False))

    if not isinstance(nPageId, int):
        return jsonify(dict(err=1, msg="页面id必须为整数", data=False))

    pageList, msg = BEOPSqliteAccess.getInstance().getAllPageOrderByShowOrder()
    if pageList == None:
        return jsonify(dict(err=1, msg="页面列表获取失败: {msg}".format(msg=msg), data=False))

    dGroup = {}
    nCurGroupId = None
    nCurOrder = None
    for page in pageList:
        if page.get("id") == nPageId:
            nCurGroupId = page.get("groupId")
            nCurOrder = page.get("order")
        if page.get("groupId") not in dGroup.keys():
            dGroup.update({page.get("groupId"): []})
        dGroup[page.get("groupId")].append(page)

    if nCurGroupId == None or nCurOrder == None:
        return jsonify(dict(err=1, msg="页面(id:{id})不存在".format(id=nPageId), data=False))

    siblingList = dGroup.get(nCurGroupId, [])
    if not isinstance(siblingList, list):
        return jsonify(dict(err=1, msg="页面(id:{id})所在的分组获取失败".format(id=nPageId), data=False))
    if not len(siblingList):
        return jsonify(dict(err=1, msg="页面(id:{id})所在的分组获取失败".format(id=nPageId), data=False))

    if nDirection == 1:
        siblingList.reverse()

    nCurIdx = None
    for idx, sibling in enumerate(siblingList):
        if sibling.get("id") == nPageId:
            nCurIdx = idx

    opposite = None
    if nCurIdx != None:
        if len(siblingList) - 1 >= nCurIdx + 1:
            opposite = siblingList[nCurIdx+1]

    if opposite != None:
        bSuc, msg = BEOPSqliteAccess.getInstance().exchangePageShowOrder(nPageId, nCurOrder, opposite.get("id"), opposite.get("order"))
        return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))
    return jsonify(dict(err=0, msg="", data=True))

@bp_page.route("/movePageGroupUpDown", methods=["POST"])
def move_page_group_up_down():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    nDirection = rcv.get("direction", 0)  # 0下调，1上调
    if nDirection not in [0, 1]:
        return jsonify(dict(err=1, msg="方向(direction)必须为0或1", data=False))

    nGroupId = rcv.get("groupId", None)
    if not isinstance(nGroupId, int):
        return jsonify(dict(err=1, msg="分组id必须为整数", data=False))

    pageList, msg = BEOPSqliteAccess.getInstance().getAllPageOrderByShowOrder()
    if pageList == None:
        return jsonify(dict(err=1, msg="页面列表获取失败: {msg}".format(msg=msg), data=False))

    bGroupIdLegal = False
    groupList = []
    nGrpId = None
    for page in pageList:
        if not len(groupList):
            groupList.append(dict(groupId=page.get("groupId"), pageList=[]))
            nGrpId = page.get("groupId")

        if nGrpId != page.get("groupId"):
            groupList.append(dict(groupId=page.get("groupId"), pageList=[]))
            nGrpId = page.get("groupId")

        groupList[-1]["pageList"].append(page)

        if page.get("groupId") == nGroupId:
            bGroupIdLegal = True

    if not bGroupIdLegal:
        return jsonify(dict(err=1, msg="该分组(id: {id})内无页面，故无法移动".format(id=nGroupId), data=False))

    objA = None
    objB = None
    nObjAIndex = None
    nObjBIndex = None
    if nDirection == 0:
        for idx, group in enumerate(groupList):
            if group.get("groupId") == nGroupId:
                if len(groupList) - 1 >= idx + 1:
                    objA = group
                    objB = groupList[idx+1]
                    nObjAIndex = idx
                    nObjBIndex = idx+1
                break

    elif nDirection == 1:
        for i in range(len(groupList)-1, -1, -1):
            if groupList[i].get("groupId") == nGroupId:
                if i-1 >= 0:
                    objA = groupList[i]
                    objB = groupList[i-1]
                    nObjAIndex = i
                    nObjBIndex = i - 1

    if objA != None and objB != None and nObjAIndex != None and nObjBIndex != None:
        groupList[nObjAIndex] = objB
        groupList[nObjBIndex] = objA

        itemList = []
        for group in groupList:
            if isinstance(group.get("pageList"), list):
                if len(group.get("pageList")):
                    itemList.extend(group.get("pageList"))

        orderTplList = []
        for idx, page in enumerate(itemList):
            orderTplList.append(
                (idx + 1, page.get("id"))
            )

        bSuc, msg = BEOPSqliteAccess.getInstance().movePageGroupUpDown(orderTplList)
        return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))
    return jsonify(dict(err=0, msg="", data=True))

@bp_page.route("/listLocalTemplateFileNames")
def list_local_template_file_names():
    templateDir = os.path.join(app.static_folder, "template")
    if not os.path.exists(templateDir):
        return jsonify(dict(err=1, msg="模板文件所在文件夹(template)不存在", data=[]))

    nameList = []
    for root, dirs, fileNames in os.walk(templateDir):
        for fileName in fileNames:
            if not fileName.endswith(".4db"):
                continue
            nameList.append(fileName)

    msg = "未发现模板文件" if not len(nameList) else ""
    return jsonify(dict(err=0, msg=msg, data=nameList))


@bp_page.route("/getImgCategoryList")
def get_img_category_list():
    categoryMap, les = get_dom_image_lib_category()
    return jsonify(dict(err=0, msg='', data=les))

@bp_page.route("/getDomdbBackupList")
def get_domdb_backup_list():
    dbFileVerDir = os.path.join(app.config["CORE_PATH"], "DBFileVersion")
    if not os.path.exists(dbFileVerDir):
        return jsonify(dict(err=1, msg="DBFileVersion文件夹不存在", data=[]))

    nameList = []
    for root, dirs, fileNames in os.walk(dbFileVerDir):
        for fileName in fileNames:
            if not fileName.startswith("domdb_autosave_"):
                continue

            if not fileName.endswith(".4db"):
                continue

            nameList.append(fileName)

    return jsonify(dict(err=0, msg="", data=nameList))

@bp_page.route("/downloadDomdbBackup", methods=["POST"])
def download_domdb_backup():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    fileName = rcv.get("fileName", None)
    if not isinstance(fileName, str):
        return jsonify(dict(err=1, msg='文件名必须为字符串', data=""))

    if not len(fileName):
        return jsonify(dict(err=1, msg='文件名不能为空', data=""))

    dbFileVerDir = os.path.join(app.config["CORE_PATH"], "DBFileVersion")
    filePath = os.path.join(dbFileVerDir, fileName)
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg='文件({file})不存在'.format(file=fileName), data=""))

    splitList = os.path.splitext(fileName)
    tempDir = os.path.join(app.static_folder, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    # 清除6小时前的历史文件
    for root, dirs, fileNames in os.walk(tempDir):
        for fileName in fileNames:
            if not fileName.endswith(".4db"):
                continue

            stTime = time.localtime(os.stat(os.path.join(root, fileName)).st_mtime)
            tEditTime = datetime.now().replace(year=stTime.tm_year, month=stTime.tm_mon, day=stTime.tm_mday,
                                               hour=stTime.tm_hour, minute=stTime.tm_min, second=stTime.tm_sec)

            if (datetime.now() - tEditTime).total_seconds() > 3600 * 6:
                try:
                    os.remove(os.path.join(root, fileName))
                except:
                    pass

    destName = "{name}_{uid}{ext}".format(name=splitList[0], uid=uuid.uuid4().hex, ext=splitList[1])
    destPath = os.path.join(tempDir, destName)
    try:
        shutil.copyfile(filePath, destPath)
    except Exception as e:
        strLog = "复制文件（{file}）时出错:{err}".format(file=fileName, err=e.__str__())
        return jsonify(dict(err=1, msg=strLog, data=""))

    return jsonify(dict(err=0, msg="", data=destName))

