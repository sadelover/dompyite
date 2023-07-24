
import csv, tablib
import os.path
import xlrd
from datetime import datetime, timedelta
import time


standard_time_format = '%Y-%m-%d %H:%M:%S'

from siteinterface.BEOPDataAccess import BEOPDataAccess

class ExcelFile:

    def __init__(self, *headers):
        self.headers = headers
        self.data = tablib.Dataset(headers = headers)

    def append_row(self, row):
        return self.data.append(row)


def read_warning_config_from_xlsx(strFileNameAbs):
    workbook = xlrd.open_workbook(strFileNameAbs)
    booksheet = workbook.sheet_by_index(0)
    configBoolList = list()
    nDataType = 0
    ptNameList = []
    nRowIndex = 0
    for row in range(booksheet.nrows):
        nRowIndex += 1
        if nRowIndex == 1:
            continue
        oneData = dict(hhenable=0, henable=0, lenable=0, llenable=0, hhlimit=0, hlimit= 0, llimit=0, lllimit=0, pointname='', hhinfo='',
                       hinfo='', linfo='', llinfo ='', type='',boolWarningInfo='', boolWarningLevel='',  warningGroup='', ofPosition = '', ofSystem = '', ofDepartment= '', ofGroup='', id=-1, tag='', script='',
                       unitproperty01 = '', unitproperty02 = '', unitproperty03 = '', unitproperty04 = '', unitproperty05 = '')
        try:
            if isinstance(booksheet.cell(row, 0).value, str) and len(booksheet.cell(row, 0).value)==0:
                continue
            oneData['type'] = 1
            oneData['id'] = int(booksheet.cell(row, 0).value)
            oneData['pointname'] = booksheet.cell(row, 1).value
            oneData['boolWarningInfo'] = booksheet.cell(row, 2).value
            oneData['boolWarningLevel'] = booksheet.cell(row, 3).value
            oneData['ofPosition'] = booksheet.cell(row, 4).value
            oneData['ofSystem'] = booksheet.cell(row, 5).value
            oneData['ofDepartment'] = booksheet.cell(row, 6).value
            oneData['ofGroup'] = booksheet.cell(row, 7).value
            oneData['tag'] = booksheet.cell(row, 8).value
            oneData['unitproperty01'] = booksheet.cell(row, 9).value
            oneData['unitproperty02'] = booksheet.cell(row, 10).value
            oneData['unitproperty03'] = booksheet.cell(row, 11).value
            oneData['unitproperty04'] = booksheet.cell(row, 12).value
            oneData['unitproperty05'] = booksheet.cell(row, 13).value

            configBoolList.append(oneData)
        except Exception as e:
            print('ERROR in read_warning_config_from_xlsx:%s'%(e.__str__()))

    booksheet = workbook.sheet_by_index(1)
    configRangeList = list()
    nDataType = 0
    ptNameList = []
    nRowIndex = 0
    for row in range(booksheet.nrows):
        nRowIndex += 1
        if nRowIndex == 1:
            continue
        oneData = dict(hhenable=0, henable=0, lenable=0, llenable=0, hhlimit=0, hlimit= 0, llimit=0, lllimit=0,
                       pointname='', hhinfo='',
                       hinfo='', linfo='', llinfo='', type='', boolWarningInfo='', boolWarningLevel='', warningGroup='',
                       ofPosition='', ofSystem='', ofDepartment='', ofGroup='', id=-1, tag='', script='',
                       unitproperty01='', unitproperty02='', unitproperty03='', unitproperty04='', unitproperty05='')

        oneData['type']=0 #0:highlow

        if isinstance(booksheet.cell(row, 0).value, str) and len(booksheet.cell(row, 0).value) == 0:
            continue

        try:
            oneData['id'] = int(booksheet.cell(row, 0).value)
        except:
            continue
        oneData['pointname'] = booksheet.cell(row, 1).value
        try:
            fv= float(booksheet.cell(row, 2).value)
            oneData['henable'] = 1
        except:
            fv = 0
        oneData['hlimit'] = fv
        oneData['hinfo'] = booksheet.cell(row, 3).value
        try:
            fv = float(booksheet.cell(row, 4).value)
            oneData['lenable'] = 1
        except:
            fv = 0
        oneData['llimit'] = fv
        oneData['linfo'] = booksheet.cell(row, 5).value
        oneData['boolWarningLevel'] = booksheet.cell(row, 6).value
        oneData['ofPosition'] = booksheet.cell(row, 7).value
        oneData['ofSystem'] = booksheet.cell(row, 8).value
        oneData['ofDepartment'] = booksheet.cell(row, 9).value
        oneData['ofGroup'] = booksheet.cell(row, 10).value
        oneData['tag'] = booksheet.cell(row, 11).value
        oneData['unitproperty01'] = booksheet.cell(row, 12).value
        oneData['unitproperty02'] = booksheet.cell(row, 13).value
        oneData['unitproperty03'] = booksheet.cell(row, 14).value
        oneData['unitproperty04'] = booksheet.cell(row, 15).value
        oneData['unitproperty05'] = booksheet.cell(row, 16).value

        configRangeList.append(oneData)

    booksheet = workbook.sheet_by_index(2)
    configRuleList = list()
    nDataType = 0
    ptNameList = []
    nRowIndex = 0
    for row in range(booksheet.nrows):
        nRowIndex += 1
        if nRowIndex == 1:
            continue

        oneData = dict(hhenable=0, henable=0, lenable=0, llenable=0, hhlimit=0, hlimit= 0, llimit=0, lllimit=0,
                       pointname='', hhinfo='',
                       hinfo='', linfo='', llinfo='', type='', boolWarningInfo='', boolWarningLevel='', warningGroup='',
                       ofPosition='', ofSystem='', ofDepartment='', ofGroup='', id=-1, tag='', script='',
                       unitproperty01='', unitproperty02='', unitproperty03='', unitproperty04='', unitproperty05='')

        if isinstance(booksheet.cell(row, 0).value, str) and len(booksheet.cell(row, 0).value) == 0:
            continue

        oneData['type'] = 3
        oneData['id'] = int(booksheet.cell(row, 0).value)
        oneData['pointname'] = booksheet.cell(row, 1).value
        oneData['script'] = booksheet.cell(row, 2).value
        oneData['boolWarningInfo'] = booksheet.cell(row, 3).value
        oneData['boolWarningLevel'] = booksheet.cell(row, 4).value
        oneData['ofPosition'] = booksheet.cell(row, 5).value
        oneData['ofSystem'] = booksheet.cell(row, 6).value
        oneData['ofDepartment'] = booksheet.cell(row, 7).value
        oneData['ofGroup'] = booksheet.cell(row, 8).value
        oneData['tag'] = booksheet.cell(row, 9).value
        oneData['infoDetail'] = booksheet.cell(row, 10).value
        oneData['unitproperty01'] = booksheet.cell(row, 11).value
        oneData['unitproperty02'] = booksheet.cell(row, 12).value
        oneData['unitproperty03'] = booksheet.cell(row, 13).value
        oneData['unitproperty04'] = booksheet.cell(row, 14).value
        oneData['unitproperty05'] = booksheet.cell(row, 15).value

        configRuleList.append(oneData)
    return (configBoolList, configRangeList, configRuleList)


def read_xlsx(strFileName):
    strPath = os.getcwd()
    strFilePath = os.path.join(strPath, 'data')
    strFileNameAbs = os.path.join(strFilePath, strFileName)
    workbook = xlrd.open_workbook(strFileNameAbs)
    booksheet = workbook.sheet_by_index(0)
    p = list()
    nDataType= 0  #0表示导入的excel是格式0号表格类型：总共三列，每行是：时间、点名、值。  1号格式：可以N列，每列是时间、点名1值、点名2值。。。点名N值。2号格式是1号格式基础上增加一列时间（日期与时间分开）
    ptNameList = []
    for row in range(booksheet.nrows):
        row_data = []
        cel0 = booksheet.cell(row, 0)
        cel1 = booksheet.cell(row, 1)
        strCellValue00 = cel0.value
        if isinstance(strCellValue00, str):
            if strCellValue00 in ["标识名","名称","中文名","description","释义", "时间"]:
                continue
            strCellValue00 = strCellValue00.lower()

        if strCellValue00 == 'pointtime' or strCellValue00=='time' or strCellValue00=='时间':
            if cel1.value=='pointname' or cel1.value=="点名":
                nDataType = 0
            elif cel1.value=='pointtime'  or cel1.value=='time' or cel1.value=='时间':
                nDataType = 2 # datetime two columns
                for col in range(booksheet.ncols):
                    if col==0 or col==1:
                        continue
                    ptNameList.append(booksheet.cell(row, col).value)
            else:
                nDataType = 1
                for col in range(booksheet.ncols):
                    if col==0:
                        continue
                    ptNameList.append(booksheet.cell(row, col).value)
            continue

        pt = None
        bRowIsRealtimeData = False
        if isinstance(strCellValue00, str) and strCellValue00 in ["当期时刻", "实时", "当前", "now", "最新", "NOW", "Now", "Realtime", "realtime", "REALTIME"]:
            bRowIsRealtimeData = True
        try:
            pt = xlrd.xldate.xldate_as_datetime(cel0.value, 0)
        except Exception as ex:
            if isinstance(cel0.value, str):
                pt = analysis_time_str(cel0.value)

        if pt is None and not bRowIsRealtimeData:
            print('One Row Format not valid, ignored')
            continue


        if nDataType==0:
            cel1 = booksheet.cell(row, 1)
            cel2 = booksheet.cell(row, 2)
            if bRowIsRealtimeData:
                oneData = dict(pointtime="REALTIME", pointname=cel1.value,
                               pointvalue=str(cel2.value))
            else:
                oneData = dict(pointtime= pt.strftime(standard_time_format), pointname=cel1.value, pointvalue= str(cel2.value))
            p.append(oneData)
        elif nDataType==1:
            for col in range(booksheet.ncols):
                if col == 0:
                    continue
                if bRowIsRealtimeData:
                    oneData = dict(pointtime= "REALTIME", pointname=ptNameList[col-1], pointvalue= str(booksheet.cell(row,col).value))
                else:
                    oneData = dict(pointtime=pt.strftime(standard_time_format), pointname=ptNameList[col - 1],
                                   pointvalue=str(booksheet.cell(row, col).value))
                p.append(oneData)
        elif nDataType==2:
            pt2 = xlrd.xldate.xldate_as_datetime(cel0.value, 1)
            pt_together = datetime(pt.year, pt.month, pt.day, pt2.hour, pt2.minute, pt2.second)
            for col in range(booksheet.ncols):
                if col == 0 or col==1:
                    continue
                if bRowIsRealtimeData:
                    oneData = dict(pointtime="REALTIME", pointname=ptNameList[col - 2],
                                   pointvalue=str(booksheet.cell(row, col).value))
                else:
                    oneData = dict(pointtime= pt_together.strftime(standard_time_format), pointname=ptNameList[col-2], pointvalue= str(booksheet.cell(row,col).value))
                p.append(oneData)

    return p



def analysis_time_str(str):
    strFormatList = ['%Y-%m-%d %H:%M:%S', '%H:%M:%S %Y-%m-%d', '%H-%M-%S %Y-%m-%d',
                     '%Y-%m-%d %H:%M', '%m-%d-%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S']
    for strFormat in strFormatList:
        try:
            tempPt = datetime.strptime(str,strFormat)
            if isinstance(tempPt , datetime):
                return tempPt
        except:
            continue

    return None


def readPointsListFromExcel(filePath):
    workbook = xlrd.open_workbook(filePath)
    booksheet = workbook.sheet_by_index(0)
    p = list()
    nDataType = 0
    pointList = []
    for row in range(booksheet.nrows):
        if row==0:
            cel00 = booksheet.cell(row, 0)
            if cel00.value!='pointindex':
                return None
            continue

        onePointInfo = []
        for col in range(25):
            onePointInfo.append(booksheet.cell(row, col).value)

        pointList.append(onePointInfo)

    return pointList