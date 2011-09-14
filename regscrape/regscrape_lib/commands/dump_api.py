import urllib2
import settings
import os
from regscrape_lib.regs_gwt.regs_client import RegsClient
from regscrape_lib.util import download
from regscrape_lib.search import search

def run():
    client = RegsClient()
    position = settings.DUMP_START
    num_digits = len(str(settings.DUMP_END))
    while position <= settings.DUMP_END:
        print "Downloading page %s of %s..." % ((position / settings.DUMP_INCREMENT) + 1, ((settings.DUMP_END - settings.DUMP_START) / settings.DUMP_INCREMENT) + 1)
        download(
            search(settings.DUMP_INCREMENT, position, client),
            os.path.join(settings.DUMP_DIR, 'dump_%s.gwt' % str(position).zfill(num_digits)),
        )
        
        position += settings.DUMP_INCREMENT
