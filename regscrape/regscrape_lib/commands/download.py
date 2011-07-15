#!/usr/bin/env python

from regscrape_lib.processing import *
from regscrape_lib.util import download, download_wget
import settings
import subprocess, os, urlparse, sys, traceback, datetime
from gevent.pool import Pool
import urllib2
import pymongo

MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    run_for_view_type('document views', find_views, update_view)
    run_for_view_type('attachment views', find_attachment_views, update_attachment_view)

def get_downloader(result, update_func):
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
            start = datetime.datetime.now()
            size = download_wget(result['view']['url'], newfullpath)
            download_succeeded = True
            elapsed = datetime.datetime.now() - start
        except urllib2.HTTPError as e:
            print 'Download of %s failed due to error %s.' % (result['view']['url'], e.code)
            result['view']['downloaded'] = "failed"
            result['view']['failure_reason'] = e.code
            update_func(**result)
        except:
            exc = sys.exc_info()
            print traceback.print_tb(exc[2])
        
        if download_succeeded and size >= MIN_SIZE:
            # print status
            ksize = int(round(size/1024.0))
            print 'Downloaded %s: %sk in %s seconds (%sk/sec)' % (result['view']['url'], ksize, elapsed.seconds, round(float(ksize)/elapsed.seconds * 10)/10 if elapsed.seconds > 0 else '--')
            
            # update database record to point to file
            result['view']['downloaded'] = True
            result['view']['file'] = newfullpath
            result['view']['decoded'] = False
            update_func(**result)
    
    return download_view

def run_for_view_type(view_label, find_func, update_func):
    print 'Preparing download of %s.' % view_label
    
    views = find_func(downloaded=False, query=settings.FILTER)
    workers = Pool(getattr(settings, 'DOWNLOADERS', 5))
    
    # keep the decoders busy with tasks as long as there are more results
    while True:
        try:
            result = views.next()
        except pymongo.errors.OperationFailure:
            # occasionally pymongo seems to lose track of the cursor for some reason, so reset the query
            views = find_func(downloaded=False, query=settings.FILTER)
            continue
        except StopIteration:
            break
        
        workers.spawn(get_downloader(result, update_func))
    
    workers.join()
    print 'Done with %s.' % view_label

if __name__ == "__main__":
    run()
