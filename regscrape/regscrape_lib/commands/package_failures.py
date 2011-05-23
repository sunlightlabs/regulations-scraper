#!/usr/bin/env python

from regscrape_lib.processing import *
import settings

def run():
    import subprocess, os, urlparse, json, zipfile
    view_cursor = find_views(downloaded=True, decoded=False)
    
    failures = zipfile.ZipFile(os.path.join(settings.DOWNLOAD_DIR, 'failures.zip'), 'w')
    for result in view_cursor.find():
        filename = result['value']['view']['file']
        arcname = os.path.join('failures', filename.split('/')[-1])
        failures.write(filename, arcname)
    
    failures.close()
    print 'Wrote zipfile to /data/downloads/failures.zip'
