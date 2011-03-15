#!/usr/bin/env python

from gevent.monkey import patch_all
patch_all()

from scrapelib.actors import MasterActor
import time

master = MasterActor.start(3)
master.send_request_reply({'command': 'scrape', 'max': 100})
while True:
    time.sleep(3600)
