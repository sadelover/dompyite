# -*- encoding=utf-8 -*-
__author__ = 'yan'

from logic.Singleton import Singleton
import logging, sys, os, threading
from datetime import datetime

#log操作类
class LogOperator(Singleton):

    _lock = threading.Lock()

    def __init__(self):
        cwd = os.getcwd()
        cwd = cwd if os.path.isdir(cwd) else os.path.dirname(cwd)
        self.log_dir = os.path.join(cwd, 'log')
        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)

    def writeLog(self, logText, toFile=True):
        with LogOperator._lock:
            sys.stdout.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' --> ' + logText)
            sys.stdout.write('\n')
            logging.basicConfig(level=logging.ERROR,
                                format=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                       # + '[%(filename)s]'
                                       # + '[%(funcName)s]'
                                       # + '[%(lineno)d]'
                                       + '-->'
                                       + '%(message)s',
                                filename=self.log_dir+'/%s.log'%(datetime.now().strftime('%Y-%m-%d'),),
                                filemode='a')
            if toFile:
                logging.error(logText)
            
