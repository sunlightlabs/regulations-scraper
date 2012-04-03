def run():
    from regscrape_lib.util import get_db
    from regscrape_lib.search import get_agencies
    from pymongo.errors import DuplicateKeyError
    
    db = get_db()
    new = 0
    
    print 'Fetching agencies...'
    agencies = get_agencies()

    print 'Saving agencies...'

    stop_words = ['the', 'and', 'of', 'on', 'in', 'for']
    for agency in agencies:
        name_parts = agency.name.split(' ')
        capitalized_parts = [name_parts[0].title()] + [word.title() if word.lower() not in stop_words else word.lower() for word in name_parts[1:]]
        name = ' '.join(capitalized_parts)

        record = {
            '_id': agency.abbr,
            'name': name
        }

        result = db.agencies.update(
            {
                '_id': record['_id']
            },
            {
                '$set': {'name': record['name']}
            },
            upsert=True,
            safe=True
        )
        new += 1 if 'updatedExisting' in result and not result['updatedExisting'] else 0
    
    print 'Iterated over %s agencies, of which %s were new.' % (len(agencies), new)
    
    return {'total': len(agencies), 'new': new}
