def run():
    from regscrape_lib.util import get_db
    import settings
    
    query = settings.FILTER.copy()
    query['scraped'] = 'failed'
    
    db = get_db()
    db.docs.update(query, {'$set': {'scraped': False}}, multi=True, safe=True)
    
    print 'Reset all failed scrapes.'
