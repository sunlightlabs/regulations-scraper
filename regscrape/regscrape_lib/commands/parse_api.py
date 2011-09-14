from regs_gwt.regs_client import RegsClient
import os
import settings
from regscrape_lib.util import get_db
import pymongo
import sys
from search import parse
import pytz
import datetime

def make_view(format, object_id):
    return {
        'type': format,
        'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (object_id, format),
        'downloaded': False,
        'extracted': False,
        'ocr': False
    }

def run():
    now = datetime.datetime.now(tz=pytz.utc)
    
    print 'Starting decoding...'
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
    client = RegsClient()
    
    db = get_db()
    db.docs.ensure_index('document_id', unique=True)
    db.docs.ensure_index('last_seen')
    
    num_docs = 0
    num_written = 0
    num_updated = 0
    for file in files:
        sys.stdout.write('Parsing file %s... ' % file)
        sys.stdout.flush()
        
        docs = parse(os.path.join(settings.DUMP_DIR, file), client)
        
        written = 0
        updated = 0
        for doc in docs:
            current_docs = db.docs.find({'document_id': doc['document_id']})
            if current_docs:
                # we already have this doc, so repair it and update its last-seen
                current = current_docs[0]
                print 'old version'
                print current
                
                if current['scraped'] == 'failed':
                    current['scraped'] = False
                
                if doc['formats']:
                    for format in doc['formats']:
                        already_exists = [view for view in current['views'] if view['format'] == format]
                        if not already_exists:
                            current['views'].append(make_view(format, doc['object_id']))
                        elif already_exists and already_exists[0]['downloaded'] == 'failed':
                            already_has_format[0]['downloaded'] = False
                
                # update the last-seen date
                current['last_seen'] = now
            else:
                # we need to create this document
                db_doc = {'document_id': doc['document_id'], 'views': [], 'docket_id': doc['docket_id'], 'agency': doc['agency'], 'scraped': False, 'object_id': doc['object_id']}
                if doc['formats']:
                    for format in doc['formats']:
                        db_doc['views'].append(make_view(format, doc['object_id']))
            
            try:
 #               db.docs.save(db_doc, safe=True)
                if '_id' in db_doc:
                    updated += 1
                    print 'updated version'
                    print db_doc
                else:
                    written += 1
                    print 'first version'
                    print db_doc
            except pymongo.errors.DuplicateKeyError:
                # this shouldn't happen unless there's another process or thread working on the same data at the same time
                pass
        
        num_docs += len(docs)
        num_written += written
        sys.stdout.write('Done (got %s documents, of which %s were new and %s were updated)\n' % (len(docs), written, updated))
    
    print 'Decoding complete: decoded %s documents, of which %s were new and %s were updated' % (num_docs, num_written, num_updated)
    
    sys.stdout.write('Flagging deletions...')
#    db.docs.update({'last_seen': {'$lt': now}}, {'$set': {'deleted': True}})
    sys.stdout.write(' done.\n')
