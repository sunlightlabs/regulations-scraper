import settings
from regscrape_lib.regs_gwt.regs_client import RegsClient
from regscrape_lib.document import scrape_document
import urllib2
import sys
import os

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
        
        if error or not doc:
            doc = record
            doc['scrape_failed'] = True
            if error:
                doc['failure_reason'] = str(error)
        
        db.docs.save(doc)

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