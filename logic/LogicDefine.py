# -*- encoding=utf-8 -*-
__author__ = 'murphy'

from logic.Utils import *
from logic.SQLiteOperator import SQLiteOperator as sqlite
from logic.MySQLOperator import MySQLOperator as mysql
from logic.LogOperator import LogOperator
from datetime import datetime
import importlib as myimp
import os, sys


class LogicBase:

    @staticmethod
    def makeFileAndRun(name, text):
        path = os.getcwd()
        os.chdir(path)
        file = open(('temp/%s.py' % name), 'w')
        file.write(text)
        file.close()
        module = myimp.import_module('temp.%s' % name)
        return module.main()

    @staticmethod
    def actLogic(*args, **kargs):
        """
        在该函数中调用算法，来完成指定的策略
        #Log("我是日志")，调用Log方法，将日志记录到mysql中
        :param args: 元组参数， 可不填
        :param kargs: 字典参数， 可不填
        :return: True or False
        """
        try:
            #ptList = 'AddCtMinHz'
            #start = '2017-06-08 11:00:00'
            #end = '2017-06-08 12:59:59'
            #fmt = 'm1'
            #arrHis = mysql.get_history_data(ptList, start, end, fmt)
            #return

            # generate file
            arrSqlite = []
            arrRunName = []
            strContent = '# -*- encoding=utf-8 -*-\n' \
                         'from logic.API import *\n\n'

            name = str(args[0])
            period = int(args[1])   ###
            arrSqlite = sqlite.get_formula_item(name)
            if len(arrSqlite) <= 0:
                return
            for item in arrSqlite:
                itemName = item[0]
                formula = item[1]
                formula = formula.replace('def main():', 'def main_'+itemName+'():')
                arrRunName.append(itemName)
                strContent +=  formula + '\n\n'
            strContent += 'def main():\n'
            for itemName in arrRunName:
                strContent += '    return main_' + itemName + '()\n'

            return LogicBase.makeFileAndRun(name, strContent)
        except Exception as e:
            LogOperator().writeLog('actLogic error, %s:' % (get_current_func_name()) + e.__str__(), True)
        return False
