import sqlite3
import traceback

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class SqliteConnectionException(Exception):
    pass

class SqliteOperateException(Exception):
    pass

class SqliteManager:
    def __init__(self, db_dir):
        self.__db_dir = db_dir
        self.__conn = None
        self.__cur = None

    def __close_db(self):
        if self.__conn:
            self.__conn.close()

    def roll_back(self):
        if self.__conn:
            self.__conn.rollback()

    def __enter__(self):
        try:
            if self.__db_dir is None:
                raise SqliteConnectionException("数据库不存在")
            self.__connect_db()
        except Exception:
            self.__connect_db()
        finally:
            return self

    def __exit__(self, type, value, trace):
        if isinstance(value, Exception):
            self.__conn.rollback()
            self.__close_db()
            raise value
        else:
            self.commit()
            self.__close_db()

    def __connect_db(self):
        try:
            self.__conn = sqlite3.connect('file:///'+ self.__db_dir +'?mode=ro', uri=True )
            self.__conn.text_factory = bytes
            self.__conn.row_factory = dict_factory
            self.__cur = self.__conn.cursor()
        except SqliteConnectionException:
            self.__conn = None
            self.__cur = None
            raise Exception("数据库连接失败")

    def __handle_input_param(self, param):
        if isinstance(param, dict):
            return tuple(param.values())
        elif isinstance(param, list):
            return tuple(param)
        elif isinstance(param, tuple):
            return param
        else:
            raise SqliteOperateException("参数类型错误")

    def exec_query(self, str_sql, param=()):
        if not self.__cur or not self.__conn:
            self.__connect_db()
        exec_param = self.__handle_input_param(param)
        try:
            self.__cur.execute(str_sql, exec_param)
            res = self.__cur.fetchall()
            return res
        except Exception:
            # raise SqliteOperateException("执行异常")
            traceback.print_exc()

    def exec_none_query(self, str_sql, param=()):
        if not self.__cur or not self.__conn:
            self.__connect_db()
        exec_param = self.__handle_input_param(param)
        try:
            self.__cur.execute(str_sql, exec_param)
        except Exception:
            raise SqliteOperateException("执行异常")

    def commit(self):
        try:
            if self.__conn:
                self.__conn.commit()
        except Exception:
            raise SqliteOperateException("数据提交失败")
