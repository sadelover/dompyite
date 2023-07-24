
from datetime import datetime

import os
import logging

def findProcess( strProcessName, pidNotHandle):
      # 获取当前计算机的pid
    for each in pidNotHandle:
        a = str(each)  # each 是class 类型 ，可用type（each） 查看类型
        # a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
        if each.name() == strProcessName:
            return each

    return None


def searchSQLFile():
    currentPath = os.getcwd()

    # word = '.4db'
    findFileName = ''
    for filename in os.listdir(currentPath):
        fp = os.path.join(currentPath, filename)
        fp = fp.replace('\\', '/')
        fnLower = filename.lower()

        if os.path.isfile(fp) and fnLower.endswith('sql'):
            return fnLower

    return None

if __name__=='__main__':

    now = datetime.now()
    currentPath = os.getcwd()
    logPath = os.path.join(currentPath, 'log')
    if not os.path.exists(logPath):
        os.mkdir(logPath)

    logFileName = './log/errorlog_domMySQLRestore_%s.txt' % now.strftime('%Y-%m-%d')  #所有log都放到自己的log目录中
    logging.basicConfig(filename=logFileName, format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)


    strInfo = 'start to find *.sql in current path'
    print(strInfo)
    logging.error(strInfo)

    sqlfile = searchSQLFile()
    if sqlfile is None:
        height = input("Failed to restore for no SQL file found...")
    else:
        strInfo = 'Start to restore mysql database from %s, Please wait...'%(sqlfile)
        print(strInfo)
        logging.info(strInfo)
        strSQLFileName = os.path.join(currentPath, sqlfile)
        strCMD= 'mysql -u root --password=RNB.beop-2013 < "%s"'%(strSQLFileName)
        nRC = os.system(strCMD)


        height = input("Restore Finished, Press any key to continue...")
