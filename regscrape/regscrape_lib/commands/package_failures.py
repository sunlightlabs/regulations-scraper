#!/usr/bin/env python

from regscrape_lib.processing import *

def run():
    import subprocess, os, urlparse, json, zipfile
    view_cursor = find_views(Downloaded=True, Decoded=False)
    
    failures = zipfile.ZipFile('/data/downloads/failures.zip', 'w')
    for result in view_cursor.find():
        filename = result['value']['view']['File']
        arcname = os.path.join('failures', filename.split('/')[-1])
        failures.write(filename, arcname)
    
    failures.close()
    print 'Wrote zipfile to /data/downloads/failures.zip'