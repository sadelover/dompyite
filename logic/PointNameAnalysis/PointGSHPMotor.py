from logic.PointNameAnalysis.PointBase import PointBase

class PointGSHPMotor(PointBase):
    def __init__(self, strTypePrefix, equipNo, GSHPNo, strRoomName):
        self._nNo = equipNo
        self._strTypePrefix = strTypePrefix
        self._GSHPNo = GSHPNo
        self._strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if self.have(strDescription, ["运行状态", "状态"]):
            return "%s%s%02dOnOff%02d" % (self._strRoomName, self._strTypePrefix, self._nNo, self._GSHPNo)
        if self.have(strDescription, ["输入电流"]):
            return  '%s%s%02dIA%02d'%(self._strRoomName, self._strTypePrefix, self._nNo, self._GSHPNo)
