from logic.PointNameAnalysis.PointBase import PointBase

class PointGSHP(PointBase):
    def __init__(self, strTypePrefix, GSHPNo, strRoomName):
        self._strTypePrefix = strTypePrefix
        self._nNo = GSHPNo
        self._strRoomName = strRoomName

    def analysis_description(self, strDescription):
        if self.have(strDescription, ["运行状态", "状态"]):
            return "%s%sOnOff%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have(strDescription, ["开关指令"]):
            return "%s%sOnOffSetting%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have(strDescription, ["开关指令"]):
            return "%s%sOnOffSetting%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have(strDescription, ["故障"]):
            return "%s%sErr%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["制热热水", "能量调节", "需求"]):
            return "%s%sHotWaterEnergyAdjustNeed%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["制冷冷水", "能量调节", "需求"]):
            return "%s%sColdWaterEnergyAdjustNeed%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["输出", "制热热水", "能量调节"]):
            return "%s%sHotWaterEnergyAdjust%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["输出", "制冷冷水", "能量调节"]):
            return "%s%sColdWaterEnergyAdjust%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)

        if self.have_all(strDescription, ["激活", "警报代码"]):
            return "%s%sActivateAlarmCode%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["平均", "运行时数"]):
            return "%s%sMeanRunHour%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["压缩机数量"]):
            return "%s%sMotorCount%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)
        if self.have_all(strDescription, ["压缩机数量"]):
            return "%s%sMotorCount%02d" % (self._strRoomName, self._strTypePrefix, self._nNo)

        if strDescription.find("蒸发器") >= 0:
            if self.have(strDescription, ["出水"]) and self.have(strDescription, ["温度"]):
                return '%s%sLeaveEvapTemp%02d' % (self._strRoomName, self._strTypePrefix, self._nNo)
        if strDescription.find("蒸发器") >= 0:
            if self.have(strDescription, ["进水"]) and self.have(strDescription, ["温度"]):
                return '%s%sEnterEvapTemp%02d' % (self._strRoomName, self._strTypePrefix, self._nNo)

