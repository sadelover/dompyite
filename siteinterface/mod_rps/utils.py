
import oss2
import os
import logging

# 对于单个资产的标签序号上限
RFID_MAX_LABEL_INDEX_OF_ONE_ASSET = 9

# 资产编码字符串长度
ASSET_CODE_LENGTH = 12

# RFID码的字符串长度
RFID_CODE_LENGTH = 16

# 单据类型: 1-销售订单;2-入库单;3-出库单;4-物流单;5-报废单
BILL_TYPE_LIST = [1, 2, 3, 4, 5]

# 进出库类型:0-新箱入库单;1-循环箱入库单;2-循环箱出库单
IN_OUT_TYPE_LIST = [0, 1, 2]

# 报废后的处置方式:0-回收;1-就地废品处理;2-其它
DISPOSAL_LIST = [0, 1, 2]

# 固定资产模板ID列表（RFID设备）
FIXED_ASSET_TEMPLATE_ID_LIST = [12, 13]

# 附件类型映射
ATTACHMENT_TYPE = {
    ".pdf": 0,
    ".docx": 1,
    ".bmp": 2,
    ".jpeg": 2,
    ".png": 2,
    ".jpg": 2,
    ".gif": 2
}

# OSS配置
OSS_CONFIG = {
    "AccessKeyId": "LTAIHx3M29s7FSwf",
    "AccessKeySecret": "7isuhrgdsQPcxHgCPB7L5N0ETj5AEv",
    "region": "oss-cn-shanghai.aliyuncs.com",
    "bucketName": "dom-soft-release",
    "folderName": "rps-attachment"
}

# 数据库表字段中文映射
FIELD_NAME_MAP = {
    "clientId": "客户ID",
    "salesId": "销售ID",
    "clientContact": "客户联系信息",
    "deliveryTime": "建议发货日期",
    "dueTime": "截止到货日期",
    "amount": "合同金额",
    "warehouseId": "仓库ID",
    "transportId": "物流ID",
    "additional": "附加信息",
    "contractId": "订单ID",
    "departWarehouseId": "出发仓库ID",
    "destWarehouseId": "到达仓库ID",
    "estimatedArriveDate": "预计到达日期",
    "reason": "报废原因",
    "remark": "备注",
    "clientIdOrig": "客户ID",
    "salesIdOrig": "销售ID",
    "clientContactOrig": "客户联系信息",
    "deliveryTimeOrig": "建议发货日期",
    "dueTimeOrig": "截止到货日期",
    "amountOrig": "合同金额",
    "warehouseIdOrig": "仓库ID",
    "transportIdOrig": "物流ID",
    "additionalOrig": "附加信息",
    "contractIdOrig": "订单ID",
    "departWarehouseIdOrig": "出发仓库ID",
    "destWarehouseIdOrig": "到达仓库ID",
    "estimatedArriveDateOrig": "预计到达日期",
    "reasonOrig": "报废原因",
    "remarkOrig": "备注"
}

def is_digit(tar):
    try:
        n = float(tar)
        return True
    except:
        return False

def get_lon_and_lat(strLocation):
    if strLocation.find(",") == -1:
        return {}, "经纬度格式有误"
    if strLocation.count(",") != 1:
        return {}, "经纬度格式有误"

    lon = strLocation.split(",")[0]
    lat = strLocation.split(",")[1]
    if not is_digit(lon):
        return {}, "经度必须为数字"
    if not is_digit(lat):
        return {}, "维度必须为数字"

    return dict(lon=lon, lat=lat), ""

def process_asset_code(tar):
    res = tar
    try:
        if is_digit(tar):
            res = str(int(float(tar)))
        else:
            res = str(tar)
    except:
        pass
    return res

"""
strFilePath: 待上传文件的绝对路径
strFileName: 待上传文件的文件名
subFolderName: oss上空间中的二级文件夹名
"""
def upload_to_oss(strFilePath, strFileName, subFolderName):
    res = False
    try:
        AccessKeyId = OSS_CONFIG.get("AccessKeyId")
        AccessKeySecret = OSS_CONFIG.get("AccessKeySecret")
        region = OSS_CONFIG.get("region")
        bucketName = OSS_CONFIG.get("bucketName")

        auth = oss2.Auth(AccessKeyId, AccessKeySecret)
        bucket = oss2.Bucket(auth, region, bucketName)

        ossPath = "{0}/{1}".format(subFolderName, strFileName)

        if strFilePath:
            with open(strFilePath, "rb") as fileobj:
                fileobj.seek(0, os.SEEK_SET)
                bucket.put_object(ossPath, fileobj)
                res = True
        else:
            print("文件不存在")
    except Exception as e:
        print("上传至OSS失败: %s" % e.__str__())
    finally:
        return res

def delete_file_from_oss(strFileNameOrList, subFolderName):
    try:
        fileNameList = strFileNameOrList
        if not isinstance(strFileNameOrList, list):
            fileNameList = [strFileNameOrList]

        AccessKeyId = OSS_CONFIG.get("AccessKeyId")
        AccessKeySecret = OSS_CONFIG.get("AccessKeySecret")
        region = OSS_CONFIG.get("region")
        bucketName = OSS_CONFIG.get("bucketName")

        auth = oss2.Auth(AccessKeyId, AccessKeySecret)
        bucket = oss2.Bucket(auth, region, bucketName)

        for fileName in fileNameList:
            ossPath = "{0}/{1}".format(subFolderName, fileName)
            bucket.delete_object(ossPath)

        return True
    except Exception as e:
        logging.error("从OSS删除文件失败: %s" % e.__str__())
        return False

"""生成资产属性与索引字典
{4: "生产商", 5:"生产日期", 6: "成本"}
"""
def process_equip_import_table_header(values):
    dRes = {}
    for idx, value in enumerate(values):
        if not value.startswith("资产信息"):
            continue

        if value.find(">") == -1:
            continue

        if len(value.split(">")) != 2:
            continue

        param = value.split(">")[1]
        dRes.update({idx: param})
    return dRes








