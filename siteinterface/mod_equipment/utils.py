import re
from siteinterface import app
import os
import logging
from datetime import datetime


equipCategoryList = [{
        "prefix": "Ch",
        "key": "ChGroupList",
        "name_zh": "冷机"
    }, {
        "prefix": "PriChWP",
        "key": "PriChWPGroupList",
        "name_zh": "一次冷冻泵"
    }, {
        "prefix": "SecChWP",
        "key": "SecChWPGroupList",
        "name_zh": "二次冷冻泵"
    }, {
        "prefix": "CWP",
        "key": "CWPGroupList",
        "name_zh": "冷却泵"
    }, {
        "prefix": "CT",
        "key": "CTGroupList",
        "name_zh": "冷却塔"
    }, {
        "prefix": "GlycolPump",
        "key": "GlycolPumpGroupList",
        "name_zh": "乙二醇泵"
    }]

"""
Plant01Ch01
"""

def get_equipment_template_type(identity):
    dPat = {r"Ch[0-9]{2}": "冷机", r"PriChWP[0-9]{2}": "水泵", r"CWP[0-9]{2}": "水泵", r"SecChWP[0-9]{2}": "水泵",
               r"CT[0-9]{2}":"冷却塔", r"CTFan[0-9]{2}":"冷却塔风机", r"AHU[0-9]{2}":"空调箱", r"AirCompressor[0-9]{2}":"空压机", r"Dryer[0-9]{2}":"干燥机"}

    matchList = []

    for pat, strType in dPat.items():
        matchList.clear()
        matchList = re.findall(pat, identity)
        if len(matchList):
            return strType, ""
    return None, ",".join(list(set(dPat.values())))


def fetchImportAssetTmplTable(excelTable, fileName):
    try:
        staticFolder = app.static_folder
        tempFolder = os.path.join(staticFolder, "files")
        if not os.path.exists(tempFolder):
            os.mkdir(tempFolder)

        tempFolder = os.path.join(tempFolder, "temp")
        if not os.path.exists(tempFolder):
            os.mkdir(tempFolder)


        saveFilePath = os.path.join(tempFolder, "{name}_{time}.xlsx".format(name=os.path.splitext(fileName)[0], time=datetime.now().strftime("%Y-%m-%d-%H-%M-%S")))
        if os.path.exists(saveFilePath):
            os.remove(saveFilePath)
        excelTable.save(saveFilePath)

        return saveFilePath

    except Exception as e:
        strLog = "ERROR in fetchInfoTable: %s" % e.__str__()
        print(strLog)
        logging.error(strLog)
        return None

def is_digit(tar):
    try:
        n = float(tar)
        return True
    except:
        return False
