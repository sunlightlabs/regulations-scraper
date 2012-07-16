GEVENT = False

import settings
from regsdotgov.document import scrape_docket
import urllib2
import sys
import os
import traceback
from models import *
import pymongo

import multiprocessing
from Queue import Empty
from regs_common.mp_types import Counter
from regs_common.exceptions import DoesNotExist

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes.  Defaults to number of cores if not specified.")
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

def process_record(record, num_succeeded, num_failed):
    if record is None:
        return
    
    docket = None
    
    for i in range(3):
        error = None
        try:
            docket = scrape_docket(record.id)
            docket._created = record._created
            print '[%s] Scraped docket %s...' % (os.getpid(), docket.id)
            num_succeeded.increment()
            break
        except DoesNotExist:
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
        docket.scraped = 'failed'
        if error:
            print 'Scrape of %s failed because of %s' % (docket.id, str(error))
        num_failed.increment()
    
    try:
        docket.save()
    except:
        print "Warning: database save failed on document %s (scraped based on original doc ID %s)." % (docket.id, record.id)

def worker(todo_queue, num_succeeded, num_failed):
    pid = os.getpid()
    
    print '[%s] Worker started.' % pid
    
    while True:
        try:
            record = todo_queue.get(timeout=5)
        except Empty:
            print '[%s] Processing complete.' % pid
            return
        
        process_record(record, num_succeeded, num_failed)
        
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
        
    conditions = {'scraped': 'no'}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['id'] = options.docket
    to_scrape = Docket.objects(**conditions)
    
    while True:
        try:
            record = to_scrape.next()
        except pymongo.errors.OperationFailure:
            to_scrape = Docket.objects(**conditions)
            continue
        except StopIteration:
            break
            
        todo_queue.put(record)
    
    todo_queue.join()
    
    print 'Scrape complete.'
    
    print 'Scrape complete with %s successes and %s failures.' % (num_succeeded.value, num_failed.value)
    return {'scraped': num_succeeded.value, 'failed': num_failed.value}
