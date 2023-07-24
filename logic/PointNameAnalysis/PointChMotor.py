from logic.PointNameAnalysis.PointBase import PointBase


class PointChMotor(PointBase):
    def __init__(self, strTypePrefiex, equipNo, nChillerNo, strRoomName):
        self._nNo = equipNo
        self._strTypePrefix = strTypePrefiex
        self._nChillerNo = nChillerNo
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if strDescription.find('A相电压')>=0:
            return  '%s%s%02dUA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('B相电压')>=0:
            return  '%s%s%02dUB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('C相电压')>=0:
            return  '%s%s%02dUC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)

        if strDescription.find('A相电流')>=0:
            return  '%s%s%02dIA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('B相电流')>=0:
            return  '%s%s%02dIB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('C相电流')>=0:
            return  '%s%s%02dIC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)

        if strDescription.find('A相功率')>=0:
            return  '%s%s%02dPA%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('B相功率')>=0:
            return  '%s%s%02dPB%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('C相功率')>=0:
            return  '%s%s%02dPC%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('三相有功功率')>=0:
            return  '%s%s%02dPower%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('有功电能')>=0:
            return  '%s%s%02dPowerTotal%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif self.have(strDescription, ["故障", "故障状态"]):
            return  '%s%s%02dErr%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif self.have(strDescription, ["运行状态", "状态"]):
            return  '%s%s%02dOnOff%02d'%(self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)

        elif strDescription.find('负载率') >= 0:
            return '%s%s%02dAMPS%02d' % (self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('油槽压力') >= 0:
            return '%s%s%02dOilSumpPressure%02d' % (self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)
        elif strDescription.find('供油压力') >= 0:
            return '%s%s%02dOilPressureSupply%02d' % (self.strRoomName, self._strTypePrefix, self._nNo, self._nChillerNo)



