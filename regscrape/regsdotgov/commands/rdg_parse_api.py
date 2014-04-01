GEVENT = False

import os
import settings
import sys
from search import parse, iter_parse
import pytz
import datetime
import operator
import time
import json
import re
from regs_common.tmp_redis import TmpRedis
from regs_common.mp_types import Counter
from regs_common.util import listify
from regsdotgov.document import make_view
from regs_models import *


import multiprocessing
from Queue import Empty

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes. Defaults to number of cores if not specified.")
arg_parser.add_option("-k", "--keep-cache", dest="keep_cache", action="store_true", default=False, help="Prevents the cache from being deleted at the end of processing to make testing faster.")
arg_parser.add_option("-u", "--use-cache", dest="use_cache", action="store", default=None, help="Use pre-existing cache to make testing faster.")
arg_parser.add_option("-A", "--add-only", dest="add_only", action="store_true", default=False, help="Skip reconciliation, assume that all records are new, and go straight to the add step.")
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

FR_DOC_TYPES = set(['notice', 'rule', 'proposed_rule'])

def repair_views(old_views, new_views):
    for new_view in new_views:
        already_exists = [view for view in old_views if view.type == new_view.type]
        if not already_exists:
            old_views.append(new_view)
        elif already_exists and already_exists[0].downloaded == 'failed':
            already_exists[0].downloaded = "no"

def reconcile_process(record, cache, db, now, repaired_counter, updated_counter, deleted_counter):
    # check and see if this doc has been updated
    new_record = cache.get(record['_id'])
    if new_record:
        # do we need to fix anything?
        statuses = [[view['downloaded'] for view in record.get('views', [])]] + [[view['downloaded'] for view in attachment.get('views', [])] for attachment in record.get('attachments', [])]

        #main_views = [make_view(format) for format in listify(new_record.get('fileFormats', []))]
        
        if record['scraped'] == 'failed' or 'failed' in reduce(operator.add, statuses, []) or (record['scraped'] == 'yes' and len(record.get('attachments', [])) != new_record.get('attachmentCount', 0)):
            # needs a repair; grab the full document
            current_docs = Doc.objects(id=record['_id'])
            
            db_doc = current_docs[0]
            
            db_doc.scraped = "no"
            
            # rebuild views
            #repair_views(db_doc.views, main_views)
            
            # update the last-seen date
            db_doc.last_seen = now

            # reset a couple of flags to trigger reprocessing
            db_doc.in_search_index = False
            db_doc.in_cluster_db = False
            db_doc.entities_last_extracted = None
            
            # do save
            try:
                db_doc.save()
                repaired_counter.increment()
            except:
                print "Failed to repair %s" % db_doc.id
        else:
            # we don't need a full repair, so just do an update on the date
            Doc.objects(id=record['_id']).update_one(set__last_seen=now)
            updated_counter.increment()
        
        # either way, delete the document from the cache so we can tell what's new at the end
        cache.delete(record['_id'])
    else:
        # this document isn't in the new data anymore, so mark it deleted
        Doc.objects(id=record['_id']).update_one(set__deleted=True)
        deleted_counter.increment()

def reconcile_worker(todo_queue, cache_wrapper, now, repaired_counter, updated_counter, deleted_counter):
    pid = os.getpid()
    
    print '[%s] Reconciliation worker started.' % pid
    
    cache = cache_wrapper.get_pickle_connection()
    
    import pymongo
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    while True:
        record = todo_queue.get()
        
        reconcile_process(record, cache, db, now, repaired_counter, updated_counter, deleted_counter)
        
        todo_queue.task_done()
    
def add_new_docs(cache_wrapper, now):
    print 'Adding new documents to the database...'
    
    cache = cache_wrapper.get_pickle_connection()
    
    new = 0
    for id in cache.keys():
        doc = cache.get(id)

        if doc.get('documentStatus', None) == "Withdrawn":
            continue

        db_doc = Doc(**{
            'id': doc['documentId'],
            'title': unicode(doc.get('title', '')),
            'docket_id': doc['docketId'],
            'agency': doc['agencyAcronym'],
            'type': DOC_TYPES[doc['documentType']],
            'fr_doc': DOC_TYPES[doc['documentType']] in FR_DOC_TYPES,
            'last_seen': now,
            'created': now
        })
        
        try:
            db_doc.save()
            new += 1
        except:
            print "Failed to save document %s" % db_doc.id
    
    written = new
    print 'Wrote %s new documents.' % (written)
    
    return written

def reconcile_dumps(options, cache_wrapper, now):
    sys.stdout.write('Reconciling dumps with current data...\n')
    sys.stdout.flush()
    
    # get workers going
    num_workers = options.multi
    
    todo_queue = multiprocessing.JoinableQueue(num_workers * 3)
    repaired_counter = Counter()
    updated_counter = Counter()
    deleted_counter = Counter()
    
    processes = []
    for i in range(num_workers):
        proc = multiprocessing.Process(target=reconcile_worker, args=(todo_queue, cache_wrapper, now, repaired_counter, updated_counter, deleted_counter))
        proc.start()
        processes.append(proc)
    
    import pymongo
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    conditions = {'last_seen': {'$lt': now}, 'deleted': False, 'source': 'regulations.gov'}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['docket_id'] = options.docket

    fields = {'_id': 1, 'scraped': 1, 'views.downloaded': 1, 'views.type': 1, 'attachments.views.downloaded': 1, 'attachments.views.type': 1, 'attachments.object_id': 1}
    to_check = db.docs.find(conditions, fields)
    
    while True:
        try:
            record = to_check.next()
        except pymongo.errors.OperationFailure:
            print 'OH NOES!'
            to_scrape = db.docs.find(conditions, fields)
            continue
        except StopIteration:
            break
            
        todo_queue.put(record)
    
    todo_queue.join()
    
    for proc in processes:
        print 'Terminating reconciliation worker %s...' % proc.pid
        proc.terminate()
    
    # compile and print some stats
    num_updated = updated_counter.value
    num_repaired = repaired_counter.value
    num_deleted = deleted_counter.value
    num_docs = num_updated + num_repaired + num_deleted
    print 'Reconciliation complete: examined %s documents, of which %s were updated, %s were repaired, and %s were flagged as deleted.' % (num_docs, num_updated, num_repaired, num_deleted)
    
    return {'updated': num_updated, 'repaired': num_repaired, 'deleted': num_deleted}

def parser_process(file, cache):
    docs = iter_parse(os.path.join(settings.DUMP_DIR, file))
    print '[%s] Done with JSON decode.' % os.getpid()
    
    count = 0
    for doc in docs:
        cache.set(doc['documentId'], doc)
        count += 1
    
    return {'docs': count}

def parser_worker(todo_queue, done_queue, cache_wrapper):
    pid = os.getpid()
    
    print '[%s] Parser worker started.' % pid
    
    cache = cache_wrapper.get_pickle_connection()
    
    while True:
        file = todo_queue.get()
        
        sys.stdout.write('[%s] Parsing file %s...\n' % (pid, file))
        sys.stdout.flush()
        start = datetime.datetime.now()
        
        stats = parser_process(file, cache)
        
        elapsed = datetime.datetime.now() - start
        sys.stdout.write('[%s] Done with %s in %s minutes\n' % (pid, file, round(elapsed.total_seconds() / 60.0)))
        sys.stdout.flush()
        
        done_queue.put(stats)
        
        todo_queue.task_done()
    
def parse_dumps(options, cache_wrapper):
    # figure out which files are ours
    id_string = 'all'
    if options.agency and options.docket:
        raise Exception("Specify either an agency or a docket")
    elif options.agency:
        id_string = 'agency_' + options.agency
    elif options.docket:
        id_string = 'docket_' + options.docket.replace('-', '_')

    num_workers = options.multi
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.startswith('dump_%s' % id_string) and file.endswith('.json')]

    if len(files) < 1:
        # something is wrong, as there should be more than ten files
        raise Exception('Too few .json files; something went wrong.')
    
    # it's a small number of files, so just make a queue big enough to hold them all, to keep from having to block
    todo_queue = multiprocessing.JoinableQueue(len(files))
    done_queue = multiprocessing.Queue(len(files))
    
    sys.stdout.write('Starting parser workers...\n')
    processes = []
    for i in range(num_workers):
        proc = multiprocessing.Process(target=parser_worker, args=(todo_queue, done_queue, cache_wrapper))
        proc.start()
        processes.append(proc)
    
    for file in files:
        todo_queue.put(file)
    
    todo_queue.join()
    
    for proc in processes:
        print 'Terminating parser worker %s...' % proc.pid
        proc.terminate()
    
    # print totals
    print 'Done parsing files.'

def run(options, args):
    sys.stdout.write('Starting decoding...\n')
    sys.stdout.flush()
    
    # get workers going
    now = datetime.datetime.now(tz=pytz.utc)
    
    num_workers = options.multi
    
    # set up caching
    sys.stdout.write('Spinning up Redis instance...\n')
    
    if options.use_cache:
        cache_wrapper = TmpRedis(db_uuid=options.use_cache)
        # give it time to rebuild its cache from disk if we're using an already-built cache
        sys.stdout.write('Loading cache from disk...')
        time.sleep(15)
        sys.stdout.write(' done.\n')
    else:
        cache_wrapper = TmpRedis()
        parse_dumps(options, cache_wrapper)
    
    stats = {}
    if not options.add_only:
        stats = reconcile_dumps(options, cache_wrapper, now)
    else:
        print 'Skipping reconciliation step.'
    
    # still-existing and deleted stuff is now done, but we still have to do the new stuff
    stats['new'] = add_new_docs(cache_wrapper, now)
    
    sys.stdout.write('Terminating Redis cache...\n')
    
    if options.keep_cache:
        cache_wrapper.terminate(delete=False)
        print 'Cache preserved with UUID %s.' % cache_wrapper.uuid
    else:
        cache_wrapper.terminate()
    
    return stats