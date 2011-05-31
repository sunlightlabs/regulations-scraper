from regscrape_lib.util import get_db
import settings

def run():
    query = settings.FILTER.copy()
    query['scrape_failed'] = True
    
    db = get_db()
    db.docs.update(query, {'$unset': {'scrape_failed': True}}, multi=True, safe=True)
    
    print 'Reset all failed scrapes.'
