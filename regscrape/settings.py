TARGET_SERVER = 'www.regulations.gov'
DEBUG = True
DB_NAME = 'regulations'
ES_HOST = 'thrift://localhost:9500'
ES_INDEX = 'regulations'
DATA_DIR = '/data'
EXTRACTORS = 2

DUMP_START = 0
DUMP_END = 3850000
DUMP_INCREMENT = 10000
MAX_WAIT = 600
CHUNK_SIZE = 10
FILTER = {}

INSTANCES = 2
THREADS_PER_INSTANCE = 2

SITES = ['regsdotgov', 'sec_cftc']

try:
    from local_settings import *
except:
    pass
