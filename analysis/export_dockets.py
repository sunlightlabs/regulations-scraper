#!/usr/bin/env python

import sys
import os
import csv
import time
from datetime import datetime
from collections import namedtuple
from pymongo import Connection

pid = os.getpid()

DOCKETS_QUERY = {'scraped': True}

DOCKET_FIELDS = ['docket_id', 'title', 'agency', 'year']


if __name__ == '__main__':
    # set up options
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] host dbname file_prefix")
    
    (options, args) = parser.parse_args()
    
    # fetch options, args
    host = args[0]
    dbname = args[1]
    prefix = args[2]
    
    writer = csv.writer(open(sys.argv[3] + '_dockets.csv', 'w'))
    writer.writerow(DOCKET_FIELDS)
    
    cursor = Connection(host=host)[dbname].docs.find(DOCS_QUERY)
    
    run_start = time.time()
    print '[%s] Starting export...' % pid
    
    for row in cursor:
        csv.writerow([row[field] for field in DOCKET_FIELDS])
    
    print '[%s] Completed export in %s seconds.' % (pid, time.time() - run_start)
