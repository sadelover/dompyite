
import struct
import re

def genModbusByteList(rsp):
    strHexList = []
    try:
        if rsp and hasattr(rsp, 'registers'):
            for xx in rsp.registers:
                oneStr = str(hex(xx)[2:])
                oneStr = oneStr.zfill(4)
                strHexList.append(oneStr[0:2])
                strHexList.append(oneStr[2:4])
    except:
        pass
    return strHexList

def genModbusBitList(rsp):
    if not rsp:
        return []
    if not hasattr(rsp, "bits"):
        return []

    dataList = []
    for item in rsp.bits:
        nData = 1 if item == True else 0
        dataList.append(nData)

    return dataList

def getModbusExceptionCodeDesc(nCode):
    dEnum = {
        1: "IllegalFunction",
        2: "IllegalAddress",
        3: "IllegalValue",
        4: "SlaveFailure",
        5: "Acknowledge",
        6: "SlaveBusy",
        8: "MemoryParityError",
        10: "GatewayPathUnavailable",
        11: "GatewayNoResponse"
    }
    return dEnum.get(nCode, "未知")

"""
10进制转二进制，返回长度为nCharCount的二进制字符串
"""
def dec_to_bin_with_certain_char_return(nDec, nCharCount):
    if not isinstance(nDec, int):
        return ""

    strBin = bin(nDec if nDec > 0 else nDec + (1<<32)).replace("0b", "")
    strBin = strBin.rjust(nCharCount, "0")
    if len(strBin) >= nCharCount:
        return strBin[-nCharCount:]
    return ""

"""
10进制转十六进制，返回长度为nCharCount的十六进制字符串
"""
def dec_to_hex_with_certain_char_return(nDec, nCharCount):
    if not isinstance(nDec, int):
        return ""

    strHex = hex(nDec).replace("0x", "").upper()
    return strHex.rjust(nCharCount, "0")

"""
处理科学计数法浮点数，将有效数字部分保留小数位。如2.343333e-41
"""
def prcocess_scientific_notation_float(fValue, nDecimal):
    strValue = str(fValue)
    strProcessedValue = None
    if re.match(r"^[0-9]*\.[0-9]*e-[0-9]*$", strValue):
        nIndexE = strValue.find("e")
        if nIndexE >= 0:
            strFront = strValue[:nIndexE]
            strLatter = strValue[nIndexE:]
            fFront = round(float(strFront), nDecimal)
            strProcessedValue = "{front}{latter}".format(front=fFront, latter=strLatter)

    return strProcessedValue

def getValueInt(strHexList, nStart):
    if (nStart +1) >= len(strHexList):
        return ""

    strValue = ''
    strValue += strHexList[nStart]
    strValue += strHexList[nStart +1]
    strValue = strValue.zfill(2)
    bValue = bytes.fromhex(strValue)
    nValue = struct.unpack('!h', bValue)[0]
    return nValue


def getValueFloat(strHexList, nStart):
    if (nStart +3 ) >=len(strHexList):
        return ""

    strValue = ''
    strValue += strHexList[nStart]
    strValue += strHexList[nStart +1]
    strValue += strHexList[nStart + 2]
    strValue += strHexList[nStart + 3]
    strValue = strValue.zfill(4)
    bValue = bytes.fromhex(strValue)
    fValue = struct.unpack('!f', bValue)[0]

    strProcessedValue = prcocess_scientific_notation_float(fValue, 3)
    if strProcessedValue != None:
        return strProcessedValue

    return str(fValue)


def getValueFloat_Reverse(strHexList, nStart):
    if (nStart +3) >=len(strHexList):
        return ""

    strValue = ''
    strValue += strHexList[nStart + 2]
    strValue += strHexList[nStart + 3]
    strValue += strHexList[nStart]
    strValue += strHexList[nStart + 1]
    strValue = strValue.zfill(4)
    bValue = bytes.fromhex(strValue)
    fValue = struct.unpack('!f', bValue)[0]

    strProcessedValue = prcocess_scientific_notation_float(fValue, 3)
    if strProcessedValue != None:
        return strProcessedValue

    return str(fValue)


def getValueDWORD(strHexList, nStart):
    if (nStart +3) >=len(strHexList):
        return ""

    strValue = ''
    strValue += strHexList[nStart]
    strValue += strHexList[nStart +1]
    strValue += strHexList[nStart + 2]
    strValue += strHexList[nStart + 3]
    strValue = strValue.zfill(4)
    bValue = bytes.fromhex(strValue)
    nValue = struct.unpack('!i', bValue)[0]
    return nValue

def getValueDWORD_Reverse(strHexList, nStart):
    if (nStart + 3) >= len(strHexList):
        return ""

    strValue = ''
    strValue += strHexList[nStart + 2]
    strValue += strHexList[nStart + 3]
    strValue += strHexList[nStart]
    strValue += strHexList[nStart + 1]
    strValue = strValue.zfill(4)
    bValue = bytes.fromhex(strValue)
    nValue = struct.unpack('!i', bValue)[0]
    return nValue


def getValueDouble(strHexList, nStart):
    if (nStart + 3) >=len(strHexList):
        return ""

    try:
        strValue = ''
        strValue += strHexList[nStart]
        strValue += strHexList[nStart +1]
        strValue += strHexList[nStart + 2]
        strValue += strHexList[nStart + 3]
        strValue += strHexList[nStart + 4]
        strValue += strHexList[nStart + 5]
        strValue += strHexList[nStart + 6]
        strValue += strHexList[nStart + 7]
        strValue = strValue.zfill(8)
        bValue = bytes.fromhex(strValue)
        dblValue = struct.unpack('!d', bValue)[0]

        strProcessedValue = prcocess_scientific_notation_float(dblValue, 3)
        if strProcessedValue != None:
            return strProcessedValue
        return str(dblValue)
    except:
        return ""

def getValueDouble_Reverse(strHexList, nStart):
    if (nStart + 3) >=len(strHexList):
        return None

    try:
        strValue = ''
        strValue += strHexList[nStart + 6]
        strValue += strHexList[nStart + 7]
        strValue += strHexList[nStart + 4]
        strValue += strHexList[nStart + 5]
        strValue += strHexList[nStart + 2]
        strValue += strHexList[nStart + 3]
        strValue += strHexList[nStart]
        strValue += strHexList[nStart + 1]
        strValue = strValue.zfill(8)
        bValue = bytes.fromhex(strValue)
        dblValue = struct.unpack('!d', bValue)[0]

        strProcessedValue = prcocess_scientific_notation_float(dblValue, 3)
        if strProcessedValue != None:
            return strProcessedValue
        return str(dblValue)

    except:
        return ""

def getValueLongInt(strHexList, nStart):
    if nStart + 3 >= len(strHexList):
        return None

    strValue = ""
    strValue += strHexList[nStart]
    strValue += strHexList[nStart+1]
    strValue += strHexList[nStart + 2]
    strValue += strHexList[nStart + 3]
    strValue = strValue.zfill(4)
    bValue = bytes.fromhex(strValue)
    nValue = struct.unpack('!I', bValue)[0]
    return nValue

def binStr_to_dec(strValue):
    try:
        strB = "0b" + strValue
        nValue = eval(strB)
        return nValue
    except:
        return None

def hexStr_to_dec(strValue):
    try:
        nValue = int(strValue, 16)
        return nValue
    except:
        return None

def is_float_str(strT):
    try:
        n = float(strT)
        return True
    except:
        return False
