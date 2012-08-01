GEVENT = False

import settings
from regs_models import *
from regsdotgov.document import scrape_document
import urllib2, urllib3
import sys
import os
import traceback
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

def process_record(record, num_succeeded, num_failed, cpool):
    if record is None:
        return
    
    new_doc = None
    
    for i in range(3):
        error = None
        removed = False
        try:
            new_doc = scrape_document(record.id, cpool)
            new_doc.last_seen = record.last_seen
            print '[%s] Scraped doc %s...' % (os.getpid(), new_doc.id)

            if record.views:
                new_doc.views = record.views

            if record.attachments:
                new_doc.attachments = record.attachments

            num_succeeded.increment()
            break
        except DoesNotExist:
            print "Document %s appears to have been deleted; skipping." % record.id
            removed = True
            break
        except KeyboardInterrupt:
            raise
        except:
            print 'Warning: scrape failed on try %s' % i
            error = sys.exc_info()
            traceback.print_tb(error[2], file=sys.stdout)
    
    # catch renames of documents
    if new_doc and (not error) and (not removed) and new_doc.id != record.id:
        renamed_to = new_doc.id
        new_doc = Doc.objects(id=record.id)[0]
        new_doc.scraped = 'yes'
        new_doc.attachments = []
        new_doc.views = []
        new_doc.details['renamed_to'] = renamed_to
        new_doc.renamed = True
    
    # catch errors and removes
    if removed:
        num_failed.increment()
        return None
    elif error or not new_doc:
        new_doc = Doc.objects(id=record.id)[0]
        new_doc.scraped = 'failed'
        if error:
            print 'Scrape of %s failed because of %s' % (new_doc.id, str(error))
        num_failed.increment()
    
    try:
        new_doc.save()
    except:
        print "Warning: database save failed on document %s (scraped based on original doc ID %s)." % (new_doc.id, record.id)
        traceback.print_exc()

def worker(todo_queue, num_succeeded, num_failed):
    pid = os.getpid()
    cpool = urllib3.PoolManager(maxsize=2)
    
    print '[%s] Worker started.' % pid
            
    while True:
        record = Doc._from_son(todo_queue.get())
        
        process_record(record, num_succeeded, num_failed, cpool)
        
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
    
    processes = []
    for i in range(num_workers):
        proc = multiprocessing.Process(target=worker, args=(todo_queue, num_succeeded, num_failed))
        proc.start()
        processes.append(proc)
    
    conditions = {'scraped': 'no', 'deleted': False, 'source': 'regulations.gov'}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['docket_id'] = options.docket
    to_scrape = Doc.objects(**conditions).only('id', 'last_seen', 'views', 'attachments')
    
    while True:
        try:
            record = to_scrape.next()
        except pymongo.errors.OperationFailure:
            to_scrape = Doc.objects(**conditions).only('id', 'last_seen', 'views', 'attachments')
            continue
        except StopIteration:
            break
            
        todo_queue.put(record.to_mongo())
    
    todo_queue.join()
    
    for proc in processes:
        print 'Terminating worker %s...' % proc.pid
        proc.terminate()
    
    print 'Scrape complete with %s successes and %s failures.' % (num_succeeded.value, num_failed.value)
    return {'scraped': num_succeeded.value, 'failed': num_failed.value}
