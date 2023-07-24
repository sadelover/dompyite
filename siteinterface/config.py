

class Config:
    DEBUG=True
    SECRET_KEY='develope'
    DATABASE='beopdata'
    HOST='localhost'
    RUN_PORT=5000

    TABLE_POINT='unit04'
    TABLE_UNIT01 = 'unit01'
    TABLE_INPUT='realtimedata_input'
    TABLE_OUTPUT='realtimedata_output'
    TABLE_OP='operation_record'
    DATABASE_REQ_INTERVAL=3
    DATABASE_RECONNECT_INTERVAL=7200
    USERNAME='dompysite'
    PASSWORD='DOM.cloud-2016'
    INIT_CONNECTIONS_POOL=20
    DB_POOL_NAME='DOMDBPool'
    S3DB_DIR_CLOUD=''
    S3DB_NAME=''
    USE_4DB_FILE_FORMAT = 0
    USE_4DB_NAME = ''
    CORE_VERSION = '2.0.14'
    DB_FILE_NAME = 'domdb.4db'
    TEMPLATE_DB_FILE_NAME = "template.4db"
    TEMPLATE_DB_FILE_DIR = ""


    CORE_PATH = ''
    MODE_HISTORY = False
    MODE_HISTORY_AT_TIME = True

    REDIS_HOST="127.0.0.1"
    REDIS_PORT=6379
    REDIS_PWD=''

    ONLY_RUN_AS_SERVICE = False

config= Config()
