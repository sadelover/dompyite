__author__ = 'g'

import threading
import time
from siteinterface.BEOPDataBufferController import *
from siteinterface.BEOPDataAccess import *


class DataSaveThread(threading.Thread):
    def run(self):
        time.sleep(5)
        vvs = BEOPDataBufferController.getInstance().getValues()
        if len(vvs)>0:
            BEOPDataAccess.getInstance().saveRealtimeDatas(vvs)
