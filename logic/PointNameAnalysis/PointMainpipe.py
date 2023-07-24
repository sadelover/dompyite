from logic.PointNameAnalysis.PointBase import PointBase

class PointMainpipe(PointBase):
    def __init__(self, strTypePrefix, strRoomName):
        self.strType = strTypePrefix
        self.strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if self.have_all(strDescription, ["冷量表", "供水温度"]):
            return "%s%sColdMeterTempSupply" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "回水温度"]):
            return "%s%sColdMeterTempReturn" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "瞬时流量"]):
            return "%s%sColdMeterInstantFlowRate" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "瞬时热流量"]):
            return "%s%sColdMeterInstantHotFlowRate" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "正累积热量"]):
            return "%s%sColdMeterPositiveAccumHeat" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "负累积热量"]):
            return "%s%sColdMeterNegativeAccumHeat" % (self.strRoomName, self.strType)
        if self.have_all(strDescription, ["冷量表", "净累积热量"]):
            return "%s%sColdMeterNetAccumHeat" % (self.strRoomName, self.strType)