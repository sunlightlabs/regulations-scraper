#!/usr/bin/env python

from regscrape_lib.processing import *
import os

def run():
    import subprocess, os, urlparse
    
    # initial database pass
    f = open('/data/downloads/downloads.dat', 'w')
    view_cursor = find_views(Downloaded=False)
    for result in view_cursor.find():
        f.write(result['value']['url'])
        f.write('\n')
    f.close()
    
    # download
    proc = subprocess.Popen(['puf', '-xg', '-P', '/data/downloads', '-i', '/data/downloads/downloads.dat'])
    proc.wait()
    
    # database check pass
    for result in view_cursor.find():
        filename = result['value']['view']['URL'].split('/')[-1]
        fullpath = os.path.join('/data/downloads', filename)
        
        qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
        newname = '%s.%s' % (qs['objectId'], qs['contentType'])
        newfullpath = os.path.join('/data/downloads', newname)
        
        if os.path.exists(fullpath):
            # rename file to something more sensible
            os.rename(fullpath, newfullpath)
        
        if os.path.exists(newfullpath):
            # update database record to point to file
            view = result['value']['view'].copy()
            view['Downloaded'] = True
            view['File'] = newfullpath
            view['Decoded'] = False
            update_view(result['value']['doc'], view)
    
    # cleanup
    os.unlink('/data/downloads/downloads.dat')

if __name__ == "__main__":
    run()
