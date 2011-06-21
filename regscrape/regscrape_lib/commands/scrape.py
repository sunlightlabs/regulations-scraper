import settings
from regscrape_lib.regs_gwt.regs_client import RegsClient
from regscrape_lib.document import scrape_document
import urllib2
import sys
import os
import traceback

def run_child():
    print 'Starting child %s...' % os.getpid()
    from pymongo import Connection
    
    client = RegsClient()
    db = Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
    print 'Child %s has a connection...' % os.getpid()
    
    while True:
        record = db.docs.find_and_modify({'scraped': False, '_scraping':{'$exists': False}, 'scrape_failed': {'$exists': False}}, {'$set': {'_scraping': True}})
        
        if record is None:
            return
        
        doc = None
        
        for i in range(3):
            error = None
            try:
                doc = scrape_document(record['document_id'], client)
                doc['_id'] = record['_id']
                print '[%s] Scraped doc %s...' % (os.getpid(), doc['document_id'])
                break
            except KeyboardInterrupt:
                raise
            except:
                print 'Warning: scrape failed on try %s' % i
                error = sys.exc_info()
                print traceback.print_tb(error[2])
        
        # catch renames of documents
        if doc and (not error) and doc['document_id'] != record['document_id']:
            renamed_to = doc['document_id']
            doc = record
            doc['views'] = []
            doc['scraped'] = True
            doc['renamed_to'] = renamed_to
        
        # catch errors
        if error or not doc:
            doc = record
            doc['scrape_failed'] = True
            if error:
                print 'Scrape of %s failed because of %s' % (doc['document_id'], str(error))
                doc['failure_reason'] = str(error)
        
        try:
            db.docs.save(doc, safe=True)
        except:
            print "Warning: database save failed on document %s (scraped based on original doc ID %s)." % (doc['document_id'], record['document_id'])

def run():
    is_master = True
    for i in range(settings.INSTANCES):
        if is_master:
            pid = os.fork()
            if pid == 0:
                is_master = False
                break
    
    if is_master:
        os.waitpid(-1, 0)
    
    else:
        run_child()
