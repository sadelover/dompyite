#-*- coding: utf-8 -*-
__author__ = 'inwhile'

from siteinterface import app



#mysql数据库的连接信息
mysql_config = dict(host = 'localhost', database = app.config['DATABASE'])

#sqlite数据库的连接信息
sqlite_config = dict(host = 'localhost', database = 'D://111.s3db')

#任务的相关参数
task_config = dict(period = 1)

#心跳包相关参数
heartbeat_config = dict(cmd = 'regcmd:runLogic1', port=5000, period=60)

#http相关参数
http_config = dict(host = 'localhost', port=5000)