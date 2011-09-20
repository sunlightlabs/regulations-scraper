import settings
from regscrape_lib.regs_gwt.regs_client import RegsClient
from regscrape_lib.document import scrape_document
from pygwt.types import ActionException
import urllib2
import sys
import os
import traceback

import multiprocessing
from Queue import Empty

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes.  Defaults to number of cores if not specified.")

def process_record(record, client, db):
    if record is None:
        return
    
    doc = None
    
    for i in range(3):
        error = None
        removed = False
        try:
            doc = scrape_document(record['document_id'], client)
            doc['_id'] = record['_id']
            doc['last_seen'] = record['last_seen']
            print '[%s] Scraped doc %s...' % (os.getpid(), doc['document_id'])
            break
        except ActionException:
            error = sys.exc_info()
            if 'failed to load document data' in str(error[1]):
                # this document got deleted
                print "Document %s appears to have been deleted; skipping." % record['_id']
                removed = True
                break
            else:
                # treat like any other error
                print 'Warning: scrape failed on try %s with server exception: %s' % (i, error[1])
                print traceback.print_tb(error[2])
        except KeyboardInterrupt:
            raise
        except:
            print 'Warning: scrape failed on try %s' % i
            error = sys.exc_info()
            print traceback.print_tb(error[2])
    
    # catch renames of documents
    if doc and (not error) and (not removed) and doc['document_id'] != record['document_id']:
        renamed_to = doc['document_id']
        doc = db.docs.find({'_id': record['_id']})[0]
        doc['views'] = []
        doc['scraped'] = True
        doc['renamed_to'] = renamed_to
    
    # catch errors and removes
    if removed:
        return None
    elif error or not doc:
        doc = db.docs.find({'_id': record['_id']})[0]
        doc['scraped'] = 'failed'
        if error:
            print 'Scrape of %s failed because of %s' % (doc['document_id'], str(error))
            doc['failure_reason'] = str(error)
    
    try:
        db.docs.save(doc, safe=True)
    except:
        print "Warning: database save failed on document %s (scraped based on original doc ID %s)." % (doc['document_id'], record['document_id'])

def worker(todo_queue):
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
        
        process_record(record, client, db)
        
        todo_queue.task_done()

def run(options, args):
    sys.stdout.write('Starting scrape...\n')
    sys.stdout.flush()
    
    # get workers going
    num_workers = options.multi
    
    todo_queue = multiprocessing.JoinableQueue(num_workers * 3)
    
    for i in range(num_workers):
        proc = multiprocessing.Process(target=worker, args=(todo_queue,))
        proc.start()
    
    import pymongo
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    conditions = {'scraped': False, 'deleted': False}
    fields = {'document_id': 1, 'last_seen': 1}
    to_scrape = db.docs.find(conditions, fields)
    
    while True:
        try:
            record = to_scrape.next()
        except pymongo.OperationFailure:
            to_scrape = db.docs.find(conditions, fields)
            continue
        except StopIteration:
            break
            
        todo_queue.put(record)
    
    todo_queue.join()
    
    print 'Scrape complete.'
