from logic.PointNameAnalysis.PointBase import PointBase

class PointChiller(PointBase):
    def __init__(self, chillerNo, strRoomName):
        self._nNo = int(chillerNo)
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if strDescription.find('A相电压')>=0:
            return  '%sChUA%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('B相电压')>=0:
            return  '%sChUB%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('C相电压')>=0:
            return  '%sChUC%02d'%(self.strRoomName, self._nNo)

        if self.have(strDescription, ["A相电流", "电流A", "总电流"]):
            return  '%sChIA%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["B相电流", "电流B"]):
            return  '%sChIB%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["C相电流", "电流C"]):
            return  '%sChIC%02d'%(self.strRoomName, self._nNo)

        if strDescription.find('A相功率')>=0:
            return  '%sChPA%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('B相功率')>=0:
            return  '%sChPB%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('C相功率')>=0:
            return  '%sChPC%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["三相有功功率", "功率"]):
            return  '%sChPower%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["有功电能", "电能"]):
            return  '%sChPowerTotal%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, '累计运行时间'):
            return '%sChMotorRunHour%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["开关控制", "开关指令", "开关设定", "启停"]) and not self.have(strDescription, ["蒸发器", "冷凝器", "冷冻阀门", "冷冻电动阀", "冷却阀门"]):
            return '%sChOnOffSetting%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["设备故障状态", "故障", "报警"]) and not self.have(strDescription, ["冷冻阀门", "冷冻阀", "冷冻电动阀", "冷冻水阀", "冷冻侧阀门", "冷却阀门", "冷却阀", "冷却电动阀", "冷却水阀", "冷却侧阀门"]):
            return  '%sChErr%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["报警复位"]):
            return  '%sChErrReset%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["控制状态"]) and not self.have(strDescription, ["蒸发器", "冷凝器", "冷冻阀门", "冷冻电动阀", "冷却阀门"]):
            return '%sChCtrlStatus%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["转速"]):
            return '%sChMotorRotateSpeed%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["允许dom控制"]):
            return '%sChControlJiankeEnabled%02d' % (self.strRoomName, self._nNo)


        elif self.have(strDescription, ["冷冻阀门", "冷冻阀", "冷冻电动阀", "冷冻水阀", "冷冻侧阀门"]):
            if self.have_all(strDescription, ["开启", "状态"]):
                return "%sChEvapValveOn%02d" % (self.strRoomName, self._nNo)
            elif self.have_all(strDescription, ["关闭", "状态"]):
                return "%sChEvapValveOff%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开关状态", "状态"]):
                return "%sChEvapValveStatus%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开关设定"]):
                return "%sChEvaValveOnOffSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["手自动"]) and self.have(strDescription, ["命令"]):
                return "%sChEvapValveAutoMode%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开阀", "开启控制"]):
                return "%sChEvapValveOnSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["关阀", "关闭控制"]):
                return "%sChEvapValveOffSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["远程"]):
                return "%sChEvapValveRemote%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开到位"]):
                return "%sChEvapValveOn%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["关到位"]):
                return "%sChEvapValveOff%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["故障"]):
                return "%sChEvapValveErr%02d" % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["冷却阀门", "冷却阀", "冷却电动阀", "冷却水阀", "冷却侧阀门"]):
            if self.have(strDescription, ["开关状态", "状态"]):
                return "%sChCondValveStatus%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开关设定"]):
                return "%sChCondValveOnOffSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["手自动"]) and self.have(strDescription, ["命令"]):
                return "%sChCondValveAutoMode%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开阀"]):
                return "%sChCondValveOnSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["关阀"]):
                return "%sChCondValveOffSetting%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["远程"]):
                return "%sChCondValveRemote%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开到位"]):
                return "%sChCondValveOn%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["关到位"]):
                return "%sChCondValveOff%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["故障"]):
                return "%sChCondValveErr%02d" % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["热水阀"]):
            if self.have(strDescription, ["开关状态", "状态"]):
                return "%sChHotWValveStatus%02d" % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["开关设定"]):
                return "%sChHotWValveOnOffSetting%02d" % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["机组状态"]):
            return  '%sChState%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["本地远程状态", "手自动"]):
            return  '%sChAutoMode%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["运行状态", "状态", "运行反馈"]) and not self.have(strDescription, ["蒸发器", "冷凝器", "冷冻阀门", "冷冻电动阀", "冷却阀门"]):
            return  '%sChOnOff%02d'%(self.strRoomName, self._nNo)

        elif self.have(strDescription, ["电流限定设定", '主机电流百分比限定值设定', "负载限制"]):
            return '%sChAmpLmtSetPoint%02d' % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["当前负载", "电流百分比"]):
            return  '%sChAMPS%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('蒸发温度')>=0:
            return  '%sChEvapTemp%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('冷凝温度')>=0:
            return  '%sChCondTemp%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["蒸发压力", "蒸发器压力"]):
            return  '%sChEvapPressure%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["冷凝压力", "冷凝器压力"]):
            return  '%sChCondPressure%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["排气温度", "出口温度"]):
            return  '%sChGasExhaustTemp%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('吸气温度')>=0:
            return  '%sChGasSuctionTemp%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('排气压力')>=0:
            return  '%sChGasExhaustPressure%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('吸气压力')>=0:
            return  '%sChGasSuctionPressure%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('油温')>=0:
            return  '%sChOilTemp%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('蒸发器水流开关')>=0:
            return  '%sChEvapFlowSwitchOnOff%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('冷凝器水流开关')>=0:
            return  '%sChCondFlowSwitchOnOff%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('油温')>=0:
            return  '%sChOilTemp%02d'%(self.strRoomName, self._nNo)
        elif strDescription.find('油温')>=0:
            return  '%sChOilTemp%02d'%(self.strRoomName, self._nNo)
        elif self.have(strDescription, ["油压力差", "油压差", "油压"]):
            return  '%sChOilDP%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["机组模式"]):
            return  '%sChMode%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["机组控制"]):
            return  '%sChControl%02d' % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["压缩机数量"]):
            return  '%sChMotorNum%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["制冷温度设定"]):
            return '%sChLeaveEvapTempSetting%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["制热温度设定"]):
            return '%sChLeaveCondTempSetting%02d' % (self.strRoomName, self._nNo)


        # 冷冻水供回水单独处理
        elif self.have(strDescription, ["出口", "出水"]) and self.have_all(strDescription, ["蒸发器", "温度"]):
            return '%sChLeaveEvapTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have_all(strDescription, ["冷冻水", "供水温度"]):
            return '%sChLeaveEvapTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["进口", "回水"]) and self.have_all(strDescription, ["蒸发器", "温度"]):
            return '%sChEnterEvapTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have_all(strDescription, ["冷冻水", "回水温度"]):
            return '%sChEnterEvapTemp%02d' % (self.strRoomName, self._nNo)


        if self.have(strDescription, ["冷冻水", "冷水"]):
            if self.have_all(strDescription, ["出水温度", "设定"]):
                return '%sChChWTempSupplySetPoint%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["出水温度"]):
                return '%sChLeaveEvapTemp%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["进水温度"]):
                return '%sChEnterEvapTemp%02d' % (self.strRoomName, self._nNo)



        if strDescription.find('蒸发器')>=0:
            if self.have(strDescription, ['出口','出水']) and strDescription.find('压力')>=0:
                return  '%sChLeaveEvapPressure%02d'%(self.strRoomName, self._nNo)
            elif (strDescription.find('出口')>=0 or strDescription.find('出水')>=0) and self.have_all(strDescription, ["温度", "反馈"]):
                return '%sChLeaveEvapTempFeedback%02d' % (self.strRoomName, self._nNo)
            elif (strDescription.find("出口")>=0 or strDescription.find("出水")>=0) and self.have_all(strDescription, ["温度", "设定"]):
                return '%ChChWTempSupplySetPoint%02d' % (self.strRoomName, self._nNo)

            elif (strDescription.find('进水')>=0 or strDescription.find('回水')>=0) and strDescription.find('温度')>=0:
                return  '%sChEnterEvapTemp%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ['进口','回水']) and strDescription.find('压力')>=0:
                return  '%sChEnterEvapPressure%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['出口管道','进口管道']) and strDescription.find('开关控制')>=0:
                return  '%sChEvapValveOnOffSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('开控制')>=0:
                return  '%sChEvapEnterValveOnSetting%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('开控制')>=0:
                return  '%sChEvapLeaveValveOnSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('关控制')>=0:
                return  '%sChEvapEnterValveOffSetting%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('关控制')>=0:
                return  '%sChEvapLeaveValveOffSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('开状态') >= 0:
                return '%sChEvapEnterValveOn%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('开状态') >= 0:
                return '%sChEvapLeaveValveOn%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('关状态') >= 0:
                return '%sChEvapEnterValveOff%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('关状态') >= 0:
                return '%sChEvapLeaveValveOff%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, "出口管道") and strDescription.find("阀门是否参与自动控制设定值"):
                return '%sChEvapValveAutoCtrlEnalbedSetting%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, '过热度'):
                return '%sChEvapSuperHeat%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["饱和温度"]):
                return '%sChEvapSaturatedTemp%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["趋近温度"]):
                return "%sChEvapApprTemp%02d" % (self.strRoomName, self._nNo)

        # 冷却水供回水单独处理
        elif self.have(strDescription, ["回水", "进水", "入水"]) and self.have_all(strDescription, ["冷却水", "温度"]):
            return '%sChEnterCondTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ['进口','回水', '入水', '进水']) and self.have_all(strDescription, ["冷凝器", "温度"]):
            return '%sChEnterCondTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ['出口','出水', "送水", "供水"]) and self.have_all(strDescription, ["冷却水", "温度"]):
            return '%sChLeaveCondTemp%02d' % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ['出口','出水']) and self.have_all(strDescription, ["冷凝器", "温度"]):
            return '%sChLeaveCondTemp%02d' % (self.strRoomName, self._nNo)

        elif strDescription.find('冷凝器')>=0:
            if (strDescription.find('出口')>=0 or strDescription.find('出水')>=0) and strDescription.find('压力')>=0:
                return  '%sChLeaveCondPressure%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ["出口", "出水"]) and self.have_all(strDescription, ["温度", "设定", "反馈"]):
                return  '%sChLeaveCondTempSettingFeedback%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ["出口", "出水"]) and self.have_all(strDescription, ["温度", "设定"]):
                return  '%sChLeaveCondTempSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription,['出口','出水']) and strDescription.find('温度')>=0:
                return  '%sChLeaveCondTemp%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription,['进口','回水', '入水', '进水']) and strDescription.find('温度')>=0:
                return  '%sChEnterCondTemp%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription,['进口','回水', '入水', '进水']) and strDescription.find('压力')>=0:
                return  '%sChEnterCondPressure%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['出口管道','进口管道']) and strDescription.find('开关控制')>=0:
                return  '%sChCondValveOnOffSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('开控制')>=0:
                return  '%sChCondEnterValveOnSetting%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('开控制')>=0:
                return  '%sChCondLeaveValveOnSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('关控制')>=0:
                return  '%sChCondEnterValveOffSetting%02d'%(self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('关控制')>=0:
                return  '%sChCondLeaveValveOffSetting%02d'%(self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('开状态') >= 0:
                return '%sChCondEnterValveOn%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('开状态') >= 0:
                return '%sChCondLeaveValveOn%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, ['进口管道']) and strDescription.find('关状态') >= 0:
                return '%sChCondEnterValveOff%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ['出口管道']) and strDescription.find('关状态') >= 0:
                return '%sChCondLeaveValveOff%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, "出口管道") and strDescription.find("阀门是否参与自动控制设定值"):
                return '%sChCondValveAutoCtrlEnalbedSetting%02d' % (self.strRoomName, self._nNo)

            elif self.have(strDescription, '过冷度'):
                return '%sChCondSuperCool%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["饱和温度"]):
                return '%sChCondSaturatedTemp%02d' % (self.strRoomName, self._nNo)
            elif self.have(strDescription, ["趋近温度"]):
                return "%sChCondApprTemp%02d" % (self.strRoomName, self._nNo)

        elif self.have(strDescription, ["压缩机压力"]):
            return "%sChCondPressure%02d" % (self.strRoomName, self._nNo)


        return None

