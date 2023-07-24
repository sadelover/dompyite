# -*- encoding=utf-8 -*-
__author__ = 'yan'

import inspect
from logic.SQLiteOperator import SQLiteOperator as op

#该文件提供基础的公共方法
def get_current_func_name():
    return inspect.stack()[1][3]

#写用户自定义的Log
def Log(logText):
    op.write_log(logText)