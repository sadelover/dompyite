
import sys
from configobj import ConfigObj
import time
from datetime import datetime
import requests
import os, shutil
import progressbar
import logging

def downloadFromFTP():
    currentPath = os.getcwd()

    fatherPath = os.path.dirname(currentPath)
    dompysitePath = os.path.join(fatherPath, 'dompysite')

    try:
        configPath = os.path.join(dompysitePath , 'config.ini')
        cf = ConfigObj(configPath, encoding='UTF8')
        strProjectName = cf['cloud']['projectname']
    except:
        strError = 'No projectname info found in config.ini(%s). cloud data upload canceled.'%(configPath)
        print(strError)
        logging.error(strError)

        return False

    try:

        tempPath  = os.path.join(currentPath, 'temp')
        if not os.path.exists(tempPath):
            os.mkdir(tempPath)

        src_4db = os.path.join(tempPath, 'domdbtemp%s.dbtemp'%(datetime.now().strftime('%Y%m%d%H%M%S')))

        strURL = 'http://139.196.79.46:5000/4db/download/%s/fjdsaf7aF6fdXDf5fd8af8shj'%(strProjectName)
        #res = requests.get(strURL)

        response = requests.request("GET", strURL, stream=True, data=None, headers=None)
        if response.ok:
            save_path = src_4db

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

            print('start to overwrite domdb.4db')

            des_4db = os.path.join(fatherPath, 'domdb.4db')
            if os.path.exists(des_4db):

                strPathBackup = os.path.join(fatherPath, 'backupdb')
                if not os.path.exists(strPathBackup):
                    os.mkdir(strPathBackup)
                strBackup4dbFileName = 'domdb%s.4db'%(datetime.now().strftime('%Y%m%d%H%M%S'))
                strInfo = 'found domdb.4db current exsiting, backup it into backupdb directory as %s' % (
                    strBackup4dbFileName)
                print(strInfo)
                shutil.copy(des_4db, os.path.join(strPathBackup, strBackup4dbFileName))
            shutil.copy(src_4db, des_4db)
            os.remove(src_4db)
    except Exception as e:
        strError = 'ERROR in downloadFromFTP: %s'%(e.__str__())
        print(strError)
        logging.error(strError)
        return False
    return True


def uploadToFTP():
    currentPath = os.getcwd()

    fatherPath = os.path.dirname(currentPath)
    dompysitePath = os.path.join(fatherPath, 'dompysite')

    try:
        configPath = os.path.join(dompysitePath, 'config.ini')
        cf = ConfigObj(configPath, encoding='UTF8')
        strProjectName = cf['cloud']['projectname']
    except:
        strError = 'No projectname info found in config.ini(%s). cloud data upload canceled.' % (configPath)
        print(strError)

        return False

    des_4db = os.path.join(fatherPath, 'domdb.4db')
    strURL = 'http://139.196.79.46:5000/4db/upload/%s/fjdsaf7aF6fdXDf5fd8af8shj' % (strProjectName)

    print('Uploading...')
    files = {'file': open(des_4db, 'rb')}
    rv = requests.post(strURL, files=files)

    if rv.ok:
        return True
    else:
        strError = 'ERROR in upload : request not return ok'
        print(strError)
        logging.error(strError)

    return False


if __name__=='__main__':

    now = datetime.now()
    currentPath = os.getcwd()
    logPath = os.path.join(currentPath, 'log')
    if not os.path.exists(logPath):
        os.mkdir(logPath)

    logFileName = './log/errorlog_dompDownload_%s.txt' % now.strftime('%Y-%m-%d')  #所有log都放到自己的log目录中
    logging.basicConfig(filename=logFileName, format='%(asctime)s:%(levelname)s:%(message)s', level=logging.ERROR)

    strInfo = 'domDownload act once'
    logging.error(strInfo)


    logging.error('download from server')
    if not downloadFromFTP():
        print('FAILED to download')
        logging.error('FAILED to download')
    else:
        print('Upload Successfully!')
        logging.error('Upload Successfully!')

    height = input("Download Finished, Press any key to continue...")



    time.sleep(30)