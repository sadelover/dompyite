from logic.PointNameAnalysis.PointBase import PointBase


class PointColdMeter(PointBase):
    def __init__(self, strTypePrefiex, equipNo, strRoomName):
        self._nNo = equipNo
        self._strTypePrefix = strTypePrefiex
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if strDescription.find('供水温度')>=0:
            return  '%s%sTempSupply%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('回水温度')>=0:
            return  '%s%sTempReturn%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('瞬时热流量')>=0:
            return  '%s%sCold%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('瞬时流量')>=0:
            return  '%s%sFlow%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('正累积热量')>=0:
            return  '%s%sPositiveColdTotal%02d'%(self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('负累积热量') >= 0:
            return '%s%sNegativeColdTotal%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)
        elif strDescription.find('净累积热量') >= 0:
            return '%s%sColdTotal%02d' % (self.strRoomName, self._strTypePrefix, self._nNo)



