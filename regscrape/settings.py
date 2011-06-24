TARGET_SERVER = 'www.regulations.gov'
DEBUG = True
DB_NAME = 'regulations'
DATA_DIR = '/data'
DECODERS = 2

DUMP_START = 0
DUMP_END = 3500000
DUMP_INCREMENT = 100000
MAX_WAIT = 600
CHUNK_SIZE = 10
FILTER = {}

INSTANCES = 2
THREADS_PER_INSTANCE = 2

try:
    from local_settings import *
except:
    pass
