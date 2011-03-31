from pykka.gevent import GeventActor
from selenium import webdriver
from listing import scrape_listing
import sys
import os
from pymongo import Connection
import time
from datetime import datetime, timedelta

from regscrape_lib import logger
from regscrape_lib.exceptions import Finished
from regscrape_lib.util import pseudoqs_encode
import settings

class MasterActor(GeventActor):
    def __init__(self, num_actors):
        self.num_actors = num_actors
        self.actors = []
        self.assignments = {}
        self.temporary_hopper = []
    
    def react(self, message):
        if message.get('command') == 'scrape':
            logger.info('Starting scrape...')
            self.current = 0
            self.max = message.get('max')
            self.db = DbActor.start()
            for i in range(self.num_actors):
                actor = ScraperActor.start(self.actor_ref, self.db)
                self.actors.append(actor)
        elif message.get('command') == 'ready':
            actor = message.get('actor')
            if actor.actor_urn in self.assignments:
                del self.assignments[actor.actor_urn]
            
            new_url = self.get_url()
            
            if new_url:
                actor.send_one_way({'command': 'scrape_listing', 'url': new_url})
                self.assignments[actor.actor_urn] = {'actor': actor, 'url': new_url, 'assigned': datetime.now()}
            else:
                self.shutdown(actor)
        elif message.get('command') == 'finished':
            message_position = int(message.get('url').split('=')[-1])
            if self.max == 0 or message_position < self.max:
                self.max = message_position
            self.shutdown(message.get('actor'))
        elif message.get('command') == 'tick':
            now = datetime.now()
            diff = timedelta(seconds=settings.MAX_WAIT)
            for urn, record in self.assignments.items():
                if now - record['assigned'] > diff:
                    logger.warn("Actor %s has been working on its assigned URL for longer than the maximum-allowed time; resetting browser and reassigning %s." % (urn, record['url']))
                    self.shutdown(record['actor'])
                    del self.assignments[urn]
                    
                    self.temporary_hopper.append(record['url'])
                    
                    replacement = ScraperActor.start(self.actor_ref, self.db)
                    
                    self.actors.append(replacement)
    
    def get_url(self):
        if len(self.temporary_hopper) > 0:
            return self.temporary_hopper.pop(0)
        elif self.max == 0 or self.current <= self.max:
            url = "http://%s/#!searchResults;so=ASC;sb=postedDate;%s;rpp=%s;po=%s" % (settings.TARGET_SERVER, pseudoqs_encode(settings.SEARCH), settings.PER_PAGE, self.current)
            self.current += settings.PER_PAGE
            return url
        else:
            return None
    
    def shutdown(self, actor):
        try:
            actor.send_one_way({'command': 'shutdown'})
        except:
            pass
        time.sleep(0.5)
        actor.stop()
        self.actors.remove(actor)
        if len(self.actors) == 0:
            logger.info('Done')
            time.sleep(5)
            os._exit(os.EX_OK)

class ScraperActor(GeventActor):
    def __init__(self, master, db):
        self.browser = getattr(webdriver, settings.BROWSER['driver'])(**(settings.BROWSER.get('kwargs', {})))
        self.master = master
        self.db = db
        
        self.master.send_one_way({'command': 'ready', 'actor': self.actor_ref})
    
    def react(self, message):
        if message.get('command') == 'scrape_listing':
            docs = None
            for i in range(2):
                try:
                    docs, errors = scrape_listing(self.browser, message.get('url'))
                    break
                except Finished:
                    logger.info('Reached end of search results; terminating.')
                    self.master.send_one_way({'command': 'finished', 'actor': self.actor_ref, 'url': message.get('url')})
                    return
                except:
                    pass
            if docs:
                self.write('docs', docs)
                if errors:
                    self.write('errors', errors)
            else:
                logger.error('Gave up on listing %s' % message['url'])
                self.write('errors', [{'type': 'listing', 'reason': 'Failed to scrape listing', 'url': message.get('url')}])
            self.master.send_one_way({'command': 'ready', 'actor': self.actor_ref})
        elif message.get('command') == 'shutdown':
            self.browser.quit()
    
    def write(self, collection, records):
        self.db.send_one_way({'command': 'write', 'collection': collection, 'records': records})

class DbActor(GeventActor):
    def __init__(self):
        self.db = Connection('localhost', 27017)['regulations']
        if settings.CLEAR_FIRST:
            self.db.docs.drop()
            self.db.errors.drop()
    
    def react(self, message):
        if message.get('command') == 'write':
            try:
                self.db[message['collection']].insert(message['records'], safe=True)
            except:
                logger.error("Error writing to database: %s" % sys.exc_info()[0])
