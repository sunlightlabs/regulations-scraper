#!/usr/bin/env python

from regscrape_lib.processing import *
import os
import settings
import subprocess, os, urlparse
from gevent.pool import Pool

MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    run_for_view_type('document views', find_views, update_view)
    run_for_view_type('attachment views', find_attachment_views, update_attachment_view)

def get_downloader(result):
    def download_view():
        print 'Downloading %s...' % result['view']['url']
        filename = result['view']['url'].split('/')[-1]
        fullpath = os.path.join(settings.DOWNLOAD_DIR, filename)
        
        qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
        newname = '%s.%s' % (qs['objectId'], qs['contentType'])
        newfullpath = os.path.join(settings.DOWNLOAD_DIR, newname)
        
        download_succeeded = False
        size = 0
        try:
            size = download(result['view']['url'], newfullpath)
            download_succeeded = True
        except:
            pass
        
        if download_succeeded and size >= MIN_SIZE:
            # update database record to point to file
            result['view']['downloaded'] = True
            result['view']['file'] = newfullpath
            result['view']['decoded'] = False
            update_func(**result)
    
    return download_view

def run_for_view_type(view_label, find_func, update_func):
    print 'Preparing download of %s.' % view_label
    
    views = find_func(downloaded=False, query=settings.FILTER)
    workers = Pool(getattr(settings, 'DOWNLOADERS', 20))
    
    # keep the decoders busy with tasks as long as there are more results
    while True:
        try:
            result = views.next()
        except StopIteration:
            break
        
        workers.spawn(get_downloader(result))
        workers.wait_available()
    
    workers.join()
    print 'Done with %s.' % view_label

if __name__ == "__main__":
    run()
