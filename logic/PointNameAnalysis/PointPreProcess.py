
class PointPreProcess:
    def __init__(self, strDescList):
        self.strDescList = strDescList
        self.listResult = list()

    def process(self):
        pass

    def process_chiller_desc(self, strDesc):
        pass



    def have(self, strAll, strOR1List):
        if isinstance(strOR1List, str):
            return strAll.find(strOR1List)>=0
        elif isinstance(strOR1List, list):
            for item in strOR1List:
                if strAll.find(item)>=0:
                    return True

        return False