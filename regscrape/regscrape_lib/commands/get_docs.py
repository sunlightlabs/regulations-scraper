from optparse import OptionParser
from regscrape_lib.listing import scrape_listing, get_count
from regscrape_lib.util import get_url_for_count
import settings
import collections
from selenium import webdriver
import sys
import json
import math

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-o", "--output", action="store", dest="output", default=None)
arg_parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False)

def run(options, args):
    # simple extractor of all of the document IDs in a set
    browser = getattr(webdriver, settings.BROWSER['driver'])(**(settings.BROWSER.get('kwargs', {})))
    count = get_count(browser, get_url_for_count(0), visit_first=True)
    if options.verbose:
        print 'Count is %s' % count
    
    settings.PER_PAGE = 1000
    results = collections.OrderedDict()
    
    position = 0
    last = int(math.floor(float(count - 1) / settings.PER_PAGE) * settings.PER_PAGE)
    while position <= last:
        url = get_url_for_count(position)
        
        (ids, errors) = scrape_listing(browser, url, visit_first=True, ids_only=True)
        results[url] = dict(ids=ids, errors=errors)
        if options.verbose:
            print results[url]
        
        browser.get('about:blank')
        position += settings.PER_PAGE
    
    out = open(options.output, 'w') if options.output else sys.stdout
    
    out.write(json.dumps(results))
    
    if options.output:
        out.close()
    
    browser.quit()