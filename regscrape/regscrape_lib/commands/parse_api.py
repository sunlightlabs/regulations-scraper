from regs_gwt.regs_client import RegsClient
import os
import settings
import sys
from search import parse
import pytz
import datetime
import operator
import time
from regscrape_lib.tmp_redis import TmpRedis
from regscrape_lib.mp_types import Counter


import multiprocessing
from Queue import Empty

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes. Defaults to number of cores if not specified.")
arg_parser.add_option("-k", "--keep-cache", dest="keep_cache", action="store_true", default=False, help="Prevents the cache from being deleted at the end of processing to make testing faster.")
arg_parser.add_option("-u", "--use-cache", dest="use_cache", action="store", default=None, help="Use pre-existing cache to make testing faster.")
arg_parser.add_option("-a", "--add-only", dest="add_only", action="store_true", default=False, help="Skip reconciliation, assume that all records are new, and go straight to the add step.")

def make_view(format, object_id):
    return {
        'type': format,
        'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (object_id, format),
        'downloaded': False,
        'extracted': False,
        'ocr': False
    }

def reconcile_process(record, cache, db, now, repaired_counter, updated_counter, deleted_counter):
    # check and see if this doc has been updated
    new_record = cache.get(record['document_id'])
    if new_record:
        # do we need to fix anything?
        statuses = [view['downloaded'] for view in record['views']] + reduce(operator.add, [[view['downloaded'] for view in attachment['views']] for attachment in record.get('attachments', [])], [])
        types = [view['type'] for view in record['views']]
        
        if 'failed' in statuses or sorted(new_record['formats'] or []) != sorted(types):
            # needs a repair; grab the full document
        
            current_docs = db.docs.find({'_id': record['_id']})
            
            db_doc = current_docs[0]
            
            if db_doc['scraped'] == 'failed':
                db_doc['scraped'] = False
            
            # rebuild views
            if new_record['formats']:
                for format in new_record['formats']:
                    already_exists = [view for view in db_doc['views'] if view['type'] == format]
                    if not already_exists:
                        db_doc['views'].append(make_view(format, new_record['object_id']))
                    elif already_exists and already_exists[0]['downloaded'] == 'failed':
                        already_exists[0]['downloaded'] = False
                        if 'failure_reason' in already_exists[0]:
                            del already_exists[0]['failure_reason']
        
            # while we're here, reset attachment download status (can't do a full rebuild without rescrape, but I can live with that for now)
            if 'attachments' in db_doc:
                for attachment in db_doc['attachments']:
                    for view in attachment['views']:
                        if view['downloaded'] == 'failed':
                            view['downloaded'] = False
                            if 'failure_reason' in view:
                                del view['failure_reason']
            
            # update the last-seen date
            db_doc['last_seen'] = now
            
            # do save
            db.doc.save(db_doc, safe=True)
            repaired_counter.increment()
        else:
            # we don't need a full repair, so just do an update on the date
            db.docs.update({'_id': record['_id']}, {'$set': {'last_seen': now}}, safe=True)
            updated_counter.increment()
        
        # either way, delete the document from the cache so we can tell what's new at the end
        cache.delete(record['document_id'])
    else:
        # this document isn't in the new data anymore, so mark it deleted
        db.docs.update({'_id': record['_id']}, {'$set': {'deleted': True}}, safe=True)
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
    
    import pymongo
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    cache = cache_wrapper.get_pickle_connection()
    
    new = 0
    replaced = 0
    for id in cache.keys():
        doc = cache.get(id)
        db_doc = {'document_id': doc['document_id'], 'views': [], 'docket_id': doc['docket_id'], 'agency': doc['agency'], 'scraped': False, 'object_id': doc['object_id'], 'last_seen': now, 'deleted': False}
        if doc['formats']:
            for format in doc['formats']:
                db_doc['views'].append(make_view(format, doc['object_id']))
    
        try:
            db.docs.save(db_doc, safe=True)
            new += 1
        except pymongo.errors.DuplicateKeyError:
            # apparently sometimes documents get deleted and recreated; when this occurs, nuke the existing one and replace it
            db.docs.remove({'document_id': doc['document_id']}, safe=True)
            db.docs.save(db_doc, safe=True)
            replaced += 1
    
    written = new + replaced
    print 'Wrote %s new documents, of which %s were replacements for documents flagged as deleted.' % (written, replaced)
    
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
    
    conditions = {'last_seen': {'$lt': now}, 'deleted': False}
    fields = {'document_id': 1, 'views.downloaded': 1, 'views.type': 1, 'attachments.views.downloaded': 1, 'attachments.views.type': 1}
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

def parser_process(file, client, cache):    
    docs = parse(os.path.join(settings.DUMP_DIR, file), client)
    print '[%s] Done with GWT decode.' % os.getpid()
    
    for doc in docs:
        cache.set(doc['document_id'], doc)
    
    return {'docs': len(docs)}

def parser_worker(todo_queue, done_queue, cache_wrapper):
    pid = os.getpid()
    
    print '[%s] Parser worker started.' % pid
    
    client = RegsClient()
    cache = cache_wrapper.get_pickle_connection()
    
    while True:
        file = todo_queue.get()
        
        sys.stdout.write('[%s] Parsing file %s...\n' % (pid, file))
        sys.stdout.flush()
        start = datetime.datetime.now()
        
        stats = parser_process(file, client, cache)
        
        elapsed = datetime.datetime.now() - start
        sys.stdout.write('[%s] Done with %s in %s minutes\n' % (pid, file, round(elapsed.total_seconds() / 60.0)))
        sys.stdout.flush()
        
        done_queue.put(stats)
        
        todo_queue.task_done()
    
def parse_dumps(options, cache_wrapper):
    num_workers = options.multi
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
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
    add_new_docs(cache_wrapper, now)
    
    sys.stdout.write('Terminating Redis cache...\n')
    
    if options.keep_cache:
        cache_wrapper.terminate(delete=False)
        print 'Cache preserved with UUID %s.' % cache_wrapper.uuid
    else:
        cache_wrapper.terminate()
    
    return stats