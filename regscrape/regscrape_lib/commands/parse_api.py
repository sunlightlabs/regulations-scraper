from regs_gwt.regs_client import RegsClient
import os
import settings
import sys
from search import parse
import pytz
import datetime

import multiprocessing
from Queue import Empty

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=multiprocessing.cpu_count(), help="Set number of worker processes.  Defaults to number of cores if not specified.")

def make_view(format, object_id):
    return {
        'type': format,
        'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (object_id, format),
        'downloaded': False,
        'extracted': False,
        'ocr': False
    }

def get_db():
    import pymongo
    return pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
def process(file, client, db, now):    
    docs = parse(os.path.join(settings.DUMP_DIR, file), client)
    print '[%s] Done with GWT decode.'
    
    written = 0
    updated = 0
    repaired = 0
    for doc in docs:
        # check and see if we already have this doc and, if so, whether or not it needs fixing
        current_subset = db.docs.find({'document_id': doc['document_id']}, {'views.downloaded': 1, 'views.type': 1, 'attachments.views.downloaded': 1, 'attachments.views.type': 1})
        if current_subset.count():
            # do we need to fix anything?
            doc_subset = current_subset[0]
            statuses = [view['downloaded'] for view in doc_subset['views']] + reduce(operator.add, [[view['downloaded'] for view in attachment['views']] for attachment in doc_subset.get('attachments', [])], [])
            types = [view['type'] for view in d['views']]
            
            if 'failed' in statuses or sorted(doc['formats']) != sorted(types):
                # needs a repair; grab the full document
            
                current_docs = db.docs.find({'_id': doc_subset['_id']})
                
                db_doc = current_docs[0]
                
                if db_doc['scraped'] == 'failed':
                    db_doc['scraped'] = False
                
                # rebuild views
                if doc['formats']:
                    for format in doc['formats']:
                        already_exists = [view for view in db_doc['views'] if view['type'] == format]
                        if not already_exists:
                            db_doc['views'].append(make_view(format, doc['object_id']))
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
#                db.doc.save(db_doc, safe=True)
                repaired += 1
            else:
                # we don't need a full repair, so just do an update on the date
#                   db.docs.update({'_id': doc_subset['_id']}, {'$set': {'last_seen': now}}, safe=True)
                updated += 1
        else:
            # we need to create this document
            db_doc = {'document_id': doc['document_id'], 'views': [], 'docket_id': doc['docket_id'], 'agency': doc['agency'], 'scraped': False, 'object_id': doc['object_id']}
            if doc['formats']:
                for format in doc['formats']:
                    db_doc['views'].append(make_view(format, doc['object_id']))
        
            try:
#               db.docs.save(db_doc, safe=True)
                written += 1
            except pymongo.errors.DuplicateKeyError:
                # this shouldn't happen unless there's another process or thread working on the same data at the same time
                pass
        if (updated + written + repaired) % 1000 == 0:
            print '[%s] %s completed so far.' % (os.getpid(), updated + written + repaired)
    
    return {'docs': len(docs), 'updated': updated, 'written': written, 'repaired': repaired}

def worker(todo_queue, done_queue, now):
    pid = os.getpid()
    
    print '[%s] Worker started.' % pid
    
    db = get_db()
    client = RegsClient()
    
    while True:
        try:
            file = todo_queue.get(timeout=5)
        except Empty:
            print '[%s] Processing complete.' % os.getpid()
            return
        
        sys.stdout.write('[%s] Parsing file %s...\n' % (pid, file))
        sys.stdout.flush()
        start = datetime.datetime.now()
        
        stats = process(file, client, db, now)
        
        elapsed = datetime.datetime.now() - start
        sys.stdout.write('[%s] Done with %s in %s minutes (got %s documents, of which %s were new, %s were updated, and %s were repaired)\n' % (pid, file, round(elapsed.total_seconds() / 60.0), stats['docs'], stats['written'], stats['updated'], stats['repaired']))
        sys.stdout.flush()
        
        done_queue.put(stats)
        
        todo_queue.task_done()
    
def run(options, args):
    sys.stdout.write('Starting decoding...\n')
    sys.stdout.flush()
    
    # get workers going
    now = datetime.datetime.now(tz=pytz.utc)
    
    num_workers = options.multi
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
    # it's a small number of files, so just make a queue big enough to hold them all, to keep from having to block
    todo_queue = multiprocessing.JoinableQueue(len(files))
    done_queue = multiprocessing.Queue(len(files))
    
    for i in range(num_workers):
        proc = multiprocessing.Process(target=worker, args=(todo_queue, done_queue, now))
        proc.start()
    
    for file in files:
        todo_queue.put(file)
    
    todo_queue.join()
    
    # print totals
    print 'Tabulating stats...'
    num_docs = 0
    num_written = 0
    num_updated = 0
    num_repaired = 0
    while True:
        try:
            stats = done_queue.get(timeout=0)
            num_docs += stats['docs']
            num_written += stats['written']
            num_updated += stats['updated']
            num_repaired += stats['repaired']
        except Empty:
            break
    
    print 'Decoding complete: decoded %s documents, of which %s were new and %s were updated' % (num_docs, num_written, num_updated, num_repaired)
    
    sys.stdout.write('Flagging deletions...')
#    get_db().docs.update({'last_seen': {'$lt': now}}, {'$set': {'deleted': True}}, multi=True)
    sys.stdout.write(' done.\n')
