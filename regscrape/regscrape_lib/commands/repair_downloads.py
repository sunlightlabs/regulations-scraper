#!/usr/bin/env python

MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    global os, settings, Pool
    from regscrape_lib.processing import *
    import settings
    import os
    from gevent.pool import Pool

    run_for_view_type('document views', find_views, update_view)
    run_for_view_type('attachment views', find_attachment_views, update_attachment_view)
    
def run_for_view_type(view_label, find_func, update_func):
    print 'Checking download of %s.' % view_label
    
    views = find_func(downloaded=True, query=settings.FILTER)
    
    # keep the decoders busy with tasks as long as there are more results
    for result in views:
        state = None
        error = False
        try:
            stat = os.stat(result['view']['file'])
            if stat.st_size < MIN_SIZE:
                print "Oh noes, file %s of the %s of %s is too small." % (result['view']['file'], view_label, result['doc'])
                error = True
        except OSError:
            print "Oh noes, file %s of the %s of %s isn't there." % (result['view']['file'], view_label, result['doc'])
            error = True
        
        if error:
            result['view']['downloaded'] = False
            update_func(**result)
            if stat:
                os.unlink(result['view']['file'])
    
    print 'Done with %s.' % view_label

if __name__ == "__main__":
    run()
