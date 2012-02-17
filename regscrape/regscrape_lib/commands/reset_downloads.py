#!/usr/bin/env python

MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    global os, settings
    from regscrape_lib.processing import *
    import os
    import settings

    run_for_view_type('document views', find_views, update_view)
    run_for_view_type('attachment views', find_attachment_views, update_attachment_view)

def run_for_view_type(view_label, find_func, update_func):
    print 'Resetting %s.' % view_label
    views = find_func(downloaded='failed', query={'deleted': False})
    
    for result in views:
        result['view']['downloaded'] = False
        update_func(**result)
    
    print 'Done with %s.' % view_label

if __name__ == "__main__":
    run()
