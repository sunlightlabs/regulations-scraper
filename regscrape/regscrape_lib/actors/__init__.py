from pykka.gevent import GeventActor

class BaseActor(GeventActor):
    def on_receive(self, message):
        command = message.get('command', None)
        if command and not command.startswith('_'):
            method = getattr(self, command, None)
            if callable(method):
                return method(message)

from regscrape_lib.actors.master import MasterActor
from regscrape_lib.actors.scrapers import *
