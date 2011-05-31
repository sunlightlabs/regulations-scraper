from regscrape_lib.actors import BaseActor
from selenium import webdriver
from regscrape_lib import logger

from regscrape_lib.actors.scrapers import *
from regscrape_lib.util import get_url_for_count, get_db
import settings

import math
import json
from bson import Code

from datetime import datetime, timedelta
import time

import os

class MasterActor(BaseActor):
    def __init__(self, num_actors):
        self.num_actors = num_actors
        self.actors = []
        self.assignments = {}
        self.temporary_hopper = []
    
    def scrape(self, message):
        logger.info('Starting scrape...')
        self.current = 0
        self.max = message.get('max')
        self.db = get_db()
        
        # ensure database is configured properly
        if settings.CLEAR_FIRST:
            self.db.journal.drop()
        
        logger.info('Ensuring proper database indexes...')
        self.db.docs.ensure_index('document_id', unique=True)
        self.db.docs.ensure_index('agency')
        self.db.docs.ensure_index('_job_id', sparse=True)
        self.db.docs.ensure_index('scraped')
        
        # start the right kind of scrapers
        if settings.MODE == 'search':
            self.prep_journal()
            ScraperActor = ListingScraperActor
        else:
            ScraperActor = DocumentScraperActor
                
        # start actors and being scraping
        while len(self.actors) < self.num_actors:
            try:
                actor = ScraperActor.start(self.actor_ref)
                self.actors.append(actor)
            except:
                pass
    
    def prep_journal(self):
        # check to see if we need a count to build journal
        if settings.CLEAR_FIRST:
            if not self.max:
                tmp_browser = getattr(webdriver, settings.BROWSER['driver'])(**(settings.BROWSER.get('kwargs', {})))
                count = get_count(tmp_browser, get_url_for_count(0), visit_first=True)
                tmp_browser.quit()
                
                if not count:
                    logger.error('Could not determine result count.')
                    os._exit(os.EX_OK)
                self.count = count
            else:
                self.count = max
            
            # build journal
            logger.info('Building journal to scrape %s results.' % self.count)
            position = 0
            last = int(math.floor(float(self.count - 1) / settings.PER_PAGE) * settings.PER_PAGE)
            while position <= last:
                url = get_url_for_count(position)
                self._write('journal', [{'url': url, 'state': 'not started'}])
                position += settings.PER_PAGE
        else:
            # reset 'STARTED' to 'NOT_STARTED'
            logger.info('Resuming previous scrape...')
            self.db.journal.update({'state': 'started'}, {'$set': {'state': 'not started'}}, multi=True)
    
    def ready(self, message):
        if settings.MODE == 'search':
            self.listing_ready(message)
        else:
            self.document_ready(message)
    
    def listing_ready(self, message):
        actor = message.get('actor')
        if actor.actor_urn in self.assignments:
            # mark URL as finished
            self.db.journal.update({'url': self.assignments[actor.actor_urn]['url']}, {'$set': {'state': 'finished'}})
            
            del self.assignments[actor.actor_urn]
        
        if actor in self.actors:
            new_url = self._get_url()
            if new_url:
                actor.send_one_way({'command': 'scrape', 'url': new_url})
                self.assignments[actor.actor_urn] = {'actor': actor, 'url': new_url, 'assigned': datetime.now(), 'pid': message['pid']}
            else:
                self._shutdown(actor)
    
    def document_ready(self, message):
        actor = message.get('actor')
        if actor.actor_urn in self.assignments:
            del self.assignments[actor.actor_urn]
        
        if actor in self.actors:
            reusing_id = False
            if len(self.temporary_hopper) > 0:
                new_job_id = self.temporary_hopper.pop(0)
                reusing_id = True
                ids = []
            else:
                new_job_id = '%s/%s' % (actor.actor_urn, int(time.time()))
                
                # there's no way to do an update with a limit, so do a weird-ass server-side eval thing instead
                conditions = {'scraped': False, '_job_id': {'$exists': False}, 'scrape_failed': {'$exists': False}}
                conditions.update(getattr(settings, 'FILTER', {}))
                
                ids = self.db.eval(Code("""
                    function() {
                        return db.docs.find(%s).limit(%s).map(function(obj) {
                            obj._job_id = '%s';
                            db.docs.save(obj);
                            return obj._id;
                        })
                    }
                """ % (json.dumps(conditions), settings.CHUNK_SIZE, new_job_id)))
            
            if reusing_id or len(ids) > 0:
                actor.send_one_way({'command': 'scrape', 'job_id': new_job_id})
                self.assignments[actor.actor_urn] = {'actor': actor, 'job_id': new_job_id, 'assigned': datetime.now(), 'pid': message['pid']}
            else:
                self._shutdown(actor)
    
    def finished(self, message):
        if 'url' in message:
            message_position = int(message.get('url').split('=')[-1])
            if self.max == 0 or message_position < self.max:
                self.max = message_position
        self._shutdown(message.get('actor'))
    
    def tick(self, message):
        now = datetime.now()
        diff = timedelta(seconds=settings.MAX_WAIT)
        for urn, record in self.assignments.items():
            if now - record['assigned'] > diff:
                logger.warn("Actor %s has been working on its assigned URL for longer than the maximum-allowed time; resetting browser and reassigning %s." % (urn, record['url'] if 'url' in record else record['job_id']))
                self._handle_dead_scraper(urn, record)
                
                # if the actor is doing something, it won't stop until it finishes, which may never happen, so wait a second and nuke its browser from orbit
                time.sleep(1)
                if record['pid']:
                    try:
                        os.kill(record['pid'], 9)
                    except:
                        pass
    
    def dead(self, message):
        actor = message['actor']
        if actor in self.actors:
            # a browser died and we didn't kill it
            urn = actor.actor_urn
            record = self.assignments[urn]
            logger.warn('Actor %s had its browser die while working on %s.' % (urn, record['url'] if 'url' in record else record['job_id']))
            self._handle_dead_scraper(urn, record)
    
    def _handle_dead_scraper(self, urn, record):
        self._shutdown(record['actor'], True)
        del self.assignments[urn]
        
        self.temporary_hopper.append(record['url'] if 'url' in record else record['job_id'])
        
        replacement = None
        while replacement is None:
            try:
                replacement = ScraperActor.start(self.actor_ref)
            except:
                pass
        
        self.actors.append(replacement)
    
    def _get_url(self):
        if len(self.temporary_hopper) > 0:
            return self.temporary_hopper.pop(0)
        else:
            record = self._find_and_modify('journal', {'state': 'not started'}, {'$set': {'state': 'started'}})
            if record and 'url' in record:
                return record['url']
            else:
                return None
    
    def _shutdown(self, actor, will_replace=False):
        actor.stop(block=False)
        self.actors.remove(actor)
        logger.debug('Shut down 1 worker, %s remaining.' % len(self.actors))
        if len(self.actors) == 0 and will_replace == False:
            logger.info('Done')
            time.sleep(5)
            os._exit(os.EX_OK)
    
    def _write(self, collection, records):
        self.db[collection].insert(records, safe=True)
    
    def _find_and_modify(self, collection, search, record, parameters={}):
        kwargs = parameters
        kwargs['upsert'] = False
        return self.db[collection].find_and_modify(search, record, **kwargs)