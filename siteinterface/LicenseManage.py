# coding:utf8
# register.py
# 功能说明：用户运行程序后，自动检测认证状态，如果未经认证，就需要注册。注册过程是用户将程序运行后显示的机器码（卷序号）发回给管理员，管理员通过加密后生成加密文件或字符串给回用户。
# 每次登录，在有注册文件或者注册码的情况下，软件就会通过DES和base64解码，如果解码后和重新获取的机器码一致，则通过认证，进入主程序。

import base64
import win32api
import configparser
import wmi
import os
import time
import pythoncom
from pyDes import *
import logging
import traceback
from datetime import  datetime

from configobj import ConfigObj
import hashlib
from siteinterface.BEOPDataAccess import BEOPDataAccess

global_wmi = wmi.WMI()
g_VolumeSerialNumberList = []
DEFAULT_SERIAL = 'MY97ioaE0n8L'
for physical_disk in global_wmi.Win32_DiskDrive():
    # 硬盘序列号
    if physical_disk.SerialNumber:
        strNUM = physical_disk.SerialNumber.strip()
        if strNUM:#maybe will be empty
            #if len(strNUM)<=7:
             #   strNUMLong= strNUM + DEFAULT_SERIAL
            g_VolumeSerialNumberList.append(strNUM)
            #g_VolumeSerialNumberList.append(strNUM)

if len(g_VolumeSerialNumberList)==0:
    g_VolumeSerialNumberList.append(DEFAULT_SERIAL)

# from binascii import a2b_hex    #如果需要用二进制编码保存注册码和注册文件可以使用binascii转换

class LicenseManage:
    def __init__(self, _nKeyVersion):
        self._nLicVer  = _nKeyVersion
        if _nKeyVersion==0:
            self.Des_Key = "BHC#@*UM"  # Key
            self.Des_IV = b"\x22\x33\x35\x81\xBC\x38\x5A\xE7"  # 自定IV向量
        elif _nKeyVersion==1:
            self.Des_Key = "AHC#@*UN"  # Key
            self.Des_IV = b"\x29\xF3\x37\x83\xBD\x3A\x53\xEE"  # 自定IV向量
        else:
            self.Des_Key = "BHC#@*UM"  # Key
            self.Des_IV = b"\x22\x33\x35\x81\xBC\x38\x5A\xE7"  # 自定IV向量

    # 获取C盘卷序列号
    # 使用C盘卷序列号的优点是长度短，方便操作，比如1513085707，但是对C盘进行格式化或重装电脑等操作会影响C盘卷序列号。
    # win32api.GetVolumeInformation(Volume Name, Volume Serial Number, Maximum Component Length of a file name, Sys Flags, File System Name)
    # return('', 1513085707, 255, 65470719, 'NTFS'),volume serial number is  1513085707.
    def getCVolumeSerialNumber(self):
        CVolumeSerialNumber = win32api.GetVolumeInformation("C:\\")[1]
        # print chardet.detect(str(CVolumeSerialNumber))
        # print CVolumeSerialNumber
        if CVolumeSerialNumber:
            return str(
                CVolumeSerialNumber)  # number is long type，has to be changed to str for comparing to content after.
        else:
            return 0

    def getMD5OfSerialNumber(self, volnumber):
        try:
            strVolNumberMD5 = hashlib.md5(volnumber.encode(encoding='UTF-8')).hexdigest()[8:24]
            strVolNumberMD5 = strVolNumberMD5[0:4] + '-' + strVolNumberMD5[4:8] + '-' + strVolNumberMD5[8:12] + '-' + strVolNumberMD5[12:16]
        except:
            strVolNumberMD5 = volnumber

        return strVolNumberMD5

    # 获取硬盘序列号
    def getVolumeSerialNumberList(self):
        global g_VolumeSerialNumberList
        return g_VolumeSerialNumberList

    # 使用DES加base64的形式加密
    # 考虑过使用M2Crypto和rsa，但是都因为在windows环境中糟糕的安装配置过程而放弃
    def DesEncrypt(self, str):
        k = des(self.Des_Key.encode('UTF-8'), CBC, self.Des_IV, pad=None, padmode=PAD_PKCS5)
        EncryptStr = k.encrypt(str)
        # EncryptStr = binascii.unhexlify(k.encrypt(str))
        return base64.b64encode(EncryptStr)  # 转base64编码返回

    # des解码
    def DesDecrypt(self, str):
        k = des(self.Des_Key.encode('UTF-8'), CBC, self.Des_IV, pad=None, padmode=PAD_PKCS5)
        DecryptStr = k.decrypt(str)
        # DecryptStr = a2b_hex(k.decrypt(str))
        return DecryptStr

    # 获取注册码，验证成功后生成注册文件
    def regist(self, key=''):
        #key = raw_input('please input your register code: ')
        # 由于输入类似“12”这种不符合base64规则的字符串会引起异常，所以需要增加输入判断
        # while key
        if key:
            contentList = self.getVolumeSerialNumberList()
            contentMD5List =  [self.getMD5OfSerialNumber(item) for item in contentList]
            contentList = contentList.copy()
            contentList.extend(contentMD5List)
            try:
                key_decrypted = self.DesDecrypt(base64.b64decode(key)).decode()
            except Exception as e2:
                strError = 'ERROR in LicenseManage.regist:' + e2.__str__()
                print(strError)
                logging.error(strError)
                return False

            if contentList and key_decrypted != 0:

                bFindOneSuit = False
                for content in contentList:
                    if key_decrypted.find(content) == 0:
                        bFindOneSuit  = True
                        break

                if not bFindOneSuit:
                    logging.error("regist failed: key:%s register code: %s;%s"%(str(key), str(key_decrypted), str(contentList)))
                    return False
                else:
                    print( "register succeed.")
                    # 读写文件要加判断

                    cf = ConfigObj('config.ini', encoding='UTF8')
                    if cf.get('license') is None:
                        cf['license'] = dict(key=key)
                    elif cf.get('license').get('key') is None:
                        cf['license']['key'] = key
                    else:
                        cf['license']['key'] = key

                    cf.write()
                    BEOPDataAccess.getInstance().saveLicenseVersion(self._nLicVer)
                    return True
            else:
                logging.error("regist: error in: %s;%s" % (str(key_decrypted), str(contentList)))
                return False
        logging.error("regist error: key is null")
        return False

    def checkLicenseAndKey(self, serialList, mykey):
        if isinstance(serialList, list) and len(serialList)==0:
            return 0,60 #可以通过

        contentMD5List = [self.getMD5OfSerialNumber(item) for item in serialList]
        serialList = serialList.copy()
        serialList.extend(contentMD5List)

        checkAuthoredResult = 1
        leftdays = 0
        current_struct_time =time.gmtime()
        current_str_time = '%d%02d%02d' % (current_struct_time.tm_year, current_struct_time.tm_mon, current_struct_time.tm_mday)
        # 读写文件要加判断

        try:
            #config = configparser.ConfigParser()
            #config.read('config.ini')
            cf = ConfigObj('config.ini', encoding='UTF8')
            key = mykey
            if key:
                missing_padding = 4 - len(key) % 4
                if missing_padding:
                    key += '=' * missing_padding

                key_decrypted = self.DesDecrypt(base64.b64decode(key)).decode()

                bFindOneSuit = False
                for content in serialList:
                    if key_decrypted.find(content) == 0:
                        bFindOneSuit = True
                        break

                if not bFindOneSuit:
                    return 0,0

                hdSerial = key_decrypted[0:len(content)]
                expireDate = key_decrypted[len(content):len(content)+8]
                expireDate_stamp = time.mktime(time.strptime(expireDate, "%Y%m%d"))
                leftdays = int((expireDate_stamp-time.time())/3600/24)+1
                leftdays = 0 if leftdays < 0 else leftdays
                if hdSerial == content and int(expireDate) >= int(current_str_time):
                    checkAuthoredResult = 0
        except Exception as e:
            logging.error('ERROR in LicenseManage::checkAuthored failed :'+ e.__str__())
            checkAuthoredResult = 1
            leftdays=0


        return checkAuthoredResult, leftdays

    '''
    额外限制配置中计算出的剩余天数
    '''
    def getLeftdaysFromLimit(self):
        nLeftDays = 365*100
        try:
            cf = ConfigObj('config.ini', encoding='UTF8')

            if cf.get('license') is not None:
                key = cf.get('license').get('limit')
                if key:
                    try:
                        tDate = datetime.strptime(key, "%Y-%m-%d")
                        nLeftDays = int((tDate-datetime.now()).total_seconds() / 60.0/60.0/24.0)
                    except Exception as eee:
                        pass
        except:
            pass
        return nLeftDays

    '''
    checkAuthoredResult: 1表示过期，0表示未过期
    leftdays: 表示剩余可用天数
    
    '''
    def checkAuthored(self):
        return 0,30000 #开放永久授权
        contentList = self.getVolumeSerialNumberList()
        if isinstance(contentList, list) and len(contentList)==0:
            return 0,60 #可以通过

        contentMD5List = [self.getMD5OfSerialNumber(item) for item in contentList]
        contentList = contentList.copy()
        contentList.extend(contentMD5List)

        checkAuthoredResult = 1
        leftdays = 0
        current_struct_time =time.gmtime()
        current_str_time = '%d%02d%02d' % (current_struct_time.tm_year, current_struct_time.tm_mon, current_struct_time.tm_mday)
        # 读写文件要加判断

        try:
            #config = configparser.ConfigParser()
            #config.read('config.ini')
            cf = ConfigObj('config.ini', encoding='UTF8')

            key = 'unlicensed'
            if cf.get('license') is None:
                cf['license'] = dict(key= key)
                cf.write()
            else:
                key = cf.get('license').get('key')

            if key is None:
                key = 'unlicensed'

            if key:
                missing_padding = 4 - len(key) % 4
                if missing_padding:
                    key += '=' * missing_padding

                key_decrypted = self.DesDecrypt(base64.b64decode(key)).decode()

                bFindOneSuit = False
                for content in contentList:
                    if key_decrypted.find(content) == 0:
                        bFindOneSuit = True
                        break

                if not bFindOneSuit:
                    return 0,0

                hdSerial = key_decrypted[0:len(content)]
                expireDate = key_decrypted[len(content):len(content)+8]
                expireDate_stamp = time.mktime(time.strptime(expireDate, "%Y%m%d"))
                leftdays = int((expireDate_stamp-time.time())/3600/24)+1
                leftdays = 0 if leftdays < 0 else leftdays
                if hdSerial == content and int(expireDate) >= int(current_str_time):
                    checkAuthoredResult = 0

                nExtraLimitLeftdays = self.getLeftdaysFromLimit()
                if checkAuthoredResult==0 and nExtraLimitLeftdays<=0:
                    checkAuthoredResult = 1
                    leftdays = 0
                elif checkAuthoredResult==0 and nExtraLimitLeftdays< leftdays:
                    leftdays = nExtraLimitLeftdays
        except Exception as e:
            logging.error('ERROR in LicenseManage::checkAuthored failed: %s'%(e.__str__()))
            traceback.print_exc()
            checkAuthoredResult = 1
            leftdays=0


        return checkAuthoredResult, leftdays
