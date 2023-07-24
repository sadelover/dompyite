from logic.PointNameAnalysis.PointBase import PointBase


class PointCTFan(PointBase):
    def __init__(self, strTypePrefiex, equipNo, nCTNo, strRoomName):
        self._nNo = equipNo
        self._strTypePrefix = strTypePrefiex
        self._nCTNo = nCTNo
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if strDescription.find('A相电压')>=0:
            return  '%s%s%02dUA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('B相电压')>=0:
            return  '%s%s%02dUB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('C相电压')>=0:
            return  '%s%s%02dUC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)

        if strDescription.find('A相电流')>=0:
            return  '%s%s%02dIA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('B相电流')>=0:
            return  '%s%s%02dIB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('C相电流')>=0:
            return  '%s%s%02dIC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)

        if strDescription.find('A相功率')>=0:
            return  '%s%s%02dPA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('B相功率')>=0:
            return  '%s%s%02dPB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('C相功率')>=0:
            return  '%s%s%02dPC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('三相有功功率')>=0:
            return  '%s%s%02dPower%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('有功电能')>=0:
            return  '%s%s%02dPowerTotal%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)


        if strDescription.find('一拖多选择开关')>=0:
            return  '%s%s%02dVSDSwitchOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('运行状态')>=0:
            return  '%s%s%02dOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('故障')>=0:
            return  '%s%s%02dErr%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('本地远程状态')>=0:
            return  '%s%s%02dAutoMode%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('频率调节')>=0:
            return  '%s%s%02dVSDFreqSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('开关控制')>=0:
            return  '%s%s%02dOnOffSetting%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)
        elif strDescription.find('频率反馈')>=0:
            return  '%s%s%02dVSDFreqFeedback%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nCTNo)


