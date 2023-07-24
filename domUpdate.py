
import sys
from configobj import ConfigObj
import time
from datetime import datetime
import requests
import os, shutil
import progressbar
import logging
import zipfile
import json
import psutil
import win32api


def findProcess( strProcessName, pidNotHandle):
      # 获取当前计算机的pid
    for each in pidNotHandle:
        a = str(each)  # each 是class 类型 ，可用type（each） 查看类型
        # a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
        if each.name() == strProcessName:
            return each

    return None

def downloadFromWeb():
    currentPath = os.getcwd()
    tnow = datetime.now()

    fatherPath = os.path.dirname(currentPath)
    dompysitePath = os.path.join(fatherPath, 'dompysite')

    try:
        configPath = os.path.join(dompysitePath , 'config.ini')
        cf = ConfigObj(configPath, encoding='UTF8')
    except Exception as e:
        strError = 'ERROR: Read config.ini of dompysite : %s'%(e.__str__())
        print(strError)
        logging.error(strError)

    try:

        tempPath  = os.path.join(currentPath, 'temp')
        if not os.path.exists(tempPath):
            os.mkdir(tempPath)

        tempUpdatePath = os.path.join(tempPath, 'update%s'%(tnow.strftime('%Y%m%d%H%M%S')))
        if not os.path.exists(tempUpdatePath):
            os.mkdir(tempUpdatePath)

        src_dom_package = os.path.join(tempUpdatePath, 'dom-noinstall.zip')

        strURL = 'http://139.196.79.46:5000/domsoft/download/fjdsaf7aF6fdXDf5fd8af8shj/0'
        #res = requests.get(strURL)

        response = requests.request("GET", strURL, stream=True, data=None, headers=None)
        if response.ok:
            save_path = src_dom_package

            total_length = int(response.headers.get("Content-Length"))
            with open(save_path, 'wb') as f:

                widgets = ['Progress: ', progressbar.Percentage(), ' ',
                           progressbar.Bar(marker='#', left='[', right=']'),
                           ' ', progressbar.ETA(), ' ', progressbar.FileTransferSpeed()]
                pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_length).start()
                nLengthCount = 0
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        nLengthCount+= len(chunk)
                    pbar.update(nLengthCount)
                    #print('%d/%d'%(nLengthCount, total_length))
                pbar.finish()

            f.close()

            print('start to overwrite domsoft')
            logging.info('start to overwrite domsoft')

            zipf = zipfile.ZipFile(src_dom_package)

            zipf.extractall(tempUpdatePath)

            backup_path = os.path.join(tempUpdatePath, 'backup')
            if not os.path.exists(backup_path):
                os.mkdir(backup_path)

            #shutdown all processes
            pidNotHandle = list(psutil.process_iter())

            live_domhost = findProcess('domhost.exe', pidNotHandle) is not None
            live_domcore = findProcess('domcore.exe', pidNotHandle) is not None
            live_domlogic = findProcess('domlogic.exe', pidNotHandle) is not None
            live_dompysite = findProcess('dompysite.exe', pidNotHandle) is not None
            live_omsite = findProcess('omsite.exe', pidNotHandle) is not None
            live_factory = findProcess('factory.exe', pidNotHandle) is not None

            os.popen("taskkill /im domhost.exe -f")
            os.popen("taskkill /im domcore.exe -f")
            os.popen("taskkill /im domlogic.exe -f")
            os.popen("taskkill /im dompysite.exe -f")
            os.popen("taskkill /im omsite.exe -f")
            os.popen("taskkill /im factory.exe -f")

            time.sleep(5)

            softBackupList = ['core', 'omsite', 'factory']
            for soft in softBackupList:
                src_domsoft = os.path.join(tempUpdatePath,soft)
                des_domsoft = os.path.join(fatherPath, soft)
                backup_domsoft = os.path.join(backup_path, soft)

                if os.path.exists(des_domsoft):
                    print('backup %s start'%(soft))
                    logging.info('backup %s start' % (soft))
                    try:
                        shutil.copytree(des_domsoft, backup_domsoft)

                    except Exception as e:
                        strError = 'ERROR in backup files: %s' % (e.__str__())
                        print(strError)
                        logging.error(strError)
                    print('backup %s finished' % (soft))
                    print('upgrade %s start'%(soft))

                if os.path.exists(src_domsoft):
                    try:
                        shutil.rmtree(des_domsoft)
                        shutil.copytree(src_domsoft, des_domsoft)
                    except Exception as e:
                        strError = 'ERROR in upgrade files: %s' % (e.__str__())
                        print(strError)
                        logging.error(strError)
                    print('upgrade %s finished' % (soft))
                    logging.info('upgrade %s finished' % (soft))

                    #os.remove(src_domsoft)

            if live_omsite:
                strExeDir = os.path.join(fatherPath, 'omsite')
                strExePath = os.path.join(strExeDir, 'OM.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart omsite')

            if live_factory:
                strExeDir = os.path.join(fatherPath, 'factory')
                strExePath = os.path.join(strExeDir, 'Factory.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart Factory')

            if live_domcore:
                strExeDir = os.path.join(fatherPath, 'core')
                strExePath = os.path.join(strExeDir, 'domcore.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart domcore')

            if live_domlogic:
                strExeDir = os.path.join(fatherPath, 'core')
                strExePath = os.path.join(strExeDir, 'domlogic.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart domlogic')

            if live_dompysite:
                strExeDir = os.path.join(fatherPath, 'core')
                strExeDir = os.path.join(strExeDir, 'dompysite')
                strExePath = os.path.join(strExeDir, 'dompysite.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart dompysite')

            if live_domhost:
                strExeDir = os.path.join(fatherPath, 'core')
                strExeDir = os.path.join(strExeDir, 'domhost')
                strExePath = os.path.join(strExeDir, 'domhost.exe')
                win32api.ShellExecute(0, 'open', strExePath, '', strExeDir, 1)
                logging.info('restart domhost')


    except Exception as e:
        strError = 'ERROR in download dom soft from web: %s'%(e.__str__())
        print(strError)
        logging.error(strError)
        return False
    return True


if __name__=='__main__':

    now = datetime.now()
    currentPath = os.getcwd()
    logPath = os.path.join(currentPath, 'log')
    if not os.path.exists(logPath):
        os.mkdir(logPath)

    logFileName = './log/errorlog_dompUpdate_%s.txt' % now.strftime('%Y-%m-%d')  #所有log都放到自己的log目录中
    logging.basicConfig(filename=logFileName, format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)

    strInfo = 'domUpdate act once'
    logging.info(strInfo)


    logging.info('download from server')
    if not downloadFromWeb():
        print('FAILED to download')
        logging.error('FAILED to download')


    height = input("Download Finished, Press any key to continue...")
