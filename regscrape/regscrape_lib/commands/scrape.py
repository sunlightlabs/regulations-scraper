#!/usr/bin/env python

from optparse import OptionParser
from regscrape_lib.util import get_db
import sys

# arguments
arg_parser = OptionParser()
arg_parser.add_option('-r', '--restart', action="store_true", dest="restart_scrape", default=False)
arg_parser.add_option("-c", "--continue", action="store_true", dest="continue_scrape", default=False)

def run(options, args):
    from gevent.monkey import patch_all
    patch_all()
    
    from regscrape_lib.actors import MasterActor
    import time
    
    import settings
    
    db = get_db()
    if (not options.continue_scrape) and (not options.restart_scrape) and len(db.collection_names()) > 0:
        print 'This database already contains data; please run with either --restart or --continue to specify what you want to do with it.'
        sys.exit()
        
    
    if settings.BROWSER['driver'] == 'Chrome':
        from regscrape_lib.monkey import patch_selenium_chrome
        patch_selenium_chrome()
    
    if options.continue_scrape:
        settings.CLEAR_FIRST = False
    else:
        settings.CLEAR_FIRST = True
    
    master = MasterActor.start(settings.INSTANCES)
    master.send_request_reply({'command': 'scrape', 'max': settings.MAX_RECORDS})
    while True:
        time.sleep(60)
        master.send_one_way({'command': 'tick'})
