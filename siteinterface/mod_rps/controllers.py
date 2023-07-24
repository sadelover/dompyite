# -*- coding: utf-8 -*-
from siteinterface.mod_rps import bp_rps
from flask import request, jsonify
from siteinterface.BEOPDataAccess import BEOPDataAccess
from datetime import datetime, timedelta
from siteinterface.utils import isValidDate
from siteinterface.mod_rps.utils import *
import os
from siteinterface import app
import xlrd
import time
from siteinterface.RedisManager import RedisManager
import json


@bp_rps.route("/addClient", methods=["POST"])
def add_client():
    rcv = request.get_json()
    name = rcv.get("name", None)
    address = rcv.get("address", "")
    code = rcv.get("code", None)

    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="客户名称为空或格式有误", data=False))
    if not isinstance(address, str):
        return jsonify(dict(err=1, msg="客户地址必须为字符串", data=False))
    if not isinstance(code, str):
        return jsonify(dict(err=1, msg="客户编码为空或格式有误", data=False))

    maxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_client")
    nId = maxId + 1

    bNameExists = BEOPDataAccess.getInstance().fieldExistsInTable("name", name, "rps_client")
    if bNameExists:
        return jsonify(dict(err=1, msg="该客户名称已存在", data=False))

    bCodeExists = BEOPDataAccess.getInstance().fieldExistsInTable("code", code, "rps_client")
    if bCodeExists:
        return jsonify(dict(err=1, msg="该客户编码已存在", data=False))

    strCreateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bSuc = BEOPDataAccess.getInstance().addRpsClient(nId, name, address, strCreateTime, code)
    if not bSuc:
        return jsonify(dict(err=1, msg="创建失败", data=False))
    return jsonify(dict(err=0, msg="创建成功", data=True))


@bp_rps.route("/deleteClient", methods=["POST"])
def delete_client():
    rcv = request.get_json()
    id = rcv.get("id", None)
    name = rcv.get("name", None)
    code = rcv.get("code", None)

    if id == None and name == None and code == None:
        return jsonify(dict(err=1, msg="客户ID，客户名称，客户编码至少传入一个", data=False))
    if id != None and not isinstance(id, int):
        return jsonify(dict(err=1, msg="客户ID必须为整数", data=False))
    if name != None and not isinstance(name, str):
        return jsonify(dict(err=1, msg="客户名称必须为字符串", data=False))
    if code != None and not isinstance(code, str):
        return jsonify(dict(err=1, msg="客户编码必须为字符串", data=False))

    anchor = ()
    priorityList = ["id", "code", "name"]
    for prio in priorityList:
        if prio == "name" and name != None:
            anchor = "name", name
            break
        if prio == "code" and code != None:
            anchor = "code", code
            break
        if prio == "id" and id != None:
            anchor = "id", id
            break

    if not anchor:
        return jsonify(dict(err=1, msg="删除失败", data=False))

    bSuc = BEOPDataAccess.getInstance().deleteRpsClient(anchor[0], anchor[1])
    if not bSuc:
        return jsonify(dict(err=1, msg="删除失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))


@bp_rps.route("/updateClient", methods=["POST"])
def update_client():
    rcv = request.get_json()
    id = rcv.get("id", None)
    name = rcv.get("name", None)
    code = rcv.get("code", None)
    address = rcv.get("address", None)

    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="客户ID必须为整数", data=False))
    if name != None and not isinstance(name, str):
        return jsonify(dict(err=1, msg="客户名称必须为字符串", data=False))
    if code != None and not isinstance(code, str):
        return jsonify(dict(err=1, msg="客户编码必须为字符串", data=False))
    if address != None and not isinstance(address, str):
        return jsonify(dict(err=1, msg="地址必须为字符串", data=False))

    updateList = []
    if name != None:
        updateList.append(("name", name))
    if code != None:
        updateList.append(("code", code))
    if address != None:
        updateList.append(("address", address))

    if not len(updateList):
        return jsonify(dict(err=1, msg="无内容可修改", data=False))

    bSuc = BEOPDataAccess.getInstance().updateRpsClient(id, updateList)
    if not bSuc:
        return jsonify(dict(err=1, msg="更新失败", data=False))
    return jsonify(dict(err=0, msg="更新成功", data=True))

@bp_rps.route("/getClient", methods=["POST"])
def get_client():
    rcv = request.get_json()
    id = rcv.get("id", None)
    name = rcv.get("name", None)
    code = rcv.get("code", None)

    if id != None and not isinstance(id, int):
        return jsonify(dict(err=1, msg="客户ID必须为整数", data=[]))
    if name != None and not isinstance(name, str):
        return jsonify(dict(err=1, msg="客户名称必须为字符串", data=[]))
    if code != None and not isinstance(code, str):
        return jsonify(dict(err=1, msg="客户编码必须为字符串", data=[]))

    anchor = ()
    priorityList = ["id", "code", "name"]
    for prio in priorityList:
        if prio == "name" and name != None:
            anchor = "name", name
            break
        if prio == "code" and code != None:
            anchor = "code", code
            break
        if prio == "id" and id != None:
            anchor = "id", id
            break

    result = BEOPDataAccess.getInstance().getRpsClient(anchor)
    if result == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="查询成功", data=result))

@bp_rps.route("/enableClient", methods=["POST"])
def enable_client():
    rcv = request.get_json()
    id = rcv.get("id", None)
    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="客户ID必须为整形", data=False))
    bSuc = BEOPDataAccess.getInstance().enableRpsClient(id)
    if not bSuc:
        return jsonify(dict(err=1, msg="启用客户失败", data=False))
    return jsonify(dict(err=0, msg="启用客户成功", data=True))


@bp_rps.route("/addAttachmentToContract", methods=["POST"])
def add_attachment_to_contract():
    id = request.form.get("contractId", None) #这里都要求前端不要给id这样的无意义类的通用英文名是为了方便理解，看到contractId就知道是要给订单id
    userId = request.form.get("userId", None)
    deadline = request.form.get("deadline", None)

    fileList = []
    for i in range(0, 10):
        file = request.files.get("file{0:02d}".format(i))
        if file is None or not isinstance(file.content_type, str):
            continue
        fileList.append(file)

    if is_digit(id):
        id = int(float(id))

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if not len(fileList):
        return jsonify(dict(err=1, msg="未发现文件", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", id, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, id)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus not in [0, 1, 13]:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    maxFileId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_attachment")
    if maxFileId == None:
        return jsonify(dict(err=1, msg="获取附件表最大ID失败", data=False))

    fileId = maxFileId + 1

    attachmentFileInfoList = []
    fileIdList = []
    fileNameList = []
    for file in fileList:
        strExt = os.path.splitext(file.filename)[1]

        fileName = "{fileId}_{originalName}".format(fileId=fileId, originalName=file.filename)
        fileNameList.append(fileName)

        tempFilePath = os.path.join(tempDir, fileName)

        file.stream.read()
        file.stream.seek(0)
        file.save(tempFilePath)

        bSuc = upload_to_oss(tempFilePath, fileName, OSS_CONFIG["folderName"])

        fileIdList.append(fileId)

        nType = -1
        ossPath = ""
        enabled = 1
        if bSuc:
            nType = ATTACHMENT_TYPE.get(strExt.lower(), -1)
            ossPath = "https://{bucketName}.{region}/{folderName}/{fileName}".format(
                bucketName=OSS_CONFIG["bucketName"],
                region=OSS_CONFIG["region"],
                folderName=OSS_CONFIG["folderName"],
                fileName=fileName)

        attachmentFileInfoList.append(
            (fileId, fileName, nType, ossPath, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), enabled)
        )
        time.sleep(0.2)
        fileId += 1

    bSuc = BEOPDataAccess.getInstance().addRpsAttachment(attachmentFileInfoList)
    if not bSuc:
        return jsonify(dict(err=1, msg="将文件信息存入附件表失败", data=False))

    # 若订单处于未提交校核则直接修改
    if curStatus == 0:
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfContract(id)
        if attachmentIdList == None:
            return jsonify(dict(err=1, msg="订单当前附件id列表获取失败", data=False))

        attachmentIdList.extend(fileIdList)

        attachmentIdList = list(set(attachmentIdList))

        updateList = [("attachment_id", ",".join([str(attachmentId) for attachmentId in attachmentIdList]))]
        bSuc = BEOPDataAccess.getInstance().updateRpsContract(id, updateList)

    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nType = 1  # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1  # 审核结果初始值-1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfContract(id)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="订单当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        targetFileIdList.extend(fileIdList)
        targetFileIdList = list(set(targetFileIdList))

        dTarget.update({"fileIdList": targetFileIdList})

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [id]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, id, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

    for fileName in fileNameList:
        path = os.path.join(tempDir, fileName)
        if os.path.exists(path):
            os.remove(path)

    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteAttachmentOfContract", methods=["POST"])
def delete_attachment_to_contract():
    rcv = request.get_json()
    contractId = rcv.get("contractId", None)
    fileIdList = rcv.get("fileIdList", [])
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    if not isinstance(contractId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if not len(fileIdList):
        return jsonify(dict(err=1, msg="未发现需删除的文件ID列表", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, contractId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus not in [0, 1, 13]:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0: # 未提交到校核则直接删除
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfContract(contractId)
        for fileId in fileIdList:
            if not is_digit(fileId):
                continue

            nFileId = int(float(fileId))
            if nFileId in attachmentIdList:
                attachmentIdList.remove(nFileId)

        dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
        if dFileInfo == None:
            return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

        attachmentFileNameList = []
        for value in dFileInfo.values():
            fName = value.get("fileName", "")
            if fName:
                attachmentFileNameList.append(fName)

        strAttachment = ",".join([str(nId) for nId in attachmentIdList])

        sqlContract = "UPDATE rps_contract SET attachment_id=%s WHERE id=%s"
        paramContract = [strAttachment, contractId]

        sqlAttach = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
        paramAttach = [(fileId,) for fileId in fileIdList]

        queryList = [sqlContract, sqlAttach]
        paramList = [tuple(paramContract), tuple(paramAttach)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        bSuc = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if not bSuc:
            return jsonify(dict(err=1, msg="从OSS删除文件失败", data=False))
        return jsonify(dict(err=0, msg="", data=True))

    else:  # 若在订单在进行中则先投入审核
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nType = 1  # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfContract(contractId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="订单当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        for fileId in fileIdList:
            if fileId in targetFileIdList:
                targetFileIdList.remove(fileId)

        dTarget.update({"fileIdList": targetFileIdList})

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [contractId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, contractId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))


@bp_rps.route("/addContract", methods=["POST"])
def add_contract():
    rcv = request.get_json()
    userId = rcv.get("userId", None)
    clientId = rcv.get("clientId", None)
    salesId = rcv.get("salesId", None)
    clientContact = rcv.get("clientContact", None)
    deliveryTime = rcv.get("deliveryTime", "")
    dueTime = rcv.get("dueTime", "")
    amount = rcv.get("amount", None)

    if is_digit(userId):
        userId = int(float(userId))

    if is_digit(clientId):
        clientId = int(float(clientId))

    if is_digit(salesId):
        salesId = int(float(salesId))

    if is_digit(amount):
        amount = int(float(amount))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(clientId, int):
        return jsonify(dict(err=1, msg="客户ID必须为整数", data=False))
    if not isinstance(salesId, int):
        return jsonify(dict(err=1, msg="销售员ID必须为整数", data=False))
    if not isinstance(clientContact, str):
        return jsonify(dict(err=1, msg="客户联系人有误", data=False))

    if deliveryTime != None and not isinstance(deliveryTime, str):
        return jsonify(dict(err=1, msg="开始发货日期必须为字符串", data=False))
    if deliveryTime != None and len(deliveryTime) and not isValidDate(deliveryTime, "%Y-%m-%d"):
        return jsonify(dict(err=1, msg="开始发货日期格式有误（%Y-%m-%d）", data=False))

    if dueTime != None and not isinstance(dueTime, str):
        return jsonify(dict(err=1, msg="截止到货日期必须为字符串", data=False))
    if dueTime != None and len(dueTime) and not isValidDate(dueTime, "%Y-%m-%d"):
        return jsonify(dict(err=1, msg="截止到货日期格式有误(%Y-%m-%d)", data=False))

    # if auditDeadline != None:
    #     if not isinstance(auditDeadline, str):
    #         return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
    #     if not isValidDate(auditDeadline, "%Y-%m-%d"):
    #         return jsonify(dict(err=1, msg="审核截止日期格式有误(%Y-%m-%d)", data=False))
    #     if datetime.strptime(auditDeadline, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
    #         return jsonify(dict(err=1, msg="审核截止不得小于当前日期", data=False))
    #     auditDeadline = auditDeadline + " 00:00:00"

    if deliveryTime:
        if datetime.strptime(deliveryTime, "%Y-%m-%d") < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="建议开始发货日期不能小于当前日期", data=False))

    if dueTime:
        if datetime.strptime(dueTime, "%Y-%m-%d") < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="截止到货日期不能小于当前日期", data=False))

    if dueTime and deliveryTime:
        if datetime.strptime(deliveryTime, "%Y-%m-%d") > datetime.strptime(dueTime, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="开始发货日期不能大于截止到货日期", data=False))

    if amount != None:
        if not isinstance(amount, float) and not isinstance(amount, int):
            return jsonify(dict(err=1, msg="金额必须为数字", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bClientIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", clientId, "rps_client")
    if not bClientIdExists:
        return jsonify(dict(err=1, msg="客户ID不存在", data=False))

    dSalesIdInfo = BEOPDataAccess.getInstance().get_user_info(salesId)
    if not dSalesIdInfo:
        return jsonify(dict(err=1, msg="销售员ID不存在", data=False))

    strAttachmentId = ""  # 附件ID字符串
    nStatus = 0  # 初始订单状态

    maxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_contract")
    nId = maxId + 1

    # 插入订单记录
    sqlCont = "INSERT INTO rps_contract (id, client_id, sales_id, client_contact, attachment_id, create_time, status, creator_id"
    strValues = ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s"
    paramCont = [nId, clientId, salesId, clientContact, strAttachmentId, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nStatus, userId]
    if deliveryTime:
        sqlCont += ",delivery_time"
        strValues += ",%s"
        paramCont.append(deliveryTime)
    if dueTime:
        sqlCont += ",due_time"
        strValues += ",%s"
        paramCont.append(dueTime)
    if amount != None:
        sqlCont += ",amount"
        strValues += ",%s"
        paramCont.append(amount)
    sqlCont += strValues
    sqlCont += ")"

    quaryList = [sqlCont]
    paramList = [(tuple(paramCont),)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteContract", methods=["POST"])
def delete_contract():
    rcv = request.get_json()
    id = rcv.get("id", None)
    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="订单ID有误", data=False))

    attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfContract(id)
    if attachmentIdList == None:
        return jsonify(dict(err=1, msg="获取订单的附件ID列表失败", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, id)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 0:
        return jsonify(dict(err=1, msg="当前状态为{cur}，无法执行该操作".format(cur=curStatus), data=False))

    dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(attachmentIdList)
    if dFileInfo == None:
        return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

    attachmentFileNameList = []
    for value in dFileInfo.values():
        fName = value.get("fileName", "")
        if fName:
            attachmentFileNameList.append(fName)

    bSucDel = False
    count = 0
    while count < 5:
        bSucDel = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if bSucDel:
            break
        time.sleep(0.2)
        count += 1

    nType = 1 # 销售订单

    # 禁用附件
    sqlDis = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
    paramDis = [(fileId,) for fileId in attachmentIdList]

    # 删除订单记录
    sqlDel1 = "DELETE FROM rps_contract WHERE id=%s"
    paramDel1 = (id,)

    sqlDel2 = "DELETE FROM rps_contract_asset_template WHERE contract_id=%s"
    paramDel2 = (id,)

    queryList = [sqlDel1, sqlDel2]
    paramList = [(paramDel1,), (paramDel2,)]

    if len(attachmentIdList):
        queryList.append(sqlDis)
        paramList.append(tuple(paramDis))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="删除失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))


@bp_rps.route("/updateContract", methods=["POST"])
def update_contract():
    rcv = request.get_json()
    id = rcv.get("id", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    clientId = rcv.get("clientId", None)
    salesId = rcv.get("salesId", None)
    clientContact = rcv.get("clientContact", None)
    deliveryTime = rcv.get("deliveryTime", None)
    dueTime = rcv.get("dueTime", None)
    amount = rcv.get("amount", None)

    clientIdOrig = rcv.get("clientIdOrig", None)
    salesIdOrig = rcv.get("salesIdOrig", None)
    clientContactOrig = rcv.get("clientContactOrig", None)
    deliveryTimeOrig = rcv.get("deliveryTimeOrig", None)
    dueTimeOrig = rcv.get("dueTimeOrig", None)
    amountOrig = rcv.get("amountOrig", None)

    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="订单ID有误", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", id, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    if clientId != None:
        if not isinstance(clientId, int):
            return jsonify(dict(err=1, msg="客户ID必须为整数", data=False))
        bClientExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", clientId, "rps_client")
        if not bClientExists:
            return jsonify(dict(err=1, msg="客户ID不存在", data=False))

    if clientIdOrig != None:
        if not isinstance(clientIdOrig, int):
            return jsonify(dict(err=1, msg="客户ID必须为整数", data=False))
        bClientExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", clientIdOrig, "rps_client")
        if not bClientExists:
            return jsonify(dict(err=1, msg="客户ID不存在", data=False))

    if salesId != None:
        if not isinstance(salesId, int):
            return jsonify(dict(err=1, msg="销售ID必须为整数", data=False))
        dUserInfo = BEOPDataAccess.getInstance().get_user_info(salesId)
        if not dUserInfo:
            return jsonify(dict(err=1, msg="salesId不存在", data=False))

    if salesIdOrig != None:
        if not isinstance(salesIdOrig, int):
            return jsonify(dict(err=1, msg="销售ID必须为整数", data=False))
        dUserInfo = BEOPDataAccess.getInstance().get_user_info(salesIdOrig)
        if not dUserInfo:
            return jsonify(dict(err=1, msg="salesId不存在", data=False))

    if clientContact != None:
        if not isinstance(clientContact, str):
            return jsonify(dict(err=1, msg="客户联系人必须为字符串", data=False))

    if clientContactOrig != None:
        if not isinstance(clientContactOrig, str):
            return jsonify(dict(err=1, msg="客户联系人必须为字符串", data=False))

    if deliveryTime != None:
        if not isinstance(deliveryTime, str):
            return jsonify(dict(err=1, msg="开始发货时间必须为字符串", data=False))
        if not isValidDate(deliveryTime, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="开始发货时间格式有误", data=False))
        if datetime.strptime(deliveryTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="建议开始发货时间不能小于当前时间", data=False))

    if deliveryTimeOrig != None:
        if not isinstance(deliveryTimeOrig, str):
            return jsonify(dict(err=1, msg="开始发货时间必须为字符串", data=False))
        if not isValidDate(deliveryTimeOrig, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="开始发货时间格式有误", data=False))

    if dueTime != None:
        if not isinstance(dueTime, str):
            return jsonify(dict(err=1, msg="过期时间必须为字符串", data=False))
        if not isValidDate(dueTime, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="过期时间格式有误", data=False))
        if datetime.strptime(dueTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="截止日期不能小于当前时间", data=False))

    if dueTimeOrig != None:
        if not isinstance(dueTimeOrig, str):
            return jsonify(dict(err=1, msg="过期时间必须为字符串", data=False))
        if not isValidDate(dueTimeOrig, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="截止日期格式有误", data=False))

    if deliveryTime and dueTime:
        if datetime.strptime(deliveryTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) > datetime.strptime(dueTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify(dict(err=1, msg="建议开始发货时间不能大于截止日期", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    if is_digit(amount):
        amount = float(amount)

    if is_digit(amountOrig):
        amountOrig = float(amountOrig)

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, id)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取订单状态失败", data=False))

    if curStatus not in [0, 1, 13]:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:
        updateList = []
        if clientId != None:
            updateList.append(("client_id", clientId))
        if salesId != None:
            updateList.append(("sales_id", salesId))
        if clientContact != None:
            updateList.append(("client_contact", clientContact))
        if deliveryTime != None:
            updateList.append(
                ("delivery_time", datetime.strptime(deliveryTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))
            )
        if dueTime != None:
            updateList.append(
                ("due_time", datetime.strptime(dueTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))
            )
        if amount != None:
            updateList.append(("amount", amount))

        if not len(updateList):
            return jsonify(dict(err=1, msg="未发现需修改的内容", data=False))

        bSuc = BEOPDataAccess.getInstance().updateRpsContract(id, updateList)
        if not bSuc:
            return jsonify(dict(err=1, msg="更新失败", data=False))
        return jsonify(dict(err=0, msg="更新成功", data=True))

    elif curStatus == 1 or curStatus == 13:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 1 # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}
        if clientIdOrig != None:
            dOriginal.update({"clientIdOrig": clientIdOrig})
        if salesIdOrig != None:
            dOriginal.update({"salesIdOrig": salesIdOrig})
        if clientContactOrig != None:
            dOriginal.update({"clientContactOrig": clientContactOrig})
        if deliveryTimeOrig != None:
            dOriginal.update({"deliveryTimeOrig": datetime.strptime(deliveryTimeOrig, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")})
        if dueTimeOrig != None:
            dOriginal.update({"dueTimeOrig": datetime.strptime(dueTimeOrig, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")})
        if amountOrig != None:
            dOriginal.update({"amountOrig": amountOrig})

        if clientId != None:
            dTarget.update({"clientId": clientId})
        if salesId != None:
            dTarget.update({"salesId": salesId})
        if clientContact != None:
            dTarget.update({"clientContact": clientContact})
        if deliveryTime != None:
            dTarget.update({"deliveryTime": datetime.strptime(deliveryTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")})
        if dueTime != None:
            dTarget.update({"dueTime": datetime.strptime(dueTime, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")})
        if amount != None:
            dTarget.update({"amount": amount})

        if not dOriginal and not dTarget:
            return jsonify(dict(err=1, msg="未发现需修改的内容", data=False))

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [id]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, id, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/getContract", methods=["POST"])
def get_contract():
    rcv = request.get_json()
    id = rcv.get("id", None)
    clientId = rcv.get("clientId", None)
    salesId = rcv.get("salesId", None)

    if id != None:
        if not isinstance(id, int):
            return jsonify(dict(err=1, msg="订单ID必须为整数", data=[]))

    if clientId != None:
        if not isinstance(clientId, int):
            return jsonify(dict(err=1, msg="客户ID必须为整数", data=[]))

    if salesId != None:
        if not isinstance(salesId, int):
            return jsonify(dict(err=1, msg="销售员ID必须为整数", data=[]))

    checkList = []
    if id != None:
        checkList.append(("id", id))
    if clientId != None:
        checkList.append(("client_id", clientId))
    if salesId != None:
        checkList.append(("sales_id", salesId))

    dataList = BEOPDataAccess.getInstance().getRpsContract(checkList)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

    procFileIdList = []
    contractIdList = []
    for data in dataList:
        attachment = data.get("attachment", {})
        if attachment:
            fileIdList = list(attachment.keys())
            procFileIdList.extend(fileIdList)
        contractIdList.append(data.get("id"))

    dAttachmentFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(procFileIdList)
    if dAttachmentFileInfo == None:
        return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

    dAssetInfo = BEOPDataAccess.getInstance().getRpsContractAssetInfo(contractIdList)
    if dAssetInfo == None:
        return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

    dCheckAudit = BEOPDataAccess.getInstance().getRpsCheckAndAuditRecords(contractIdList, 1)
    if dCheckAudit == None:
        return jsonify(dict(err=1, msg="校核、审核信息查询失败", data=[]))

    for data in dataList:
        for attachmentId in data.get("attachment", {}).keys():
            dFile = dAttachmentFileInfo.get(attachmentId, {})
            if dFile:
                data.get("attachment").get(attachmentId).update(dFile)

        # 判断附件是否在审核单中（审核项为删除）
        auditToDeleteFileIdList = []
        if dCheckAudit.get(data["id"], {}):
            if dCheckAudit.get(data["id"]).get("editAudit", []):
                editAuditList = dCheckAudit.get(data["id"]).get("editAudit")
                for dEditAudit in editAuditList:
                    if dEditAudit.get("original", {}) and dEditAudit.get("target", {}):
                        if "fileIdList" in dEditAudit.get("original").keys() and "fileIdList" in dEditAudit.get("target").keys():
                            orignalList = dEditAudit.get("original").get("fileIdList")
                            targetList = dEditAudit.get("target").get("fileIdList")
                            for originalId in orignalList:
                                if originalId not in targetList:
                                    auditToDeleteFileIdList.append(originalId)

        dAttachment = data.get("attachment", {})
        lAttachment = []
        for attachId, dAttachInfo in dAttachment.items():
            dAttachInfo.update(dict(status=1))
            if attachId in auditToDeleteFileIdList:
                dAttachInfo.update(dict(status=-1))
            lAttachment.append(dAttachInfo)

        data.update({"attachment": lAttachment})
        data.update(dict(asset=dAssetInfo.get(data["id"])))

        data.update(dict(check=dCheckAudit.get(data["id"], {}).get("check", [])))
        data.update(dict(createAudit=dCheckAudit.get(data["id"], {}).get("createAudit", [])))
        data.update(dict(editAudit=dCheckAudit.get(data["id"], {}).get("editAudit", [])))
        data.update(dict(terminateAudit=dCheckAudit.get(data["id"], {}).get("terminateAudit", [])))
        data.update(dict(finishAudit=dCheckAudit.get(data["id"], {}).get("finishAudit", [])))

    return jsonify(dict(err=0, msg="查询成功", data=dataList))


@bp_rps.route("/addWarehouse", methods=["POST"])
def add_warehouse():
    rcv = request.get_json()
    name = rcv.get("name", None)
    address = rcv.get("address", "")
    adminId = rcv.get("adminId", None)
    nType = rcv.get("type", None)
    location = rcv.get("location", "")

    if not isinstance(name, str):
        return jsonify(dict(err=1, msg="名称必须为字符串", data=False))
    if address:
        if not isinstance(address, str):
            return jsonify(dict(err=1, msg="仓库地址必须为字符串", data=False))
    if adminId:
        if not isinstance(adminId, str):
            return jsonify(dict(err=1, msg="管理员ID必须为字符串", data=False))

    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="仓库类型必须为整形", data=False))

    strLoc = ""
    if location:
        if not isinstance(location, str):
            return jsonify(dict(err=1, msg="仓库经纬度必须为字符串", data=False))
        dLocation, strMsg = get_lon_and_lat(location)
        if strMsg:
            return jsonify(dict(err=1, msg=strMsg, data=False))
        strLoc = "{lon},{lat}".format(lon=dLocation["lon"], lat=dLocation["lat"])

    adminName = None
    if adminId != None:
        userNameEn = None
        userInfoList = BEOPDataAccess.getInstance().get_all_users()
        for userInfo in userInfoList:
            if str(userInfo.get("userid")) == str(adminId):
                adminName = userInfo.get("username_zh", None)
                userNameEn = userInfo.get("username", None)
                break

        if adminName == None:
            authDict = RedisManager.get("FaultAuthInfo")
            if authDict:
                if userNameEn != None:
                    adminName = authDict.get(userNameEn, {}).get("name_zh", "")

    maxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_warehouse")
    nId = maxId + 1

    # code 与id一致
    code = str(nId)

    insertList = [("id", nId), ("name", name), ("type", nType), ("code", code)]
    if address:
        insertList.append(("address", address))
    if adminId != None:
        insertList.append(("admin_id", adminId))
        if adminName == None:
            adminName = ""
        insertList.append(("admin_name", adminName))
    if strLoc:
        insertList.append(("location", strLoc))

    bSuc = BEOPDataAccess.getInstance().addRpsWarehouse(insertList)

    if not bSuc:
        return jsonify(dict(err=1, msg="创建仓库失败", data=False))
    return jsonify(dict(err=0, msg="创建仓库成功", data=True))


@bp_rps.route("/deleteWarehouse", methods=["POST"])
def delete_warehouse():
    rcv = request.get_json()
    id = rcv.get("id", None)
    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整形", data=False))

    bSuc = BEOPDataAccess.getInstance().deleteRpsWarehouse(id)
    if not bSuc:
        return jsonify(dict(err=1, msg="删除仓库失败", data=False))
    return jsonify(dict(err=0, msg="删除仓库成功", data=True))


@bp_rps.route("/enableWarehouse", methods=["POST"])
def enable_warehouse():
    rcv = request.get_json()
    id = rcv.get("id", None)
    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整形", data=False))

    bSuc = BEOPDataAccess.getInstance().enableRpsWarehouse(id)
    if not bSuc:
        return jsonify(dict(err=1, msg="启用仓库失败", data=False))
    return jsonify(dict(err=0, msg="启用仓库成功", data=True))


@bp_rps.route("/updateWarehouse", methods=["POST"])
def update_warehouse():
    rcv = request.get_json()
    id = rcv.get("id", None)
    name = rcv.get("name", None)
    address = rcv.get("address", None)
    adminId = rcv.get("adminId", None)
    adminName = rcv.get("adminName", None)
    nType = rcv.get("type", None)
    location = rcv.get("location", None)

    if not isinstance(id, int):
        return jsonify(dict(err=1, msg="仓库ID有误", data=False))
    if name != None:
        if not isinstance(name, str):
            return jsonify(dict(err=1, msg="仓库名称必须为字符串", data=False))
    if address != None:
        if not isinstance(address, str):
            return jsonify(dict(err=1, msg="仓库地址必须为字符串", data=False))
    if adminId != None:
        if not isinstance(adminId, str):
            return jsonify(dict(err=1, msg="仓库管理员ID必须为字符串", data=False))
    if adminName != None:
        if not isinstance(adminName, str):
            return jsonify(dict(err=1, msg="仓库管理员名称必须为字符串", data=False))
    if nType != None:
        if nType not in [0, 1, 2]:
            return jsonify(dict(err=1, msg="仓库类型有误", data=False))

    strLoc = ""
    if location != None:
        if not isinstance(location, str):
            return jsonify(dict(err=1, msg="仓库经纬度必须为字符串", data=False))

        if len(location):
            dLocation, strMsg = get_lon_and_lat(location)
            if strMsg:
                return jsonify(dict(err=1, msg=strMsg, data=False))
            strLoc = "{lon},{lat}".format(lon=dLocation["lon"], lat=dLocation["lat"])

    updateList = []
    if name != None:
        updateList.append(("name", name))
    if address != None:
        updateList.append(("address", address))
    if adminId != None:
        updateList.append(("admin_id", adminId))
    if adminName != None:
        updateList.append(("admin_name", adminName))
    if nType != None:
        updateList.append(("type", nType))
    if location != None and strLoc:
        updateList.append(("location", strLoc))

    if not len(updateList):
        return jsonify(dict(err=1, msg="无需更新", data=False))

    bSuc = BEOPDataAccess.getInstance().updateRpsWarehouse(id, updateList)
    if not bSuc:
        return jsonify(dict(err=1, msg="更新仓库信息失败", data=False))
    return jsonify(dict(err=0, msg="更新仓库信息成功", data=True))

@bp_rps.route("/getWarehouse", methods=["POST"])
def get_warehouse():
    rcv = request.get_json()
    id = rcv.get("id", None)
    nType = rcv.get("type", None)

    if id != None:
        if not isinstance(id, int):
            return jsonify(dict(err=1, msg="仓库ID必须为整数", data=False))

    if nType != None:
        if nType not in [0, 1, 2]:
            return jsonify(dict(err=1, msg="仓库类型有误", data=False))

    checkList = []
    if id != None:
        checkList.append(("id",id))
    if nType != None:
        checkList.append(("type", nType))

    result = BEOPDataAccess.getInstance().getRpsWarehouse(checkList)
    if result == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="查询成功", data=result))


@bp_rps.route("/importAssetMulti", methods=["POST"])
def import_asset_multi():
    file = request.files.get('file')
    fileName = file.filename
    if not fileName.endswith(".xlsx"):
        return jsonify(dict(err=1, msg="仅支持.xlsx文件", data=False))

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    nameWithoutExt = os.path.splitext(fileName)[0]
    strExt = os.path.splitext(fileName)[1]

    tempFilePath = os.path.join(tempDir, "{name}_{time}.{ext}".format(name=nameWithoutExt, time=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"), ext=strExt))
    file.stream.read()
    file.stream.seek(0)
    file.save(tempFilePath)

    if not os.path.exists(tempFilePath):
        return jsonify(dict(err=1, msg="导入失败，因暂存.xlsx文件失败", data=False))

    book = xlrd.open_workbook(tempFilePath)
    sheet = book.sheet_by_index(0)
    nRows = sheet.nrows

    errDuplicateList = []
    errExistingList = []
    errUnknownTemplateIdList = []
    errInvalidAssetCode = []

    templateIdPreCheckList = []
    dData = {}

    # {4: "生产商", 5:"生产日期", 6: "成本"}
    dHeaderIndexContent = {}
    for idx in range(nRows):
        if idx == 0:
            values = sheet.row_values(idx)
            dHeaderIndexContent = process_equip_import_table_header(values)
            continue

        values = sheet.row_values(idx)
        equipName = values[1]
        templateId = str(int(float(values[2])))
        assetCode = values[3]   # assetCode 在导入表格中，单元格格式应为文本
        if len(assetCode) > ASSET_CODE_LENGTH:
            errInvalidAssetCode.append(assetCode)
            continue

        if assetCode in dData.keys():
            if assetCode in dData.keys():
                del dData[assetCode]
            errDuplicateList.append(assetCode)
            continue

        templateIdPreCheckList.append(templateId)

        # {4: "SIEMENS", 5: "2022-01-01", 6: "10000"}
        dAssetOfRow = {}
        for j in range(4, len(values)):
            if values[j] == None or values[j] == "":
                continue

            dAssetOfRow.update({j: values[j]})

        dData.update({assetCode: (equipName, templateId, dAssetOfRow)})
    """
    {
        35: {"生产商": "manufacture", "生产日期": "date", "成本": "cost"},
        36: {...}
    }
    """
    equipAssetTmplDetail = BEOPDataAccess.getInstance().getEquipAssetTmpl(templateIdPreCheckList)

    existingList = BEOPDataAccess.getInstance().getAlreadyExistingAsset(list(dData.keys()))
    if existingList == None:
        return jsonify(dict(err=1, msg="检查设备编号是否已存在失败", data=False))

    if len(existingList):
        for asset in existingList:
            errExistingList.append("{code}(设备名称:{name})".format(name=asset[0], code=asset[1]))
            if asset[1] in dData.keys():
                del dData[asset[1]]

    # 检查模板ID是否存在
    checkList = BEOPDataAccess.getInstance().getAlreadyExistingTemplateId(templateIdPreCheckList)
    if checkList == None or not isinstance(checkList, list):
        return jsonify(dict(err=1, msg="模板设备ID存在性检查失败", data=False))

    nMaxIdEquipList = BEOPDataAccess.getInstance().getMaxIdInTable("equip_list")
    nEquipListTableId = nMaxIdEquipList + 1
    postList = []
    equipAssetTablePost = []
    for assetCode, (equipName, templateId, dAssetOfRow) in dData.items():
        try:
            if templateId not in checkList:
                errUnknownTemplateIdList.append("{templateId}(设备编码:{code},设备名称:{name})".format(templateId=templateId, code=assetCode, name=equipName))
                continue

            defaultEquipType = ""
            projectId = 0
            description = ""
            maintenanceStatus = 0
            repairStatus = 0
            repairResponsiblePerson = ""
            installLocation = ""
            communicateStatus = 0
            warningStatus = 0
            areaId = 0
            systemId = 1

            postList.append(
                (nEquipListTableId, defaultEquipType, projectId, equipName, description, assetCode, maintenanceStatus, repairStatus,
                 repairResponsiblePerson, installLocation, communicateStatus, warningStatus, areaId, templateId, systemId)
            )

            dAssetTmpl = equipAssetTmplDetail.get(int(templateId), None)
            if dAssetTmpl == None:
                continue

            for colIdx, colContent in dAssetOfRow.items():
                if dHeaderIndexContent.get(colIdx, None) == None:
                    continue

                paramCnContent = dHeaderIndexContent.get(colIdx)
                if dAssetTmpl.get(paramCnContent, None) == None:
                    continue

                paramEnContent = dAssetTmpl.get(paramCnContent)
                paramValue = colContent

                equipAssetTablePost.append(
                    (nEquipListTableId, paramEnContent, paramValue, projectId)
                )

        except:
            pass
        finally:
            nEquipListTableId += 1

    bSuc1 = BEOPDataAccess.getInstance().addRpsEquipMulti(postList)

    bSuc2 = BEOPDataAccess.getInstance().updateAssetMulti(equipAssetTablePost)

    strErrMsg = ""
    if len(errExistingList):
        strErrMsg += "\n以下设备编码已存在于数据库，故在导入过程已跳过这些编码对应的设备:" + ",".join(errExistingList) + "\n"

    if len(errDuplicateList):
        strErrMsg += "\n以下设备编码在导入的表格中重复"
        for nCode in errDuplicateList:
            strErrMsg += "," + str(nCode)

    if len(errUnknownTemplateIdList):
        strErrMsg += "\n以下设备的模板ID数据库中不存在，故在导入过程中已跳过这些设备:" + ",".join(errUnknownTemplateIdList) + "\n"

    if len(errInvalidAssetCode):
        strErrMsg += "\n以下资产编码字符串超过长度上限，故在导入过程中已跳过这些编码对应的设备:" + ",".join(errInvalidAssetCode) + "\n"

    if not bSuc1 or not bSuc2:
        return jsonify(dict(err=1, msg="导入失败"+strErrMsg, data=False))
    return jsonify(dict(err=0, msg="导入成功"+strErrMsg, data=True))

@bp_rps.route("/getAssetImportTemplateFile")
def get_asset_import_template_file():
    filePath = os.path.join(app.static_folder, "files", "asset_template", "rps_equip_import.xlsx")
    if not os.path.exists(filePath):
        return jsonify(dict(err=1, msg="rps_equip_import.xlsx文件不存在", data=""))
    return jsonify(dict(err=0, msg="", data="rps_equip_import.xlsx"))

@bp_rps.route("/keywordSearchAssetCode", methods=["POST"])
def keyword_search_asset_code():
    rcv = request.get_json()
    keyword = rcv.get("keyword", None)
    if not isinstance(keyword, str):
        return jsonify(dict(err=1, msg="关键字必须为字符串", data=[]))

    result = BEOPDataAccess.getInstance().keywordSearchRpsAssetCode(keyword)
    if result == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="查询成功", data=result))

@bp_rps.route("/addRFID", methods=["POST"])
def add_rfid():
    rcv = request.get_json()
    assetCode = rcv.get("assetCode", None)
    assetTemplateId = rcv.get("assetTemplateId", None)
    if not isinstance(assetCode, str):
        return jsonify(dict(err=1, msg="资产编码不能为空且必须为字符串", data=""))

    if len(assetCode) != ASSET_CODE_LENGTH:
        return jsonify(dict(err=1, msg="资产编码长度有误", data=""))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("online_addr", assetCode, "equip_list")
    if not bExists:
        return jsonify(dict(err=1, msg="该资产编码不存在", data=""))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", assetTemplateId, "equip_asset_tmpl_def")
    if not bExists:
        return jsonify(dict(err=1, msg="该资产模板ID不存在", data=""))

    labelIndexList, rfidCodeList = BEOPDataAccess.getInstance().getLabelIndexAndRFIDOfAsset(assetCode)
    if labelIndexList == None:
        return jsonify(dict(err=1, msg="最大标签数查询失败", data=""))

    maxLabelIndex = 0
    if len(labelIndexList):
        maxLabelIndex = max(labelIndexList)

        if maxLabelIndex >= RFID_MAX_LABEL_INDEX_OF_ONE_ASSET:
            return jsonify(dict(err=1, msg="最大标签数已达上限", data=""))

    nLabelIndex = maxLabelIndex + 1

    strFRID = "{assetCode}{nLabelIndex}{assetTemplateId:03d}".format(assetCode=assetCode,
                                                                     nLabelIndex=nLabelIndex,
                                                                     assetTemplateId=assetTemplateId)

    bSuc = BEOPDataAccess.getInstance().addRFID(assetCode, nLabelIndex, assetTemplateId, strFRID)
    if not bSuc:
        return jsonify(dict(err=1, msg="FRID添加失败", data=""))
    return jsonify(dict(err=0, msg="FRID添加成功", data=strFRID))


@bp_rps.route("/updateRFID", methods=["POST"])
def update_rfid():
    rcv = request.get_json()
    assetCode = rcv.get("assetCode", None)
    assetTemplateId = rcv.get("templateId", None)
    userId = rcv.get("userId", None)
    actuatorId = rcv.get("actuatorId", None)
    rfidCodeList = rcv.get("rfidCodeList", None)

    if not isinstance(assetCode, str):
        return jsonify(dict(err=1, msg="资产编码应为字符串", data={}))
    if len(assetCode) != ASSET_CODE_LENGTH:
        return jsonify(dict(err=1, msg="资产编码长度有误", data={}))
    if not isinstance(assetTemplateId, int):
        return jsonify(dict(err=1, msg="资产模板ID应为整数", data={}))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId应为整数", data={}))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data={}))
    if not isinstance(rfidCodeList, list):
        return jsonify(dict(err=1, msg="rfidCodeList必须为列表", data={}))

    failMsgList = []

    oldCodeList = []
    newCodeList = []
    for item in rfidCodeList:
        if item.get("old", None):
            oldCodeList.append(item.get("old"))
        if item.get("new", None):
            newCode = item.get("new")
            if len(newCode) != RFID_CODE_LENGTH:
                failMsgList.append(dict(code=newCode, cause="该码为需存入的新RFID码，但其长度有误"))
            else:
                newCodeList.append(newCode)

    oldCodeList = list(set(oldCodeList))
    newCodeList = list(set(newCodeList))

    dNewCodeExistsCheck = BEOPDataAccess.getInstance().getRpsRFIDByRFIDCodeList(newCodeList)
    if dNewCodeExistsCheck == None:
        return jsonify(dict(err=1, msg="newRFIDCode存在性减查失败", data={}))

    newCodeListToInsert = []
    for newCode in newCodeList:
        if dNewCodeExistsCheck.get(newCode, None) != None:
            failMsgList.append(dict(code=newCode, cause="该码为需存入的新RFID码，但它已存在于数据库"))
            continue

        newCodeListToInsert.append(newCode)

    sqlDelOld = "DELETE FROM rps_rfid WHERE rfid_code in (%s)"
    paramDelOld = [(oldCode,) for oldCode in oldCodeList]

    sqlInsNew = "INSERT INTO rps_rfid (asset_code, label_index, asset_template_id, rfid_code, creator_id, create_time, actuator_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    paramInsNew = []
    createTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for rfidCode in newCodeListToInsert:
        paramInsNew.append(
            (assetCode, int(rfidCode[12:13]), assetTemplateId, rfidCode, userId, createTime, actuatorId)
        )

    queryList = [sqlDelOld]
    paramList = [tuple(paramDelOld)]
    if len(paramInsNew):
        queryList.append(sqlInsNew)
        paramList.append(tuple(paramInsNew))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

    rsData = {}
    if len(failMsgList):
        rsData.update(dict(failedList=failMsgList))

    strErr = "执行成功"
    if len(failMsgList):
        strErr += ",但有一些错误，见data"

    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data={}))
    return jsonify(dict(err=0, msg=strErr, data=rsData))


@bp_rps.route("/searchRFIDByAssetCode", methods=["POST"])
def search_rfid_by_asset_code():
    rcv = request.get_json()
    assetCode = rcv.get("assetCode", None)
    if not isinstance(assetCode, str):
        return jsonify(dict(err=1, msg="资产编码不能为空且必须为字符串", data=[]))

    if len(assetCode) != ASSET_CODE_LENGTH:
        return jsonify(dict(err=1, msg="资产编码字符串长度有误", data=[]))

    labelIndexList, rfidCodeList = BEOPDataAccess.getInstance().getLabelIndexAndRFIDOfAsset(assetCode)
    if labelIndexList == None or rfidCodeList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="查询成功", data=rfidCodeList))

@bp_rps.route("/searchRFID", methods=["POST"])
def search_rfid():
    rcv = request.get_json()
    rfidCode = rcv.get("rfidCode", None)
    if not isinstance(rfidCode, str):
        return jsonify(dict(err=1, msg="rfidCode不能为空且必须为字符串", data=[]))

    if len(rfidCode) != RFID_CODE_LENGTH:
        return jsonify(dict(err=1, msg="RFID码字符串长度有误", data=[]))

    dInfo = BEOPDataAccess.getInstance().searchRFID(rfidCode)
    if dInfo == None:
        return jsonify(dict(err=1, msg="查询失败", data={}))
    return jsonify(dict(err=0, msg="查询成功", data=dInfo))

@bp_rps.route("/deleteRFID", methods=["POST"])
def delete_rfid():
    rcv = request.get_json()
    rfidCode = rcv.get("rfidCode", None)
    if not isinstance(rfidCode, str):
        return jsonify(dict(err=1, msg="rfidCode不能为空且必须为字符串", data=False))

    if len(rfidCode) != RFID_CODE_LENGTH:
        return jsonify(dict(err=1, msg="RFID码字符串长度有误", data=[]))

    bSuc = BEOPDataAccess.getInstance().deleteRFID(rfidCode)
    if not bSuc:
        return jsonify(dict(err=1, msg="删除失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))

"""
定位板事件保送接口
"""
@bp_rps.route("/LBSEventSubmit", methods=["POST"])
def lbs_event_submit():
    rcv = request.get_json()
    lbsId = rcv.get("lbsId", None)
    lon = rcv.get("lon", None)  # 经度
    lat = rcv.get("lat", None)  # 纬度
    lbsPosition = rcv.get("lbsPosition", None)  # 基站位置
    dataPackage = rcv.get("dataPackage", None)  # 数据包
    assetCode = rcv.get("assetCode", None)  # 定位板资产编码

    if not isinstance(lbsId, int):
        return jsonify(dict(err=1, msg="定位板ID必须为整数", data=False))
    if not is_digit(lon):
        return jsonify(dict(err=1, msg="经度必须为数字", data=False))
    if not is_digit(lat):
        return jsonify(dict(err=1, msg="纬度必须为数字", data=False))
    if not isinstance(lbsPosition, str):
        return jsonify(dict(err=1, msg="基站位置必须为字符串", data=False))
    if not isinstance(dataPackage, str):
        return jsonify(dict(err=1, msg="数据包必须为字符串", data=False))
    if not isinstance(assetCode, str):
        return jsonify(dict(err=1, msg="资产编码必须为字符串", data=False))

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_locate_plate_log")
    nId = nMaxId + 1
    strLbsXy = "{lon},{lat}".format(lon=lon, lat=lat)
    nQuality = 1
    strQualityDesc = ""
    nEnabled = 1

    bSuc = BEOPDataAccess.getInstance().addRpsLBSEventLog(nId, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                          lbsId, strLbsXy, lbsPosition, dataPackage, assetCode, nQuality, strQualityDesc, nEnabled)
    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/rfidEventSubmit", methods=["POST"])
def rfid_event_submit():
    rcv = request.get_json()
    rfidCodeList = rcv.get("rfidCodeList", None)
    receiverId = rcv.get("receiverId", None)

    if not isinstance(rfidCodeList, list):
        return jsonify(dict(err=1, msg="rfidCodeList必须为数组", data=False))
    if not isinstance(receiverId, int):
        return jsonify(dict(err=1, msg="接收器ID必须为整数", data=False))

    tempList = []
    for rfidCode in rfidCodeList:
        if len(rfidCode) != RFID_CODE_LENGTH:
            continue

        assetCode = rfidCode[0:12]
        tempList.append(
            (assetCode, rfidCode)
        )

    dAssetCodeWarehouesId = BEOPDataAccess.getInstance().getInstallationOfDevice([item[0] for item in tempList])
    if dAssetCodeWarehouesId == None:
        return jsonify(dict(err=1, msg="获取仓库ID失败", data=False))

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_rfid_log")
    nId = nMaxId + 1

    strTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    param = []
    for assetCode, rfidCode in tempList:
        warehouseId = dAssetCodeWarehouesId.get(assetCode, None)

        quality = 1
        qualityDesc = "正常"
        nEnabled = 1
        if warehouseId == None:
            quality = 2
            qualityDesc = "仓库ID不明"
            warehouseId = -1

        param.append(
            (nId, assetCode, rfidCode, strTime, receiverId, warehouseId, quality, qualityDesc, nEnabled)
        )
        nId += 1

    bSuc = BEOPDataAccess.getInstance().rfidEventSubmit(param)
    if not bSuc:
        return jsonify(dict(err=1, msg="提交失败", data=False))
    return jsonify(dict(err=0, msg="提交成功", data=True))


@bp_rps.route("/addAssetToContract", methods=["POST"])
def add_asset_to_contract():
    rcv = request.get_json()
    nId = rcv.get("contractId", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    assetList = rcv.get("assetList", [])   # [{"templateId": 1, "quantity": 1000}, {}, {}]
    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if not len(assetList):
        return jsonify(dict(err=1, msg="需添加的资产列表不能为空", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    dInfo = {}
    for asset in assetList:
        templateId = asset.get("templateId", None)
        quantity = asset.get("quantity", None)
        if templateId != None:
            if templateId not in dInfo.keys():
                dInfo.update({templateId: 0})

        if quantity != None:
            dInfo[templateId] += quantity

    # 检查模板ID是否存在
    preCheckList = [str(nId) for nId in dInfo.keys()]
    checkList = BEOPDataAccess.getInstance().getAlreadyExistingTemplateId(preCheckList)
    if checkList == None or not isinstance(checkList, list):
        return jsonify(dict(err=1, msg="模板设备ID存在性检查失败", data=False))

    for tmpId in dInfo.keys():
        if str(tmpId) not in checkList:
            return jsonify(dict(err=1, msg="未知模板ID", data=False))

    param = []
    for templateId, quantity in dInfo.items():
        if quantity != 0:
            param.append(
                (nId, templateId, quantity)
            )

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().addAssetToContract(param)
        if not bSuc:
            return jsonify(dict(err=1, msg="添加失败", data=False))
        return jsonify(dict(err=0, msg="添加成功", data=True))

    elif curStatus == 1 or curStatus == 13:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nType = 1  # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dTarget.update({"AddAssetList": param})

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [nId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, nId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(paramStatus)

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/deleteAssetFromContract", methods=["POST"])
def delete_asset_from_contract():
    rcv = request.get_json()
    contractId = rcv.get("contractId", None)
    templateId = rcv.get("templateId", None)
    deadline = rcv.get("deadline", None)
    userId = rcv.get("userId", None)

    if not isinstance(contractId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if not isinstance(templateId, int):
        return jsonify(dict(err=1, msg="模板ID必须为整数", data=False))
    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, contractId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().deleteAssetFromContract(contractId, templateId)
        if not bSuc:
            return jsonify(dict(err=1, msg="删除失败", data=False))
        return jsonify(dict(err=0, msg="删除成功", data=True))

    elif curStatus == 1 or curStatus == 13:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nType = 1  # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dTarget.update(
            {"DeleteAssetList": [(contractId, templateId)]}
        )

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [contractId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, contractId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/updateAssetFromContract", methods=["POST"])
def update_asset_from_contract():
    rcv = request.get_json()
    contractId = rcv.get("contractId", None)
    templateId = rcv.get("templateId", None)
    quantity = rcv.get("quantity", None)
    deadline = rcv.get("deadline", None)
    userId = rcv.get("userId", None)

    if not isinstance(contractId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if not isinstance(templateId, int):
        return jsonify(dict(err=1, msg="模板ID必须为整数", data=False))
    if not isinstance(quantity, int):
        return jsonify(dict(err=1, msg="数量必须为整数", data=False))
    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    checkList = BEOPDataAccess.getInstance().getAlreadyExistingTemplateId([str(templateId)])
    if checkList == None or not isinstance(checkList, list):
        return jsonify(dict(err=1, msg="模板设备ID存在性检查失败", data=False))

    if str(templateId) not in checkList:
        return jsonify(dict(err=1, msg="模板ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(1, contractId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().updateAssetFromContract(contractId, templateId, quantity)
        if not bSuc:
            return jsonify(dict(err=1, msg="更新失败", data=False))
        return jsonify(dict(err=0, msg="更新成功", data=True))

    elif curStatus == 1 or curStatus == 13:
        dInfo = BEOPDataAccess.getInstance().getAssetOfContract(contractId)
        if dInfo == None:
            return jsonify(dict(err=1, msg="获取订单的资产信息失败", data=False))

        quantityOrig = dInfo.get(templateId, 0)

        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nType = 1  # 销售订单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dOriginal.update({"UpdateAsset": dict(contractId=contractId,
                                                      templateId=templateId,
                                                      quantity=quantityOrig)})
        dTarget.update({"UpdateAsset": dict(contractId=contractId,
                                                      templateId=templateId,
                                                      quantity=quantity)})

        sqlStatus = "UPDATE rps_contract SET status=13 WHERE id=%s"
        paramStatus = [contractId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, contractId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/getAssetOfContract", methods=["POST"])
def get_asset_of_contract():
    rcv = request.get_json()
    contractId = rcv.get("contractId", None)
    if not isinstance(contractId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))

    dataList = BEOPDataAccess.getInstance().getAllEquipAssetTmpl(FIXED_ASSET_TEMPLATE_ID_LIST)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))

    toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(contractId, 1, -1)
    if toAuditList == None:
        return jsonify(dict(err=1, msg="获取订单待审核项失败", data=False))

    dAssetAudit = {}
    for item in toAuditList:
        nAuditId = item.get("nAuditId")
        creatorId = item.get("creatorId")
        createTime = item.get("createTime")
        deadline = item.get("deadline")
        if "AddAssetList" in item.get("target", {}):
            contractAddAssetList = item.get("target").get("AddAssetList")
            for param in contractAddAssetList:
                templateId = param[1]
                quantity = param[2]
                if templateId not in dAssetAudit.keys():
                    dAssetAudit.update({templateId: dict(delete=[], update=[])})
                dAssetAudit.get(templateId).get("update").append(dict(quantity=quantity,
                                                                      nAuditId=nAuditId,
                                                                      creatorId=creatorId,
                                                                      deadline=deadline,
                                                                      createTime=createTime))

        if "UpdateAsset" in item.get("target", {}):
            templateId = item.get("target").get("UpdateAsset").get("templateId")
            quantity = item.get("target").get("UpdateAsset").get("quantity")
            if templateId not in dAssetAudit.keys():
                dAssetAudit.update({templateId: dict(delete=[], update=[])})
            dAssetAudit.get(templateId).get("update").append(dict(quantity=quantity,
                                                                      nAuditId=nAuditId,
                                                                      creatorId=creatorId,
                                                                      deadline=deadline,
                                                                      createTime=createTime))

        if "DeleteAssetList" in item.get("target", {}):
            contractDeleteAssetList = item.get("target").get("DeleteAssetList")
            for param in contractDeleteAssetList:
                templateId = param[1]
                if templateId not in dAssetAudit.keys():
                    dAssetAudit.update({templateId: dict(delete=[], update=[])})
                dAssetAudit.get(templateId).get("delete").append(dict(delete=True,
                                                                      nAuditId=nAuditId,
                                                                      creatorId=creatorId,
                                                                      deadline=deadline,
                                                                      createTime=createTime))

    dContractAsset = BEOPDataAccess.getInstance().getAssetOfContract(contractId)
    for data in dataList:
        templateId = data["id"]
        quantity = dContractAsset.get(templateId, None)
        if quantity != None:
            data.update({"quantity": quantity, "belong": 1})  #belong用来做什么?
        else:
            data.update({"quantity": 0, "belong": 0})

        data.update(dict(audit={}))
        audit = dAssetAudit.get(templateId, None)
        if audit != None:
            data["audit"].update(audit)

    for i in range(len(dataList)):
        for j in range(len(dataList)-i-1):
            if dataList[j]["quantity"] < dataList[j+1]["quantity"]:
                dataList[j],dataList[j+1] = dataList[j+1],dataList[j]

    return jsonify(dict(err=0, msg="", data=dataList))


@bp_rps.route("/getAssetOfInOutWarehouse", methods=["POST"])
def get_asset_of_in_out_warehouse():
    rcv = request.get_json()
    nInOutWarehouseId = rcv.get("inOutWarehouseId", None)

    if nInOutWarehouseId is None:
        nInOutWarehouseId = rcv.get("id", None)

    if not isinstance(nInOutWarehouseId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整数", data=False))

    dataList = BEOPDataAccess.getInstance().getAllEquipAssetTmpl(FIXED_ASSET_TEMPLATE_ID_LIST)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))

    toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nInOutWarehouseId, 2, -1) #-1表示待审核 ,
    if toAuditList == None:
        return jsonify(dict(err=1, msg="获取进出库单待审核项失败", data=False))


    dAssetAudit = {}
    for item in toAuditList:
        nAuditId = item.get("nAuditId")
        creatorId = item.get("creatorId")
        createTime = item.get("createTime")
        deadline = item.get("deadline")
        if "AddAssetList" in item.get("target", {}):
            contractAddAssetList = item.get("target").get("AddAssetList")
            for param in contractAddAssetList:
                templateId = param[1]
                quantity = param[2]
                if templateId not in dAssetAudit.keys():
                    dAssetAudit.update({templateId: dict(delete=[], update=[])})
                dAssetAudit.get(templateId).get("update").append(dict(quantity=quantity,
                                                                      nAuditId=nAuditId,
                                                                      creatorId=creatorId,
                                                                      deadline=deadline,
                                                                      createTime=createTime))

        if "UpdateAsset" in item.get("target", {}):
            templateId = item.get("target").get("UpdateAsset").get("templateId")
            quantity = item.get("target").get("UpdateAsset").get("quantity")
            if templateId not in dAssetAudit.keys():
                dAssetAudit.update({templateId: dict(delete=[], update=[])})
            dAssetAudit.get(templateId).get("update").append(dict(quantity=quantity,
                                                                  nAuditId=nAuditId,
                                                                  creatorId=creatorId,
                                                                  deadline=deadline,
                                                                  createTime=createTime))

        if "DeleteAssetList" in item.get("target", {}):
            contractDeleteAssetList = item.get("target").get("DeleteAssetList")
            for param in contractDeleteAssetList:
                templateId = param[1]
                if templateId not in dAssetAudit.keys():
                    dAssetAudit.update({templateId: dict(delete=[], update=[])})
                dAssetAudit.get(templateId).get("delete").append(dict(delete=True,
                                                                      nAuditId=nAuditId,
                                                                      creatorId=creatorId,
                                                                      deadline=deadline,
                                                                      createTime=createTime))

    #根据出入库单ID获取该出入库单内的资产清单,格式是资产模板号: 该资产模板数量的字典
    dAsset = BEOPDataAccess.getInstance().getAssetOfInOutWarehouse(nInOutWarehouseId)

    #遍历系统所有资产模板 , 每个资产模板都要定义是否在此出入库单内(belong=1表示在内) ,audit内容就是所有待审核的数量更改项
    for data in dataList:
        #先更新本出入库单的资产数量信息
        templateId = data["id"]
        quantity = dAsset.get(templateId, None)
        if quantity != None:
            data.update({"quantity": quantity, "belong": 1})  #belong用来表示是否属于此出入库单
        else:
            data.update({"quantity": 0, "belong": 0})

        # 然后更新本出入库单的审核单中的资产信息
        data.update(dict(audit={}))
        audit = dAssetAudit.get(templateId, None)
        if audit != None:
            data["audit"].update(audit)

    #排序：按照数量从多到少排序资产，资产模板数量多的在前，为了给前端直接显示，后面数量为零的自然belong=0
    for i in range(len(dataList)):
        for j in range(len(dataList)-i-1):
            if dataList[j]["quantity"] < dataList[j+1]["quantity"]:
                dataList[j],dataList[j+1] = dataList[j+1],dataList[j]

    return jsonify(dict(err=0, msg="", data=dataList))


@bp_rps.route("/addTransport", methods=["POST"])
def add_transport():
    rcv = request.get_json()
    #contractId = rcv.get("contractId", None)
    #2022-05-13改为和出入库订单绑定
    inoutwarehouseId = rcv.get("inoutwarehouseId", None)
    departWarehouseId = rcv.get("departWarehouseId", None)
    destWarehouseId = rcv.get("destWarehouseId", None)
    estimatedArriveDate = rcv.get("estimatedArriveDate", None)

    if is_digit(inoutwarehouseId):
        contractId = int(float(inoutwarehouseId))

    if is_digit(departWarehouseId):
        departWarehouseId = int(float(departWarehouseId))

    if is_digit(destWarehouseId):
        destWarehouseId = int(float(destWarehouseId))

    # if not isinstance(contractId, int):
    #     return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if not isinstance(inoutwarehouseId, int):
        return jsonify(dict(err=1, msg="出入库单ID必须为整数", data=False))
    if not isinstance(departWarehouseId, int):
        return jsonify(dict(err=1, msg="订单发出仓库ID必须为整数", data=False))
    if not isinstance(destWarehouseId, int):
        return jsonify(dict(err=1, msg="订单到达仓库ID必须为整数", data=False))
    if not isinstance(estimatedArriveDate, str):
        return jsonify(dict(err=1, msg="预计到达日期必须为字符串", data=False))
    if not isValidDate(estimatedArriveDate, "%Y-%m-%d"):
        return jsonify(dict(err=1, msg="预计到达日期格式有误", data=False))

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_transport")
    nId = nMaxId + 1

    # bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
    # if not bContractIdExists:
    #     return jsonify(dict(err=1, msg="订单ID不存在", data=False))
    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", inoutwarehouseId, "rps_in_out_warehouse")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="出入库单ID不存在", data=False))

    bDepartIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", departWarehouseId, "rps_warehouse")
    if not bDepartIdExists:
        return jsonify(dict(err=1, msg="出发仓库ID不存在", data=False))

    bDestIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", destWarehouseId, "rps_warehouse")
    if not bDestIdExists:
        return jsonify(dict(err=1, msg="到达仓库ID不存在", data=False))

    if departWarehouseId == destWarehouseId:
        return jsonify(dict(err=1, msg="出发和到达仓库ID不能一样", data=False))

    if datetime.strptime(estimatedArriveDate, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now():
        return jsonify(dict(err=1, msg="预计到达日期不能小于当前时间", data=False))

    estimatedArriveDate += " 00:00:00"
    nStatus = 0
    # bSuc = BEOPDataAccess.getInstance().addTransport(nId, contractId, departWarehouseId, destWarehouseId,
    #                                                  estimatedArriveDate, nStatus)
    bSuc = BEOPDataAccess.getInstance().addTransport(nId, inoutwarehouseId, departWarehouseId, destWarehouseId, estimatedArriveDate, nStatus)
    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/addReceiveImgToTransport", methods=["POST"])
def add_transport_receive_img():
    transportId = request.form.get("id", None)
    userId = request.form.get("userId", None)
    deadline = request.form.get("deadline", None)

    if is_digit(userId):
        userId = int(float(userId))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if is_digit(transportId):
        transportId = int(float(transportId))

    fileList = []
    for i in range(0, 10):
        file = request.files.get("file%02d" % i)
        if not file or not isinstance(file.content_type, str):
            continue
        fileList.append(file)

    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))

    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    maxFileId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_attachment")
    fileIdList = []
    fileNameList = []
    nFileId = maxFileId + 1
    attachmentFileInfoList = []
    for oFile in fileList:

        strExt = os.path.splitext(oFile.filename)[1]

        fileName = "{fileId}_{originalName}".format(fileId=nFileId, originalName=oFile.filename)

        tempFilePath = os.path.join(tempDir, fileName)

        oFile.stream.read()
        oFile.stream.seek(0)
        oFile.save(tempFilePath)

        if not os.path.exists(tempFilePath):
            continue

        fileNameList.append(fileName)

        nType = -1
        ossPath = ""
        enabled = 1
        bSuc = upload_to_oss(tempFilePath, fileName, OSS_CONFIG["folderName"])
        if bSuc:
            nType = ATTACHMENT_TYPE.get(strExt.lower(), -1)
            ossPath = "https://{bucketName}.{region}/{folderName}/{fileName}".format(
                bucketName=OSS_CONFIG["bucketName"],
                region=OSS_CONFIG["region"],
                folderName=OSS_CONFIG["folderName"],
                fileName=fileName)
            fileIdList.append(nFileId)

        attachmentFileInfoList.append(
            (nFileId, fileName, nType, ossPath, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), enabled)
        )
        time.sleep(0.2)
        nFileId += 1

    bSuc = BEOPDataAccess.getInstance().addRpsAttachment(attachmentFileInfoList)
    if not bSuc:
        return jsonify(dict(err=1, msg="将文件信息存入附件表失败", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))
    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    if curStatus == 0:
        existingFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportReceiveImg(transportId)
        if existingFileIdList == None:
            return jsonify(dict(err=1, msg="获取当前图片ID列表失败", data=False))

        existingFileIdList.extend(fileIdList)
        existingFileIdList = list(set(existingFileIdList))
        bSuc = BEOPDataAccess.getInstance().updateRpsTransportReceiveImg(transportId, existingFileIdList)

    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 4  # 物流单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1  # 审核结果初始值-1
        dOriginal = {}
        dTarget = {}

        origReceiveImgIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportReceiveImg(transportId)
        if origReceiveImgIdList == None:
            return jsonify(dict(err=1, msg="获取物流单当前到货照片ID列表获取失败", data=False))

        dOriginal.update({"receiveDeliveryImgFileIdList": origReceiveImgIdList})

        targetFileIdList = origReceiveImgIdList.copy()
        targetFileIdList.extend(fileIdList)
        targetFileIdList = list(set(targetFileIdList))

        dTarget.update({"receiveDeliveryImgFileIdList": targetFileIdList})

        paramAuditList = [nIdAudit, transportId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]
        bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)

    for fName in fileNameList:
        strPath = os.path.join(tempDir, fName)
        if os.path.exists(strPath):
            os.remove(strPath)

    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteReceiveImgFromTransport", methods=["POST"])
def delete_transport_receive_img():
    rcv = request.get_json()
    transportId = rcv.get("id", None)
    fileIdList = rcv.get("fileIdList", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    if is_digit(transportId):
        transportId = int(float(transportId))

    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if not isinstance(fileIdList, list):
        return jsonify(dict(err=1, msg="fileIdList必须为列表", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))
    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportReceiveImg(transportId)
        if attachmentIdList == None:
            return jsonify(dict(err=1, msg="获取当前图片ID列表失败", data=False))

        for nFileId in fileIdList:
            if not is_digit(nFileId):
                continue

            if nFileId in attachmentIdList:
                attachmentIdList.remove(nFileId)

        dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
        if dFileInfo == None:
            return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

        attachmentFileNameList = []
        for value in dFileInfo.values():
            fName = value.get("fileName", "")
            if fName:
                attachmentFileNameList.append(fName)

        strAttachment = ",".join([str(nId) for nId in attachmentIdList])

        sqlTrans = "UPDATE rps_transport SET receive_delivery_img=%s WHERE id=%s"
        paramTrans = [strAttachment, transportId]

        sqlAttach = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
        paramAttach = [(fileId,) for fileId in fileIdList]

        queryList = [sqlTrans, sqlAttach]
        paramList = [tuple(paramTrans), tuple(paramAttach)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))

        bSuc = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if not bSuc:
            return jsonify(dict(err=1, msg="删除失败", data=False))
        return jsonify(dict(err=0, msg="删除成功", data=True))
    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 4  # 物流单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportReceiveImg(transportId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"receiveDeliveryImgFileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        for fileId in fileIdList:
            if fileId in targetFileIdList:
                targetFileIdList.remove(fileId)

        dTarget.update({"receiveDeliveryImgFileIdList": targetFileIdList})

        paramAuditList = [nIdAudit, transportId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]

        bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="", data=True))


@bp_rps.route("/addSignImgToTransport", methods=["POST"])
def add_transport_sign_img():
    transportId = request.form.get("id", None)
    userId = request.form.get("userId", None)
    deadline = request.form.get("deadline", None)

    if is_digit(userId):
        userId = int(float(userId))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if is_digit(transportId):
        transportId = int(float(transportId))

    fileList = []
    for i in range(0, 10):
        file = request.files.get("file%02d" % i)
        if not file or not isinstance(file.content_type, str):
            continue
        fileList.append(file)

    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))

    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    maxFileId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_attachment")
    fileIdList = []
    fileNameList = []
    nFileId = maxFileId + 1
    attachmentFileInfoList = []
    for oFile in fileList:

        strExt = os.path.splitext(oFile.filename)[1]

        fileName = "{fileId}_{originalName}".format(fileId=nFileId, originalName=oFile.filename)

        tempFilePath = os.path.join(tempDir, fileName)

        oFile.stream.read()
        oFile.stream.seek(0)
        oFile.save(tempFilePath)

        if not os.path.exists(tempFilePath):
            continue

        fileNameList.append(fileName)

        nType = -1
        ossPath = ""
        enabled = 1
        bSuc = upload_to_oss(tempFilePath, fileName, OSS_CONFIG["folderName"])
        if bSuc:
            nType = ATTACHMENT_TYPE.get(strExt.lower(), -1)
            ossPath = "https://{bucketName}.{region}/{folderName}/{fileName}".format(
                bucketName=OSS_CONFIG["bucketName"],
                region=OSS_CONFIG["region"],
                folderName=OSS_CONFIG["folderName"],
                fileName=fileName)
            fileIdList.append(nFileId)

        attachmentFileInfoList.append(
            (nFileId, fileName, nType, ossPath, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), enabled)
        )
        time.sleep(0.2)
        nFileId += 1

    bSuc = BEOPDataAccess.getInstance().addRpsAttachment(attachmentFileInfoList)
    if not bSuc:
        return jsonify(dict(err=1, msg="将文件信息存入附件表失败", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))
    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    if curStatus == 0:
        existingFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportSignImg(transportId)
        if existingFileIdList == None:
            return jsonify(dict(err=1, msg="获取当前图片ID列表失败", data=False))

        existingFileIdList.extend(fileIdList)
        existingFileIdList = list(set(existingFileIdList))
        bSuc = BEOPDataAccess.getInstance().updateRpsTransportSignImg(transportId, existingFileIdList)

    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 4  # 物流单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1  # 审核结果初始值-1
        dOriginal = {}
        dTarget = {}

        origReceiveImgIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportSignImg(transportId)
        if origReceiveImgIdList == None:
            return jsonify(dict(err=1, msg="获取物流单当前到货照片ID列表获取失败", data=False))

        dOriginal.update({"signImgFileIdList": origReceiveImgIdList})

        targetFileIdList = origReceiveImgIdList.copy()
        targetFileIdList.extend(fileIdList)
        targetFileIdList = list(set(targetFileIdList))

        dTarget.update({"signImgFileIdList": targetFileIdList})

        paramAuditList = [nIdAudit, transportId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]
        bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)

    for fName in fileNameList:
        strPath = os.path.join(tempDir, fName)
        if os.path.exists(strPath):
            os.remove(strPath)

    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteSignImgFromTransport", methods=["POST"])
def delete_transport_sign_img():
    rcv = request.get_json()
    transportId = rcv.get("id", None)
    fileIdList = rcv.get("fileIdList", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    if is_digit(transportId):
        transportId = int(float(transportId))

    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if not isinstance(fileIdList, list):
        return jsonify(dict(err=1, msg="fileIdList必须为列表", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))
    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportSignImg(transportId)
        if attachmentIdList == None:
            return jsonify(dict(err=1, msg="获取当前图片ID列表失败", data=False))

        for nFileId in fileIdList:
            if not is_digit(nFileId):
                continue

            if nFileId in attachmentIdList:
                attachmentIdList.remove(nFileId)

        dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
        if dFileInfo == None:
            return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

        attachmentFileNameList = []
        for value in dFileInfo.values():
            fName = value.get("fileName", "")
            if fName:
                attachmentFileNameList.append(fName)

        strAttachment = ",".join([str(nId) for nId in attachmentIdList])

        sqlTrans = "UPDATE rps_transport SET sign_img=%s WHERE id=%s"
        paramTrans = [strAttachment, transportId]

        sqlAttach = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
        paramAttach = [(fileId,) for fileId in fileIdList]

        queryList = [sqlTrans, sqlAttach]
        paramList = [tuple(paramTrans), tuple(paramAttach)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))

        bSuc = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if not bSuc:
            return jsonify(dict(err=1, msg="删除失败", data=False))
        return jsonify(dict(err=0, msg="删除成功", data=True))
    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 4  # 物流单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportSignImg(transportId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"signImgFileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        for fileId in fileIdList:
            if fileId in targetFileIdList:
                targetFileIdList.remove(fileId)

        dTarget.update({"signImgFileIdList": targetFileIdList})

        paramAuditList = [nIdAudit, transportId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]

        bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="", data=True))


@bp_rps.route("/deleteTransport", methods=["POST"])
def delete_transport():
    rcv = request.get_json()
    transportId = rcv.get("id", None)
    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))

    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))
    if curStatus != 0:
        return jsonify(dict(err=1, msg="当前状态为{cur}，无法执行该操作".format(cur=curStatus), data=False))

    receiveImgIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportReceiveImg(transportId)
    if receiveImgIdList == None:
        return jsonify(dict(err=1, msg="获取图片ID列表失败", data=False))

    signImgIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfTransportSignImg(transportId)
    if signImgIdList == None:
        return jsonify(dict(err=1, msg="获取图片ID列表失败", data=False))

    fileIdList = []
    fileIdList.extend(receiveImgIdList)
    fileIdList.extend(signImgIdList)

    dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
    if dFileInfo == None:
        return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

    fileNameList = []
    for value in dFileInfo.values():
        fName = value.get("fileName", "")
        if fName:
            fileNameList.append(fName)

    bSucDel = False
    count = 0
    while count < 5:
        bSucDel = delete_file_from_oss(fileNameList, OSS_CONFIG["folderName"])
        if bSucDel:
            break
        time.sleep(0.2)
        count += 1

    # 禁用附件
    sqlDis = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
    paramDis = [(fileId,) for fileId in fileIdList]

    # 删除物流记录
    sqlDel1 = "DELETE FROM rps_transport WHERE id=%s"
    paramDel1 = (transportId,)

    queryList = [sqlDel1]
    paramList = [(paramDel1,)]

    if len(fileIdList):
        queryList.append(sqlDis)
        paramList.append(tuple(paramDis))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="删除失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))



@bp_rps.route("/updateTransport", methods=["POST"])
def update_transport():
    rcv = request.get_json()
    transportId = rcv.get("transportId", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    #contractId = rcv.get("contractId", None)
    inoutwarehouseId = rcv.get("inoutwarehouseId", None)
    departWarehouseId = rcv.get("departWarehouseId", None)
    destWarehouseId = rcv.get("destWarehouseId", None)
    estimatedArriveDate = rcv.get("estimatedArriveDate", None)

    contractIdOrig = rcv.get("contractIdOrig", None)
    departWarehouseIdOrig = rcv.get("departWarehouseIdOrig", None)
    destWarehouseIdOrig = rcv.get("destWarehouseIdOrig", None)
    estimatedArriveDateOrig = rcv.get("estimatedArriveDateOrig", None)

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    if not bTransportIdExists:
        return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    if inoutwarehouseId != None:
        if not isinstance(inoutwarehouseId, int):
            return jsonify(dict(err=1, msg="出入库ID必须为整型", data=False))
        bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", inoutwarehouseId, "rps_in_out_warehouse")
        if not bContractIdExists:
            return jsonify(dict(err=1, msg="出入库ID不存在", data=False))

    if contractIdOrig != None:
        if not isinstance(contractIdOrig, int):
            return jsonify(dict(err=1, msg="原始订单ID必须为整型", data=False))
        bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractIdOrig, "rps_contract")
        if not bContractIdExists:
            return jsonify(dict(err=1, msg="原始订单ID不存在", data=False))

    if departWarehouseId != None:
        if not isinstance(departWarehouseId, int):
            return jsonify(dict(err=1, msg="出发仓库ID必须为整型", data=False))
        bDepartWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", departWarehouseId, "rps_warehouse")
        if not bDepartWarehouseIdExists:
            return jsonify(dict(err=1, msg="出发仓库ID不存在", data=False))

    if departWarehouseIdOrig != None:
        if not isinstance(departWarehouseIdOrig, int):
            return jsonify(dict(err=1, msg="原始出发仓库ID必须为整型", data=False))
        bDepartWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", departWarehouseIdOrig, "rps_warehouse")
        if not bDepartWarehouseIdExists:
            return jsonify(dict(err=1, msg="原始出发仓库ID不存在", data=False))

    if destWarehouseId != None:
        if not isinstance(destWarehouseId, int):
            return jsonify(dict(err=1, msg="到达仓库ID必须为整型", data=False))
        bDestWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", destWarehouseId, "rps_warehouse")
        if not bDestWarehouseIdExists:
            return jsonify(dict(err=1, msg="到达仓库ID不存在", data=False))

    if destWarehouseIdOrig != None:
        if not isinstance(destWarehouseIdOrig, int):
            return jsonify(dict(err=1, msg="原始到达仓库ID必须为整型", data=False))
        bDestWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", destWarehouseIdOrig, "rps_warehouse")
        if not bDestWarehouseIdExists:
            return jsonify(dict(err=1, msg="原始到达仓库ID不存在", data=False))

    if estimatedArriveDate != None:
        if not isinstance(estimatedArriveDate, str):
            return jsonify(dict(err=1, msg="预计到达日期必须为字符串", data=False))
        if not isValidDate(estimatedArriveDate, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="预计到达日期格式有误", data=False))
        if datetime.strptime(estimatedArriveDate, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now():
            return jsonify(dict(err=1, msg="预计到达日期不能小于当前时间", data=False))
        estimatedArriveDate += " 00:00:00"

    if estimatedArriveDateOrig != None:
        if not isinstance(estimatedArriveDateOrig, str):
            return jsonify(dict(err=1, msg="原始预计到达日期必须为字符串", data=False))
        if not isValidDate(estimatedArriveDateOrig, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="原始预计到达日期格式有误", data=False))
        if datetime.strptime(estimatedArriveDateOrig, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now():
            return jsonify(dict(err=1, msg="原始预计到达日期不能小于当前时间", data=False))
        estimatedArriveDateOrig += " 00:00:00"

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(4, transportId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="当前状态获取失败", data=False))

    if curStatus == 0 or curStatus == 13:
        updateList = []
        if inoutwarehouseId != None:
            updateList.append(("inoutwarehouse_id", inoutwarehouseId))
        if departWarehouseId != None:
            updateList.append(("depart_warehouse_id", departWarehouseId))
        if destWarehouseId != None:
            updateList.append(("dest_warehouse_id", destWarehouseId))
        if estimatedArriveDate != None:
            updateList.append(("estimated_arrive_time", estimatedArriveDate))

        if not len(updateList):
            return jsonify(dict(err=0, msg="", data=True))

        bSuc = BEOPDataAccess.getInstance().updateRpsTransport(transportId, updateList)
        if not bSuc:
            return jsonify(dict(err=1, msg="修改失败", data=False))
        return jsonify(dict(err=0, msg="修改成功", data=True))
    elif curStatus == 1 :
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 4  # 物流单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        if contractIdOrig != None:
            dOriginal.update({"contractIdOrig": contractIdOrig})
        if departWarehouseIdOrig != None:
            dOriginal.update({"departWarehouseIdOrig": departWarehouseIdOrig})
        if destWarehouseIdOrig != None:
            dOriginal.update({"destWarehouseIdOrig": destWarehouseIdOrig})
        if estimatedArriveDateOrig != None:
            dOriginal.update({"estimatedArriveDateOrig": estimatedArriveDateOrig})

        if inoutwarehouseId != None:
            dTarget.update({"inoutwarehouseId": inoutwarehouseId})
        if departWarehouseId != None:
            dTarget.update({"departWarehouseId": departWarehouseId})
        if destWarehouseId != None:
            dTarget.update({"destWarehouseId": destWarehouseId})
        if estimatedArriveDate != None:
            dTarget.update({"estimatedArriveDate": estimatedArriveDate})

        sqlStatus = "UPDATE rps_transport SET status=13 WHERE id=%s"
        paramStatus = [transportId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, transportId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlStatus, sqlAudit]
        paramList = [tuple(paramStatus), tuple(paramAudit)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))

@bp_rps.route("/getTransport", methods=["POST"])
def get_transport():
    rcv = request.get_json()
    transportId = rcv.get("id", None)

    if transportId != None:
        if not isinstance(transportId, int):
            return jsonify(dict(err=1, msg="物流ID必须为整型", data=[]))
        bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
        if not bTransportIdExists:
            return jsonify(dict(err=1, msg="物流订单ID不存在", data=[]))

    dataList = BEOPDataAccess.getInstance().getRpsTransport(transportId)

    fileIdList = []
    nTransportIdList = []
    for data in dataList:
        fileIdList.extend(data.get("receiveImgList"))
        fileIdList.extend(data.get("signImgList"))
        nTransportIdList.append(data.get("transportId"))

    fileIdList = list(set(fileIdList))
    dAttachmentInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)

    dCheckAudit = BEOPDataAccess.getInstance().getRpsCheckAndAuditRecords(nTransportIdList, 4)
    if dCheckAudit == None:
        return jsonify(dict(err=1, msg="校核、审核信息查询失败", data=[]))

    for data in dataList:
        receiveImgList = data["receiveImgList"]
        receiveImgDetailList = []
        for imgId in receiveImgList:
            if dAttachmentInfo.get(imgId, None) != None:
                receiveImgDetailList.append(dAttachmentInfo[imgId])
        data["receiveImgList"] = receiveImgDetailList

        signImgList = data["signImgList"]
        signImgDetailList = []
        for imgId in signImgList:
            if dAttachmentInfo.get(imgId, None) != None:
                signImgDetailList.append(dAttachmentInfo[imgId])
        data["signImgList"] = signImgDetailList

        data.update(dict(check=dCheckAudit.get(data["transportId"], {}).get("check", {})))
        data.update(dict(createAudit=dCheckAudit.get(data["transportId"], {}).get("createAudit", {})))
        data.update(dict(editAudit=dCheckAudit.get(data["transportId"], {}).get("editAudit", {})))
        data.update(dict(terminateAudit=dCheckAudit.get(data["transportId"], {}).get("terminateAudit", {})))
        data.update(dict(finishAudit=dCheckAudit.get(data["transportId"], {}).get("finishAudit", {})))

    return jsonify(dict(err=0, msg="", data=dataList))


@bp_rps.route("/addInOutWarehouse", methods=["POST"])
def add_in_out_warehouse():
    rcv = request.get_json()
    warehouseId = rcv.get("warehouseId", None)
    #transportId = rcv.get("transportId", None)
    #2022-05-13 改为和订单ID绑定
    contractId = rcv.get("contractId", None)
    nType = rcv.get("type", None)       # 类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单
    creatorId = rcv.get("creatorId", None)
    additional = rcv.get("additional", None)

    if not isinstance(warehouseId, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整型", data=False))
    # if transportId != None:
    #     if not isinstance(transportId, int):
    #         return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    if contractId != None:
        if not isinstance(contractId, int):
            return jsonify(dict(err=1, msg="订单ID必须为整型", data=False))
    if nType not in [0, 1, 2]:
        return jsonify(dict(err=1, msg="type必须为0或1或2", data=False))
    if not isinstance(creatorId, int):
        return jsonify(dict(err=1, msg="创建者ID必须为整型", data=False))

    if additional != None:
        if not isinstance(additional, str):
            return jsonify(dict(err=1, msg="附加信息必须为字符串", data=False))

    bWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
    if not bWarehouseIdExists:
        return jsonify(dict(err=1, msg="仓库ID不存在", data=False))
    # if contractId != None:
    #     bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    #     if not bTransportIdExists:
    #         return jsonify(dict(err=1, msg="物流ID不存在", data=False))
    if contractId != None:
        bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
        if not bTransportIdExists:
            return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    dCreatorInfo = BEOPDataAccess.getInstance().get_user_info(creatorId)
    if not dCreatorInfo:
        return jsonify(dict(err=1, msg="创建者ID不存在", data=False))

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_in_out_warehouse")
    nId = nMaxId + 1
    strCreateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nStatus = 0
    nEnabled = 1

    strQuery = "INSERT INTO rps_in_out_warehouse (id, warehouse_id, type, creator_id, create_time, status, enabled"
    strParam = "(%s,%s,%s,%s,%s,%s,%s"
    paramList = [nId, warehouseId, nType, creatorId, strCreateTime, nStatus, nEnabled]
    if additional != None:
        strQuery += " ,additional"
        strParam += ",%s"
        paramList.append(additional)

    if contractId != None:
        strQuery += ",contract_id"
        strParam += ",%s"
        paramList.append(contractId)
    # if transportId != None:
    #     strQuery += ",transport_id"
    #     strParam += ",%s"
    #     paramList.append(transportId)
    strQuery += ") VALUES "
    strParam += ")"

    strInsert = strQuery + strParam

    queryList = [strInsert]
    paramList = [paramList]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="创建失败", data=False))
    return jsonify(dict(err=0, msg="创建成功", data=True))


@bp_rps.route("/addAttachmentToInOutWarehouse", methods=["POST"])
def add_attachment_to_in_out_warehouse():
    # 从前端给的body结构体中获取键名为"id"的值，放入后台的nInOutId变量中，因此这里前端要求是body里写"id"，这里的get(""里的要和postman统一
    nInOutId = request.form.get("inOutWarehouseId", None)
    userId = request.form.get("userId", None)
    deadline = request.form.get("deadline", None)
    nType = request.form.get("type", None)        # 0-新箱入库；1-循环箱入库；2-循环箱出库

    if is_digit(nInOutId):
        nInOutId = int(float(nInOutId))
    if is_digit(userId):
        userId = int(float(userId))
    if is_digit(nType):
        nType = int(float(nType))

    if not isinstance(nInOutId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整数", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="类型必须为整数", data=False))

    if nType not in IN_OUT_TYPE_LIST:
        return jsonify(dict(err=1, msg="类型必须在{s}之中".format(s=str(IN_OUT_TYPE_LIST)), data=False))
    nBillType = 2 if nType in [0, 1] else 3 # 2-入库；3-出库

    fileList = []
    for i in range(0, 10):
        file = request.files.get("file%02d" % i)
        if not file or not isinstance(file.content_type, str):
            continue
        fileList.append(file)

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nInOutId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, nInOutId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus not in [0, 1,13]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_attachment")
    nFileId = nMaxId + 1
    paramList = []
    fileIdList = []
    fileNameList = []
    for file in fileList:
        originalFileName = os.path.splitext(file.filename)[0]
        strExt = os.path.splitext(file.filename)[1]
        fileName = "{nId}_{originalName}{ext}".format(nId=nFileId, originalName=originalFileName, ext=strExt)

        tempPath = os.path.join(tempDir, fileName)
        file.stream.read()
        file.stream.seek(0)
        file.save(tempPath)

        if not os.path.exists(tempPath):
            continue

        fileNameList.append(fileName)

        bSuc = upload_to_oss(tempPath, fileName, OSS_CONFIG["folderName"])
        nFileType = -1
        ossPath = ""
        enabled = 1
        if bSuc:
            nFileType = ATTACHMENT_TYPE.get(strExt.lower(), -1)
            ossPath = "https://{bucketName}.{region}/{folderName}/{fileName}".format(
                bucketName=OSS_CONFIG["bucketName"],
                region=OSS_CONFIG["region"],
                folderName=OSS_CONFIG["folderName"],
                fileName=fileName)
            fileIdList.append(nFileId)

        paramList.append(
            (nFileId, fileName, nFileType, ossPath, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), enabled)
        )

        time.sleep(0.2)
        nFileId += 1

    bSuc = BEOPDataAccess.getInstance().addRpsAttachment(paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="将文件信息存入附件表失败", data=False))

    if curStatus == 0:
        existingFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListInOutWarehouse(nInOutId)
        if existingFileIdList == None:
            return jsonify(dict(err=1, msg="获取当前附件ID列表失败", data=False))

        existingFileIdList.extend(fileIdList)
        existingFileIdList = list(set(existingFileIdList))

        updateList = [("attachment_id", ",".join([str(nId) for nId in existingFileIdList]))]
        bSuc = BEOPDataAccess.getInstance().updateRpsInOutWarehouse(nInOutId, updateList)
    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1  # 审核结果初始值-1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListInOutWarehouse(nInOutId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        targetFileIdList.extend(fileIdList)
        targetFileIdList = list(set(targetFileIdList))

        dTarget.update({"fileIdList": targetFileIdList})

        sqlStatus = "UPDATE rps_in_out_warehouse SET status=13 WHERE id=%s"
        paramStatus = [nInOutId]  #这里的id小写后就变成了python系统内置的一个函数指针了，虽然不报错但是运行会出问题

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, nInOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAudit)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        #这里updateRpsMultiTrans是批量执行多条mysql数据，捆绑为一个事务执行，其中一个执行不成功，那么整个事务都会回滚，避免一部分成功，因此数据误改一半
        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

   #     paramAuditList = [nIdAudit, nInOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
   #                       json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]
   #    bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)

    for fileName in fileNameList:
        strPath = os.path.join(tempDir, fileName)
        if os.path.exists(strPath):
            os.remove(strPath)

    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteAttachmentFromInOutWarehouse", methods=["POST"])
def delete_attachment_from_in_out_warehouse():
    rcv = request.get_json()
    nInOutId = rcv.get("nInOutId", None)
    fileIdList = rcv.get("fileIdList", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)
    nType = rcv.get("type", None)  # 类型  0-新箱入库；1-循环箱入库；2-循环箱出库

    if not isinstance(nInOutId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整型", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if nType not in IN_OUT_TYPE_LIST:
        return jsonify(dict(err=1, msg="类型必须在{s}之中".format(s=str(IN_OUT_TYPE_LIST)), data=False))
    nBillType = 2 if nType in [0, 1] else 3 # 2-入库；3-出库

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nInOutId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, nInOutId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取订单状态失败", data=False))
    if curStatus not in [0, 1,13]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if not isinstance(fileIdList, list):
        return jsonify(dict(err=1, msg="fileIdList必须为列表", data=False))

    if not len(fileIdList):
        return jsonify(dict(err=1, msg="fileIdList不能为空", data=False))

    if curStatus == 0 or curStatus == 13:
        existingFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListInOutWarehouse(nInOutId)
        if existingFileIdList == None:
            return jsonify(dict(err=1, msg="获取当前附件ID列表失败", data=False))

        for fileId in fileIdList:
            if not is_digit(fileId):
                continue

            nId = int(float(fileId))
            if nId in existingFileIdList:
                existingFileIdList.remove(nId)

        strAttach = ",".join([str(nId) for nId in existingFileIdList])
        dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
        if dFileInfo == None:
            return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

        attachFileNameList = []
        for value in dFileInfo.values():
            fName = value.get("fileName", "")
            if fName:
                attachFileNameList.append(fName)

        sqlContract = "UPDATE rps_in_out_warehouse SET attachment_id=%s WHERE id=%s"
        paramContract = [strAttach, nInOutId]

        sqlAttach = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
        paramAttach = [(fileId,) for fileId in fileIdList]

        queryList = [sqlContract, sqlAttach]
        paramList = [tuple(paramContract), tuple(paramAttach)]
        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))

        bSuc = delete_file_from_oss(attachFileNameList, OSS_CONFIG["folderName"])
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListInOutWarehouse(nInOutId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        for fileId in fileIdList:
            if fileId in targetFileIdList:
                targetFileIdList.remove(fileId)

        dTarget.update({"fileIdList": targetFileIdList})

        # paramAuditList = [nIdAudit, nInOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
        #                   json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]

        sqlStatus = "UPDATE rps_in_out_warehouse SET status=13 WHERE id=%s"
        paramStatus = [nInOutId]  # 这里的id小写后就变成了python系统内置的一个函数指针了，虽然不报错但是运行会出问题

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAuditList = [nIdAudit, nInOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                          nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]

        queryList = [sqlAudit]
        paramList = [tuple(paramAuditList)]

        if curStatus == 1 or curStatus == 13:
            queryList.append(sqlStatus)
            paramList.append(tuple(paramStatus))

        # 这里updateRpsMultiTrans是批量执行多条mysql数据，捆绑为一个事务执行，其中一个执行不成功，那么整个事务都会回滚，避免一部分成功，因此数据误改一半
        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

        #bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))


@bp_rps.route("/deleteInOutWarehouse", methods=["POST"])
def delete_in_out_warehouse():
    rcv = request.get_json()
    nId = rcv.get("id", None)

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整型", data=False))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(2, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 0:
        return jsonify(dict(err=1, msg="当前状态为{cur}，无法执行该操作".format(cur=curStatus), data=False))

    fileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListInOutWarehouse(nId)
    if fileIdList == None:
        return jsonify(dict(err=1, msg="获取图片ID列表失败", data=False))

    dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
    if dFileInfo == None:
        return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

    fileNameList = []
    for value in dFileInfo.values():
        fName = value.get("fileName", "")
        if fName:
            fileNameList.append(fName)

    bSucDel = False
    count = 0
    while count < 5:
        bSucDel = delete_file_from_oss(fileNameList, OSS_CONFIG["folderName"])
        if bSucDel:
            break
        time.sleep(0.2)
        count += 1

    # 禁用附件
    sqlDis = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
    paramDis = [(fileId,) for fileId in fileIdList]

    # 删除进出库
    sqlDel1 = "DELETE FROM rps_in_out_warehouse WHERE id=%s"
    paramDel1 = (nId,)

    sqlDel2 = "DELETE FROM rps_in_out_warehouse_detail WHERE in_out_id=%s"
    paramDel2 = (nId,)

    queryList = [sqlDel1, sqlDel2]
    paramList = [(paramDel1,), (paramDel2,)]
    if len(fileIdList):
        queryList.append(sqlDis)
        paramList.append(tuple(paramDis))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


@bp_rps.route("/updateInOutWarehouse", methods=["POST"])
def update_in_out_warehouse():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    deadline = rcv.get("deadline", None)
    userId = rcv.get("userId", None)

    warehouseId = rcv.get("warehouseId", None)
    #transportId = rcv.get("transportId", None)
    #2022-05-13 改为订单ID
    contractId = rcv.get("contractId", None)
    nType = rcv.get("type", None)    # 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单
    additional = rcv.get("additional", None)

    warehouseIdOrig = rcv.get("warehouseIdOrig", None)
    #transportIdOrig = rcv.get("transportIdOrig", None)
    contractIdOrig = rcv.get("contractIdOrig", None)
    additionalOrig = rcv.get("additionalOrig", None)

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整型", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    if warehouseId != None:
        if not isinstance(warehouseId, int):
            return jsonify(dict(err=1, msg="仓库ID必须为整型", data=False))
        bWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
        if not bWarehouseIdExists:
            return jsonify(dict(err=1, msg="仓库ID不存在", data=False))
    if contractId != None:
        if not isinstance(contractId, int):
            return jsonify(dict(err=1, msg="订单D必须为整型", data=False))
        bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
        if not bTransportIdExists:
            return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    # if transportId != None:
    #     if not isinstance(transportId, int):
    #         return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    #     bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportId, "rps_transport")
    #     if not bTransportIdExists:
    #         return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))

    if nType != None:
        if nType not in IN_OUT_TYPE_LIST:
            return jsonify(dict(err=1, msg="type必须为0或1或2", data=False))

    if additional != None:
        if not isinstance(additional, str):
            return jsonify(dict(err=1, msg="附加信息必须为字符串", data=False))

    if warehouseIdOrig != None:
        if not isinstance(warehouseIdOrig, int):
            return jsonify(dict(err=1, msg="仓库ID必须为整型", data=False))
        bWarehouseIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseIdOrig, "rps_warehouse")
        if not bWarehouseIdExists:
            return jsonify(dict(err=1, msg="仓库ID不存在", data=False))

    if contractIdOrig != None:
        if not isinstance(contractIdOrig, int):
            return jsonify(dict(err=1, msg="订单ID必须为整型", data=False))
        bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractIdOrig, "rps_contract")
        if not bTransportIdExists:
            return jsonify(dict(err=1, msg="订单ID不存在", data=False))
    # if transportIdOrig != None:
    #     if not isinstance(transportIdOrig, int):
    #         return jsonify(dict(err=1, msg="物流ID必须为整型", data=False))
    #     bTransportIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", transportIdOrig, "rps_transport")
    #     if not bTransportIdExists:
    #         return jsonify(dict(err=1, msg="物流订单ID不存在", data=False))
    if additionalOrig != None:
        if not isinstance(additionalOrig, str):
            return jsonify(dict(err=1, msg="附加信息必须为字符串", data=False))

    nBillType = 2 if nType in [0, 1] else 3  # 2-入库单; 3-出库单
    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取进出库状态失败", data=False))

    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:
        updateList = []
        if warehouseId != None:
            updateList.append(("warehouse_id", warehouseId))
        if contractId != None:
            updateList.append(("contract_id", contractId))
        # if transportId != None:
        #     updateList.append(("transport_id", transportId))
        if nType != None:
            updateList.append(("type", nType))
        if additional != None:
            updateList.append(("additional", additional))

        bSuc = BEOPDataAccess.getInstance().updateRpsInOutWarehouse(nId, updateList)
        if not bSuc:
            return jsonify(dict(err=1, msg="修改失败", data=False))
        return jsonify(dict(err=0, msg="修改成功", data=True))
    elif curStatus == 1:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1

        if nType == None:
            return jsonify(dict(err=1, msg="当前状态为进行中，若提交修改则必须传入type", data=False))

        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        if warehouseId != None:
            dTarget.update({"warehouseId": warehouseId})
        if contractId != None:
            dTarget.update({"transportId": contractId})
        # if transportId != None:
        #     dTarget.update({"transportId": transportId})
        if additional != None:
            dTarget.update({"additional": additional})

        if warehouseIdOrig != None:
            dOriginal.update({"warehouseIdOrig": warehouseIdOrig})
        if contractIdOrig != None:
            dOriginal.update({"transportIdOrig": contractIdOrig})
        # if transportIdOrig != None:
        #     dOriginal.update({"transportIdOrig": transportIdOrig})
        if additionalOrig != None:
            dOriginal.update({"additionalOrig": additionalOrig})

        sqlStatus = "UPDATE rps_in_out_warehouse SET status=13 WHERE id=%s"
        paramStatus = [nId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, nId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlStatus, sqlAudit]
        paramList = [tuple(paramStatus), tuple(paramAudit)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/addAssetToInOutWarehouse", methods=["POST"])
def add_asset_to_in_out_warehouse():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    assetList = rcv.get("assetList", [])
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)
    nType = rcv.get("type", None)  # 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="进出库ID必须为整型", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if nType not in IN_OUT_TYPE_LIST:
        return jsonify(dict(err=1, msg="type必须在{s}".format(s=str(IN_OUT_TYPE_LIST)), data=False))
    nBillType = 2 if nType in [0, 1] else 3

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    dInfo = {}
    for asset in assetList:
        templateId = asset.get("templateId", None)
        quantity = asset.get("quantity", None)
        if templateId != None:
            if templateId not in dInfo.keys():
                dInfo.update({templateId: 0})

        if quantity != None:
            dInfo[templateId] += quantity

    # 检查模板ID是否存在
    preCheckList = [str(nId) for nId in dInfo.keys()]
    checkList = BEOPDataAccess.getInstance().getAlreadyExistingTemplateId(preCheckList)
    if checkList == None or not isinstance(checkList, list):
        return jsonify(dict(err=1, msg="模板设备ID存在性检查失败", data=False))

    for tmpId in dInfo.keys():
        if str(tmpId) not in checkList:
            return jsonify(dict(err=1, msg="未知模板ID", data=False))

    paramList = []
    for templateId, quantity in dInfo.items():
        if quantity != 0:
            paramList.append(
                (nId, templateId, quantity)
            )

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().addAssetToInOutWarehouse(paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="添加失败", data=False))
        return jsonify(dict(err=0, msg="添加成功", data=True))
    elif curStatus == 1:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dTarget.update({"inOutAddAssetList": paramList})

        paramAuditList = [nIdAudit, nId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                           json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]
        bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/deleteAssetFromInOutWarehouse", methods=["POST"])
def delete_asset_to_in_out_warehouse():
    rcv = request.get_json()
    inOutId = rcv.get("inOutId", None)
    templateId = rcv.get("templateId", None)
    deadline = rcv.get("deadline", None)
    userId = rcv.get("userId", None)
    nType = rcv.get("type", None)  # 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单

    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库记录ID必须为整型", data=False))

    if templateId != None:
        if not isinstance(templateId, int):
            return jsonify(dict(err=1, msg="资产模板ID必须为整型", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if nType not in IN_OUT_TYPE_LIST:
        return jsonify(dict(err=1, msg="type必须在{s}".format(s=str(IN_OUT_TYPE_LIST)), data=False))
    nBillType = 2 if nType in [0, 1] else 3

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, inOutId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().deleteRpsInOutWarehouseAsset(inOutId, templateId)
        if not bSuc:
            return jsonify(dict(err=1, msg="删除失败", data=False))
        return jsonify(dict(err=0, msg="删除成功", data=True))
    elif curStatus == 1 or curStatus == 13:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dTarget.update(
            {"DeleteAssetList": [(inOutId, templateId)]}
        )

        #bSuc = BEOPDataAccess.getInstance().addRpsAuditSingle(paramAuditLiset)

        sqlStatus = "UPDATE rps_in_out_warehouse SET status=13 WHERE id=%s"
        paramStatus = [inOutId]  # 这里的id小写后就变成了python系统内置的一个函数指针了，虽然不报错但是运行会出问题

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

        paramAuditList = [nIdAudit, inOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                           nAuditType,
                           json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]

        queryList = [sqlAudit]
        paramAuditList = [tuple(paramAuditList)]

        if curStatus == 1 or curStatus == 13:
            queryList.append(sqlStatus)
            paramAuditList.append(tuple(paramStatus))

        # 这里updateRpsMultiTrans是批量执行多条mysql数据，捆绑为一个事务执行，其中一个执行不成功，那么整个事务都会回滚，避免一部分成功，因此数据误改一半
        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramAuditList)

        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))

@bp_rps.route("/updateAssetOfInOutWarehouse", methods=["POST"])
def update_asset_of_in_out_warehouse():
    rcv = request.get_json()
    inOutId = rcv.get("inOutId", None)
    templateId = rcv.get("templateId", None)
    quantity = rcv.get("quantity", None)
    deadline = rcv.get("deadline", None)
    userId = rcv.get("userId", None)
    nType = rcv.get("type", None)  # 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单

    #inOutId = request.form.get("inOutId", None)
    #templateId = request.form.get("templateId", None)
    #quantity = request.form.get("quantity", None)
    #deadline = request.form.get("deadline", None)
    #userId = request.form.get("userId", None)
    #nType = request.form.get("type", None)  # 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单

    #if is_digit(inOutId):
     #   inOutId = int(float(inOutId))
    #if is_digit(templateId):
     #   templateId = int(float(templateId))
    #if is_digit(quantity):
     #   quantity = int(float(quantity))
    #if is_digit(userId):
     #   userId = int(float(userId))
    #if is_digit(nType):
     #   nType = int(float(nType))

    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库记录ID必须为整型", data=False))
    if not isinstance(templateId, int):
        return jsonify(dict(err=1, msg="资产模板ID必须为整型", data=False))
    if not isinstance(quantity, int):
        return jsonify(dict(err=1, msg="数量必须为整型", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if nType not in IN_OUT_TYPE_LIST:
        return jsonify(dict(err=1, msg="type必须在{s}".format(s=str(IN_OUT_TYPE_LIST)), data=False))
    nBillType = 2 if nType in [0, 1] else 3

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", inOutId, "rps_in_out_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nBillType, inOutId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus == 0:
        bSuc = BEOPDataAccess.getInstance().updateRpsInOutWarehouseAssetQuantity(inOutId, templateId, quantity)
        if not bSuc:
            return jsonify(dict(err=1, msg="更新失败", data=False))
        return jsonify(dict(err=0, msg="更新成功", data=True))
    elif curStatus == 1 or curStatus == 13:
        dInfo = BEOPDataAccess.getInstance().getAssetOfInOutWarehouse(inOutId)
        if dInfo == None:
            return jsonify(dict(err=1, msg="获取订单的资产信息失败", data=False))

        quantityOrig = dInfo.get(templateId, 0)

        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        dOriginal.update({"UpdateAsset": dict(inOutId=inOutId,
                                                      templateId=templateId,
                                                      quantity=quantityOrig)})
        dTarget.update({"UpdateAsset": dict(inOutId=inOutId,
                                                    templateId=templateId,
                                                    quantity=quantity)})

        sqlStatus = "UPDATE rps_in_out_warehouse SET status=13 WHERE id=%s"
        paramStatus = [inOutId]  # 这里的id小写后就变成了python系统内置的一个函数指针了，虽然不报错但是运行会出问题

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

        paramAuditList = [nIdAudit, inOutId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                          nAuditType,
                          json.dumps(dOriginal), json.dumps(dTarget), deadline, nEnabled, nResult]
        queryList = [sqlAudit]
        paramAuditList = [tuple(paramAuditList)]

        if curStatus == 1:
            queryList.append(sqlStatus)
            paramAuditList.append(tuple(paramStatus))

        # 这里updateRpsMultiTrans是批量执行多条mysql数据，捆绑为一个事务执行，其中一个执行不成功，那么整个事务都会回滚，避免一部分成功，因此数据误改一半
        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramAuditList)

        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))

@bp_rps.route("/getInOutWarehouse", methods=["POST"])
def get_in_out_warehouse():
    rcv = request.get_json()
    inOutId = rcv.get("id", None)

    if inOutId != None:
        if not isinstance(inOutId, int):
            return jsonify(dict(err=1, msg="出入库记录ID必须为整型", data=False))
        bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", inOutId, "rps_in_out_warehouse")
        if not bExists:
            return jsonify(dict(err=1, msg="进出库ID不存在", data=False))

    dataList = BEOPDataAccess.getInstance().getInOutWarehouse(inOutId)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败，售后再试", data=[]))

    fileIdList = []
    inOutIdList = []
    for data in dataList:
        inOutIdList.append(data["id"])
        if not data.get("attachment", {}):
            continue
        fileIdList.extend(list(data["attachment"].keys()))

    dAsset = BEOPDataAccess.getInstance().getRpsInOutAsset(inOutIdList)
    if dAsset == None:
        return jsonify(dict(err=1, msg="查询失败，售后再试", data=[]))

    dCheckAudit = BEOPDataAccess.getInstance().getRpsCheckAndAuditRecords(inOutIdList, [2, 3])
    if dCheckAudit == None:
        return jsonify(dict(err=1, msg="校核、审核信息查询失败", data=[]))

    dAttachment = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
    if dAttachment == None:
        return jsonify(dict(err=1, msg="查询失败，售后再试", data=[]))

    for data in dataList:
        inOutId = data["id"]
        data["asset"] = dAsset.get(inOutId, [])

        fileList = []
        for fileId in data.get("attachment").keys():
            dInfo = dAttachment.get(fileId, {})
            if dInfo:
                fileList.append(dInfo)

        data["attachment"] = fileList

        data.update(dict(check=dCheckAudit.get(data["id"], {}).get("check", {})))
        data.update(dict(createAudit=dCheckAudit.get(data["id"], {}).get("createAudit", {})))
        data.update(dict(editAudit=dCheckAudit.get(data["id"], {}).get("editAudit", {})))
        data.update(dict(terminateAudit=dCheckAudit.get(data["id"], {}).get("terminateAudit", {})))
        data.update(dict(finishAudit=dCheckAudit.get(data["id"], {}).get("finishAudit", {})))

    return jsonify(dict(err=0, msg="", data=dataList))


@bp_rps.route("/auditContract", methods=["POST"])
def audit_contract():
    rcv = request.get_json()
    contractId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)      # 审核状态: 0-待校核;1-待审核；2-审核通过;3-驳回;4-暂停;5-关闭
    opinion = rcv.get("opinion", "")
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(contractId, int):
        return jsonify(dict(err=1, msg="订单ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4,5]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    bContractIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", contractId, "rps_contract")
    if not bContractIdExists:
        return jsonify(dict(err=1, msg="订单ID不存在", data=False))

    # 销售订单
    nType = 1

    strOpLog = ""
    nOpType = -1  # 0-校核；1-审核；-1-其他
    nContractStatus = None

    # 审核状态: 0-待校核;1-待审核；2-审核通过;3-驳回;4-暂停;5-关闭
    # 订单状态: 0-待校核；1-待审核；2-生效
    if nAuditStatus == 0:
        nContractStatus = 0
        nOpType = -1
    elif nAuditStatus == 1:
        nContractStatus = 1
        nOpType = 0
        strOpLog = "用户(userId: {uId})对订单(id:{cId}) 完成校核".format(uId=userId, cId=contractId)
    elif nAuditStatus == 2:
        nContractStatus = 2
        nOpType = 1
        strOpLog = "用户(userId: {uId})对订单(id:{cId}) 执行审核通过".format(uId=userId, cId=contractId)
    elif nAuditStatus == 3:
        nContractStatus = 1
        nOpType = 1
        strOpLog = "用户(userId:{uId})对订单(id:{cId}) 驳回".format(uId=userId, cId=contractId)
    elif nAuditStatus == 4:
        nContractStatus = 1
        nOpType = -1
        strOpLog = "用户(userId:{uId})对订单(id:{cId}) 执行暂停操作".format(uId=userId, cId=contractId)
    elif nAuditStatus == 5:
        nContractStatus = 1
        nOpType = -1
        strOpLog = "用户(userId:{uId})对订单(id:{cId}) 执行关闭操作".format(uId=userId, cId=contractId)

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 订单状态
    sqlContractStatus = "UPDATE rps_contract SET status=%s WHERE id=%s"
    tplContractStatus = ((nContractStatus, contractId),)

    # 审核状态
    sqlContractAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplContractAudit = ((nAuditStatus,
                        userId,
                        opinion,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        contractId,
                        nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlContractStatus, sqlContractAudit]
    paramList = [tplContractStatus, tplContractAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


@bp_rps.route("/auditTransport", methods=["POST"])
def audit_transport():
    rcv = request.get_json()
    transportId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)  # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    opinion = rcv.get("opinion", None)
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(transportId, int):
        return jsonify(dict(err=1, msg="物流ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    # 物流
    nType = 4
    nOpType = 0   # 0-其他；1-审核
    nTransStatus = 0
    strOpLog = ""

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    # 物流状态: 0-待审核；1-生效
    if nAuditStatus == 0:
        nTransStatus = 0
        nOpType = 0
    elif nAuditStatus == 1:
        nTransStatus = 1
        nOpType = 1
        strOpLog = "用户(userId: {uId})对物流单(id:{cId}) 审核通过".format(uId=userId, cId=transportId)
    elif nAuditStatus == 2:
        nTransStatus = 0
        nOpType = 1
        strOpLog = "用户(userId: {uId})对物流单(id:{cId}) 驳回".format(uId=userId, cId=transportId)
    elif nAuditStatus == 3:
        nTransStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对物流单(id:{cId}) 暂停".format(uId=userId, cId=transportId)
    elif nAuditStatus == 4:
        nTransStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对物流单(id:{cId}) 关闭".format(uId=userId, cId=transportId)

    # 物流状态
    sqlTransStatus = "UPDATE rps_transport SET status=%s WHERE id=%s"
    tplTransStatus = ((nTransStatus, transportId),)

    # 审核状态
    sqlTransAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplTransAudit = ((nAuditStatus,
                         userId,
                         opinion,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         transportId,
                         nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlTransStatus, sqlTransAudit]
    paramList = [tplTransStatus, tplTransAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 入库审核
@bp_rps.route("/auditInWarehouse", methods=["POST"])
def audit_in_warehouse():
    rcv = request.get_json()
    inOutId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)  # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    opinion = rcv.get("opinion", None)
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    # 入库
    nType = 2
    nOpType = 0  # 0-其他；1-审核
    nInWarehouseStatus = 0
    strOpLog = ""

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    # 入库状态: 0-待审核；1-生效
    if nAuditStatus == 0:
        nInWarehouseStatus = 0
        nOpType = 0
    elif nAuditStatus == 1:
        nInWarehouseStatus = 1
        nOpType = 1
        strOpLog = "用户(userId: {uId})对入库单(id:{cId}) 审核通过".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 2:
        nInWarehouseStatus = 0
        nOpType = 1
        strOpLog = "用户(userId: {uId})对入库单(id:{cId}) 驳回".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 3:
        nInWarehouseStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对入库单(id:{cId}) 暂停".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 4:
        nInWarehouseStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对入库单(id:{cId}) 关闭".format(uId=userId, cId=inOutId)

    # 入库状态
    sqlInWarehouseStatus = "UPDATE rps_in_out_warehouse SET status=%s WHERE id=%s"
    tplInWarehouseStatus = ((nInWarehouseStatus, inOutId),)

    # 审核状态
    sqlInWarehouseAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplInWarehouseAudit = ((nAuditStatus,
                      userId,
                      opinion,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      inOutId,
                      nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlInWarehouseStatus, sqlInWarehouseAudit]
    paramList = [tplInWarehouseStatus, tplInWarehouseAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 入库完成审核
@bp_rps.route("/auditInWarehouseDone", methods=["POST"])
def audit_in_warehouse_done():
    rcv = request.get_json()
    inOutId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)  # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    opinion = rcv.get("opinion", None)
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    # 入库完成
    nType = 5
    nOpType = 0  # 0-其他；1-审核
    nInStatus = 0
    strOpLog = ""

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    # 入库完成状态: 0-待审核；1-生效
    if nAuditStatus == 0:
        nInStatus = 0
        nOpType = 0
    elif nAuditStatus == 1:
        nInStatus = 1
        nOpType = 1
        strOpLog = "用户(userId: {uId})对入库完成单(id:{cId}) 审核通过".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 2:
        nInStatus = 0
        nOpType = 1
        strOpLog = "用户(userId: {uId})对入库完成单(id:{cId}) 驳回".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 3:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对入库完成单(id:{cId}) 暂停".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 4:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对入库完成单(id:{cId}) 关闭".format(uId=userId, cId=inOutId)

    # 入库完成状态
    sqlInStatus = "UPDATE rps_in_out_warehouse SET status=%s WHERE id=%s"
    tplInStatus = ((nInStatus, inOutId),)

    # 审核状态
    sqlInAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplInAudit = ((nAuditStatus,
                      userId,
                      opinion,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      inOutId,
                      nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlInStatus, sqlInAudit]
    paramList = [tplInStatus, tplInAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 出库单审核
@bp_rps.route("/auditOutWarehouse", methods=["POST"])
def audit_out_warehouse():
    rcv = request.get_json()
    inOutId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)  # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    opinion = rcv.get("opinion", None)
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    nType = 3  # 出库
    nOpType = 0  # 0-其他；1-审核
    nInStatus = 0
    strOpLog = ""

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    # 出库状态: 0-待审核；1-生效
    if nAuditStatus == 0:
        nInStatus = 0
        nOpType = 0
    elif nAuditStatus == 1:
        nInStatus = 1
        nOpType = 1
        strOpLog = "用户(userId: {uId})对出库单(id:{cId}) 审核通过".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 2:
        nInStatus = 0
        nOpType = 1
        strOpLog = "用户(userId: {uId})对出库单(id:{cId}) 驳回".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 3:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对出库单(id:{cId}) 暂停".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 4:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对出库单(id:{cId}) 关闭".format(uId=userId, cId=inOutId)

    # 出库状态
    sqlInStatus = "UPDATE rps_in_out_warehouse SET status=%s WHERE id=%s"
    tplInStatus = ((nInStatus, inOutId),)

    # 审核状态
    sqlInAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplInAudit = ((nAuditStatus,
                      userId,
                      opinion,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      inOutId,
                      nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlInStatus, sqlInAudit]
    paramList = [tplInStatus, tplInAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 出库完成审核
@bp_rps.route("/auditOutWarehouseDone", methods=["POST"])
def audit_out_warehouse_done():
    rcv = request.get_json()
    inOutId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    nAuditStatus = rcv.get("targetStatus", None)  # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    opinion = rcv.get("opinion", None)
    remark = rcv.get("remark", "")

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if not isinstance(inOutId, int):
        return jsonify(dict(err=1, msg="出入库ID必须为整数", data=False))
    if nAuditStatus not in [0,1,2,3,4]:
        return jsonify(dict(err=1, msg="目标状态值有误", data=False))
    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注内容必须为字符串", data=False))

    nType = 6  # 出库完成
    nOpType = 0  # 0-其他；1-审核
    nInStatus = 0
    strOpLog = ""

    nMaxIdOp = BEOPDataAccess.getInstance().getMaxIdInTable("rps_operation_log")
    nIdOp = nMaxIdOp + 1

    # 审核状态: 0-待审核;1-审核通过；2-驳回;3-暂停;4-关闭
    # 出库状态: 0-待审核；1-生效
    if nAuditStatus == 0:
        nInStatus = 0
        nOpType = 0
    elif nAuditStatus == 1:
        nInStatus = 1
        nOpType = 1
        strOpLog = "用户(userId: {uId})对出库单(id:{cId}) 审核通过".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 2:
        nInStatus = 0
        nOpType = 1
        strOpLog = "用户(userId: {uId})对出库单(id:{cId}) 驳回".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 3:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对出库单(id:{cId}) 暂停".format(uId=userId, cId=inOutId)
    elif nAuditStatus == 4:
        nInStatus = 0
        nOpType = 0
        strOpLog = "用户(userId:{uId})对出库单(id:{cId}) 关闭".format(uId=userId, cId=inOutId)

    # 出库状态
    sqlInStatus = "UPDATE rps_in_out_warehouse SET status=%s WHERE id=%s"
    tplInStatus = ((nInStatus, inOutId),)

    # 审核状态
    sqlInAudit = "UPDATE rps_audit SET status=%s, auditor_id=%s, opinion=%s, audit_time=%s WHERE bill_id=%s AND type=%s"
    tplInAudit = ((nAuditStatus,
                      userId,
                      opinion,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      inOutId,
                      nType),)

    # 操作记录
    nEnabled = 1
    sqlOp = "INSERT INTO rps_operation_log (id, time, type, op_type, op_id, log, remark, enabled) VALUES (%s, %s,%s,%s,%s,%s,%s,%s)"
    tplOp = ((nIdOp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nType, nOpType, userId, strOpLog, remark, nEnabled),)

    quaryList = [sqlInStatus, sqlInAudit]
    paramList = [tplInStatus, tplInAudit]
    if len(strOpLog):
        quaryList.append(sqlOp)
        paramList.append(tplOp)

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(quaryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 提交校核
@bp_rps.route("/submitCheck", methods=["POST"])
def submit_check():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    nAuditType = 0  # 创建校核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 0:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法操作".format(cur=curStatus), data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
    nIdAudit = nMaxIdAudit + 1

    nEnabled = 1
    nResult = -1

    sqlStatus = "UPDATE {table} SET status=11 WHERE id=%s".format(table=strTableName)
    paramStatus = [nId]

    sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    paramAudit = [nIdAudit, nId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, deadline, nEnabled, nResult]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 撤回校核
@bp_rps.route("/recallCheck", methods=["POST"])
def recall_check():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)

    nAuditType = 0  # 创建校核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 11:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=0 WHERE id=%s".format(table=strTableName)
    paramStatus = [nId]

    sqlAudit = "UPDATE rps_audit SET enabled=0, auditor_id=%s, audit_time=%s WHERE bill_id=%s AND type=%s AND audit_type=%s"
    paramAudit = [userId, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nId, nType, nAuditType]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 校核通过或不通过
@bp_rps.route("/disposeCheck", methods=["POST"])
def dispose_check():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    nValue = rcv.get("value", None)  # 0-不通过；1-通过
    opinion = rcv.get("opinion", "")
    deadline = request.form.get("deadline", None)

    nCheckType = 0  # 创建校核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    if nValue not in [0, 1]:
        return jsonify(dict(err=1, msg="value必须为0或1", data=False))

    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))

    if nValue == 0 and not opinion:
        return jsonify(dict(err=1, msg="审核不通过时意见不能为空", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单据ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 11:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=%s WHERE id=%s".format(table=strTableName)
    paramStatus = [12 if nValue == 1 else 0, nId]

    sqlCheck = "UPDATE rps_audit SET result=%s, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=%s AND audit_type=%s AND result=-1 AND enabled=1"
    paramCheck = [nValue, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nType, nCheckType]

    queryList = [sqlStatus, sqlCheck]
    paramList = [tuple(paramStatus), tuple(paramCheck)]

    if nValue == 1:
        nAuditMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nAuditMaxId + 1
        nAuditType = 1 # 创建审核
        nEnabled = 1
        nResult = -1

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, nId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, deadline, nEnabled, nResult]

        queryList.append(sqlAudit)
        paramList.append(tuple(paramAudit))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 撤回已提交的审核
@bp_rps.route("/recallAudit", methods=["POST"])
def recall_audit():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)

    nAuditType = 1  # 创建审核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 12:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=11 WHERE id=%s".format(table=strTableName)
    paramStatus = [nId]

    sqlAudit = "UPDATE rps_audit SET enabled=0, auditor_id=%s, audit_time=%s WHERE bill_id=%s AND type=%s AND audit_type=%s"
    paramAudit = [userId, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nId, nType, nAuditType]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 审核通过与不通过
@bp_rps.route("/disposeAudit", methods=["POST"])
def dispose_audit():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    opinion = rcv.get("opinion", "")
    nValue = rcv.get("value", None)

    nAuditType = 1  # 创建审核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    if nValue not in [0, 1]:
        return jsonify(dict(err=1, msg="value必须为0或1", data=False))

    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))

    if nValue == 0 and not opinion:
        return jsonify(dict(err=1, msg="审核不通过时意见不能为空", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 12:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=%s WHERE id=%s".format(table=strTableName)
    paramStatus = [1 if nValue == 1 else 0, nId]

    sqlAudit = "UPDATE rps_audit SET result=%s, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=%s AND audit_type=%s AND enabled=1"
    paramAudit = [nValue, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nType, nAuditType]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))

# 完成
@bp_rps.route("/submit", methods=["POST"])
def submit():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    deadline = request.form.get("deadline", None)

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 1:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=15 WHERE id=%s".format(table=strTableName)
    paramStatus = [nId]

    nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
    nIdAudit = nMaxIdAudit + 1
    nAuditType = 4  # 完成审核
    nEnabled = 1
    nResult = -1

    sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    paramAudit = [nIdAudit, nId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, deadline,
                  nEnabled, nResult]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 终止
@bp_rps.route("/terminate", methods=["POST"])
def terminate():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)
    reason = rcv.get("reason", None)

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    if not isinstance(reason, str):
        return jsonify(dict(err=1, msg="原因不能为空且必须为字符串", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 1:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=14 WHERE id=%s".format(table=strTableName)
    paramStatus = [nId]

    nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
    nIdAudit = nMaxIdAudit + 1
    nAuditType = 3  # 终止审核
    nEnabled = 1
    nResult = -1

    sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, deadline, enabled, opinion, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    paramAudit = [nIdAudit, nId, nType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, deadline,
                  nEnabled, reason, nResult]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))

# 审核修改的内容，若通过，则将修改内容更新进相应的数据表里
@bp_rps.route("/disposeContentAudit", methods=["POST"])
def dispose_content_audit():
    rcv = request.get_json()
    nId = rcv.get("id", None)   # 单据ID
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    nValue = rcv.get("value", None)
    opinion = rcv.get("opinion", "")
    nAuditId = rcv.get("auditId", None)

    nAuditType = 2  # 修改审核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if nValue not in [0, 1]:
        return jsonify(dict(err=1, msg="value必须为0或1", data=False))

    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))

    if nValue == 0 and not opinion:
        return jsonify(dict(err=1, msg="审核不通过时意见不能为空", data=False))

    if not isinstance(nAuditId, int):
        return jsonify(dict(err=1, msg="审核单ID不能为空且必须为整数", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 13:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    if nType == 1:  # 销售订单
        if nValue == 0:
            sqlStatus = "UPDATE rps_contract SET status=1 WHERE id=%s" #status=1完成提交
            paramStatus = [nId]

            sqlAudit = "UPDATE rps_audit SET result=0, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=1 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 1, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                queryList.append(sqlStatus)
                paramList.append(tuple(paramStatus))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))

        else:
            target = BEOPDataAccess.getInstance().getRpsEditAuditTarget(nId, nType, nAuditType, nAuditId)
            if target == None:
                return jsonify(dict(err=1, msg="获取目标修改内容失败", data=False))

            contractStKey = {
                "clientId": "client_id",
                "salesId": "sales_id",
                "clientContact": "client_contact",
                "deliveryTime": "delivery_time",
                "dueTime": "due_time",
                "amount": "amount"
            }

            setSqlList = []
            setPrmList = []

            sqlAddAsset = None
            addAssetPrmList = None
            sqlDeleteAsset = None
            deleteAssetPrmList = None
            sqlUpdateAsset = None
            updateAssetPrmList = None
            for key, value in target.items():
                if key == "fileIdList":
                    setSqlList.append("attachment_id=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key == "AddAssetList":
                    sqlAddAsset = "REPLACE INTO rps_contract_asset_template (contract_id, template_id, quantity) VALUES (%s, %s, %s)"
                    addAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "DeleteAssetList":
                    sqlDeleteAsset = "DELETE FROM rps_contract_asset_template WHERE contract_id=%s AND template_id=%s"
                    deleteAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "UpdateAsset":
                    sqlUpdateAsset = "REPLACE INTO rps_contract_asset_template (contract_id, template_id, quantity) VALUES (%s, %s, %s)"
                    updateAssetPrmList = [(value["contractId"], value["templateId"], value["quantity"])]
                    continue

                if key not in contractStKey.keys():
                    continue

                setSqlList.append("{0}=%s".format(contractStKey[key]))
                setPrmList.append(value)

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 1, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                setSqlList.append("status=%s")
                setPrmList.append(1)

            sqlBill = "UPDATE rps_contract SET " + ",".join(setSqlList) + " WHERE id=%s"
            setPrmList.append(nId)

            sqlAudit = "UPDATE rps_audit SET result=1, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=1 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            if len(setSqlList):
                queryList.append(sqlBill)
                paramList.append(tuple(setPrmList))

            if sqlAddAsset:
                queryList.append(sqlAddAsset)
                paramList.append(tuple(addAssetPrmList))

            if sqlDeleteAsset:
                queryList.append(sqlDeleteAsset)
                paramList.append(tuple(deleteAssetPrmList))

            if sqlUpdateAsset:
                queryList.append(sqlUpdateAsset)
                paramList.append(tuple(updateAssetPrmList))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))

    elif nType == 2:  # 入库单
        if nValue == 0:
            sqlStatus = "UPDATE rps_in_out_warehouse SET status=1 WHERE id=%s"
            paramStatus = [nId]

            sqlAudit = "UPDATE rps_audit SET result=0, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=2 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 2, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                queryList.append(sqlStatus)
                paramList.append(tuple(paramStatus))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))
        else:
            target = BEOPDataAccess.getInstance().getRpsEditAuditTarget(nId, nType, nAuditType, nAuditId)
            if target == None:
                return jsonify(dict(err=1, msg="获取目标修改内容失败", data=False))

            inStKey = {
                "warehouseId": "warehouse_id",
                "transportId": "transport_id",
                "additional": "additional"
            }

            sqlAddAsset = None
            addAssetPrmList = None
            sqlDeleteAsset = None
            deleteAssetPrmList = None
            sqlUpdateAsset = None
            updateAssetPrmList = None

            setSqlList = []
            setPrmList = []
            for key, value in target.items():
                if key == "fileIdList":
                    setSqlList.append("attachment_id=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key == "inOutAddAssetList":
                    sqlAddAsset = "REPLACE INTO rps_in_out_warehouse_detail (in_out_id, template_id, quantity) VALUES (%s, %s, %s)"
                    addAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "inOutDeleteAssetList":
                    sqlDeleteAsset = "DELETE FROM rps_in_out_warehouse_detail WHERE in_out_id=%s AND template_id=%s"
                    deleteAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "inOutUpdateAsset":
                    sqlUpdateAsset = "REPLACE INTO rps_in_out_warehouse_detail (in_out_id, template_id, quantity) VALUES (%s, %s, %s)"
                    updateAssetPrmList = [(value["inOutId"], value["templateId"], value["quantity"])]
                    continue

                if key not in inStKey.keys():
                    continue

                setSqlList.append("{0}=%s".format(inStKey[key]))
                setPrmList.append(value)

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 2, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                setSqlList.append("status=%s")
                setPrmList.append(1)

            sqlBill = "UPDATE rps_in_out_warehouse SET " + ",".join(setSqlList) + " WHERE id=%s"
            setPrmList.append(nId)

            sqlAudit = "UPDATE rps_audit SET result=1, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=2 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            if len(setSqlList):
                queryList.append(sqlBill)
                paramList.append(tuple(setPrmList))

            if sqlAddAsset:
                queryList.append(sqlAddAsset)
                paramList.append(tuple(addAssetPrmList))

            if sqlDeleteAsset:
                queryList.append(sqlDeleteAsset)
                paramList.append(tuple(deleteAssetPrmList))

            if sqlUpdateAsset:
                queryList.append(sqlUpdateAsset)
                paramList.append(tuple(updateAssetPrmList))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))

    elif nType == 3:  # 出库单
        if nValue == 0:
            sqlStatus = "UPDATE rps_in_out_warehouse SET status=1 WHERE id=%s"
            paramStatus = [nId]

            sqlAudit = "UPDATE rps_audit SET result=0, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=3 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 3, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                queryList.append(sqlStatus)
                paramList.append(tuple(paramStatus))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))
        else:
            target = BEOPDataAccess.getInstance().getRpsEditAuditTarget(nId, nType, nAuditType, nAuditId)
            if target == None:
                return jsonify(dict(err=1, msg="获取目标修改内容失败", data=False))

            outStKey = {
                "warehouseId": "warehouse_id",
                "transportId": "transport_id",
                "additional": "additional"
            }

            sqlAddAsset = None
            addAssetPrmList = None
            sqlDeleteAsset = None
            deleteAssetPrmList = None
            sqlUpdateAsset = None
            updateAssetPrmList = None

            setSqlList = []
            setPrmList = []
            for key, value in target.items():
                if key == "fileIdList":
                    setSqlList.append("attachment_id=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key == "inOutAddAssetList":
                    sqlAddAsset = "REPLACE INTO rps_in_out_warehouse_detail (in_out_id, template_id, quantity) VALUES (%s, %s, %s)"
                    addAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "inOutDeleteAssetList":
                    sqlDeleteAsset = "DELETE FROM rps_in_out_warehouse_detail WHERE in_out_id=%s AND template_id=%s"
                    deleteAssetPrmList = [tuple(item) for item in value]
                    continue

                if key == "inOutUpdateAsset":
                    sqlUpdateAsset = "REPLACE INTO rps_in_out_warehouse_detail (in_out_id, template_id, quantity) VALUES (%s, %s, %s)"
                    updateAssetPrmList = [(value["inOutId"], value["templateId"], value["quantity"])]
                    continue

                if key not in outStKey.keys():
                    continue

                setSqlList.append("{0}=%s".format(outStKey[key]))
                setPrmList.append(value)

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 3, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                setSqlList.append("status=%s")
                setPrmList.append(1)

            sqlBill = "UPDATE rps_in_out_warehouse SET " + ",".join(setSqlList) + " WHERE id=%s"
            setPrmList.append(nId)

            sqlAudit = "UPDATE rps_audit SET result=1, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=3 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            if len(setSqlList):
                queryList.append(sqlBill)
                paramList.append(tuple(setPrmList))

            if sqlAddAsset:
                queryList.append(sqlAddAsset)
                paramList.append(addAssetPrmList)

            if sqlDeleteAsset:
                queryList.append(sqlDeleteAsset)
                paramList.append(deleteAssetPrmList)

            if sqlUpdateAsset:
                queryList.append(sqlUpdateAsset)
                paramList.append(updateAssetPrmList)

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))

    elif nType == 4:  # 物流单
        if nValue == 0:
            sqlStatus = "UPDATE rps_transport SET status=1 WHERE id=%s"
            paramStatus = [nId]

            sqlAudit = "UPDATE rps_audit SET result=0, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=4 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 4, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                queryList.append(sqlStatus)
                paramList.append(tuple(paramStatus))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))
        else:
            target = BEOPDataAccess.getInstance().getRpsEditAuditTarget(nId, nType, nAuditType, nAuditId)
            if target == None:
                return jsonify(dict(err=1, msg="获取目标修改内容失败", data=False))

            transStKey = {
                "contractId": "contract_id",
                "departWarehouseId": "depart_warehouse_id",
                "destWarehouseId": "dest_warehouse_id",
                "estimatedArriveDate": "estimated_arrive_time"
            }

            setSqlList = []
            setPrmList = []
            for key, value in target.items():
                if key == "receiveDeliveryImgFileIdList":
                    setSqlList.append("receive_delivery_img=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key == "signImgFileIdList":
                    setSqlList.append("sign_img=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key not in transStKey.keys():
                    continue

                setSqlList.append("{0}=%s".format(transStKey[key]))
                setPrmList.append(value)

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 4, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                setSqlList.append("status=%s")
                setPrmList.append(1)

            sqlBill = "UPDATE rps_transport SET " + ",".join(setSqlList) + " WHERE id=%s"
            setPrmList.append(nId)

            sqlAudit = "UPDATE rps_audit SET result=1, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=4 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            if len(setSqlList):
                queryList.append(sqlBill)
                paramList.append(tuple(setPrmList))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))

    elif nType == 5:  # 报废单
        if nValue == 0:
            sqlStatus = "UPDATE rps_retirement SET status=1 WHERE id=%s"
            paramStatus = [nId]

            sqlAudit = "UPDATE rps_audit SET result=0, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=5 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 5, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                queryList.append(sqlStatus)
                paramList.append(tuple(paramStatus))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))
        else:
            target = BEOPDataAccess.getInstance().getRpsEditAuditTarget(nId, nType, nAuditType, nAuditId)
            if target == None:
                return jsonify(dict(err=1, msg="获取目标修改内容失败", data=False))

            retirementStKey = {
                "reason": "reason",
                "remark": "remark",
                "warehouseId": "warehouse_id"
            }

            setSqlList = []
            setPrmList = []

            for key, value in target.items():
                if key == "fileIdList":
                    setSqlList.append("attachment_id=%s")
                    setPrmList.append(",".join([str(nId) for nId in value]))
                    continue

                if key not in retirementStKey.keys():
                    continue

                setSqlList.append("{0}=%s".format(retirementStKey[key]))
                setPrmList.append(value)

            # 只有当所有审核项都通过后才改变状态
            toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, 5, -1)
            if toAuditList == None:
                return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
            bChangeStatus = True
            for obj in toAuditList:
                if obj.get("nAuditId") != nAuditId:
                    bChangeStatus = False
                    break

            if bChangeStatus:
                setSqlList.append("status=%s")
                setPrmList.append(1)

            sqlBill = "UPDATE rps_retirement SET " + ",".join(setSqlList) + " WHERE id=%s"
            setPrmList.append(nId)

            sqlAudit = "UPDATE rps_audit SET result=1, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=5 AND audit_type=2 AND enabled=1 AND id=%s"
            paramAudit = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nAuditId]

            queryList = [sqlAudit]
            paramList = [tuple(paramAudit)]

            if len(setSqlList):
                queryList.append(sqlBill)
                paramList.append(tuple(setPrmList))

            bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
            if not bSuc:
                return jsonify(dict(err=1, msg="执行失败", data=False))
            return jsonify(dict(err=0, msg="执行成功", data=True))


# 审核终止
@bp_rps.route("/disposeTerminate", methods=["POST"])
def dispose_terminate():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    opinion = rcv.get("opinion", "")
    nValue = rcv.get("value", None)

    nAuditType = 3  # 创建审核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    if nValue not in [0, 1]:
        return jsonify(dict(err=1, msg="value必须为0或1", data=False))

    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))

    if nValue == 0 and not opinion:
        return jsonify(dict(err=1, msg="审核不通过时意见不能为空", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 14:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=%s WHERE id=%s".format(table=strTableName)
    paramStatus = [-1 if nValue == 1 else 1, nId]

    sqlAudit = "UPDATE rps_audit SET result=%s, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=%s AND audit_type=%s AND enabled=1"
    paramAudit = [nValue, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nType, nAuditType]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))

# 审核完成
@bp_rps.route("/disposeSubmit", methods=["POST"])
def dispose_submit():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    nType = rcv.get("type", None)  # 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    userId = rcv.get("userId", None)
    opinion = rcv.get("opinion", "")
    nValue = rcv.get("value", None)

    nAuditType = 4  # 创建审核

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=False))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type类型必须为整数", data=False))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type类型必须在1,2,3,4,5中间", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))

    if nValue not in [0, 1]:
        return jsonify(dict(err=1, msg="value必须为0或1", data=False))

    if not isinstance(opinion, str):
        return jsonify(dict(err=1, msg="审核意见必须为字符串", data=False))

    if nValue == 0 and not opinion:
        return jsonify(dict(err=1, msg="审核不通过时意见不能为空", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    strTableName = ""
    if nType == 1:
        strTableName = "rps_contract"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nType == 4:
        strTableName = "rps_transport"
    elif nType == 5:
        strTableName = "rps_retirement"

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, strTableName)
    if not bExists:
        return jsonify(dict(err=1, msg="单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(nType, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 15:
        return jsonify(dict(err=1, msg="订单当前状态为{cur}，无法执行此操作".format(cur=curStatus), data=False))

    sqlStatus = "UPDATE {table} SET status=%s WHERE id=%s".format(table=strTableName)
    paramStatus = [2 if nValue == 1 else 1, nId]

    sqlAudit = "UPDATE rps_audit SET result=%s, audit_time=%s, auditor_id=%s, opinion=%s WHERE bill_id=%s AND type=%s AND audit_type=%s AND enabled=1"
    paramAudit = [nValue, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, opinion, nId, nType, nAuditType]

    queryList = [sqlStatus, sqlAudit]
    paramList = [tuple(paramStatus), tuple(paramAudit)]

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 获取某个单（比如某个销售订单）的所有修改造成的校核、审核项
@bp_rps.route("/getRpsAuditRecord", methods=["POST"])
def get_rps_edit_audit_record():
    rcv = request.get_json()
    nId = rcv.get("id", None)   # 单据ID
    nType = rcv.get("type", None)  # 类型  1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
    nFlag = rcv.get("flag", None)  # 结果类型：-1：待审核；1-已通过审核；0-审核不通过；None-表示全部

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单ID必须为整数", data=[]))
    if not isinstance(nType, int):
        return jsonify(dict(err=1, msg="type必须为整数", data=[]))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="type 必须为1或2或3或4或5", data=[]))

    if nFlag != None:
        if nFlag not in [-1, 0, 1]:
            return jsonify(dict(err=1, msg="flag必须为-1或1或0", data=[]))

    dataList = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, nType, nFlag)
    if dataList == None:
        return jsonify(dict(err=1, msg="获取失败", data=False))

    attachmentFileIdList = []
    for data in dataList:
        original = data.get("original", {})
        for key, value in original.items():
            if key in ["fileIdList", "receiveDeliveryImgFileIdList", "signImgFileIdList"]:
                attachmentFileIdList.extend(value)

        target = data.get("target", {})
        for key, value in target.items():
            if key in ["fileIdList", "receiveDeliveryImgFileIdList", "signImgFileIdList"]:
                attachmentFileIdList.extend(value)

    attachmentFileIdList = list(set(attachmentFileIdList))
    dAttachmentInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(attachmentFileIdList)
    if dAttachmentInfo == None:
        return jsonify(dict(err=1, msg="获取附件信息失败", data=False))

    dTemplateInfo = BEOPDataAccess.getInstance().getAssetTemplates(0)
    if dTemplateInfo == None:
        return jsonify(dict(err=1, msg="获取模板名称失败", data=False))

    for data in dataList:
        if data.get("auditType") != 2:
            continue

        original = data.get("original")
        if original!=None:
            originalContent = {}
            for key, value in original.items():
                if key == "fileIdList":
                    originalContent.update({"attachment": []})
                    for fileId in value:
                        originalContent["attachment"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "receiveDeliveryImgFileIdList":
                    originalContent.update({"receiveDeliveryImg": []})
                    for fileId in value:
                        originalContent["receiveDeliveryImg"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "signImgFileIdList":
                    originalContent.update({"signImg": []})
                    for fileId in value:
                        originalContent["signImg"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "UpdateAsset":
                    templateId = value["templateId"]
                    templateName = dTemplateInfo.get(templateId, "")
                    value.update({"templateName": templateName})
                    originalContent.update(dict(UpdateAsset=value))
                    continue

                strChName = FIELD_NAME_MAP.get(key) if FIELD_NAME_MAP.get(key, None) != None else key
                originalContent.update({strChName: value})

        target = data.get("target")
        if target != None:
            targetContent = {}
            for key, value in target.items():
                if key == "fileIdList":
                    targetContent.update({"attachment": []})
                    for fileId in value:
                        targetContent["attachment"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "receiveDeliveryImgFileIdList":
                    targetContent.update({"receiveDeliveryImg": []})
                    for fileId in value:
                        targetContent["receiveDeliveryImg"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "signImgFileIdList":
                    targetContent.update({"signImg": []})
                    for fileId in value:
                        targetContent["signImg"].append(
                            dAttachmentInfo.get(fileId, {})
                        )
                    continue

                if key == "AddAssetList":
                    targetContent.update({"AddAsset": []})
                    for les in value:
                        templateId = les[1]
                        templateName = dTemplateInfo.get(templateId, "")
                        quantity = les[2]
                        targetContent["AddAsset"].append(dict(templateId=templateId,
                                                                      templateName=templateName,
                                                                      quantity=quantity))
                    continue

                if key == "DeleteAssetList":
                    targetContent.update({"DeleteAsset": []})
                    for les in value:
                        templateId = les[1]
                        templateName = dTemplateInfo.get(templateId, "")
                        targetContent["DeleteAsset"].append(dict(templateId=templateId,
                                                                         templateName=templateName))
                    continue

                if key == "UpdateAsset":
                    templateId = value["templateId"]
                    templateName = dTemplateInfo.get(templateId, "")
                    value.update({"templateName": templateName})
                    targetContent.update(dict(UpdateAsset=value))
                    continue

                strChName = FIELD_NAME_MAP.get(key) if FIELD_NAME_MAP.get(key, None) != None else key
                targetContent.update({strChName: value})

            if "original" in data:
                del data["original"]

            if "target" in data:
                del data["target"]
            data.update(dict(original=originalContent, target=targetContent))

    return jsonify(dict(err=0, msg="", data=dataList))


# 根据RFID事件记录获取某个时间段内进出某个仓库的所有资产信息
@bp_rps.route("/getRelatedAssetFromRFIDInPeriod", methods=["POST"])
def get_related_asset_from_rfid_in_period():
    rcv = request.get_json()
    warehouseId = rcv.get("warehouseId", None)
    strBegin = rcv.get("begin", None)
    strEnd = rcv.get("end", None)

    if not isinstance(warehouseId, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整数", data=[]))
    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="仓库ID不存在", data=False))
    if not isinstance(strBegin, str):
        return jsonify(dict(err=1, msg="起始时间必须为字符串", data=[]))
    if not isinstance(strEnd, str):
        return jsonify(dict(err=1, msg="结束时间必须为字符串", data=[]))
    if not isValidDate(strBegin, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="起始时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))
    if not isValidDate(strEnd, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="结束时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))

    dataList = BEOPDataAccess.getInstance().getRelatedAssetFromRFIDInPeriod(warehouseId, strBegin, strEnd)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="", data=dataList))


# 根据蓝牙网关事件记录获取某个时间段内进出某个仓库的所有资产信息
@bp_rps.route("/getRelatedAssetFromBeaconInPeriod", methods=["POST"])
def get_related_asset_from_beacon_in_period():
    rcv = request.get_json()
    warehouseId = rcv.get("warehouseId", None)
    strBegin = rcv.get("begin", None)
    strEnd = rcv.get("end", None)

    if not isinstance(warehouseId, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整数", data=[]))
    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="仓库ID不存在", data=False))
    if not isinstance(strBegin, str):
        return jsonify(dict(err=1, msg="起始时间必须为字符串", data=[]))
    if not isinstance(strEnd, str):
        return jsonify(dict(err=1, msg="结束时间必须为字符串", data=[]))
    if not isValidDate(strBegin, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="起始时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))
    if not isValidDate(strEnd, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="结束时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))

    dataList = BEOPDataAccess.getInstance().getRelatedAssetFromBeaconInPeriod(warehouseId, strBegin, strEnd)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="", data=dataList))


# 根据定位板事件记录获取某个时间段内进出某个仓库的所有资产信息
@bp_rps.route("/getRelatedAssetFromLbsInPeriod", methods=["POST"])
def get_related_asset_from_lbs_in_period():
    rcv = request.get_json()
    warehouseId = rcv.get("warehouseId", None)
    strBegin = rcv.get("begin", None)
    strEnd = rcv.get("end", None)

    if not isinstance(warehouseId, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整数", data=[]))
    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
    if not bExists:
        return jsonify(dict(err=1, msg="仓库ID不存在", data=False))
    if not isinstance(strBegin, str):
        return jsonify(dict(err=1, msg="起始时间必须为字符串", data=[]))
    if not isinstance(strEnd, str):
        return jsonify(dict(err=1, msg="结束时间必须为字符串", data=[]))
    if not isValidDate(strBegin, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="起始时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))
    if not isValidDate(strEnd, "%Y-%m-%d %H:%M:%S"):
        return jsonify(dict(err=1, msg="结束时间格式有误(yyyy-mm-dd HH:MM:SS)", data=[]))

    dataList = BEOPDataAccess.getInstance().getRelatedAssetFromLbsInPeriod(warehouseId, strBegin, strEnd)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败", data=[]))
    return jsonify(dict(err=0, msg="", data=dataList))


@bp_rps.route("/addRetirement", methods=["POST"])
def add_retirement():
    rcv = request.get_json()
    equipId = rcv.get("equipId", None)
    reason = rcv.get("reason", None)
    userId = rcv.get("userId", None)
    warehouseId = rcv.get("warehouseId", None)
    remark = rcv.get("remark", "")

    if not isinstance(equipId, int):
        return jsonify(dict(err=1, msg="资产ID必须为整数", data=False))
    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="用户ID必须为整数", data=False))
    if not isinstance(warehouseId, int):
        return jsonify(dict(err=1, msg="仓库ID必须为整数", data=False))
    if not isinstance(reason, str):
        return jsonify(dict(err=1, msg="报废原因必须为字符串", data=False))
    if not len(reason):
        return jsonify(dict(err=1, msg="报废原因不能为空", data=False))
    if not isinstance(remark, str):
        return jsonify(dict(err=1, msg="备注必须为字符串", data=False))

    bEquipIdExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", equipId, "equip_list")
    if not bEquipIdExists:
        return jsonify(dict(err=1, msg="资产ID不存在", data=False))
    bWarehouseExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
    if not bWarehouseExists:
        return jsonify(dict(err=1, msg="仓库ID不存在", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    bAlreadyExists = BEOPDataAccess.getInstance().fieldExistsInTable("equip_id", equipId, "rps_retirement")
    if bAlreadyExists:
        return jsonify(dict(err=1, msg="该资产ID已存在于报废记录中", data=False))

    nMaxId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_retirement")
    nId = nMaxId + 1

    nStatus = 0
    strApplyTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strAttachmentId = ""
    nEnabled = 1

    bSuc = BEOPDataAccess.getInstance().addRetirement(nId, equipId, userId, warehouseId, reason, nStatus, strApplyTime, strAttachmentId, nEnabled, remark)
    if not bSuc:
        return jsonify(dict(err=1, msg="添加失败", data=False))
    return jsonify(dict(err=0, msg="添加成功", data=True))


@bp_rps.route("/deleteRetirement", methods=["POST"])
def delete_retirement():
    rcv = request.get_json()
    nId = rcv.get("id", None)

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="报废单ID必须为整数", data=False))

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_retirement")
    if not bExists:
        return jsonify(dict(err=1, msg="报废单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(5, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus != 0:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不能执行该操作".format(cur=curStatus), data=False))

    attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfRetirement(nId)
    if attachmentIdList == None:
        return jsonify(dict(err=1, msg="附件ID列表获取失败", data=False))

    dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(attachmentIdList)
    if dFileInfo == None:
        return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

    attachmentFileNameList = []
    for value in dFileInfo.values():
        fName = value.get("fileName", "")
        if fName:
            attachmentFileNameList.append(fName)

    bSucDel = False
    count = 0
    while count < 5:
        bSucDel = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if bSucDel:
            break
        time.sleep(0.2)
        count += 1

    # 禁用附件
    sqlDis = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
    paramDis = [(fileId,) for fileId in attachmentIdList]

    # 删除报废记录
    sqlDel = "DELETE FROM rps_retirement WHERE id=%s"
    paramDel = (nId,)

    queryList = [sqlDel]
    paramList = [(paramDel,)]

    if len(attachmentIdList):
        queryList.append(sqlDis)
        paramList.append(tuple(paramDis))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="删除失败", data=False))
    return jsonify(dict(err=0, msg="删除成功", data=True))


@bp_rps.route("/updateRetirement", methods=["POST"])
def update_retirement():
    rcv = request.get_json()
    nId = rcv.get("id", None)
    userId = rcv.get("userId", None)
    deadline = rcv.get("deadline", None)

    reason = rcv.get("reason", None)
    warehouseId = rcv.get("warehouseId", None)
    remark = rcv.get("remark", None)

    reasonOrig = rcv.get("reasonOrig", None)
    warehouseIdOrig = rcv.get("warehouseIdOrig", None)
    remarkOrig = rcv.get("remarkOrig", None)


    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="报废单ID必须为整数", data=False))
    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_retirement")
    if not bExists:
        return jsonify(dict(err=1, msg="报废单ID不存在", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="用户ID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"
    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    if reason != None:
        if not isinstance(reason, str):
            return jsonify(dict(err=1, msg="报废原因必须为字符串", data=False))

    if warehouseId != None:
        if not isinstance(warehouseId, int):
            return jsonify(dict(err=1, msg="仓库ID必须为整数", data=False))
        bWarehouseExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseId, "rps_warehouse")
        if not bWarehouseExists:
            return jsonify(dict(err=1, msg="仓库ID不存在", data=False))

    if remark != None:
        if not isinstance(remark, str):
            return jsonify(dict(err=1, msg="备注必须为字符串", data=False))

    if reasonOrig != None:
        if not isinstance(reasonOrig, str):
            return jsonify(dict(err=1, msg="报废原因必须为字符串", data=False))

    if warehouseIdOrig != None:
        if not isinstance(warehouseIdOrig, int):
            return jsonify(dict(err=1, msg="仓库ID必须为整数", data=False))
        bWarehouseExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", warehouseIdOrig, "rps_warehouse")
        if not bWarehouseExists:
            return jsonify(dict(err=1, msg="仓库ID不存在", data=False))

    if remarkOrig != None:
        if not isinstance(remarkOrig, str):
            return jsonify(dict(err=1, msg="备注必须为字符串", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(5, nId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:
        updateList = []
        if reason != None:
            updateList.append(("reason", reason))
        if warehouseId != None:
            updateList.append(("warehouse_id", warehouseId))
        if remark != None:
            updateList.append(("remark", remark))

        bSuc = BEOPDataAccess.getInstance().updateRpsRetirement(nId, updateList)
        if not bSuc:
            return jsonify(dict(err=1, msg="修改失败", data=False))
        return jsonify(dict(err=0, msg="修改成功", data=True))
    elif curStatus == 1:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 5  # 报废单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1

        dOriginal = {}
        dTarget = {}

        if reasonOrig != None:
            dOriginal.update({"reasonOrig": reasonOrig})
        if warehouseIdOrig != None:
            dOriginal.update({"warehouseIdOrig": warehouseIdOrig})
        if remarkOrig != None:
            dOriginal.update({"remarkOrig": remarkOrig})

        if reason != None:
            dTarget.update({"reason": reason})
        if warehouseId != None:
            dTarget.update({"warehouseId": warehouseId})
        if remark != None:
            dTarget.update({"remark": remark})

        sqlStatus = "UPDATE rps_retirement SET status=13 WHERE id=%s"
        paramStatus = [nId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, nId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType, json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlStatus, sqlAudit]
        paramList = [tuple(paramStatus), tuple(paramAudit)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态无法执行该操作", data=False))


@bp_rps.route("/addAttachmentToRetirement", methods=["POST"])
def add_attachment_to_retirement():
    userId = request.form.get("userId", None)
    retirementId = request.form.get("retirementId", None)
    deadline = request.form.get("deadline", None)

    fileList = []
    for i in range(0, 10):
        file = request.files.get("file{0:02d}".format(i))
        if file is None or not isinstance(file.content_type, str):
            continue
        fileList.append(file)

    if is_digit(retirementId):
        retirementId = int(float(retirementId))

    if is_digit(userId):
        userId = int(float(userId))

    if not isinstance(retirementId, int):
        return jsonify(dict(err=1, msg="报废单ID必须为整数", data=False))
    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", retirementId, "rps_retirement")
    if not bExists:
        return jsonify(dict(err=1, msg="报废单ID不存在", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if not len(fileList):
        return jsonify(dict(err=1, msg="未发现文件", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(5, retirementId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取报废单状态失败", data=False))

    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%d %H:%M:%S")

    filesDir = os.path.join(app.static_folder, "files")
    if not os.path.exists(filesDir):
        os.mkdir(filesDir)

    tempDir = os.path.join(filesDir, "temp")
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    maxFileId = BEOPDataAccess.getInstance().getMaxIdInTable("rps_attachment")
    if maxFileId == None:
        return jsonify(dict(err=1, msg="获取附件表最大ID失败", data=False))

    fileId = maxFileId + 1

    attachmentFileInfoList = []
    fileIdList = []
    fileNameList = []
    for file in fileList:
        strExt = os.path.splitext(file.filename)[1]

        fileName = "{fileId}_{originalName}".format(fileId=fileId, originalName=file.filename)
        fileNameList.append(fileName)

        tempFilePath = os.path.join(tempDir, fileName)

        file.stream.read()
        file.stream.seek(0)
        file.save(tempFilePath)

        bSuc = upload_to_oss(tempFilePath, fileName, OSS_CONFIG["folderName"])

        fileIdList.append(fileId)

        nType = -1
        ossPath = ""
        enabled = 1
        if bSuc:
            nType = ATTACHMENT_TYPE.get(strExt.lower(), -1)
            ossPath = "https://{bucketName}.{region}/{folderName}/{fileName}".format(
                bucketName=OSS_CONFIG["bucketName"],
                region=OSS_CONFIG["region"],
                folderName=OSS_CONFIG["folderName"],
                fileName=fileName)

        attachmentFileInfoList.append(
            (fileId, fileName, nType, ossPath, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), enabled)
        )
        time.sleep(0.2)
        fileId += 1

    bSuc = BEOPDataAccess.getInstance().addRpsAttachment(attachmentFileInfoList)
    if not bSuc:
        return jsonify(dict(err=1, msg="将文件信息存入附件表失败", data=False))

    if curStatus == 0:
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfRetirement(retirementId)
        if attachmentIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        attachmentIdList.extend(fileIdList)
        attachmentIdList = list(set(attachmentIdList))

        updateList = [("attachment_id", ",".join([str(attachmentId) for attachmentId in attachmentIdList]))]
        bSuc = BEOPDataAccess.getInstance().updateRpsRetirement(retirementId, updateList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))

    elif curStatus == 1:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 5  # 报废单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1  # 审核结果初始值-1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfRetirement(retirementId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        targetFileIdList.extend(fileIdList)
        targetFileIdList = list(set(targetFileIdList))
        dTarget.update({"fileIdList": targetFileIdList})

        sqlStatus = "UPDATE rps_retirement SET status=13 WHERE id=%s"
        paramStatus = [retirementId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, retirementId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId, nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlStatus, sqlAudit]
        paramList = [tuple(paramStatus), tuple(paramAudit)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)

        for fileName in fileNameList:
            path = os.path.join(tempDir, fileName)
            if os.path.exists(path):
                os.remove(path)

        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态不可执行该操作", data=False))


@bp_rps.route("/deleteAttachmentOfRetirement", methods=["POST"])
def delete_attachment_of_retirement():
    rcv = request.get_json()
    userId = rcv.get("userId", None)
    retirementId = rcv.get("retirementId", None)
    deadline = rcv.get("deadline", None)
    fileIdList = rcv.get("fileIdList", [])

    if not isinstance(retirementId, int):
        return jsonify(dict(err=1, msg="报废单ID必须为整数", data=False))
    if not len(fileIdList):
        return jsonify(dict(err=1, msg="未发现需删除的文件ID列表", data=False))

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userID必须为整数", data=False))

    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))

    if deadline != None:
        if not isinstance(deadline, str):
            return jsonify(dict(err=1, msg="审核截止日期必须为字符串", data=False))
        if not isValidDate(deadline, "%Y-%m-%d"):
            return jsonify(dict(err=1, msg="审核截止日期格式有误", data=False))
        deadline = deadline + " 00:00:00"

    if deadline == None:
        deadline = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", retirementId, "rps_retirement")
    if not bExists:
        return jsonify(dict(err=1, msg="报废单ID不存在", data=False))

    curStatus = BEOPDataAccess.getInstance().getRpsStatus(5, retirementId)
    if curStatus == None:
        return jsonify(dict(err=1, msg="获取当前状态失败", data=False))

    if curStatus not in [0, 1]:
        return jsonify(dict(err=1, msg="当前状态为{cur}，不可被修改".format(cur=curStatus), data=False))

    if curStatus == 0:  # 未提交到校核则直接删除
        attachmentIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfRetirement(retirementId)
        for fileId in fileIdList:
            if not is_digit(fileId):
                continue

            nFileId = int(float(fileId))
            if nFileId in attachmentIdList:
                attachmentIdList.remove(nFileId)

        dFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(fileIdList)
        if dFileInfo == None:
            return jsonify(dict(err=1, msg="获取附件名列表失败", data=False))

        attachmentFileNameList = []
        for value in dFileInfo.values():
            fName = value.get("fileName", "")
            if fName:
                attachmentFileNameList.append(fName)

        strAttachment = ",".join([str(nId) for nId in attachmentIdList])

        sqlContract = "UPDATE rps_retirement SET attachment_id=%s WHERE id=%s"
        paramContract = [strAttachment, retirementId]

        sqlAttach = "UPDATE rps_attachment SET enabled=0 WHERE id in (%s)"
        paramAttach = [(fileId,) for fileId in fileIdList]

        queryList = [sqlContract, sqlAttach]
        paramList = [tuple(paramContract), tuple(paramAttach)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))

        bSuc = delete_file_from_oss(attachmentFileNameList, OSS_CONFIG["folderName"])
        if not bSuc:
            return jsonify(dict(err=1, msg="从OSS删除文件失败", data=False))
        return jsonify(dict(err=0, msg="", data=True))

    elif curStatus == 1:
        nMaxIdAudit = BEOPDataAccess.getInstance().getMaxIdInTable("rps_audit")
        nIdAudit = nMaxIdAudit + 1
        nBillType = 5  # 报废单
        nAuditType = 2  # 修改审核
        nEnabled = 1
        nResult = -1
        dOriginal = {}
        dTarget = {}

        origAttachFileIdList = BEOPDataAccess.getInstance().getRpsAttachmentIdListOfRetirement(retirementId)
        if origAttachFileIdList == None:
            return jsonify(dict(err=1, msg="当前附件id列表获取失败", data=False))

        dOriginal.update({"fileIdList": origAttachFileIdList})

        targetFileIdList = origAttachFileIdList.copy()
        for fileId in fileIdList:
            if fileId in targetFileIdList:
                targetFileIdList.remove(fileId)

        dTarget.update({"fileIdList": targetFileIdList})

        sqlStatus = "UPDATE rps_retirement SET status=13 WHERE id=%s"
        paramStatus = [retirementId]

        sqlAudit = "INSERT INTO rps_audit (id, bill_id, type, create_time, creator_id, audit_type, original, target, deadline, enabled, result) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        paramAudit = [nIdAudit, retirementId, nBillType, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), userId,
                      nAuditType,
                      json.dumps(dOriginal), json.dumps(dTarget), deadline,
                      nEnabled, nResult]

        queryList = [sqlStatus, sqlAudit]
        paramList = [tuple(paramStatus), tuple(paramAudit)]

        bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
        if not bSuc:
            return jsonify(dict(err=1, msg="执行失败", data=False))
        return jsonify(dict(err=0, msg="执行成功", data=True))
    else:
        return jsonify(dict(err=1, msg="当前状态下无法执行该操作", data=False))


@bp_rps.route("/getRetirement", methods=["POST"])
def get_retirement():
    rcv = request.get_json()
    nId = rcv.get("id", None)

    if nId != None:
        if not isinstance(nId, int):
            return jsonify(dict(err=1, msg="报废单ID必须为整数", data=[]))

        bExists = BEOPDataAccess.getInstance().fieldExistsInTable("id", nId, "rps_retirement")
        if not bExists:
            return jsonify(dict(err=1, msg="报废单ID不存在", data=False))

    dataList = BEOPDataAccess.getInstance().getRpsRetirement(nId)
    if dataList == None:
        return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

    procFileIdList = []
    retirementIdList = []
    for data in dataList:
        attachment = data.get("attachment", {})
        if attachment:
            fileIdList = list(attachment.keys())
            procFileIdList.extend(fileIdList)
        retirementIdList.append(data.get("id"))

    dAttachmentFileInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(procFileIdList)
    if dAttachmentFileInfo == None:
        return jsonify(dict(err=1, msg="查询失败，请稍后再试", data=[]))

    dCheckAudit = BEOPDataAccess.getInstance().getRpsCheckAndAuditRecords(retirementIdList, 5)
    if dCheckAudit == None:
        return jsonify(dict(err=1, msg="校核、审核信息查询失败", data=[]))

    for data in dataList:
        for attachmentId in data.get("attachment", {}).keys():
            dFile = dAttachmentFileInfo.get(attachmentId, {})
            if dFile:
                data.get("attachment").get(attachmentId).update(dFile)

        dAttachment = data.get("attachment", {})
        lAttachment = []
        for attachId, dAttachInfo in dAttachment.items():
            lAttachment.append(dAttachInfo)

        data.update({"attachment": lAttachment})

        data.update(dict(check=dCheckAudit.get(data["id"], {}).get("check", {})))
        data.update(dict(createAudit=dCheckAudit.get(data["id"], {}).get("createAudit", {})))
        data.update(dict(editAudit=dCheckAudit.get(data["id"], {}).get("editAudit", {})))
        data.update(dict(terminateAudit=dCheckAudit.get(data["id"], {}).get("terminateAudit", {})))
        data.update(dict(finishAudit=dCheckAudit.get(data["id"], {}).get("finishAudit", {})))

    return jsonify(dict(err=0, msg="查询成功", data=dataList))


@bp_rps.route("/recallEditAudit", methods=["POST"])
def recall_edit_audit():
    rcv = request.get_json()
    nId = rcv.get("id", None)  # 审核单ID

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="审核单ID必须为整数", data=False))

    dBillInfo = BEOPDataAccess.getInstance().getRpsAuditInfoByAuditId([nId], nBillType=None, nAuditType=2, nResult=-1)
    if dBillInfo == None:
        return jsonify(dict(err=1, msg="获取单据信息失败", data=False))

    if not dBillInfo.get(nId, {}):
        return jsonify(dict(err=1, msg="该审核单信息不存在", data=False))

    dInfo = dBillInfo.get(nId)
    nResult = dInfo.get("result")
    nBillId = dInfo.get("billId")
    nBillType = dInfo.get("billType")

    if nResult in [0, 1]:
        return jsonify(dict(err=1, msg="该审核单已被执行审核，无法撤回", data=False))

    strTableName = ""
    if nBillType == 1:
        strTableName = "rps_contract"
    elif nBillType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
    elif nBillType == 4:
        strTableName = "rps_transport"
    elif nBillType == 5:
        strTableName = "rps_retirement"

    strStatus = "UPDATE {tableName} SET status=1 WHERE id=%s".format(tableName=strTableName)
    paramStatus = [nBillId]

    strAudit = "UPDATE rps_audit SET enabled=0 WHERE id=%s"
    paramAudit = [nId]

    # 只有当所有审核项都通过后才改变状态
    toAuditList = BEOPDataAccess.getInstance().getRpsAuditRecord(nBillId, nBillType, -1)
    if toAuditList == None:
        return jsonify(dict(err=1, msg="获取待审核项列表失败", data=False))
    bChangeStatus = True
    for obj in toAuditList:
        if obj.get("nAuditId") != nId:
            bChangeStatus = False
            break

    queryList = [strAudit]
    paramList = [tuple(paramAudit)]

    if bChangeStatus:
        queryList.append(strStatus)
        paramList.append(tuple(paramStatus))

    bSuc = BEOPDataAccess.getInstance().updateRpsMultiTrans(queryList, paramList)
    if not bSuc:
        return jsonify(dict(err=1, msg="执行失败", data=False))
    return jsonify(dict(err=0, msg="执行成功", data=True))


# 获取某个单所有附件的当前状态及信息（包括已有、待审核删除、待审核增加的附件）
@bp_rps.route("/getRpsAttachmentAuditRecord", methods=["POST"])
def get_rps_attachment_audit_record():
    rcv = request.get_json()
    nId = rcv.get("id", None)   # 单据ID
    nType = rcv.get("type", None)  # 类型  1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单

    if not isinstance(nId, int):
        return jsonify(dict(err=1, msg="单据ID必须为整数", data=[]))
    if nType not in BILL_TYPE_LIST:
        return jsonify(dict(err=1, msg="单据类型有误", data=[]))

    strTableName = ""
    strField = ""
    if nType == 1:
        strTableName = "rps_contract"
        strField = "attachment_id"
    elif nType in [2, 3]:
        strTableName = "rps_in_out_warehouse"
        strField = "attachment_id"
    elif nType == 4:
        strTableName = "rps_transport"
        strField = "receive_delivery_img, sign_img"
    elif nType == 5:
        strTableName = "rps_retirement"
        strField = "attachment_id"

    attachmentFileIdList = []
    curIdList = BEOPDataAccess.getInstance().getRpsCurrentAttachmentIdList(nId, strField, strTableName)
    if curIdList == None:
        return jsonify(dict(err=1, msg="获取单据当前附件ID列表失败", data=[]))

    attachmentFileIdList.extend(curIdList)

    pendingAuditRecord = BEOPDataAccess.getInstance().getRpsAuditRecord(nId, nType, -1)
    if pendingAuditRecord == None:
        return jsonify(dict(err=1, msg="获取单据未审核项失败", data=[]))

    dFileDispose = {}
    for record in pendingAuditRecord:
        if record.get("auditType") != 2:
            continue

        if not (record.get("original", {}) and record.get("target", {})):
            continue

        strKey = ""
        for key in record.get("original").keys():
            if key in ["fileIdList", "receiveDeliveryImgFileIdList", "signImgFileIdList"]:
                strKey = key
                break

        if not strKey:
            continue

        originalList = record.get("original").get(strKey)
        targetList = record.get("target").get(strKey)

        for originalId in originalList:
            if originalId not in targetList:
                if originalId not in dFileDispose.keys():
                    dFileDispose.update({originalId: []})

                if False not in dFileDispose[originalId]:
                    dFileDispose[originalId].append(False)

        for targetId in targetList:
            if targetId not in originalList:
                if targetId not in dFileDispose.keys():
                    dFileDispose.update({targetId: []})
                if True not in dFileDispose[targetId]:
                    dFileDispose[targetId].append(True)

        attachmentFileIdList.extend(originalList)
        attachmentFileIdList.extend(targetList)

    attachmentFileIdList = list(set(attachmentFileIdList))
    dAttachmentInfo = BEOPDataAccess.getInstance().getRpsAttatchmentInfo(attachmentFileIdList)
    if dAttachmentInfo == None:
        return jsonify(dict(err=1, msg="获取附件信息失败", data=False))

    dSummary = {}
    for nFileId in curIdList:
        dTar = dAttachmentInfo.get(nFileId, None)
        if dTar == None:
            continue

        nStatus = 1    # 1-正常；-1-删除待审核；2-增加待审核；3-增加待审核和删除待审核同时存在
        if nFileId in dFileDispose.keys():
            if True in dFileDispose.get(nFileId) and False in dFileDispose.get(nFileId):
                nStatus = 3
            elif True in dFileDispose.get(nFileId):
                nStatus = 2
            elif False in dFileDispose.get(nFileId):
                nStatus = -1

        dTar.update(dict(status=nStatus))
        dSummary.update({nFileId: dTar})

    for nFileId, disposeList in dFileDispose.items():
        if nFileId in dSummary.keys():
            continue

        dTar = dAttachmentInfo.get(nFileId, None)
        if dTar == None:
            continue

        nStatus = None
        if True in dFileDispose.get(nFileId) and False in dFileDispose.get(nFileId):
            nStatus = 3
        elif True in dFileDispose.get(nFileId):
            nStatus = 2
        elif False in dFileDispose.get(nFileId):
            nStatus = -1

        if nStatus == None:
            continue

        dTar.update(dict(status=nStatus))
        dSummary.update({nFileId: dTar})

    dataList = []
    for nFileId, dTar in dSummary.items():
        dataList.append(dTar)

    return jsonify(dict(err=0, msg="", data=dataList))

# 查询一个用户当前是否有需要推送的消息
@bp_rps.route("/getNoticeListOfUser", methods=["POST"])
def get_rps_all_audit_record():
    rcv = request.get_json()
    userId = rcv.get("userId", None)

    if not isinstance(userId, int):
        return jsonify(dict(err=1, msg="userId必须为整数", data=False))
    dUserInfo = BEOPDataAccess.getInstance().get_user_info(userId)
    if not dUserInfo:
        return jsonify(dict(err=1, msg="userId不存在", data=False))
    # nRole = int(float(dUserInfo.get('userofrole')))
    # if nRole not in [11, 12]:
    #     return jsonify(dict(err=1, msg="该用户非运营角色", data=False))

    nRole = int(float(dUserInfo.get('userofrole')))
    noticeContractReturnList = []
    noticeInOutWarehouseReturnList = []
    noticeRetirementReturnList = []
    if dUserInfo:
        if nRole in [11,12]:#管理或运营人员
            dataList = BEOPDataAccess.getInstance().getAllRpsAuditRecord(None, None,None,None,None)
            for item in dataList:
                if dataList == None:
                    return jsonify(dict(err=1, msg="获取订单审校记录失败", data=False))

                nResult = item.get('result')
                nCreatorid = int(item.get('creatorId'))
                nAuditType = item.get('auditType')
                if nResult == -1 and nCreatorid != userId:  # 获取订单待审核项
                    if nAuditType == 0 and nRole == 12:  # 此人是运营，且此单是校核单且该单尚未校核,11-审校人，12-校核人
                        # auditType审核类型:0-创建校核，1-创建审核，2-修改审核，3-终止审核，4-完成审核
                        if item.get('type') == 1:  # 销售订单
                            noticeContractReturnList.append(item)
                        if item.get('type') == 2:  # 出入库单
                            noticeInOutWarehouseReturnList.append(item)
                        if item.get('type') == 5:  # 报废单
                            noticeRetirementReturnList.append(item)
                    if nAuditType in [1, 2, 3, 4] and nRole == 11:  # 此人是审核人，且此单是审核单且该单尚未审核,11审核人，12校核人
                        if item.get('type') == 1:  # 销售订单
                            noticeContractReturnList.append(item)
                        if item.get('type') == 2:  # 出入库单
                            noticeInOutWarehouseReturnList.append(item)
                        if item.get('type') == 5:  # 报废单
                            noticeRetirementReturnList.append(item)
                # if nResult in [0, 1] and nCreatorid == userId and nRole == 12 and item.get('recved') == 0:
                #     # 此人是运营，创建的审核单未通过或通过，且消息未读
                #     if item.get('type') == 1:  # 销售订单
                #         noticeContractReturnList.append(item)
                #     if item.get('type') == 2:  # 出入库单
                #         noticeInOutWarehouseReturnList.append(item)
                #     if item.get('type') == 5:  # 报废单
                #         noticeRetirementReturnList.append(item)

        elif nRole not in [11, 12]:#非管理或运营人员
            dataListforUSer_contract = BEOPDataAccess.getInstance().getContractByCreatorID(userId, None)
            dataListforUSer_inoutwarehouse = BEOPDataAccess.getInstance().getInoutwarehouseByCreatorID(userId, None)

            for item in dataListforUSer_contract:  # 从rps_contract将订单id和rps_audit里的bill_id绑定
                nContractID = item.get('contractID')
                dataList = BEOPDataAccess.getInstance().getAllRpsAuditRecord(1, None, None, nContractID,
                                                                             None)#获取所有的销售订单

                if not isinstance(dataList, list):
                    continue

                for item in dataList:
                    nResult = item.get('result')
                    nCreatorid = int(item.get('creatorId'))
                    nAuditType = item.get('auditType')
                    if nResult in [0,1] and nCreatorid == userId and item.get('recved') == 0:
                        # 获取订单已审核项，审核单的creatorid=创建人id；校核通过后，再有修改审核、终止审核的动作是直接给审核人的，不经过校核
                        # 校核不通过时，creator_id=创建人id，通过或不通过都可以直接通知给创建人
                        if item.get('type') == 1:  # 销售订单
                            noticeContractReturnList.append(item)
                    if nResult in [0,1] and nCreatorid != userId and nAuditType==1 and item.get('recved') == 0:
                        #校核人提交的审核单，creator_id=校核人id，而不是创建人，所以这里是当校核人提交的审核单通过时，给创建者的通知
                        if item.get('type') == 1:  # 销售订单
                            noticeContractReturnList.append(item)

            for item in dataListforUSer_inoutwarehouse:  # 从rps_in_out_warehouse将订单id和rps_audit里的bill_id绑定
                nInoutwarehouseID = item.get('inoutwarehouseID')
                dataList = BEOPDataAccess.getInstance().getAllRpsAuditRecord(2, None, None, None,
                                                                             nInoutwarehouseID)  # 获取所有的出入库订单

                if not isinstance(dataList, list):
                    continue

                for item in dataList:
                    nResult = item.get('result')
                    nCreatorid = int(item.get('creatorId'))
                    nAuditType = item.get('auditType')
                    if nResult in [0,1] and nCreatorid == userId and item.get('recved') == 0:
                        # 获取订单已审核项，审核单的creatorid=创建人id；校核通过后，再有修改审核、终止审核的动作是直接给审核人的，不经过校核
                        #校核不通过时，creator_id=创建人id，通过或不通过都可以直接通知给创建人
                        if item.get('type') == 2:  # 出入库单
                            noticeInOutWarehouseReturnList.append(item)
                    if nResult in [0,1] and nCreatorid != userId and nAuditType==1 and item.get('recved') == 0:
                        #校核人提交的审核单，creator_id=校核人id，而不是创建人，所以这里是当校核人提交的审核单通过时，给创建者的通知
                        if item.get('type') == 2:  # 出入库单
                            noticeInOutWarehouseReturnList.append(item)
            #报废单暂无
    return jsonify(dict(err=0, msg="", data=dict(noticeContractReturnList=noticeContractReturnList,
                                                 noticeInOutWarehouseReturnList=noticeInOutWarehouseReturnList,
                                                 noticeRetirementReturnList=noticeRetirementReturnList)))



@bp_rps.route("/setAuditRecordRecved", methods=["POST"])
def set_audit_record_recved():
    rcv = request.get_json()
    AuditIdList = rcv.get("AuditIdList", None)  # 给审核单ID列表

    if not isinstance(AuditIdList, list):
        return jsonify(dict(err=1, msg='body ContractList参数必须是一个列表'))
    for auditId in AuditIdList:

        bSuc = BEOPDataAccess.getInstance().updateRpsAuditRecved(int(auditId))

    if not bSuc:
        return jsonify(dict(err=1, msg="该用户未读", data=False))
    return jsonify(dict(err=0, msg="该用户已读", data=True))


