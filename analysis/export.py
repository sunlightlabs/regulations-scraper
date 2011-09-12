#!/usr/bin/env python

import sys
import os
import csv
import time
import multiprocessing
from Queue import Empty
from datetime import datetime
from collections import namedtuple
from pymongo import Connection
import StringIO

pid = os.getpid()

import_start = time.time()
print '[%s] Loading trie...' % pid
from oxtail.matching import match
print '[%s] Loaded trie in %s seconds.' % (pid, time.time() - import_start)

F = namedtuple('F', ['csv_column', 'transform'])

def deep_get(key, dict, default=None):
    if '.' in key:
        first, rest = key.split('.', 1)
        return deep_get(rest, dict.get(first, {}), default)
    else:
        out = dict.get(key, default)
        return out if out else default

def getter(key, default=''):
    return lambda d: deep_get(key, d, default)


DOCS_QUERY = {}

DOCS_FIELDS = [
    F('document_id', getter('document_id')),
    F('docket_id', getter('docket_id')),
    F('agency', getter('agency')),
    F('date_posted', getter('details.receive_date', None)),
    F('date_due', getter('details.comment_end_date', None)),
    F('title', getter('title')),
    F('type', getter('type')),
    F('org_name', getter('details.organization')),
    F('submitter_name', lambda d: ' '.join(filter(bool, [deep_get('details.first_name', d, None), deep_get('details.mid_initial', d, None), deep_get('details.last_name', d, None)]))),
    F('on_type', getter('comment_on.type')),
    F('on_id', getter('comment_on.id')),
    F('on_title', getter('comment_on.title')),
]


def filter_for_postgres(v):
    if v is None:
        return '\N'
    
    if isinstance(v, datetime):
        return str(v)

    return v.encode('utf8').replace("\.", ".")

def process_doc(doc, fields=DOCS_FIELDS):
    # field extraction
    output = {
        'metadata': [filter_for_postgres(f.transform(doc)) for f in fields],
        'matches': [],
        'submitter_matches': []
    }
    
    # entity extraction
    if 'views' in doc and doc['views']:
        for view in doc['views']:
            if 'decoded' in view and view['decoded'] == True:
                for entity_id in match(view['text']).keys():
                    # hack to deal with documents whose scrapes failed but still got decoded
                    object_id = doc['object_id'] if 'object_id' in doc else view['file'].split('/')[-1].split('.')[0]
                    output['matches'].append([doc['document_id'], object_id, view['type'], 'view', entity_id])
    if 'attachments' in doc and doc['attachments']:
        for attachment in doc['attachments']:
            if 'views' in attachment and attachment['views']:
                for view in attachment['views']:
                    if 'decoded' in view and view['decoded'] == True:
                        for entity_id in match(view['text']).keys():
                            output['matches'].append([doc['document_id'], attachment['object_id'], view['type'], 'attachment', entity_id])
    
    # submitter matches
    for entity_id in match('\n'.join([output['metadata'][7], output['metadata'][8]])).keys():
        output['submitter_matches'].append([doc['document_id'], entity_id])
    
    return output
    
# single-core version
def dump_cursor(c, fields, filename):
    metadata_writer = csv.writer(open(sys.argv[3] + '_meta.csv', 'w'))
    metadata_writer.writerow([f.csv_column for f in fields])
    
    match_writer = csv.writer(open(sys.argv[3] + '_text_matches.csv', 'w'))
    match_writer.writerow(['document_id', 'object_id', 'file_type', 'view_type', 'entity_id'])
    
    submitter_writer = csv.writer(open(sys.argv[3] + '_submitter_matches.csv', 'w'))
    submitter_writer.writerow(['document_id', 'entity_id'])
    
    for doc in c:
        doc_data = process_doc(doc)
        metadata_writer.writerow(doc_data['metadata'])
        match_writer.writerows(doc_data['matches'])
        submitter_writer.writerows(doc_data['submitter_matches'])

# multi-core version and helpers
def write_worker(done_queue, filename, fields=DOCS_FIELDS):
    print '[%s] Writer started.' % os.getpid()
    
    metadata_writer = csv.writer(open(sys.argv[3] + '_meta.csv', 'w'))
    metadata_writer.writerow([f.csv_column for f in fields])
    
    match_writer = csv.writer(open(sys.argv[3] + '_text_matches.csv', 'w'))
    match_writer.writerow(['document_id', 'object_id', 'file_type', 'view_type', 'entity_id'])
    
    submitter_writer = csv.writer(open(sys.argv[3] + '_submitter_matches.csv', 'w'))
    submitter_writer.writerow(['document_id', 'entity_id'])
    
    while True:
        try:
            doc_data = done_queue.get(timeout=5)
        except Empty:
            print '[%s] CSV writes complete.' % os.getpid()
            return
        
        metadata_writer.writerow(doc_data['metadata'])
        match_writer.writerows(doc_data['matches'])
        submitter_writer.writerows(doc_data['submitter_matches'])
        
        done_queue.task_done()

def process_worker(todo_queue, done_queue):
    print '[%s] Worker started.' % os.getpid()
    while True:
        try:
            doc = todo_queue.get(timeout=5)
        except Empty:
            print '[%s] Processing complete.' % os.getpid()
            return
        
        doc_data = process_doc(doc)
        done_queue.put(doc_data)
        
        todo_queue.task_done()
    
def dump_cursor_multi(c, fields, filename, num_workers):
    todo_queue = multiprocessing.JoinableQueue(num_workers * 3)
    done_queue = multiprocessing.JoinableQueue(num_workers * 3)
    
    for i in range(num_workers):
        proc = multiprocessing.Process(target=process_worker, args=(todo_queue, done_queue))
        proc.start()
    proc = multiprocessing.Process(target=write_worker, args=(done_queue, filename))
    proc.start()
    
    for doc in c:
        todo_queue.put(doc)
    
    todo_queue.join()
    done_queue.join()

if __name__ == '__main__':
    # set up options
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] host dbname file_prefix")
    parser.add_option("-l", "--limit", dest="limit", action="store", type="int", default=None, help="Limit number of records for testing.")
    parser.add_option("-m", "--multi", dest="multi", action="store", type="int", default=None, help="Set number of worker processes.  Single-process model used if not specified.")
    
    (options, args) = parser.parse_args()
    
    # fetch options, args
    host = args[0]
    dbname = args[1]
    prefix = args[2]
    
    # do request and analysis
    if options.limit:
        cursor = Connection(host=host)[dbname].docs.find(DOCS_QUERY, limit=options.limit)
    else:
        cursor = Connection(host=host)[dbname].docs.find(DOCS_QUERY)
    
    run_start = time.time()
    print '[%s] Starting analysis...' % pid
    
    if options.multi:
        dump_cursor_multi(cursor, DOCS_FIELDS, prefix, options.multi)
    else:
        dump_cursor(cursor, DOCS_FIELDS, prefix)
    
    print '[%s] Completed analysis in %s seconds.' % (pid, time.time() - run_start)
