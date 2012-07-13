GEVENT = False

import zlib
import datetime
import settings

import pymongo
import traceback
import os
import multiprocessing
from Queue import Empty
from models import *

from oxtail.matching import match

def get_text(view):
    if not view.content:
        return ''
    
    return view.content.read()

def process_doc(doc):
    # entity extraction
    for view in doc.views:
        if view.extracted == 'yes':
            view_matches = match(get_text(view), multiple=True)
            if view_matches:
                view.entities = list(view_matches.keys())

    for attachment in doc.attachments:
        for view in attachment.views:
            if view.extracted == 'yes':
                view_matches = match(get_text(view), multiple=True)
                if view_matches:
                    view.entities = list(view_matches.keys())
    
    # submitter matches
    details = doc.details
    submitter_matches = match('\n'.join([
        # organization
        details.get('Organization_Name', ''),
        
        # submitter name
        ' '.join(
            filter(bool, [details.get('First_Name', ''), details.get('Last_Name', '')])
        )
    ]))
    if submitter_matches:
        doc.submitter_entities = list(submitter_matches.keys())

    doc.entities_last_extracted = datetime.datetime.now()
        
    doc.save()

    return True

def process_worker(todo_queue):
    pid = os.getpid()
    print '[%s] Worker started.' % pid
    while True:
        try:
            doc = Doc._from_son(todo_queue.get())
        except Empty:
            print '[%s] Processing complete.' % pid
            return
        
        try:
            doc_success = process_doc(doc)
            print '[%s] Processing of doc %s succeeded.' % (pid, doc.id)
        except:
            print '[%s] Processing of doc %s failed.' % (pid, doc.id)
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

    Doc._get_db()
    cursor = Doc.objects(scraped="yes", deleted=False)
    
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
        todo_queue.put(doc.to_mongo())
    
    todo_queue.join()

    for proc in processes:
        print 'Terminating worker %s...' % proc.pid
        proc.terminate()
    
    print '[%s] Completed analysis in %s seconds.' % (pid, time.time() - run_start)
