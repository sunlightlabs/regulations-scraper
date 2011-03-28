TARGET_SERVER = 'www.regulations.gov'
PER_PAGE = 50
INSTANCES = 6
CLEAR_FIRST = True
MAX_RECORDS = 0
SEARCH = {'dct': 'PS'}
MAX_WAIT = 600
# BROWSER = {'driver': 'Remote', 'kwargs': {'browser_name': 'Firefox'}}
BROWSER = {'driver': 'Firefox'}

try:
    from local_settings import *
except:
    pass
