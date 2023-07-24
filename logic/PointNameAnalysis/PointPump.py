from logic.PointNameAnalysis.PointBase import PointBase


class PointPump(PointBase):
    def __init__(self, strTypePrefiex, equipNo, strRoomName):
        self._nNo = equipNo
        self._strTypePrefix = strTypePrefiex
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if strDescription.find('A相电压')>=0:
            return  '%s%sUA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('B相电压')>=0:
            return  '%s%sUB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('C相电压')>=0:
            return  '%s%sUC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)

        if self.have(strDescription, ["A相电流", "总电流A"]):
            return  '%s%sIA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["B相电流", "总电流B"]):
            return  '%s%sIB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["C相电流", "总电流C"]):
            return  '%s%sIC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)

        if strDescription.find('A相功率')>=0:
            return  '%s%sPA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('B相功率')>=0:
            return  '%s%sPB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('C相功率')>=0:
            return  '%s%sPC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('三相有功功率')>=0:
            return  '%s%sPower%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('有功电能')>=0:
            return  '%s%sPowerTotal%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["流量"]):
            return '%s%sFlow%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)

        if strDescription.find('一拖多选择开关')>=0:
            return  '%s%sVSDSwitchOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["频率设定", "频率给定"]):
            return  '%s%sVSDFreqSetting%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)

        elif self.have(strDescription, ["运行状态", "开关状态", "启停状态", "状态", "运行反馈"]):
            return  '%s%sOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["故障", "报警", "故障报警"]):
            return  '%s%sErr%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["本地远程状态", "手自动状态", "手自动"]) and self.have(strDescription, ["命令", "设定"]):
            return  '%s%sAutoModeSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["本地远程状态", "手自动状态", "手自动", "自动反馈"]):
            return  '%s%sAutoMode%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('频率调节')>=0:
            return  '%s%sVSDFreqSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('开关控制')>=0:
            return  '%s%sOnOffSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["频率输出"]):
            return  '%s%sVSDFreqOutput%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["频率反馈", "频率"]):
            return  '%s%sVSDFreq%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)

        elif self.have(strDescription, ["运行时间"]):
            return "%sCHour%s%02d" % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["手动", "启停"]):
            return "%s%sManualOnOffSetting%02d" % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["远程"]):
            return "%s%sRemote%02d" % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["输出", "信号"]):
            return "%s%sOutputSignal%02d" % (self.strRoomName, self._strTypePrefix, self._nNo)






