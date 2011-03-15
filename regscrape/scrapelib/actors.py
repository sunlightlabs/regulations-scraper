from pykka.gevent import GeventActor
from selenium import webdriver
from listing import scrape_listing
import sys

class MasterActor(GeventActor):
    def __init__(self, num_actors):
        print 'hello'
        self.num_actors = num_actors
        self.actors = []
    
    def react(self, message):
        if message.get('command') == 'scrape':
            print 'scraping'
            self.current = 0
            self.max = message.get('max')
            for i in range(self.num_actors):
                actor = ScraperActor.start(self.actor_ref)
                actor.send_one_way({'command': 'scrape_listing', 'url': self.get_url()})
                self.actors.append(actor)
        elif message.get('command') == 'done':
            print 'got done'
            new_url = self.get_url()
            actor = message.get('actor')
            if new_url:
                actor.send_one_way({'command': 'scrape_listing', 'url': new_url})
            else:
                actor.send_request_reply({'command': 'shutdown'})
                actor.stop()
                self.actors.remove(actor)
                if len(self.actors) == 0:
                    print 'Done'
                    sys.exit(0)
    
    def get_url(self):
        if self.current <= self.max:
            url = "http://www.regulations.gov/#!searchResults;dct=PS;rpp=10;po=%s" % self.current
            self.current += 10
            return url
        else:
            return None

class ScraperActor(GeventActor):
    def __init__(self, master):
        self.browser = webdriver.Remote(browser_name='firefox')
        self.master = master
    
    def react(self, message):
        if message.get('command') == 'scrape_listing':
            docs = None
            for i in range(2):
                try:
                    docs, errors = scrape_listing(self.browser, message.get('url'))
                    break
                except:
                    pass
            if docs == None:
                print 'gave up on listing %s' % url
            print 'sending done'
            self.master.send_one_way({'command': 'done', 'actor': self.actor_ref})
        elif message.get('command') == 'shutdown':
            self.browser.quit()