from configobj import ConfigObj
import os, shutil


equip_category = [{
    "systemCategory": "chwSystem",
    "equipList": ["Ch", "PrichWP", "SecChWP", "CWP", "CT"]
},
{
    "systemCategory": "hwSystem",
    "equipList": ["PriHWP", "SecHWP"]
}]

def remove_key_value_pair_from_dict(dictObj, key):
    res = True
    try:
        value = dictObj.pop(key)
    except:
        res = False
    return res

def add_proj_to_config_ini(projId, projname):
    res = False
    try:
        cf = ConfigObj("config.ini", encoding="UTF8")
        key = "projectdb%03d" % projId
        dbFileName = "domdb%03d.4db" % projId
        cf[key] = dict(dbFileName=dbFileName, dbprojectName=projname)
        cf.write()
        res = True
    except:
        pass
    return res

def remove_proj_from_config_ini(projNo):
    res = False
    try:
        cf = ConfigObj("config.ini", encoding="UTF8")
        projKey = "projectdb%03d" % projNo
        bRemove = remove_key_value_pair_from_dict(cf, projKey)
        if bRemove:
            cf.write()
            res = True
    except:
        pass
    return res

def create_domdb_file_for_new_proj(projId, str4dbSrc, strCorePath):
    res = False
    try:
        str4dbDst = os.path.join(strCorePath, "domdb%03d.4db" % projId)
        shutil.copy(str4dbSrc, str4dbDst)
        res = True
    except:
        pass
    return res

def remove_domdb_file(projId, strCorePath):
    res = False
    try:
        strDomdbFile = os.path.join(strCorePath, "domdb%03d.4db" % projId)
        os.remove(strDomdbFile)
        res = True
    except:
        pass
    return res

def merge_dir_from_list(listDir):
    res = ""
    try:
        if isinstance(listDir, list):
            for item in listDir:
                res = os.path.join(res, item)
    except:
        pass
    return res

def match_catetory(strTar, listCate):
    res = None
    try:
        for cate in listCate:
            if strTar.find(cate) == 0:
                res = cate
                break
    except:
        pass
    return res

def is_integer(obj):
    res = False
    try:
        if isinstance(int(obj), int):
            res = True
    except:
        pass
    return res

