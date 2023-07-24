__author__ = 'inwhile'
#!/usr/bin/env python
#-*- coding: utf-8 -*-
import redis
from siteinterface import app
import json
from datetime import datetime, date,timedelta
import time


import json
import logging

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


class RedisManager:

    _mem_rtdata = {}

    try:
        host = app.config.get('REDIS_HOST')
        port = app.config.get('REDIS_PORT')
        pwd = app.config.get('REDIS_PWD')
        #连接时通过password参数指定AUTH信息，由user,pwd通过":"拼接而成
        _rm = redis.StrictRedis(host=host, port=port, password=pwd, socket_timeout=15, socket_connect_timeout=15)
        #_rm = redis.StrictRedis(host='localhost', port=6379, db=0)
    except Exception as e:
        print('[IMPORTANT]ERROR init redis connection ' + e.__str__())


    @classmethod
    def is_alive(cls):
        try:
            rt = RedisManager._rm.get('heatbeat_time')
        except Exception as e:
            return False
        return True

    @classmethod
    def get(self, key):
        value = None
        try: 
            rt = RedisManager._rm.get(key)
            if rt:
                value = json.loads(rt.decode())
        except Exception as e:
            logging.error('in RedisManager:: get %s:' % ( e.__str__()))
        return value

    @classmethod
    def mget(self, keyList):
        valueList = []
        try:
            rtList = RedisManager._rm.mget(keyList)
            for rt in rtList:
                if rt is not None:
                    value = json.loads(rt.decode())
                    valueList.append(value)
                else:
                    valueList.append(None)
        except Exception as e:
            logging.error('in RedisManager:: mget %s:' % (e.__str__()))
        return valueList

    @classmethod
    def get_all_keys(cls, ):
        strkeyList = []
        try:
            keyList = RedisManager._rm.keys()
            for item in keyList:
                strkeyList.append(item.decode())
        except Exception as e:
            logging.error('in RedisManager:: get %s:' % (e.__str__()))
        return strkeyList

    @classmethod
    def set(self, key, value):
        rt = False
        try:
            rt = RedisManager._rm.set(key, json.dumps(value ,ensure_ascii=False, cls=CJsonEncoder))
        except Exception as e:
            print('ERROR in RedisManager::set ' + e.__str__())
        return rt

    @classmethod
    def delete(self, key):
        rt = False
        try:
            rt = RedisManager._rm.delete(key)
        except Exception as e:
            print('ERROR in RedisManager::delete ' + e.__str__())
        return rt


    @classmethod
    def get_realtime_data_update_time_string(cls):
        try:
            jsonDict =  cls.get('realtime_data_update_time')
            return jsonDict.get('time')
        except:
            return None



    @classmethod
    def get_realtime_data(cls):
        return cls.get('realtime_data')

    @classmethod
    def set_realtime_data(cls, data):
        cls.set('realtime_data', data)
        return True

    @classmethod
    def get_history_data_minutes_all_points(cls, tTime):
        if not cls.is_alive():
            return None

        strTime = tTime.strftime('%Y_%m_%d_%H_%M_%S')
        strKeyName = 'HIS_MINUTE__%s' % (strTime)
        curValue = cls.get(strKeyName)
        if curValue is None:
            return None

        return curValue

    @classmethod
    def get_history_data_minutes(cls, tTime,  pointNameList):
        if not cls.is_alive():
            return None

        strTime = tTime.strftime('%Y_%m_%d_%H_%M_%S')
        strKeyName = 'HIS_MINUTE__%s' % (strTime)
        curValue = cls.get(strKeyName)
        if curValue is None:
            return None

        if not curValue:
            return [None]*len(pointNameList)

        strValueList =  []
        for item in pointNameList:
            try:
                strValue =  curValue.get(item, None)
            except:
                strValue = None
            strValueList.append(strValue)

        return strValueList

    @classmethod
    def del_history_data_minutes_keys(cls, tFrom, tTo):
        if not cls.is_alive():
            return None

        tCur = tFrom
        while tCur<=tTo:
            strTime = tCur.strftime('%Y_%m_%d_%H_%M_00')
            strKeyName = 'HIS_MINUTE__%s' % (strTime)
            nDelCount = cls._rm.delete(strKeyName)
            tCur+=timedelta(minutes=1)

        return True

    @classmethod
    def del_history_data_minutes_keys_of_date(cls, tDate):
        if not cls.is_alive():
            return None

        strTime = tDate.strftime('%Y_%m_%d_*')
        strKeyName = 'HIS_MINUTE__%s' % (strTime)
        nDelCount = cls._rm.delete(*cls._rm.keys(pattern=strKeyName))

        return nDelCount

    @classmethod
    def set_history_data_list_minutes(cls, tTime,  pointNameList,  pointDataList):
        if len(pointNameList)==0:
            return None

        if len(pointNameList)!= len(pointDataList):
            return None

        if not cls.is_alive():
            return None

        strTime = tTime.strftime('%Y_%m_%d_%H_%M_%S')
        strKeyName = 'HIS_MINUTE__%s' % (strTime)
        curValue = cls.get(strKeyName)
        if curValue is None:
            curValue = {}
        for i in range(len(pointNameList)):
            curValue[pointNameList[i]] = pointDataList[i]

        cls.set(strKeyName, curValue)



    @classmethod
    def set_history_hour_data_list_for_one_point(cls, pointName, strTimeList,  pointDataList):

        if len(strTimeList)==0:
            return None

        if len(strTimeList)!= len(pointDataList):
            return None


        if not cls.is_alive():
            return None


        strKeyName = 'HIS##%s' % (pointName)
        curValue = cls.get(strKeyName)
        if curValue is None:
            curValue = {}
        for i in range(len(strTimeList)):
            tt = datetime.strptime(strTimeList[i], '%Y-%m-%d %H:%M:%S')
            tt = tt.replace(second=0)
            if tt> datetime.now():#避免未来查询结果也保存了
                continue
            if tt.minute==0 and tt.second==0:
                if isinstance(pointDataList[i], str) and pointDataList[i]=='':#如果是空字符串，不需要写入redis
                    pass
                else:
                    curValue[strTimeList[i]] = pointDataList[i]

        cls.set(strKeyName, curValue)

    @classmethod
    def set_history_data_list(cls, pointNameList, strTimeList,  pointDataList):
        if isinstance(pointNameList, str):
            pointNameList = [pointNameList]

        if len(strTimeList)==0:
            return None

        if len(strTimeList)!= len(pointDataList):
            return None

        if len(pointNameList)!= len(pointDataList):
            return None

        if not cls.is_alive():
            return None


        for i in range(len(strTimeList)):
            strKeyName = 'HIS##%s' % (pointNameList[i])
            curValue = cls.get(strKeyName)
            if curValue is None:
                curValue = {}
            tt = datetime.strptime(strTimeList[i], '%Y-%m-%d %H:%M:%S')
            tt = tt.replace(second=0)
            if tt> datetime.now():#避免未来查询结果也保存了
                continue
            if tt.minute==0 and tt.second==0:
                curValue[strTimeList[i]] = pointDataList[i]
            if (datetime.now()-tt).total_seconds()<=60*60*24*3: #最近三天内分钟数据也保存
                cls.set_history_data_list_minutes(tt, [pointNameList[i]], [pointDataList[i]])

            cls.set(strKeyName, curValue)

    @classmethod
    def get_history_data(cls, strPointName, tTime):
        if not cls.is_alive():
            return None

        strKeyName = 'HIS##%s' % (strPointName)
        curValue = cls.get(strKeyName)
        if curValue is None or not isinstance(curValue, dict):
            return None

        rv = curValue.get(tTime.strftime('%Y-%m-%d %H:%M:%S'))
        if rv is None:
            return None
        try:
            rvFloat = float(rv)
            rv = rvFloat
        except:
            pass
        return rv

    @classmethod
    def get_point_used_page_list(cls, strPointNameList):
        if not cls.is_alive():
            return None

        strKeyName = 'POINT_PAGE_RELATION'
        curValue = cls.get(strKeyName)
        if curValue is None or not isinstance(curValue, dict):
            return None

        allPointPageList = []
        for strPointName in strPointNameList:
            onePointPage = curValue.get(strPointName, None)
            if isinstance(onePointPage, list):
                allPointPageList.extend(onePointPage)

        les = list(set(allPointPageList))
        return les


    @classmethod
    def set_point_used_page_list(cls, allMap):
        if not cls.is_alive():
            return None

        strKeyName = 'POINT_PAGE_RELATION'
        return cls.set(strKeyName, allMap)

    @classmethod
    def append_image_id_list_project(cls, nID):
        if not cls.is_alive():
            return None

        try:
            dictImages = cls.get('image_id_list_project')
            strIDList = dictImages.get('idList')
            if isinstance(strIDList, list):
                strIDList.append(nID)
                cls.set('image_id_list_project', dict(idList=strIDList))
        except Exception as e:
            logging.error('ERROR in RedisManager::append_image_id_list_project:%s'%(e.__str__()))


    @classmethod
    def set_image_id_list_project(cls, nIDList):
        if not cls.is_alive():
            return None
        cls.set('image_id_list_project', dict(idList=nIDList))

    @classmethod
    def add_image_id_list_project(cls, nIdOrList):
        if not cls.is_alive():
            return None

        if not isinstance(nIdOrList, int) and not isinstance(nIdOrList, list):
            return

        if isinstance(nIdOrList, list):
            if not len(nIdOrList):
                return
        
        dCur = cls.get("image_id_list_project")
        if not isinstance(dCur, dict):
            dCur = {}

        if "idList" not in dCur.keys():
            dCur.update({"idList": []})

        if isinstance(nIdOrList, int):
            if nIdOrList not in dCur["idList"]:
                dCur["idList"].append(nIdOrList)
        elif isinstance(nIdOrList, list):
            for item in nIdOrList:
                if item not in dCur["idList"]:
                    dCur["idList"].append(item)

        cls.set('image_id_list_project', dCur)

    @classmethod
    def set_image_id_list_template(cls, strTemplateName, nIDList):
        if not cls.is_alive():
            return None

        cls.set('image_id_list_template_'+strTemplateName, dict(idList=nIDList))

    @classmethod
    def get_image_id_list_project(cls,):
        if not cls.is_alive():
            return None
        dictImages =  cls.get('image_id_list_project')
        if dictImages is not None and isinstance(dictImages, dict):
            return dictImages.get('idList', None)


    @classmethod
    def get_image_id_list_template(cls, strTemplateName):
        if not cls.is_alive():
            return None

        dictImages = cls.get('image_id_list_template_'+strTemplateName)
        if dictImages is not None and isinstance(dictImages, dict):
            return dictImages.get('idList', None)

    @classmethod
    def get_4db_points_info(cls):
        return cls.get('all_point_info')

    @classmethod
    def get_4db_page_content(cls, strPageId):
        strPageId = str(strPageId)
        return cls.get('4db_page_content_%s'%(strPageId))

    @classmethod
    def get_4db_page_content_DebugTool(cls, strPageId):
        strPageId = str(strPageId)
        return cls.get('4db_page_content_DebugTool_%s' % (strPageId))

    @classmethod
    def set_4db_page_content(cls, strPageId, jsonContent):
        strPageId = str(strPageId)
        cls.set('4db_page_content_%s'%(strPageId), jsonContent)

    @classmethod
    def set_4db_page_content_DebugTool(cls, strPageId, jsonContent):
        strPageId = str(strPageId)
        cls.set('4db_page_content_DebugTool_%s' % (strPageId), jsonContent)

    @classmethod
    def get_baidu_token(cls, ):
        return cls.get('baidu_token')

    @classmethod
    def set_baidu_token(cls, jsonContent):
        cls.set('baidu_token', jsonContent)

    @classmethod
    def set_report_start(cls, strReportFileName):
        strKey = 'report_gen_info'
        curData = cls.get(strKey)
        if curData is None:
            curData = {}

        curData[strReportFileName] = dict(startTime=datetime.now())

        cls.set(strKey, curData)

    @classmethod
    def set_report_stop(cls, strReportFileName):
        strKey = 'report_gen_info'
        curData = cls.get(strKey)
        if curData is None:
            return

        reportInfo = curData.get(strReportFileName, {})
        reportInfo.update({"stopTime": datetime.now()})
        cls.set(strKey, curData)

    @classmethod
    def set_report_process(cls, strReportFileName, nCurProgress, nTotalProgress):
        strKey = 'report_gen_info_%s' % (strReportFileName)
        curData = cls.get(strKey)
        if curData is None:
            curData = {}

        curData.update(dict(curProgress=nCurProgress, totalProgress=nTotalProgress))

        cls.set(strKey, curData)

    @classmethod
    def set_warning_config(cls, warningConfigList):
        strKey = "warning_config_all"
        cls.set(strKey, warningConfigList)

    @classmethod
    def set_api_point_data_at_time(cls, strApi, strPointName, nYear, nMonth, nDay, strTime, value):
        strKey = "HIS__{api}_{point}".format(api=strApi, point=strPointName)
        strDateTimeKey = "{year},{month:0>2d},{day:0>2d},{time}".format(year=nYear, month=nMonth, day=nDay,
                                                                        time=strTime)
        curValue = cls.get(strKey)
        if curValue is None:
            curValue = {}
        curValue.update({strDateTimeKey: value})
        cls.set(strKey, curValue)

    @classmethod
    def get_version(self):
        try:
            ver = RedisManager._rm.execute_command('INFO')['redis_version']
            return ver
        except:
            return ""

    @classmethod
    def get_key_name_list_of_pattern(cls, strPattern):
        try:
            strCmd = "KEYS {pat}".format(pat=strPattern)
            itemList = cls._rm.execute_command(strCmd)
            resList = []
            for item in itemList:
                resList.append(item.decode())
            return resList
        except:
            return []


    @classmethod
    def check_maxmemory(cls):
        curMaxMem = cls._rm.execute_command("config get maxmemory")
        if len(curMaxMem) < 2:
            logging.error("RedisManager: fail to get maxmemory")
            return

        try:
            nMaxMem = int(float(curMaxMem[1].decode("gbk")))
            if nMaxMem < 2147483648:
                cls._rm.execute_command("config set maxmemory 2147483648")
                logging.warning("RedisManager: found redis maxmemory less than 2G, had set to 2G")
            else:
                logging.warning("RedisManager: redis memory is {memo}GB, suitable.".format(memo=nMaxMem/1024/1024/1024))
        except Exception as e:
            logging.error("ERROR in RedisManager::check_maxmemory: %s" % e.__str__())

    @classmethod
    def check_maxmemory_policy(cls):
        policy = cls._rm.execute_command("config get maxmemory-policy")
        if len(policy) < 2:
            logging.error("RedisManager: fail to get check_maxmemory_policy")
            return

        try:
            strPolicy = policy[1].decode("gbk")
            if strPolicy != "allkeys-lru":
                cls._rm.execute_command("config set maxmemory-policy allkeys-lru")
                logging.warning("RedisManager: found redis maxmemory-policy is {policy}, set to allkeys-lru".format(policy=strPolicy))
            else:
                logging.warning("RedisManager: found redis maxmemory-policy is {policy}, suitable.".format(policy=strPolicy))
        except Exception as e:
            logging.error("ERROR in RedisManager::check_maxmemory_policy: %s" % e.__str__())

    @classmethod
    def check_redis_initial_settings(cls):
        if not cls.is_alive():
            logging.error("RedisManager: redis is not alive, quit")
            return True

        cls.check_maxmemory()

        cls.check_maxmemory_policy()

        cls.maintain_local_save_settings()
        return True

    @classmethod
    def disable_local_save(cls):
        try:
            cls._rm.config_set("save", "")
        except Exception as e:
            print(e.__str__())


    @classmethod
    def maintain_local_save_settings(cls):
        if not cls.is_alive():
            logging.error("RedisManager: redis is not alive, quit")
            return True

        settings = cls._rm.execute_command("config get save")
        try:
            if len(settings[1].decode("UTF-8")):
                logging.error("RedisManager:: detect local saving is on, will turn it off")
                cls.disable_local_save()
        except:
            pass

    @classmethod
    def get_local_save_status(cls):
        if not cls.is_alive():
            logging.error("RedisManager: redis is not alive, quit")
            return []

        res = []
        settings = cls._rm.execute_command("config get save")
        if isinstance(settings, list):
            for setting in settings:
                if isinstance(setting, bytes):
                    res.append(setting.decode("UTF8"))
                elif isinstance(setting, str):
                    res.append(setting)
                else:
                    res.append(setting)
        elif isinstance(settings, bytes):
            res.append(settings.decode("UTF8"))
        elif isinstance(settings, str):
            res.append(settings)
        else:
            res.append(settings)
        return res

    @classmethod
    def get_maxmemory(cls):
        curMaxMem = cls._rm.execute_command("config get maxmemory")
        if not RedisManager.is_alive():
            return []

        res = []
        if isinstance(curMaxMem, list):
            for item in curMaxMem:
                if isinstance(item, bytes):
                    res.append(item.decode("UTF8"))
                elif isinstance(item, str):
                    res.append(item)
                else:
                    res.append(item)

        elif isinstance(curMaxMem, bytes):
            res.append(curMaxMem.decode("UTF8"))
        elif isinstance(curMaxMem, str):
            res.append(curMaxMem)
        else:
            res.append(curMaxMem)
        return res

    @classmethod
    def get_maxmemory_policy(cls):
        if not RedisManager.is_alive():
            return []

        policy = cls._rm.execute_command("config get maxmemory-policy")

        res = []
        if isinstance(policy, list):
            for item in policy:
                if isinstance(item, bytes):
                    res.append(item.decode("UTF8"))
                elif isinstance(item, str):
                    res.append(item)
                else:
                    res.append(item)

        elif isinstance(policy, str):
            res.append(policy)
        elif isinstance(policy, bytes):
            res.append(policy.decode("UTF8"))
        else:
            res.append(policy)

        return res
