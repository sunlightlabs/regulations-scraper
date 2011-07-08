#!/usr/bin/env python

from regscrape_lib.processing import *
import os
import settings

MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    run_for_view_type('document views', find_views, update_view)
    run_for_view_type('attachment views', find_attachment_views, update_attachment_view)

def run_for_view_type(view_label, find_func, update_func):
    import subprocess, os, urlparse
    
    print 'Preparing download of %s.' % view_label
    # initial database pass
    for result in find_func(downloaded=False, query=settings.FILTER):
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
        
        if download_succeded and size >= MIN_SIZE:
            # update database record to point to file
            result['view']['downloaded'] = True
            result['view']['file'] = newfullpath
            result['view']['decoded'] = False
            update_func(**result)

if __name__ == "__main__":
    run()
