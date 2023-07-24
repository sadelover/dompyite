# -*- coding: utf-8 -*-


from siteinterface.BEOPSqliteAccess import BEOPSqliteAccess
from siteinterface.ReportTool import eval_string_expression_strict
from datetime import datetime, timedelta
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface import app
import sys, os, logging


def calculation_repair_history(timeFrom, timeTo, period, strPointNameList=[]):
    strTimeFrom = timeFrom + ' 00:00:00'
    strTimeTo = timeTo + ' 23:59:59'
    tTimeFrom = datetime.strptime(strTimeFrom, '%Y-%m-%d %H:%M:%S')
    tTimeTo = datetime.strptime(strTimeTo, '%Y-%m-%d %H:%M:%S')
    if tTimeTo> datetime.now():
        tTimeTo = datetime.now()
        tTimeTo = tTimeTo.replace(second=0)

    calculationPointList = BEOPSqliteAccess.getInstance('calculation_repair_history').GetVPointCalculationList()
    filteredCalculationPointList = []
    if strPointNameList:
        for item in calculationPointList:
            if item.get('name') in strPointNameList:
                filteredCalculationPointList.append(item)
                continue
    else:
        filteredCalculationPointList = calculationPointList

    if len(filteredCalculationPointList)==0:
        print('ERROR: Calculation PointName List not exist:%s'%( str(strPointNameList)))
        return

    tCur = tTimeFrom
    tDelta = timedelta(hours=1)
    if period=='m5':
        tDelta = timedelta(minutes=5)
    elif period=='m1':
        tDelta = timedelta(minutes=1)
    elif period=='d1':
        tDelta = timedelta(days=1)

    nCount = 0
    while tCur<=tTimeTo:

        app.config['MODE_HISTORY_AT_TIME'] = tCur
        allData = BEOPDataAccess.getInstance().get_history_data_all_one_moment_padded( tCur.strftime('%Y-%m-%d %H:%M:%S'), 'm1')

        pnameList = []
        pvalueList = []
        for pp in filteredCalculationPointList:
            print('Repair PointName(%s) history at %s' % (pp.get('name'),  tCur.strftime('%Y-%m-%d %H:%M:%S')))
            strEvaResult = eval_string_expression_strict(pp.get('expression'), '2', tCur.strftime('%Y-%m-%d %H:%M:%S'), allData)
            if strEvaResult is not None:
                pnameList.append(pp.get('name'))
                pvalueList.append(strEvaResult)
                print('%s set %s -> %s'%(tCur.strftime('%Y-%m-%d %H:%M:%S'),pp.get('name'), strEvaResult ))
                insertResult = BEOPDataAccess.getInstance().insert_history_data(pp.get('name'), tCur.strftime('%Y-%m-%d %H:%M:%S'), strEvaResult, 'CAL_REPAIR', '')
                nCount+=1
            else:
                strError = 'ERROR in calculation_repair_history: eval_string_expression_strict return None, Expression: %s'%(pp.get('expression'))
                print(strError)
                logging.error(strError)

        tCur = tCur+ tDelta

    return nCount


if __name__ == "__main__":
    print('VERSION: 0.0.4')
    if len(sys.argv)<4:
        input('命令参数不足，运行命令形如: domRepairCalculationHistory.exe 2019-01-01 2019-01-02 h1')
    else:
        strTimeFrom = sys.argv[1]
        strTimeTo = sys.argv[2]
        strPeriod = sys.argv[3]
        strPointNameList = []
        if len(sys.argv)>=5:
            for i in range(4, len(sys.argv)):
                strPointName = sys.argv[i]
                strPointNameList.append(strPointName)

        app.config['MODE_HISTORY'] = True
        app.config['INIT_CONNECTIONS_POOL'] = 1

        currentPath = os.getcwd()
        fatherPath = os.path.dirname(currentPath)
        app.config.update(dict(CORE_PATH=fatherPath))
        app.config.update(dict(USE_4DB_FILE_FORMAT=1, USE_4DB_NAME = os.path.join(fatherPath, 'domdb.4db')))

        print('开始补计算%d个点的历史数据'%(len(strPointNameList)))
        calculation_repair_history(strTimeFrom, strTimeTo, strPeriod, strPointNameList)

    input('Repair finished, press any key to quit...')