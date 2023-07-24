
import os



if __name__=='__main__':
    os.popen("taskkill /im domhost.exe -f")
    os.popen("taskkill /im domcore.exe -f")
    os.popen("taskkill /im domlogic.exe -f")
    os.popen("taskkill /im dompysite.exe -f")
    os.popen("taskkill /im OM.exe -f")
    os.popen("taskkill /im factory.exe -f")
    os.popen("taskkill /im domModbusClientCore.exe -f")
    os.popen("taskkill /im domModbusServer.exe -f")
    os.popen("taskkill /im domPersagyDataClientCore.exe -f")
    os.popen("taskkill /im domCloudSync.exe -f")
    os.popen("taskkill /im domSiemenseTCPCore.exe -f")

