TARGET_SERVER = 'www.regulations.gov'
INSTANCES = 6
#BROWSER = {'driver': 'Remote', 'kwargs': {'browser_name': 'Firefox'}}
BROWSER = {'driver': 'Firefox'}
DEBUG = True
DB_NAME = 'regulations'
DATA_DIR = '/data'

# settings for bulk API dumping (mode 'prepopulate')
DUMP_START = 0
DUMP_END = 3500000
DUMP_INCREMENT = 100000
MAX_WAIT = 600
CHUNK_SIZE = 10
FILTER = {}

# settings for browser-based search (mode 'search')
SEARCH = {'dct': 'PS'}
PER_PAGE = 50
MAX_RECORDS = 0
#MAX_WAIT = 600

MODE = 'prepopulate'

try:
    from local_settings import *
except:
    pass
