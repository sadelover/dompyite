import re

from pypinyin import pinyin, lazy_pinyin
class PointBase:
    def __init__(self,):
        pass

    def have(self, strAll, strOR1List):
        if isinstance(strOR1List, str):
            return strAll.find(strOR1List)>=0
        elif isinstance(strOR1List, list):
            for item in strOR1List:
                if strAll.find(item)>=0:
                    return True

        return False

    def have_all(self, strAll, strAndList):
        if isinstance(strAndList, str):
            return strAll.find(strAndList)>=0
        elif isinstance(strAndList, list):
            for item in strAndList:
                if strAll.find(item)<0:
                    return False

        return True

    def have_not_one(self, strAll, strAndList):
        if isinstance(strAndList, str):
            return strAll.find(strAndList)<0
        elif isinstance(strAndList, list):
            for item in strAndList:
                if strAll.find(item)>=0:
                    return False

        return True

    def is_chiller(self, strDecription):
        if self.have(strDecription, ['1#压缩机','2#压缩机','3#压缩机','4#压缩机','5#压缩机','6#压缩机']):
            return -1
        detect = self.return_found_option_and_index(strDecription, ["冷机", "主机", "离心机组"])
        if detect[0]:
            nIndex = strDecription.find('#{0}'.format(detect[0]))
            if nIndex<0:
                nIndex  = strDecription.find('号{0}'.format(detect[0]))
                if nIndex<0:
                    return 0
            try:
                nNo =  int(strDecription[nIndex-1])
                return nNo
            except:
                return 0
        return -1

    def is_ch_motor(self, strDecription):
        if strDecription.find("冷机") >= 0:
            if self.have(strDecription, ['1#压缩机','2#压缩机','3#压缩机','4#压缩机','5#压缩机','6#压缩机']):
                nIndex = strDecription.find('#压缩机')
                return int(strDecription[nIndex-1])
            if self.have(strDecription, ['1号压缩机', '2号压缩机', '3号压缩机', '4号压缩机', '5号压缩机', '6号压缩机']):
                nIndex = strDecription.find('号压缩机')
                return int(strDecription[nIndex - 1])
            if self.have(strDecription, ["压缩机1", "压缩机2", "压缩机3", "压缩机4", "压缩机5", "压缩机6"]):
                nIndex = strDecription.find('压缩机')
                return int(strDecription[nIndex + 3])
        return -1

    def is_GSHP_motor(self, strDecription):
        if self.have(strDecription, ["地源热泵"]):
            if self.have(strDecription, ['1#压缩机','2#压缩机','3#压缩机','4#压缩机','5#压缩机','6#压缩机']):
                nIndex = strDecription.find('#压缩机')
                return int(strDecription[nIndex-1])
            if self.have(strDecription, ['1号压缩机', '2号压缩机', '3号压缩机', '4号压缩机', '5号压缩机', '6号压缩机']):
                nIndex = strDecription.find('号压缩机')
                return int(strDecription[nIndex - 1])
            if self.have(strDecription, ["压缩机1", "压缩机2", "压缩机3", "压缩机4", "压缩机5", "压缩机6"]):
                nIndex = strDecription.find('压缩机')
                return int(strDecription[nIndex + 3])
        return -1

    def is_ch_coldmeter(self, strDecription):
        if self.have(strDecription, ['冷量表']) and self.have(strDecription, ['冷机'])  and self.have(strDecription, ['蒸发器']):
            return 1
        elif self.have(strDecription, ['冷量表']) and self.have(strDecription, ['冷机'])  and self.have(strDecription, ['冷凝器']):
            return 2
        return -1

    def is_chw_coldmeter(self, strDecription):
        if self.have(strDecription, ['冷量表']) and self.have(strDecription, ['冷冻'])  and self.have(strDecription, ['总管']):
            nIndex = strDecription.find('#')
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 1
            return 1
        return -1



    def is_cw_coldmeter(self, strDecription):
        if self.have(strDecription, ['冷量表']) and self.have(strDecription, ['冷却'])  and self.have(strDecription, ['总管']):
            nIndex = strDecription.find('#')
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 1
            return 1
        return -1



    def get_chiller_no_of_coldmeter(self, strDecription):
        if self.have(strDecription, '冷机'):
            nIndex = strDecription.find('#冷机')
            if nIndex<0:
                nIndex  = strDecription.find('号冷机')
                if nIndex<0:
                    return 0
            try:
                nNo =  int(strDecription[nIndex-1])
                return nNo
            except:
                return 0
        return -1

    def is_ct_fan(self, strDecription):
        if self.have(strDecription, ['1#风机','2#风机','3#风机','4#风机','5#风机','6#风机','7#风机','8#风机','9#风机']):
            nIndex = strDecription.find('#风机')
            return int(strDecription[nIndex-1])
        if self.have(strDecription, ['1号风机', '2号风机', '3号风机', '4号风机', '5号风机', '6号风机']):
            nIndex = strDecription.find('号风机')
            return int(strDecription[nIndex - 1])

        return -1

    def get_ct_no_of_fan(self, strDecription):
        if self.have(strDecription, '冷却塔'):
            nIndex = strDecription.find('#冷却塔')
            if nIndex<0:
                nIndex  = strDecription.find('号冷却塔')
                if nIndex<0:
                    return 0
            try:
                nNo =  int(strDecription[nIndex-1])
                return nNo
            except:
                return 0
        return -1

    def get_chiller_no_of_motor(self, strDecription):
        if self.have(strDecription, '冷机'):
            nIndex = strDecription.find('#冷机')
            if nIndex<0:
                nIndex  = strDecription.find('号冷机')
                if nIndex<0:
                    return 0
            try:
                nNo =  int(strDecription[nIndex-1])
                return nNo
            except:
                return 0
        return -1

    def get_GSHP_no_of_motor(self, strDescription):
        if self.have(strDescription, "地源热泵"):
            nIndex = strDescription.find('#地源热泵')
            if nIndex < 0:
                nIndex = strDescription.find('号地源热泵')
                if nIndex<0:
                    return 0
            try:
                nNo = int(strDescription[nIndex-1])
                return nNo
            except:
                return 0
        return -1

    def is_pri_chwp(self, strDecription):
        listFound = self.return_found_option_and_index(strDecription, ['冷冻一次泵', '一次冷冻泵', '冷冻泵', '冷冻水泵'])
        if listFound[0]:
            nIndex = strDecription.find('#{0}'.format(listFound[0]))
            if nIndex < 0:
                nIndex = strDecription.find('号{0}'.format(listFound[0]))
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_sec_chwp(self, strDecription):
        listFound = self.return_found_option_and_index(strDecription, ['冷冻二次泵', '二次冷冻泵'])
        if listFound[0]:
            nIndex = strDecription.find('#{0}'.format(listFound[0]))
            if nIndex < 0:
                nIndex = strDecription.find('号{0}'.format(listFound[0]))
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_cwp(self, strDecription):
        listDetec = self.return_found_option_and_index(strDecription, ['冷却泵', '冷却水泵'])
        if listDetec[0]:
            nIndex = strDecription.find("#{0}".format(listDetec[0]))
            if nIndex < 0:
                nIndex = strDecription.find("号{0}".format(listDetec[0]))
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_hwp(self, strDecription):
        listDetec = self.return_found_option_and_index(strDecription, ['热水泵'])
        if listDetec[0]:
            nIndex = strDecription.find("#{0}".format(listDetec[0]))
            if nIndex < 0:
                nIndex = strDecription.find("号{0}".format(listDetec[0]))
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_higharea_sec_chwp(self, strDecription):
        listFound = self.return_found_option_and_index(strDecription, ['二级泵'])
        if listFound[0]:
            nNo = self.get_equip_no(strDecription, "#{0}".format(listFound[0]))
            if nNo < 0:
                nNo = self.get_equip_no(strDecription, "号{0}".format(listFound[0]))
                if nNo < 0:
                    return -1
            return nNo
        return -1

    def get_equip_no(self, desc, equip):
        res = -1
        lst = list()
        try:
            equipIdx = desc.find(equip)
            idx = equipIdx - 1
            while idx >= 0:
                if desc[idx].isdigit():
                    lst.append(desc[idx])
                    idx -= 1
                else:
                    break
            lst.reverse()
            res = int(str("".join(lst)))
        except:
            pass
        return res

    def is_ct(self, strDecription):
        if self.have(strDecription, ['冷却塔']):
            nIndex = strDecription.find('#冷却塔')
            if nIndex < 0:
                nIndex = strDecription.find('号冷却塔')
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDecription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_ground_source_heat_pump(self, strDescription):
        listFound = self.return_found_option_and_index(strDescription, ["热泵机组", "地源热泵"])
        if listFound[0]:
            nIndex = strDescription.find("#{0}".format(listFound[0]))
            if nIndex < 0:
                nIndex = strDescription.find("号{0}".format(listFound[0]))
                if nIndex < 0:
                    return 0
            try:
                nNo = int(strDescription[nIndex - 1])
                return nNo
            except:
                return 0
        return -1

    def is_mainpipe(self, strDescription):
        res = -1
        if self.have(strDescription, ["总管"]):
            res = 1
        return res

    def is_undefined_point(self, strDescription):
        res = False
        if strDescription in ["Miscellaneous Status", "Miscellaneous Pressure", "Miscellaneous Command"]:
            res = True
        elif self.have(strDescription, ["BINARY INPUT", "ANALOG INPUT", "ANALOG OUTPUT", "ANALOG VALUE"]):
            res = True
        return res

    def find_room_name(self, strDescription, roomDefine):
        res = ''
        if not isinstance(roomDefine, dict):
            return ""
        if not len(roomDefine.keys()):
            return ""

        if roomDefine.get("custom"):
            custom = roomDefine.get("custom")
            for key in custom.keys():
                if strDescription.find(key) >= 0:
                    res = custom.get(key)
                    break
            if res:
                return res

        if roomDefine.get("floorKeyword"):
            floorDesc = roomDefine.get("floorKeyword")
            nIndex = strDescription.find(floorDesc)
            try:
                nFloor = strDescription[:nIndex]
                res = "Floor%02d" % int(nFloor)
            except:
                res = ""

        return res


    def is_after_filter(self, strDescription, strToFilter, strAndList):
        """从注释中把strToFilter用空字符串替换后再判断注释中是否包含strAndList"""
        res = -1
        strDescription = strDescription.replace(strToFilter, "")
        if isinstance(strAndList, str):
            res = strDescription.find(strAndList)
        elif isinstance(strAndList, list):
            for item in strAndList:
                if strDescription.find(item) >= 0:
                    res = strDescription.find(item)
                    break
        return res

    def return_found_option_and_index(self, strTar, listOpt):
        """遍历listOpt，在strTar中寻找listOpt的元素，
        若找到则返回元素本身及其index"""
        res = [None, None]
        if isinstance(strTar, str) and isinstance(listOpt, list):
            for opt in listOpt:
                if strTar.find(opt) >= 0:
                    res = [opt, strTar.find(opt)]
                    break
        return res

    def is_integer(self, obj):
        res = False
        try:
            if isinstance(int(obj), int):
                res = True
        except:
            pass
        return res

