import time
import settings
from pymongo import Connection
import os
from gevent_mongo import Mongo
import urllib2

def get_db():
    db_settings = getattr(settings, 'DB_SETTINGS', {})
    return Mongo(getattr(settings, 'DB_NAME', 'regulations'), settings.INSTANCES + 2, **db_settings).get_conn()

def bootstrap_settings():
    if not getattr(settings, 'DOWNLOAD_DIR', False):
        settings.DOWNLOAD_DIR = os.path.join(settings.DATA_DIR, 'downloads')
    
    if not getattr(settings, 'DUMP_DIR', False):
        settings.DUMP_DIR = os.path.join(settings.DATA_DIR, 'dumps')

def pump(input, output, chunk_size):
    size = 0
    while True:
        chunk = input.read(chunk_size)
        if not chunk: break
        output.write(chunk)
        size += len(chunk)
    return size

def download(url, output_file, post_data=None, headers=None):
    transfer = urllib2.urlopen(urllib2.Request(url, post_data, headers if headers else {}))
    
    out = open(output_file, 'wb')
    size = pump(transfer, out, 16 * 1024)
    out.close()
    
    return size
