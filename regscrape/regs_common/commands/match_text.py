GEVENT = False

import zlib
import datetime
import settings

import pymongo
import traceback
import os
import multiprocessing
from Queue import Empty

from oxtail.matching import match

def get_text(view):
    text = view.get('text', None)
    if not text:
        return ''
    
    if type(text) == dict and 'compressed' in text:
        print 'decompressing document'
        return zlib.decompress(text['compressed'])
    else:
        return text

def process_doc(doc):
    # entity extraction
    if 'views' in doc and doc['views']:
        for view in doc['views']:
            if 'extracted' in view and view['extracted'] == True:
                view_matches = match(get_text(view), multiple=True)
                if view_matches:
                    view['entities'] = list(view_matches.keys())

    if 'attachments' in doc and doc['attachments']:
        for attachment in doc['attachments']:
            if 'views' in attachment and attachment['views']:
                for view in attachment['views']:
                    if 'extracted' in view and view['extracted'] == True:
                        view_matches = match(get_text(view), multiple=True)
                        if view_matches:
                            view['entities'] = list(view_matches.keys())
    
    # submitter matches
    details = doc.get('details', {})
    submitter_matches = match('\n'.join([
        # organization
        details.get('organization', ''),
        
        # submitter name
        ' '.join(
            filter(bool, [details.get('first_name', ''), details.get('mid_initial', ''), details.get('last_name', '')])
        )
    ]))
    if submitter_matches:
        doc['submitter_entities'] = list(submitter_matches.keys())

    doc['entities_last_extracted'] = datetime.datetime.now()
    
    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    
    db.docs.save(doc, safe=True)

    return True

def process_worker(todo_queue):
    pid = os.getpid()
    print '[%s] Worker started.' % pid
    while True:
        try:
            doc = todo_queue.get()
        except Empty:
            print '[%s] Processing complete.' % pid
            return
        
        try:
            doc_success = process_doc(doc)
            print '[%s] Processing of doc %s succeeded.' % (pid, doc['document_id'])
        except:
            print '[%s] Processing of doc %s failed.' % (pid, doc['document_id'])
            traceback.print_exc()
        
        todo_queue.task_done()

def run():
    from regs_common.entities import load_trie_from_mongo
    import time

    pid = os.getpid()

    # load trie from the mongo database
    import_start = time.time()
    print '[%s] Loading trie...' % pid
    load_trie_from_mongo()
    print '[%s] Loaded trie in %s seconds.' % (pid, time.time() - import_start)

    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    cursor = db.docs.find({'scraped': True, 'deleted': False})
    
    run_start = time.time()
    print '[%s] Starting analysis...' % pid

    num_workers = multiprocessing.cpu_count()
    
    todo_queue = multiprocessing.JoinableQueue(num_workers * 3)
    
    processes = []
    for i in range(num_workers):
        proc = multiprocessing.Process(target=process_worker, args=(todo_queue,))
        proc.start()
        processes.append(proc)
    
    for doc in cursor:
        todo_queue.put(doc)
    
    todo_queue.join()

    for proc in processes:
        print 'Terminating worker %s...' % proc.pid
        proc.terminate()
    
    print '[%s] Completed analysis in %s seconds.' % (pid, time.time() - run_start)

