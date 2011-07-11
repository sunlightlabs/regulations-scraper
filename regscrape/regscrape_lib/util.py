import time
import settings
from pymongo import Connection
import os
from gevent_mongo import Mongo
import urllib2
import subprocess

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

def download_wget(url, output_file):
    proc = subprocess.Popen(['wget', '-nv', url, '-O', output_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    out = proc.communicate('')
    if 'URL:' in out[0] and os.path.exists(output_file):
        return os.stat(output_file).st_size
    elif 'ERROR' in out[0]:
        error_match = re.match('.*ERROR (\d{3}): (.*)', out[0])
        if error_match:
            error_groups = error_match.groups()
            raise urllib2.HTTPError(url, error_groups[0], error_groups[1], {}, None)
    raise Exception("Something went wrong with the download.")
