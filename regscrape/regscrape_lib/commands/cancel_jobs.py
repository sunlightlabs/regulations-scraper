from regscrape_lib.util import get_db
import settings

def run():
    query = settings.FILTER.copy()
    query['_job_id'] = {'$exists': True}
    
    db = get_db()
    db.docs.update(query, {'$unset': {'_job_id': True}}, multi=True, safe=True)
    
    print 'Canceled all currently-assigned jobs.'
