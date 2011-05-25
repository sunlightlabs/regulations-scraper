#!/usr/bin/env python

from regscrape_lib.processing import *
import os
import settings

def run():
    import subprocess, os, urlparse
    
    # initial database pass
    f = open(os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat'), 'w')
    view_cursor = find_views(downloaded=False, query=settings.FILTER)
    for result in view_cursor.find():
        f.write(result['value']['view']['url'])
        f.write('\n')
    f.close()
    
    # download
    proc = subprocess.Popen(['puf', '-xg', '-P', settings.DOWNLOAD_DIR, '-i', os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat')])
    proc.wait()
    
    # database check pass
    for result in view_cursor.find():
        filename = result['value']['view']['url'].split('/')[-1]
        fullpath = os.path.join(settings.DOWNLOAD_DIR, filename)
        
        qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
        newname = '%s.%s' % (qs['objectId'], qs['contentType'])
        newfullpath = os.path.join(settings.DOWNLOAD_DIR, newname)
        
        if os.path.exists(fullpath):
            # rename file to something more sensible
            os.rename(fullpath, newfullpath)
        
        if os.path.exists(newfullpath):
            # update database record to point to file
            view = result['value']['view'].copy()
            view['downloaded'] = True
            view['file'] = newfullpath
            view['decoded'] = False
            update_view(result['value']['doc'], view)
    
    # cleanup
    os.unlink(os.path.join(settings.DOWNLOAD_DIR, 'downloads.dat'))
    view_cursor.drop()

if __name__ == "__main__":
    run()
