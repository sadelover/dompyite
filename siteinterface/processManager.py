
import psutil
import os
import logging
import subprocess
import win32api
import time

class ProcessManager:
    __instance = None


    def __init__(self):
        pass

    @classmethod
    def getInstance(self):
        if(self.__instance == None):
            self.__instance = ProcessManager()
        return self.__instance

    """
    strProcessName示例: domhost.exe
    """
    def findProcess(self, strProcessName):
        pid = []
        self.pidNotHandle = list(psutil.process_iter())  # 获取当前计算机的pid
        for each in self.pidNotHandle:
            a = str(each) # each 是class 类型 ，可用type（each） 查看类型
            #a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
            if each.name() == strProcessName:
                return each

        return None

    def findProcessWithMemoryBigFirst(self, strProcessName):
        self.pidNotHandle = list(psutil.process_iter())  # 获取当前计算机的pid
        fMemoryMax = 0
        rtProcess = None
        for each in self.pidNotHandle:
            a = str(each) # each 是class 类型 ，可用type（each） 查看类型
            #a 数据样式为：psutil.Process(pid=0,name='System Idle Process')
            if each.name() == strProcessName:
                fMemoryMB = each.memory_info().rss / 1024.0 / 1024.0
                if fMemoryMB> fMemoryMax:
                    rtProcess = each
                    fMemoryMax = fMemoryMB

        return rtProcess

    """
    示例
    processExeName： domhost.exe
    workDir: d:\\dom\\core\\domhost
    """
    def startProcess(self, processExeName, workDir):
        try:
            # 需要添加两个不同的执行路径，modbusServer 和 modbusClient
            proeceePath = os.path.join(workDir, processExeName)
            # print(proeceePath)
            if os.path.exists(workDir) == False:
                logging.error("domhost寻找不到可执行文件目录，期望为 %s 目录，本次运行监护对象失败" ,workDir)
                return False
            else:
                if os.path.exists(proeceePath) ==False:
                    logging.error("domhost寻找不到监护对象可执行文件，期望为 %s 目录 %s 文件 ，本次运行监护对象失败" ,workDir, processExeName)
                    return False
                else:
                    win32api.ShellExecute(0, 'open', proeceePath, '', workDir, 1)
                    return True

        except Exception as e:
            logging.error("ERROR in startProcess({process}): {err}".format(process=processExeName, err=e.__str__()))

        return True

    def killProcess(self, strProcessNameWithExt):
        print("killing {proc}".format(proc=strProcessNameWithExt))
        try:
            if not self.findProcess(strProcessNameWithExt):
                print("no {proc} found".format(proc=strProcessNameWithExt))
                return True

            os.popen("taskkill /im %s -f" % strProcessNameWithExt)
            return True
        except Exception as e:
            logging.error("ERROR in ProcessTool::kill_process: %s" % e.__str__())
            return False

    def restartOS(self):
        try:
            os.popen("shutdown -r -f -t 0")
        except Exception as e:
            logging.error('ERROR in ProcessManager::RestartOS():' + e.__str__())
            return False

        return True

    """
    strProcessNameList: ["domlogic", "domcore", "dompysite"]
    """
    def getProcessRunningStatus(self, strProcessNameList):
        result = {}
        self.pidNotHandle = list(psutil.process_iter())
        # time.sleep(1)
        for ps in self.pidNotHandle:
            psName = None
            try:
                psName = ps.name()
            except:
                pass
            if psName == None:
                continue

            if psName.replace(".exe", "") == "OM":
                result.update({"omsite": 1})
            else:
                if psName.replace(".exe", "") in strProcessNameList:
                    result.update({psName.replace(".exe", ""): 1})

        for strProcessName in strProcessNameList:
            if result.get(strProcessName, None) == None:
                result.update({strProcessName: 0})

        return result

