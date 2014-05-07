GEVENT = False

import os
import subprocess
import settings
import sys
from search import parsed_search, result_to_model
import pytz
import datetime
import operator
import time
import json
import re
import itertools
import urllib2, httplib
from regs_models import *

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-s", "--since", dest="since", action="store", type="string", default=None, help="Manually specify search start date.")

def run(options, args):
    print 'Retrieving current document IDs...'
    
    # HACK - pull ids via shell because doing it in Python is slow
    count_proc = subprocess.Popen(
        ["mongo", settings.DB_NAME] +\
            list(itertools.chain.from_iterable([("--%s" % key, str(value)) for key, value in settings.DB_SETTINGS.items()])) +\
            ["--quiet", "--eval", "printjson(db.docs.find({deleted:false},{_id:1}).map(function(i){return i._id;}))"],
        stdout=subprocess.PIPE
    )
    ids = set(json.load(count_proc.stdout))

    now = datetime.datetime.now()

    if options.since:
        most_recent = datetime.datetime.strptime(options.since, "%Y-%m-%d")
        print "Done; start date manually set to %s and total documents indexed is %s." % (most_recent.isoformat(), len(ids))
    else:
        print "Retrieving date of most recent document..."
        recent_agg = Doc._get_collection().aggregate([
            {
                "$group": {
                    "_id": 0,
                    "max": {
                        "$max": "$details.Date_Posted"
                    }
                }
            }
        ]);
        most_recent = recent_agg['result'][0]['max']

        print "Done; last document is from %s and total documents indexed is %s." % (most_recent.isoformat(), len(ids))
        
        if most_recent > now:
            most_recent = now
            print "Overriding most recent to now."
        
    search_args = {
        # date range from one day before the most recent until one day after now
        "pd": "-".join([d.strftime("%m/%d/%y") for d in (most_recent - datetime.timedelta(days=1), now + datetime.timedelta(days=1))]),

        # order ascending by posted date to reduce pagination errors
        "sb": "postedDate",
        "so": "ASC"
    }

    # start new dumps
    position = 0
    increment = 1000
    stats = {'pages_downloaded': 0, 'new_records': 0, 'existing_records': 0, 'failed_saves': 0}
    total = parsed_search(1, 0, **search_args)['totalNumRecords']
    while position <= total:
        page = None
        for i in range(3):
            try:
                current_str = (position / increment) + 1
                total_str = '?' if total == 1 else (total / increment) + 1
                print "Downloading page %s of %s..." % (current_str, total_str)
                
                page = parsed_search(increment, position, **search_args)

                stats['pages_downloaded'] += 1
                break
            except (urllib2.HTTPError, httplib.HTTPException) as e:
                if i < 2:
                    if hasattr(e, 'code') and e.code in (503, 429) and 'rate' in e.read().lower():
                        print 'Download failed because of rate limiting; will retry in an hour...'
                        time.sleep(3600)
                    else:
                        print 'Download failed; will retry in 10 seconds...'
                        time.sleep(10)
                else:
                    print 'System troubles; giving up.'
                    raise

        for result in page.get('documents', []):
            if result['documentId'] in ids:
                stats['existing_records'] += 1
            else:
                if result.get('documentStatus', None) == "Withdrawn":
                    continue
                
                db_doc = result_to_model(result, now=now)
                
                try:
                    db_doc.save()
                    stats['new_records'] += 1
                except:
                    print "Failed to save document %s" % db_doc.id
                    stats['failed_saves'] += 1
        
        position += increment
    
    print "Wrote %s new records, encountered %s existing records, and had %s failed saves." % (stats['new_records'], stats['existing_records'], stats['failed_saves'])
    
    return stats