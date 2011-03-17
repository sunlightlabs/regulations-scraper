from pykka.gevent import GeventActor
from selenium import webdriver
from listing import scrape_listing
import sys
import os
from pymongo import Connection
import time

from regscrape_lib import logger
import settings

class MasterActor(GeventActor):
    def __init__(self, num_actors):
        self.num_actors = num_actors
        self.actors = []
    
    def react(self, message):
        if message.get('command') == 'scrape':
            logger.info('Starting scrape...')
            self.current = 0
            self.max = message.get('max')
            self.db = DbActor.start()
            for i in range(self.num_actors):
                actor = ScraperActor.start(self.actor_ref, self.db)
                actor.send_one_way({'command': 'scrape_listing', 'url': self.get_url()})
                self.actors.append(actor)
        elif message.get('command') == 'done':
            new_url = self.get_url()
            actor = message.get('actor')
            if new_url:
                actor.send_one_way({'command': 'scrape_listing', 'url': new_url})
            else:
                actor.send_request_reply({'command': 'shutdown'})
                actor.stop()
                self.actors.remove(actor)
                if len(self.actors) == 0:
                    logger.info('Done')
                    time.sleep(5)
                    os._exit(os.EX_OK)
    
    def get_url(self):
        if self.current <= self.max:
            url = "http://%s/#!searchResults;dct=PS;rpp=%s;po=%s" % (settings.TARGET_SERVER, settings.PER_PAGE, self.current)
            self.current += settings.PER_PAGE
            return url
        else:
            return None

class ScraperActor(GeventActor):
    def __init__(self, master, db):
        self.browser = webdriver.Remote(browser_name='firefox')
        self.master = master
        self.db = db
    
    def react(self, message):
        if message.get('command') == 'scrape_listing':
            docs = None
            for i in range(2):
                try:
                    docs, errors = scrape_listing(self.browser, message.get('url'))
                    break
                except:
                    pass
            if docs:
                self.write('docs', docs)
                if errors:
                    self.write('errors', errors)
            else:
                logger.error('Gave up on listing %s' % url)
                self.write('errors', [{'type': 'listing', 'reason': 'Failed to scrape listing', 'url': message.get('url')}])
            self.master.send_one_way({'command': 'done', 'actor': self.actor_ref})
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
