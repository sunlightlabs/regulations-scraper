from regs_gwt.regs_client import RegsClient
from pygwt.response import Response
import os
import settings
from regscrape_lib.util import get_db
import pymongo
import sys

def parse(file, client):
    data = open(file)
    
    response = Response(client, data)
    return response.reader.read_object()

def run():
    print 'Starting decoding...'
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
    client = RegsClient()
    
    db = get_db()
    db.docs.ensure_index('document_id', unique=True)
    
    num_docs = 0
    num_written = 0
    for file in files:
        sys.stdout.write('Parsing file %s... ' % file)
        sys.stdout.flush()
        
        docs = parse(os.path.join(settings.DUMP_DIR, file), client)
    
        written = 0
        for doc in docs:
            db_doc = {'document_id': doc['document_id'], 'views': [], 'docket_id': ['doc.docket_id'], 'agency': doc['agency'], 'scraped': False}
            if doc['formats']:
                for format in doc['formats']:
                    db_doc['views'].append({
                        'type': format,
                        'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (doc['object_id'], format),
                        'downloaded': False
                    })
            
            try:
                db.docs.save(db_doc, safe=True)
                written += 1
            except pymongo.errors.DuplicateKeyError:
                # looks like we already know about this one
                pass
        
        num_docs += len(docs)
        num_written += written
        sys.stdout.write('done (got %s documents, of which %s were new)\n' % (len(docs), written))
    
    print 'Decoding complete: decoded %s documents, of which %s were new' % (num_docs, num_written)
