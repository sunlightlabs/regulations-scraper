TARGET_SERVER = 'www.regulations.gov'
PER_PAGE = 50
INSTANCES = 6
MAX_RECORDS = 0
SEARCH = {'dct': 'PS'}
MAX_WAIT = 600
# BROWSER = {'driver': 'Remote', 'kwargs': {'browser_name': 'Firefox'}}
BROWSER = {'driver': 'Firefox'}
DEBUG = True
DB_NAME = 'regulations'
DATA_DIR = '/data'

# settings for bulk API dumping
DUMP_START = 0
DUMP_END = 3500000
DUMP_INCREMENT = 100000

try:
    from local_settings import *
except:
    pass
