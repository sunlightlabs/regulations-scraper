#!/usr/bin/env python

from regscrape_lib.processing import *

def run():
    import subprocess, os, urlparse, json
    view_cursor = find_views(Downloaded=True, Decoded=False, Type='html')
    
    for result in view_cursor.find():
        interpreter = subprocess.Popen(['html2text', result['value']['view']['File']], stdout=subprocess.PIPE)
        output, error = interpreter.communicate()
        
        if not error:
            view = result['value']['view'].copy()
            view['Decoded'] = True
            view['Text'] = output
            update_view(result['value']['doc'], view)
            print 'Decoded and saved %s' % view['URL']
        else:
            print 'Error decoding %s' % result['value']['view']['URL']

if __name__ == "__main__":
    run()
