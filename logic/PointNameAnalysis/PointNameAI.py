# -*- coding: utf-8 -*-

"""
Routes and views for the flask application.
"""

from siteinterface import app
from math import floor, ceil
import os, sys
from datetime import datetime,timedelta
import time
import logging
import zipfile
from logic.PointNameAnalysis.PointChiller import PointChiller
from logic.PointNameAnalysis.PointPump import PointPump
from logic.PointNameAnalysis.PointChMotor import PointChMotor
from logic.PointNameAnalysis.PointBase import PointBase
from logic.PointNameAnalysis.PointCTFan import PointCTFan
from logic.PointNameAnalysis.PointCT import PointCT
from logic.PointNameAnalysis.PointColdMeter import PointColdMeter
from logic.PointNameAnalysis.PointGSHP import PointGSHP
from logic.PointNameAnalysis.PointGSHPMotor import PointGSHPMotor
from logic.PointNameAnalysis.PointMainpipe import PointMainpipe
from pypinyin import pinyin, lazy_pinyin

class PointNameAI(PointBase):
    __instance = None


    def __init__(self):
        self._data = dict()
        self._pointList = dict()

    @classmethod
    def getInstance(self):
        if(self.__instance == None):
            self.__instance = PointNameAI()
        return self.__instance

    def analysis_description(self, strDescription, roomDefine, nPointIdx):
        rv = dict(result='', rate=1.0)
        strResultName = ''

        strRoomName = self.find_room_name(strDescription, roomDefine)

        if strDescription == "1#主机-冷冻水供水温度":
            print("found")

        nEquipNo = self.is_GSHP_motor(strDescription)
        if nEquipNo > 0:
            nGSHPNo = self.get_GSHP_no_of_motor(strDescription)
            strResultName = PointGSHPMotor("GSHPMotor", nEquipNo, nGSHPNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_ch_motor(strDescription)
        if nEquipNo > 0:
            nChillerNo = self.get_chiller_no_of_motor(strDescription)
            strResultName = PointChMotor('ChMotor', nEquipNo, nChillerNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_ch_coldmeter(strDescription)
        if nEquipNo > 0:
            nChillerNo = self.get_chiller_no_of_coldmeter(strDescription)
            if nEquipNo==1:
                strResultName = PointColdMeter('ChEvapColdMeter', nChillerNo, strRoomName).analysis_description(strDescription)
                if strResultName:
                    return strResultName
            if nEquipNo==2:
                strResultName = PointColdMeter('ChCondColdMeter', nChillerNo, strRoomName).analysis_description(strDescription)
                if strResultName:
                    return strResultName

        nEquipNo = self.is_chw_coldmeter(strDescription)
        if nEquipNo > 0:
            if nEquipNo == 1:
                strResultName = PointColdMeter('PriChWColdMeter', nEquipNo, strRoomName).analysis_description(strDescription)
                if strResultName:
                    return strResultName

        nEquipNo = self.is_cw_coldmeter(strDescription)
        if nEquipNo > 0:
            if nEquipNo == 1:
                strResultName = PointColdMeter('CWColdMeter', nEquipNo, strRoomName).analysis_description(strDescription)
                if strResultName:
                    return strResultName

        # chiller
        nEquipNo = self.is_chiller(strDescription)
        if nEquipNo > 0:
            strResultName =  PointChiller(nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_ct_fan(strDescription)
        if nEquipNo>0:
            nCTNo = self.get_ct_no_of_fan(strDescription)
            strResultName = PointCTFan('CTFan', nEquipNo, nCTNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_pri_chwp(strDescription)
        if nEquipNo > 0:
            strResultName = PointPump('PriChWP', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_sec_chwp(strDescription)
        if nEquipNo > 0:
            strResultName = PointPump('SecChWP', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_cwp(strDescription)
        if nEquipNo > 0:
            strResultName = PointPump('CWP', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_hwp(strDescription)
        if nEquipNo > 0:
            strResultName = PointPump('HWP', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_higharea_sec_chwp(strDescription)
        if nEquipNo > 0:
            strResultName = PointPump('HighAreaSecChWP', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_ct(strDescription)
        if nEquipNo > 0:
            strResultName = PointCT('CT', nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        # GSHP
        nEquipNo = self.is_ground_source_heat_pump(strDescription)
        if nEquipNo > 0:
            strResultName = PointGSHP("GSHP", nEquipNo, strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        nEquipNo = self.is_mainpipe(strDescription)
        if nEquipNo > 0:
            strResultName = PointMainpipe("Mainpipe", strRoomName).analysis_description(strDescription)
            if strResultName:
                return strResultName

        if self.is_undefined_point(strDescription):
            return "undefined_point_%02d" % nPointIdx

        if self.have(strDescription, ['室外']) and self.have(strDescription, ['干球温度', '温度']):
            strResultName = 'OutdoorTdbin'
            return strResultName
        elif self.have(strDescription, ['室外']) and self.have(strDescription, ['相对湿度', '湿度']):
            strResultName = 'OutdoorRH'
            return strResultName
        elif self.have(strDescription, ['机房']) and self.have(strDescription, ['相对湿度', '湿度']) and self.have_not_one(strDescription, ['室外']):
            strResultName = '%sChillerPlantRoomRH' % strRoomName
            return strResultName
        elif self.have(strDescription, ['机房']) and self.have(strDescription, ['干球温度', '温度']) and self.have_not_one(strDescription, ['室外']):
            strResultName = '%sChillerPlantRoomTdbin' % strRoomName
            return strResultName

        if self.is_after_filter(strDescription, "分集水器", "分水器") >= 0:
            if strDescription.find("温度") >= 0:
                return '%sPriChWTempSupply' % strRoomName
            elif self.have_all(strDescription, ["压力", "虚拟"]):
                return '%sVirtualPriChWPressureSupply' % strRoomName
            elif strDescription.find("压力") >= 0:
                return '%sPriChWPressureSupply' % strRoomName
        if self.is_after_filter(strDescription, "分集水器", "集水器") >= 0:
            if strDescription.find("温度") >= 0:
                return '%sPriChWTempReturn' % strRoomName
            elif self.have_all(strDescription, ["压力", "虚拟"]):
                return '%sVirtualPriChWPressureReturn' % strRoomName
            elif strDescription.find("压力") >= 0:
                return '%sPriChWPressureReturn' % strRoomName

        if self.have_all(strDescription, ['冷冻','旁通', '开度', '设定']):
            strResultName = '%sPriChWBypassValveOpenRatioSetting01' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ['冷却','旁通', '开度', '设定']):
            strResultName = '%sCWBypassValveOpenRatioSetting01' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ['冷冻','旁通', '开度', '反馈']):
            strResultName = '%sPriChWBypassValveOpenRatio01' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ['冷却','旁通', '开度', '反馈']):
            strResultName = '%sCWBypassValveOpenRatio01' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷却水", "供水", "温度"]):
            strResultName = '%sCWTempSupply' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷却水", "回水", "温度"]):
            strResultName = '%sCWTempReturn' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷冻水", "供水温度", "设定"]) or self.have_all(strDescription, ["冷冻水", "送水温度", "设定"]):
            strResultName = '%sPriChWTempSupplySetting' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷冻水", "供水", "温度"]):
            strResultName = '%sPriChWTempSupply' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷冻水", "回水", "温度"]):
            strResultName = '%sPriChWTempReturn' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷冻水", "供水", "压力"]):
            strResultName = '%sPriChWPressureSupply' % strRoomName
            return strResultName
        elif self.have_all(strDescription, ["冷冻水", "回水", "压力"]):
            strResultName = '%sPriChWPressureReturn' % strRoomName
            return strResultName


        strTrans = lazy_pinyin(strDescription)

        strAllFinal =  'U_'+ '_'.join(strTrans)

        strAllFinal = strAllFinal.replace('#', '_')
        strAllFinal = strAllFinal.replace('.', '_')
        strAllFinal = strAllFinal.replace(' ', '_')
        strAllFinal = strAllFinal.replace('/', '_')
        strAllFinal = strAllFinal.replace('\\', '_')
        strAllFinal = strAllFinal.replace('*', '_')
        strAllFinal = strAllFinal.replace('-', '_')

        return strAllFinal