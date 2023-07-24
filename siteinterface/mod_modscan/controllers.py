
from siteinterface.mod_modscan import bp_modscan
from flask import request, jsonify
from pymodbus.client.sync import ModbusTcpClient
from siteinterface.commonUtils import is_ip, ping_ip

from siteinterface.mod_modscan.utils import *
from pymodbus.exceptions import ModbusIOException
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse
from pymodbus.pdu import ExceptionResponse
from pymodbus.bit_write_message import WriteSingleCoilResponse
from pymodbus.register_write_message import WriteSingleRegisterResponse, WriteMultipleRegistersResponse
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian


@bp_modscan.route("/connect", methods=["POST"])
def connect():
    rcv = request.get_json()
    ip = rcv.get("ip", None)
    port = rcv.get("port", None)

    if ip == None or not isinstance(ip, str):
        return jsonify(dict(err=1, msg="ip不能为空", data=False))
    if not len(ip):
        return jsonify(dict(err=1, msg="ip不能为空", data=False))
    if not is_ip(ip):
        return jsonify(dict(err=1, msg="ip格式有误", data=False))
    if not isinstance(port, int):
        return jsonify(dict(err=1, msg="port不能为空且必须为整数", data=False))

    client = ModbusTcpClient(ip, port=port, timeout=2)
    client.inter_char_timeout = 3000

    if not client.connect():
        if not ping_ip(ip):
            return jsonify(dict(err=1, msg="总线({ip})连接失败且ip不可ping通".format(ip=ip), data=False))
        else:
            return jsonify(dict(err=1, msg="总线({ip})连接失败但ip可ping通".format(ip=ip), data=False))

    return jsonify(dict(err=0, msg="网关({ip})连接成功".format(ip=ip), data=True))


@bp_modscan.route("/readOnce", methods=["POST"])
def read_once():
    rcv = request.get_json()
    ip = rcv.get("ip", None)
    port = rcv.get("port", None)
    deviceId = rcv.get("deviceId", None)
    registerStart = rcv.get("registerStart", None)
    length = rcv.get("length", None)
    functionCode = rcv.get("functionCode", None)  # 1:coils, 2:inputStatus , 3: holdingRegisters, 4: inputRegisters
    dataType = rcv.get("dataType", None)  # 0- 二进制；1-十进制；2-整数；3-十六进制；4-浮点；5-浮点反置；6-双精度浮点；7-双精度浮点反置

    if ip == None or not isinstance(ip, str):
        return jsonify(dict(err=1, msg="ip不能为空", data={}))
    if not len(ip):
        return jsonify(dict(err=1, msg="ip不能为空", data={}))
    if not is_ip(ip):
        return jsonify(dict(err=1, msg="ip格式有误", data={}))
    if not isinstance(port, int):
        return jsonify(dict(err=1, msg="port不能为空且必须为整数", data={}))
    if not isinstance(deviceId, int):
        return jsonify(dict(err=1, msg="站号不能为空且必须为整数", data={}))
    if deviceId <= 0:
        return jsonify(dict(err=1, msg="站号必须为大于0的整数", data={}))
    if not isinstance(registerStart, int):
        return jsonify(dict(err=1, msg="站好起始地址不能为空且必须为整数", data={}))
    if registerStart <= 0:
        return jsonify(dict(err=1, msg="站好起始地址必须为大于0的整数", data={}))
    if not isinstance(length, int):
        return jsonify(dict(err=1, msg="读取寄存器地址长度不能为空且必须为整数", data={}))
    if length <= 0:
        return jsonify(dict(err=1, msg="读取寄存器地址长度必须为大于0的整数", data={}))
    if functionCode not in [1, 2, 3, 4]:
        return jsonify(dict(err=1, msg="功能码必须为整数且在1， 2， 3， 4 中", data={}))
    if dataType not in [0, 1, 2, 3, 4, 5, 6, 7]:
        return jsonify(dict(err=1, msg="功能码必须为整数且在0, 1, 2, 3, 4, 5, 6, 7中", data={}))

    client = ModbusTcpClient(ip, port=port, timeout=2)
    client.inter_char_timeout = 3000

    if not client.connect():
        if not ping_ip(ip):
            return jsonify(dict(err=1, msg="总线({ip})连接失败且ip不可ping通".format(ip=ip), data={}))
        else:
            return jsonify(dict(err=1, msg="总线({ip})连接失败但ip可ping通".format(ip=ip), data={}))

    rsp = None
    if functionCode == 1:
        rsp = client.read_coils(registerStart - 1, length, unit=deviceId)
    elif functionCode == 2:
        rsp = client.read_discrete_inputs(registerStart - 1, length, unit=deviceId)
    elif functionCode == 3:
        rsp = client.read_holding_registers(registerStart - 1, length, unit=deviceId)
    elif functionCode == 4:
        rsp = client.read_input_registers(registerStart - 1, length, unit=deviceId)
    if rsp == None:
        return jsonify(dict(err=1, msg="modbus读取返回有误，未知错误", data={}))

    if isinstance(rsp, ModbusIOException):
        dInfo = {"errCode": 1,
                 "msg": "modbus设备连接失败",
                 "detail": "测试结果：失败。\n\n失败原因：连接modbus设备失败。\n\n过程描述：ip地址：{ip}，端口:{port}，起始寄存器地址:{register}, 读取长度:{registerCount},"
                        "功能码: {functionCode}, 站号:{deviceId}。连接报错信息:{errMsg}。\n\n".format(register=registerStart,
                                                                                                    registerCount=length,
                                                                                                     functionCode=functionCode,
                                                                                                     deviceId=deviceId,
                                                                                                     errMsg=rsp.message,
                                                                                                     ip=ip,
                                                                                                     port=port),
                 "data": []}

        return jsonify(dict(err=0, msg="", data=dInfo))

    alsDataList = []
    if isinstance(rsp, ReadCoilsResponse):
        alsDataList = genModbusBitList(rsp)
    elif isinstance(rsp, ReadDiscreteInputsResponse):
        alsDataList = genModbusBitList(rsp)
    elif isinstance(rsp, ReadHoldingRegistersResponse):
        alsDataList = genModbusByteList(rsp)
    elif isinstance(rsp, ReadInputRegistersResponse):
        alsDataList = genModbusByteList(rsp)
    elif isinstance(rsp, ExceptionResponse):
        errDesc = "未知错误"
        if hasattr(rsp, "exception_code"):
            errDesc = getModbusExceptionCodeDesc(rsp.exception_code)

        return jsonify(dict(err=0, msg="", data={"errCode": 2,
                                                 "msg": "ResponseError: {errDesc}".format(errDesc=errDesc),
                                                 "data": []}))

    if not len(alsDataList):
        dInfo = {"errCode": 3,
                 "detail": "测试结果：失败。\n\n失败原因：modbus发包后所得结果解析出的数据列表长度为0。\n\n过程描述：ip地址：{ip}，端口:{port}，起始寄存器地址:{register}, 读取长度:{registerCount},"
                        "功能码: {functionCode}, 站号:{deviceId}。连接报错信息:{errMsg}。\n\n".format(register=registerStart,
                                                                                         registerCount=length,
                                                                                         functionCode=functionCode,
                                                                                         deviceId=deviceId,
                                                                                         errMsg=rsp.message,
                                                                                         ip=ip,
                                                                                         port=port),
                 "msg": "modbus回包的解析结果为一个长度为0的数组",
                 "data": []}
        return jsonify(dict(err=0, msg="", data=dInfo))

    if rsp.transaction_id != client.transaction.tid:
        dInfo = {"errCode": 4,
                 "detail": "测试结果：失败。\n\n失败原因：modbus发包后进行的串包校验失败。\n\n过程描述：ip地址：{ip}，端口:{port}，起始寄存器地址:{register}, 读取长度:{registerCount},"
                        "功能码: {functionCode}, 站号:{deviceId}。连接报错信息:{errMsg}。\n\n".format(register=registerStart,
                                                                                         registerCount=length,
                                                                                         functionCode=functionCode,
                                                                                         deviceId=deviceId,
                                                                                         errMsg=rsp.message,
                                                                                         ip=ip,
                                                                                         port=port),
                 "msg": "modbus串包校验失败",
                 "data": []}
        return jsonify(dict(err=0, msg="", data=dInfo))

    result = []
    if functionCode == 1:
        nNum = registerStart
        for alsData in alsDataList:
            key = "{nNum:05}".format(nNum=nNum)
            value = alsData
            nNum += 1
            result.append(dict(key=key, value=value))
            if len(result) >= length:
                break

    elif functionCode == 2:
        nNum = registerStart
        for alsData in alsDataList:
            key = "1{nNum:04}".format(nNum=nNum)
            value = alsData
            nNum += 1
            result.append(dict(key=key, value=value))
            if len(result) >= length:
                break

    elif functionCode == 3 or functionCode == 4:
        strTag = "4" if functionCode == 3 else "3"
        if dataType == 0:  # 二进制
            nNum = registerStart
            for nIndex in range(length):
                nDec = getValueInt(alsDataList, nIndex * 2)
                strBin = dec_to_bin_with_certain_char_return(nDec, 16)
                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=strBin))

        elif dataType == 1:  # 十进制
            nNum = registerStart
            for nIndex in range(length):
                nDec = getValueInt(alsDataList, nIndex * 2)
                strDec = "{n:05}".format(n=nDec)
                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=strDec))

        elif dataType == 2:  # 整数
            nNum = registerStart
            for nIndex in range(length):
                nDec = getValueInt(alsDataList, nIndex * 2)
                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=nDec))

        elif dataType == 3:  # 十六进制
            nNum = registerStart
            for nIndex in range(length):
                # nDec = getValueInt(alsDataList, nIndex * 2)
                # strHex = dec_to_hex_with_certain_char_return(nDec, 4)
                strHex = ""

                if len(alsDataList) >= nIndex * 2 + 1:
                    strHex += alsDataList[nIndex * 2]
                if len(alsDataList) >= ((nIndex * 2) + 1) + 1:
                    strHex += alsDataList[(nIndex * 2) + 1]

                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=strHex.upper() + "H"))

        elif dataType == 4:  # 浮点
            nNum = registerStart
            nIndex = 0
            while nIndex <= length - 1:
                if nIndex % 2 == 0:
                    value = getValueFloat_Reverse(alsDataList, nIndex * 2)
                    if value == None:
                        value = ""
                else:
                    value = ""
                nIndex += 1
                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=str(value)))

        elif dataType == 5:  # 浮点反置
            nNum = registerStart
            nIndex = 0
            while nIndex <= length - 1:
                if nIndex % 2 == 0:
                    value = getValueFloat(alsDataList, nIndex * 2)
                    if value == None:
                        value = ""
                else:
                    value = ""
                nIndex += 1
                key = "{tag}{nNum:04}".format(nNum=nNum, tag=strTag)
                nNum += 1
                result.append(dict(key=key, value=str(value)))

        elif dataType == 6:  # 双精度浮点
            nNum = registerStart
            nIndex = 0
            while nIndex <= length - 1:
                if nIndex % 4 == 0:
                    value = getValueDouble_Reverse(alsDataList, nIndex * 2)
                    if value == None:
                        value = ""
                else:
                    value = ""
                nIndex += 1
                key = "4{nNum:04}".format(nNum=nNum)
                nNum += 1
                result.append(dict(key=key, value=str(value)))

        elif dataType == 7:  # 双精度浮点反置
            nNum = registerStart
            nIndex = 0
            while nIndex <= length - 1:
                if nIndex % 4 == 0:
                    value = getValueDouble(alsDataList, nIndex * 2)
                    if value == None:
                        value = ""
                else:
                    value = ""
                nIndex += 1
                key = "4{nNum:04}".format(nNum=nNum)
                nNum += 1
                result.append(dict(key=key, value=str(value)))

    return jsonify(dict(err=0, msg="", data={"errCode": 0, "msg": "", "data": result}))


@bp_modscan.route("/writeValue", methods=["POST"])
def write_value():
    rcv = request.get_json()
    if not isinstance(rcv, dict):
        rcv = {}

    ip = rcv.get("ip", None)
    port = rcv.get("port", None)
    deviceId = rcv.get("deviceId", None)
    functionCode = rcv.get("functionCode")   # 1:coils,  3: holdingRegisters
    dataType = rcv.get("dataType", None)  # 0- 二进制；1-十进制；2-整数；3-十六进制；4-浮点；5-浮点反置；6-双精度浮点；7-双精度浮点反置
    register = rcv.get("register", None)
    value = rcv.get("value", None)

    if ip == None or not isinstance(ip, str):
        return jsonify(dict(err=1, msg="ip不能为空", data=False))
    if not len(ip):
        return jsonify(dict(err=1, msg="ip不能为空", data=False))
    if not is_ip(ip):
        return jsonify(dict(err=1, msg="ip格式有误", data=False))
    if not isinstance(port, int):
        return jsonify(dict(err=1, msg="port不能为空且必须为整数", data=False))
    if not isinstance(deviceId, int):
        return jsonify(dict(err=1, msg="站号不能为空且必须为整数", data=False))
    if deviceId <= 0:
        return jsonify(dict(err=1, msg="站号必须为大于0的整数", data=False))
    if not isinstance(register, int):
        return jsonify(dict(err=1, msg="站好起始地址不能为空且必须为整数", data=False))
    if register <= 0:
        return jsonify(dict(err=1, msg="站好起始地址必须为大于0的整数", data=False))
    if functionCode not in [1, 3]:
        return jsonify(dict(err=1, msg="功能码必须为整数且在1, 3中", data=False))
    if dataType not in [0, 1, 2, 3, 4, 5, 6, 7]:
        return jsonify(dict(err=1, msg="功能码必须为整数且在0, 1, 2, 3, 4, 5, 6, 7中", data=False))
    if value == None:
        return jsonify(dict(err=1, msg="值不能为空", data=False))
    if not isinstance(value, str):
        return jsonify(dict(err=1, msg="值必须为字符串", data=False))
    if not len(value):
        return jsonify(dict(err=1, msg="值不能为空", data=False))
    if functionCode == 1:
        if value not in ["0", "1"]:
            return jsonify(dict(err=1, msg="功能码为01时值只能写入0或1", data=False))

    if dataType == 0:
        if not re.match(r"[0-1]{16}", value):
            return jsonify(dict(err=1, msg="当前为位模式，输入的值有误", data=False))

    client = ModbusTcpClient(ip, port=port, timeout=2)
    client.inter_char_timeout = 3000

    if not client.connect():
        if not ping_ip(ip):
            return jsonify(dict(err=1, msg="总线({ip})连接失败且ip不可ping通".format(ip=ip), data=False))
        else:
            return jsonify(dict(err=1, msg="总线({ip})连接失败但ip可ping通".format(ip=ip), data=False))

    rsp = None
    if functionCode == 1:
        rsp = client.write_coil(register-1, int(value), unit=deviceId)
    elif functionCode == 3:
        if dataType == 0:  # 二进制
            nValue = binStr_to_dec(value)
            if nValue == None:
                return jsonify(dict(err=1, msg="当前为位模式，输入的值有误", data=False))

            try:
                rsp = client.write_register(register-1, nValue, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 1: # 十进制
            try:
                rsp = client.write_register(register-1, int(value), unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 2: # 整数
            nValue = None
            try:
                nValue = int(value)
            except:
                pass
            if nValue == None:
                return jsonify(dict(err=1, msg="传入的值有误", data=False))

            try:
                rsp = client.write_register(register - 1, nValue, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 3: # 十六进制
            hexValue = value
            if value.endswith("H") and len(value) > 1:
                hexValue = value[0:len(value)-1]

            nDecValue = hexStr_to_dec(hexValue)
            if nDecValue == None:
                return jsonify(dict(err=1, msg="出入的值有误", data=False))

            try:
                rsp = client.write_registers(register - 1, nDecValue, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 4: # 浮点
            if not is_float_str(value):
                return jsonify(dict(err=1, msg="传入的值无法转为浮点", data=False))

            builder = BinaryPayloadBuilder(wordorder=Endian.Little, byteorder=Endian.Big)
            builder.add_32bit_float(float(value))
            payload = builder.build()
            try:
                rsp = client.write_registers(register - 1, payload, skip_encode=True, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 5: # 浮点反置
            if not is_float_str(value):
                return jsonify(dict(err=1, msg="传入的值无法转为浮点", data=False))

            builder = BinaryPayloadBuilder(wordorder=Endian.Big, byteorder=Endian.Big)
            builder.add_32bit_float(float(value))
            payload = builder.build()
            try:
                rsp = client.write_registers(register - 1, payload, skip_encode=True, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 6:  # 双精度浮点
            if not is_float_str(value):
                return jsonify(dict(err=1, msg="传入的值无法转为浮点", data=False))

            builder = BinaryPayloadBuilder(wordorder=Endian.Little, byteorder=Endian.Big)
            builder.add_64bit_float(float(value))
            payload = builder.build()
            try:
                rsp = client.write_registers(register - 1, payload, skip_encode=True, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

        elif dataType == 7: # 双精度浮点反置
            if not is_float_str(value):
                return jsonify(dict(err=1, msg="传入的值无法转为浮点", data=False))

            builder = BinaryPayloadBuilder(wordorder=Endian.Big, byteorder=Endian.Big)
            builder.add_64bit_float(float(value))
            payload = builder.build()
            try:
                rsp = client.write_registers(register - 1, payload, skip_encode=True, unit=deviceId)
            except Exception as ept:
                return jsonify(dict(err=1, msg="写值失败:%s" % ept.__str__(), data=False))

    bSuc = False
    msg = "写值失败"
    if isinstance(rsp, WriteSingleCoilResponse):
        msg = "写值成功"
        bSuc = True

    elif isinstance(rsp, WriteSingleRegisterResponse):
        msg = "写值成功"
        bSuc = True

    elif isinstance(rsp, WriteMultipleRegistersResponse):
        msg = "写值成功"
        bSuc = True

    elif isinstance(rsp, ExceptionResponse):
        if hasattr(rsp, "exception_code"):
            msg = getModbusExceptionCodeDesc(rsp.exception_code)

    return jsonify(dict(err=1 if not bSuc else 0, msg=msg, data=bSuc))





