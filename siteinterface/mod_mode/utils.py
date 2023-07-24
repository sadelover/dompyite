
import os
from datetime import datetime


def log_info_to_file(strLogFileName, strLogInfo):
    strLogPath = os.path.join(os.getcwd(), 'log')
    strLogFilePath = os.path.join(strLogPath, strLogFileName)

    tNow = datetime.now()
    with open(strLogFilePath, 'a+') as f:
        f.write(tNow.strftime('%Y-%m-%d %H:%M:%S')+ '    ' + strLogInfo + '\n')