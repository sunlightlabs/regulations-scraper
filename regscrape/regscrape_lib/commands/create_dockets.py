from regscrape_lib.util import get_db
from pymongo.errors import DuplicateKeyError

def run():
    db = get_db()
    new = 0
    
    print 'Starting docket query...'
    docket_ids = db.docs.distinct('docket_id')
    for docket_id in docket_ids:
        try:
            db.dockets.save({
                'docket_id': docket_id,
                'scraped': False
            }, safe=True)
            new += 1
        except:
            # we already have this one
            pass
    
    print 'Iterated over %s dockets, of which %s were new.' % (len(docket_ids), new)
