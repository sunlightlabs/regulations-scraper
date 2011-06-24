import time
import settings
from pymongo import Connection
import os
from gevent_mongo import Mongo

def get_db():
    db_settings = getattr(settings, 'DB_SETTINGS', {})
    return Mongo(getattr(settings, 'DB_NAME', 'regulations'), settings.INSTANCES + 2, **db_settings).get_conn()

def bootstrap_settings():
    if not getattr(settings, 'DOWNLOAD_DIR', False):
        settings.DOWNLOAD_DIR = os.path.join(settings.DATA_DIR, 'downloads')
    
    if not getattr(settings, 'DUMP_DIR', False):
        settings.DUMP_DIR = os.path.join(settings.DATA_DIR, 'dumps')
