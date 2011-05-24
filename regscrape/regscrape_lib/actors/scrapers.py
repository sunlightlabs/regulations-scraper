from regscrape_lib.actors import BaseActor
from selenium import webdriver
from regscrape_lib import logger
from regscrape_lib.exceptions import Finished, StillNotFound, DoesNotExist
from regscrape_lib.util import pseudoqs_encode, get_db
from listing import scrape_listing, get_count
from document import scrape_document
import settings

import urllib2, sys

class BaseScraperActor(BaseActor):
    def __init__(self, master):
        self.browser = getattr(webdriver, settings.BROWSER['driver'])(**(settings.BROWSER.get('kwargs', {})))
        self.master = master
        self.db = get_db()
        
        self._pre_ready()
        
        self._send_ready()
    
    def on_stop(self):
        try:
            self.browser.quit()
        except:
            pass
    
    def _pre_ready(self):
        pass
    
    def _write(self, collection, records):
        self.db[collection].insert(records, safe=True)
        
    def _upsert(self, collection, records, match_on):
        for record in records:
            try:
                self.db[collection].update({match_on: record[match_on]}, record, upsert=True, safe=True)
            except:
                logger.error("Error writing to database: %s" % sys.exc_info()[0])
    
    def _send_ready(self):
        pid = None
        try:
            pid = self.browser.binary.process.pid
        except:
            pass
        self.master.send_one_way({'command': 'ready', 'actor': self.actor_ref, 'pid': pid})

class ListingScraperActor(BaseScraperActor):
    def _pre_ready(self):        
        if settings.CHECK_BEFORE_SCRAPE:
            local_docs = get_db().docs
            self._check_before_scrape = lambda id: local_docs.find({'document_id': id}).count() > 0
        else:
            self._check_before_scrape = None
    
    def scrape(self, message):
        # blank browser first
        self.browser.get('about:blank')
        
        # do scrape
        docs = None
        for i in range(2):
            try:
                docs, errors = scrape_listing(self.browser, message.get('url'), check_func=self._check_before_scrape)
                break
            except Finished:
                logger.info('Reached end of search results; terminating.')
                self.master.send_one_way({'command': 'finished', 'actor': self.actor_ref, 'url': message.get('url')})
                return
            except urllib2.URLError:
                # looks like our browser died
                self.master.send_one_way({'command': 'dead', 'actor': self.actor_ref, 'url': message.get('url')})
                return
            except:
                pass
            logger.warn('Failed on first try scraping %s' % message.get('url'))
        if docs:
            self._upsert('docs', docs, match_on='document_id')
            if errors:
                self._write('errors', errors)
        elif errors:
            logger.error('Gave up on listing %s' % message['url'])
            self._write('errors', [{'type': 'listing', 'reason': 'Failed to scrape listing', 'url': message.get('url')}])
        self._send_ready()

class DocumentScraperActor(BaseScraperActor):    
    def scrape(self, message):
        # get docs to work on
        starting_docs = list(self.db.docs.find({'scraped': False, '_job_id': message['job_id']}))
        
        if len(starting_docs) == 0:
            logger.info('No more new documents; terminating.')
            self.master.send_one_way({'command': 'finished', 'actor': self.actor_ref, 'job_id': message.get('job_id')})
        else:
            logger.info("Scraping %s documents (job ID '%s')..." % (len(starting_docs), message['job_id']))
        
        # blank the browser
        self.browser.get('about:blank')
        
        # start fetching docs
        docs = []
        errors = []
        for in_doc in starting_docs:
            # weird upsert issue seems to be resolved by nuking this field
            mongo_id = in_doc['_id']
            del in_doc['_id']
            
            id = in_doc['document_id']
            
            # try it three times
            doc = None
            doc_error = None
            for i in range(3):
                try:
                    doc = scrape_document(self.browser, id, visit_first=True, document=in_doc)
                    break
                except StillNotFound:
                    # re-blank the page
                    self.browser.get('about:blank')
                except urllib2.URLError:
                    # looks like our browser died
                    self.master.send_one_way({'command': 'dead', 'actor': self.actor_ref, 'job_id': message.get('job_id')})
                    return
                except DoesNotExist:
                    # I guess there's no such document?
                    doc = in_doc
                    doc['scrape_failed'] = True
                    if '_job_id' in doc:
                        del doc['_job_id']
                    doc_error = {'type': 'document', 'reason': 'Document does not exist', 'job_id': message.get('job_id'), 'document_id': id, 'mongo_document_id': mongo_id}
                    break
                except:
                    exc = sys.exc_info()
                    print exc
                    doc = in_doc
                    doc['scrape_failed'] = True
                    if '_job_id' in doc:
                        del doc['_job_id']
                    doc_error = {'type': 'document', 'reason': '%s: %s' % (str(exc[0]), str(exc[1])), 'job_id': message.get('job_id'), 'document_id': id, 'mongo_document_id': mongo_id}
            if doc:
                docs.append(doc)
            
            if doc_error:
                errors.append(doc_error)
            
            if not doc_error and not doc:
                errors.append({'type': 'document', 'reason': 'Failed to scrape document', 'job_id': message.get('job_id'), 'document_id': id, 'mongo_document_id': mongo_id})
        
        if docs:
            self._upsert('docs', docs, match_on='document_id')
        
        if errors:
            self._write('errors', errors)
        
        logger.info('Scraped job ID %s: got %s documents of %s expected, with %s errors' % (message['job_id'], len(docs), len(starting_docs), len(errors)))
        
        self._send_ready()