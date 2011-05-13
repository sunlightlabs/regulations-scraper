from pykka.gevent import GeventActor
from selenium import webdriver
from listing import scrape_listing, get_count
import sys
import os
import urllib2
from pymongo import Connection
import time
from datetime import datetime, timedelta

from regscrape_lib import logger
from regscrape_lib.exceptions import Finished
from regscrape_lib.util import pseudoqs_encode, get_db, get_url_for_count
import settings

import math

class BaseActor(GeventActor):
    def on_receive(self, message):
        command = message.get('command', None)
        if command and not command.startswith('_'):
            method = getattr(self, command, None)
            if callable(method):
                return method(message)

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
        self.db = DbActor.start()
        
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
                self._write('journal', [{'url': url, 'state': 'NOT_STARTED'}])
                position += settings.PER_PAGE
        else:
            # reset 'STARTED' to 'NOT_STARTED'
            logger.info('Resuming previous scrape...')
            self._update('journal', {'state': 'STARTED'}, {'$set': {'state': 'NOT_STARTED'}}, parameters={'multi': True})
            
                
        # start actors and being scraping
        while len(self.actors) < self.num_actors:
            try:
                actor = ScraperActor.start(self.actor_ref, self.db)
                self.actors.append(actor)
            except:
                pass

    def ready(self, message):
        actor = message.get('actor')
        if actor.actor_urn in self.assignments:
            # mark URL as finished
            self._update('journal', {'url': self.assignments[actor.actor_urn]['url']}, {'$set': {'state': 'FINISHED'}})
            
            del self.assignments[actor.actor_urn]
        
        if actor in self.actors:
            new_url = self._get_url()
            if new_url:
                actor.send_one_way({'command': 'scrape_listing', 'url': new_url})
                self.assignments[actor.actor_urn] = {'actor': actor, 'url': new_url, 'assigned': datetime.now(), 'pid': message['pid']}
            else:
                self._shutdown(actor)
    
    def finished(self, message):
        message_position = int(message.get('url').split('=')[-1])
        if self.max == 0 or message_position < self.max:
            self.max = message_position
        self._shutdown(message.get('actor'))
    
    def tick(self, message):
        now = datetime.now()
        diff = timedelta(seconds=settings.MAX_WAIT)
        for urn, record in self.assignments.items():
            if now - record['assigned'] > diff:
                logger.warn("Actor %s has been working on its assigned URL for longer than the maximum-allowed time; resetting browser and reassigning %s." % (urn, record['url']))
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
            logger.warn('Actor %s had its browser die while working on %s.' % (urn, record['url']))
            self._handle_dead_scraper(urn, record)
    
    def _handle_dead_scraper(self, urn, record):
        self._shutdown(record['actor'], True)
        del self.assignments[urn]
        
        self.temporary_hopper.append(record['url'])
        
        replacement = None
        while replacement is None:
            try:
                replacement = ScraperActor.start(self.actor_ref, self.db)
            except:
                pass
        
        self.actors.append(replacement)
    
    def _get_url(self):
        if len(self.temporary_hopper) > 0:
            return self.temporary_hopper.pop(0)
        else:
            record = self._find_and_modify('journal', {'state': 'NOT_STARTED'}, {'$set': {'state': 'STARTED'}})
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
        self.db.send_one_way({'command': 'write', 'collection': collection, 'records': records})
    
    def _find_and_modify(self, collection, search, record, parameters={}):
        return self.db.send_request_reply({'command': 'find_and_modify', 'collection': collection, 'search': search, 'record': record, 'parameters': parameters})
    
    def _update(self, collection, spec, record, parameters={}):
        self.db.send_one_way({'command': 'update', 'collection': collection, 'spec': spec, 'record': record, 'parameters': parameters})

class ScraperActor(BaseActor):
    def __init__(self, master, db):
        self.browser = getattr(webdriver, settings.BROWSER['driver'])(**(settings.BROWSER.get('kwargs', {})))
        self.master = master
        self.db = db
        
        if settings.CHECK_BEFORE_SCRAPE:
            local_docs = get_db().docs
            self._check_before_scrape = lambda id: local_docs.find({'Document ID': id}).count() > 0
        else:
            self._check_before_scrape = None
            
        
        self._send_ready()
    
    def scrape_listing(self, message):
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
            self._upsert('docs', docs, match_on='Document ID')
            if errors:
                self._write('errors', errors)
        elif errors:
            logger.error('Gave up on listing %s' % message['url'])
            self._write('errors', [{'type': 'listing', 'reason': 'Failed to scrape listing', 'url': message.get('url')}])
        self._send_ready()
    
    def on_stop(self):
        try:
            self.browser.quit()
        except:
            pass
    
    def _write(self, collection, records):
        self.db.send_one_way({'command': 'write', 'collection': collection, 'records': records})
        
    def _upsert(self, collection, records, match_on):
        self.db.send_one_way({'command': 'upsert', 'collection': collection, 'records': records, 'match_on': match_on})
    
    def _send_ready(self):
        pid = None
        try:
            pid = self.browser.binary.process.pid
        except:
            pass
        self.master.send_one_way({'command': 'ready', 'actor': self.actor_ref, 'pid': pid})

class DbActor(BaseActor):
    def __init__(self):
        self.db = get_db()
        if settings.CLEAR_FIRST:
            self.db.journal.drop()
        
        self.db.docs.ensure_index('Document ID')
    
    def write(self, message):
        try:
            self.db[message['collection']].insert(message['records'], safe=True)
        except:
            logger.error("Error writing to database: %s" % sys.exc_info()[0])
    
    def update(self, message):
        kwargs = message.get('parameters', {})
        try:
            self.db[message['collection']].update(message['spec'], message['record'], safe=True, **kwargs)
        except:
            logger.error("Error writing to database: %s" % sys.exc_info()[0])
    
    def upsert(self, message):
        for record in message['records']:
            try:
                self.db[message['collection']].update({message['match_on']: record[message['match_on']]}, record, upsert=True, safe=True)
            except:
                logger.error("Error writing to database: %s" % sys.exc_info()[0])
    
    def find_and_modify(self, message):
        kwargs = message.get('parameters', {})
        kwargs['upsert'] = False
        return self.db[message['collection']].find_and_modify(message['search'], message['record'], **kwargs)
