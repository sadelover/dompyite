
class Config:
    DEBUG=True,
    SECRET_KEY='develope',
    DATABASE='beopdata',
    HOST='localhost',

    TABLE_POINT='unit04',
    TABLE_INPUT='realtimedata_input',
    TABLE_OUTPUT='realtimedata_output',
    TABLE_OP='operation_record',
    DATABASE_REQ_INTERVAL=3,
    DATABASE_RECONNECT_INTERVAL=7200,
    USERNAME='root',
    PASSWORD='RNB.beop-2013',
    INIT_CONNECTIONS_POOL=20,
    DB_POOL_NAME='BEOPDBPool',
    S3DB_DIR_CLOUD='',
    S3DB_NAME='',
    PORT=5000,

config= Config()
