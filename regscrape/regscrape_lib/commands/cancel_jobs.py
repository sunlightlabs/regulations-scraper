def run():
    from regscrape_lib.util import get_db
    import settings
    
    query = settings.FILTER.copy()
    query['_scraping'] = {'$exists': True}
    
    db = get_db()
    db.docs.update(query, {'$unset': {'_scraping': True}}, multi=True, safe=True)
    
    print 'Canceled all currently-assigned jobs.'
