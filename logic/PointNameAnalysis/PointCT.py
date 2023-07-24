from logic.PointNameAnalysis.PointBase import PointBase


class PointCT(PointBase):
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

        if strDescription.find('A相电流')>=0:
            return  '%s%sIA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('B相电流')>=0:
            return  '%s%sIB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('C相电流')>=0:
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
        elif self.have(strDescription, ["运行时间"]):
            return "%sCHourCT%02d" % (self.strRoomName, self._nNo)
        elif self.have(strDescription, ["水阀开关状态", "阀门状态"]):
            return "%sCTValveStatus%02d" % (self.strRoomName, self._nNo)
        elif self.have_all(strDescription, ["阀门", "手自动"]):
            return "%sCTValveAutoMode%02d" % (self.strRoomName, self._nNo)
        elif self.have_all(strDescription, ["阀门", "手动", "开"]):
            return "%sCTValveManualOnSetting%02d" % (self.strRoomName, self._nNo)
        elif self.have_all(strDescription, ["阀门", "手动", "关"]):
            return "%sCTValveManualOffSetting%02d" % (self.strRoomName, self._nNo)


        if self.have_all(strDescription, ["手动", "启停"]):
            return  '%s%sManualOnOffSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('一拖多选择开关')>=0:
            return  '%s%sVSDSwitchOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["运行状态", "启停状态", "启停", "状态", "运行反馈"]):
            return  '%s%sOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["阀门", "远程"]):
            return  '%s%sValveRemote%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["阀门", "故障"]):
            return  '%s%sValveErr%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('故障')>=0:
            return  '%s%sErr%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["本地远程状态", "手自动", "手自动状态"]) and self.have(strDescription, ["命令", "设定"]):
            return  '%s%sAutoModeSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["本地远程状态", "手自动", "手自动状态"]):
            return  '%s%sAutoMode%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["频率调节", "频率给定"]):
            return  '%s%sVSDFreqSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('开关控制')>=0:
            return  '%s%sOnOffSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["频率", "输出"]):
            return  '%s%sVSDFreqOutput%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["阀门"]) and self.have(strDescription, ["控制", "开关设定"]):
            return  '%s%sValveOnOffSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)

        elif self.have(strDescription, ["频率反馈", "频率"]):
            return  '%s%sVSDFreq%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['出口管道', '进口管道']) and strDescription.find('开控制') >= 0:
            return '%s%sValveOnSetting%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['出口管道', '进口管道']) and strDescription.find('关控制') >= 0:
            return '%s%sValveOffSetting%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['出口管道', '进口管道']) and strDescription.find('开状态') >= 0:
            return '%s%sValveOn%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['出口管道', '进口管道']) and strDescription.find('关状态') >= 0:
            return '%s%sValveOff%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['出口管道'])  and self.have(strDescription, ['温度']):
            return '%s%sLeaveTemp%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ['进口管道'])  and self.have(strDescription, ['温度']):
            return '%s%sEnterTemp%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have(strDescription, ["远程"]):
            return '%s%sRemote%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["输出", "信号"]):
            return '%s%sOutputSignal%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["阀门", "开到位"]):
            return '%s%sValveOn%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif self.have_all(strDescription, ["阀门", "关到位"]):
            return '%s%sValveOff%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)



