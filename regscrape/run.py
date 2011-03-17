#!/usr/bin/env python

from gevent.monkey import patch_all
patch_all()

from regscrape_lib.actors import MasterActor
import time

import settings

master = MasterActor.start(settings.INSTANCES)
master.send_request_reply({'command': 'scrape', 'max': settings.MAX_RECORDS})
while True:
    time.sleep(3600)
