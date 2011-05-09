#!/usr/bin/env python

from optparse import OptionParser 

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-c", "--continue", action="store_true", dest="continue_scrape", default=False)

def run(options, args):
    from gevent.monkey import patch_all
    patch_all()
    
    from regscrape_lib.actors import MasterActor
    import time
    
    import settings
    
    if settings.BROWSER['driver'] == 'Chrome':
        from regscrape_lib.monkey import patch_selenium_chrome
        patch_selenium_chrome()
    
    if options.continue_scrape:
        settings.CLEAR_FIRST = False
    
    master = MasterActor.start(settings.INSTANCES)
    master.send_request_reply({'command': 'scrape', 'max': settings.MAX_RECORDS})
    while True:
        time.sleep(60)
        master.send_one_way({'command': 'tick'})
