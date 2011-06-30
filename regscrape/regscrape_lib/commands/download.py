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
    download_needed = False
    f = open(os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat'), 'w')
    for result in find_func(downloaded=False, query=settings.FILTER):
        f.write(result['view']['url'])
        f.write('\n')
        download_needed = True
    f.close()
    
    # stop here if there's nothing to do
    if not download_needed:
        print "No %s to download; skipping." % view_label
        os.unlink(os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat'))
        return
    
    # download
    proc = subprocess.Popen(['puf', '-xg', '-P', settings.DOWNLOAD_DIR, '-i', os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat')])
    proc.wait()
    
    # database check pass
    for result in find_func(downloaded=False, query=settings.FILTER):
        filename = result['view']['url'].split('/')[-1]
        fullpath = os.path.join(settings.DOWNLOAD_DIR, filename)
        
        qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
        newname = '%s.%s' % (qs['objectId'], qs['contentType'])
        newfullpath = os.path.join(settings.DOWNLOAD_DIR, newname)
        
        if os.path.exists(fullpath):
            # rename file to something more sensible
            os.rename(fullpath, newfullpath)
        
        if os.path.exists(newfullpath) and os.stat(newfullpath).st_size >= MIN_SIZE:
            # update database record to point to file
            result['view']['downloaded'] = True
            result['view']['file'] = newfullpath
            result['view']['decoded'] = False
            update_func(**result)
    
    # cleanup
    os.unlink(os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat'))

if __name__ == "__main__":
    run()
