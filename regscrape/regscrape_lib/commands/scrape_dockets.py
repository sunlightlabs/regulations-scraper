GEVENT = False

import settings
from regscrape_lib.regs_gwt.regs_client import RegsClient
from regscrape_lib.document import scrape_docket
from pygwt.types import ActionException
import urllib2
import sys
import os
import traceback

import multiprocessing
from Queue import Empty
from regscrape_lib.mp_types import Counter

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes.  Defaults to number of cores if not specified.")

def process_record(record, client, db, num_succeeded, num_failed):
    if record is None:
        return
    
    docket = None
    
    for i in range(3):
        error = None
        try:
            docket = scrape_docket(record['_id'], client)
            print '[%s] Scraped docket %s...' % (os.getpid(), docket['_id'])
            num_succeeded.increment()
            break
        except ActionException:
            error = sys.exc_info()
            # treat like any other error
            print 'Warning: scrape failed on try %s with server exception: %s' % (i, error[1])
        except KeyboardInterrupt:
            raise
        except:
            error = sys.exc_info()
            print 'Warning: scrape failed on try %s' % i
    
    # catch errors
    if error or not docket:
        docket = record
        docket['scraped'] = 'failed'
        if error:
            print 'Scrape of %s failed because of %s' % (docket['_id'], str(error))
            docket['failure_reason'] = str(error)
        num_failed.increment()
    
    try:
        db.dockets.save(docket, safe=True)
    except:
        print "Warning: database save failed on document %s (scraped based on original doc ID %s)." % (docket['_id'], record['_id'])

def worker(todo_queue, num_succeeded, num_failed):
    pid = os.getpid()
    
    print '[%s] Worker started.' % pid
    
    from pymongo import Connection
    
    client = RegsClient()
    db = Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    while True:
        try:
            record = todo_queue.get(timeout=5)
        except Empty:
            print '[%s] Processing complete.' % pid
            return
        
        process_record(record, client, db, num_succeeded, num_failed)
        
        todo_queue.task_done()

def run(options, args):
    sys.stdout.write('Starting scrape...\n')
    sys.stdout.flush()
    
    # get workers going
    num_workers = options.multi
    
    todo_queue = multiprocessing.JoinableQueue(num_workers * 3)
    
    # set up some counters to track progress
    num_succeeded = Counter()
    num_failed = Counter()
    
    for i in range(num_workers):
        proc = multiprocessing.Process(target=worker, args=(todo_queue, num_succeeded, num_failed))
        proc.start()
    
    import pymongo
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    conditions = {'scraped': False}
    to_scrape = db.dockets.find(conditions)
    
    while True:
        try:
            record = to_scrape.next()
        except pymongo.errors.OperationFailure:
            to_scrape = db.dockets.find(conditions)
            continue
        except StopIteration:
            break
            
        todo_queue.put(record)
    
    todo_queue.join()
    
    print 'Scrape complete.'
    
    print 'Scrape complete with %s successes and %s failures.' % (num_succeeded.value, num_failed.value)
    return {'scraped': num_succeeded.value, 'failed': num_failed.value}
