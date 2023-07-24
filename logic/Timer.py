# -*- encoding=utf-8 -*-
__author__ = 'golding'

import threading, time
from datetime import datetime
from logic.LogOperator import LogOperator
from logic.Utils import *

#定时任务类，可执行周期性的任务，并可以带参数
class CronTab(threading.Thread):

    def __init__(self, name, func, params, interval=30):
        threading.Thread.__init__(self)
        self.name = name
        self.func = func
        self.params = params
        self.interval = interval
        self.last_act_time = None

    def run(self):
        while True:
            try:
                do = False
                now_time = datetime.now()
                if self.last_act_time is None:
                    do = True
                else:
                    if (now_time - self.last_act_time).total_seconds() >= self.interval:
                        do = True
                if do:
                    try:

                        r = self.func(*self.params)
                        if r:
                            strInfo = ('%s actlogic %s once successfully' % (now_time.strftime('%Y-%m-%d %H:%M:%S'), self.name))
                            LogOperator().writeLog(strInfo, False)
                        else:
                            strInfo = ('%s actlogic %s once failed' % (now_time.strftime('%Y-%m-%d %H:%M:%S'), self.name))
                            LogOperator().writeLog(strInfo, False)
                    except Exception as e:
                        strInfo = ('ERROR in %s actlogic %s: %s' % (now_time.strftime('%Y-%m-%d %H:%M:%S'), self.name, e.__str__()))
                        LogOperator().writeLog(strInfo, False)
                    self.last_act_time = now_time
                time.sleep(1)
            except Exception as e:
                LogOperator().writeLog('%s-%s:' % (self.getName(), get_current_func_name()) + e.__str__())


