GEVENT = False


def run():
    import settings

    from influenceexplorer import InfluenceExplorer
    api = InfluenceExplorer(settings.API_KEY, getattr(settings, 'AGGREGATES_API_BASE_URL', "http://transparencydata.com/api/1.0/"))

    entities = []
    for type in ['individual', 'organization', 'politician']:
        count = api.entities.count(type)
        for i in range(0, count, 10000):
            entities.extend(api.entities.list(i, i + 10000, type))

    from regs_common.util import get_db
    db = get_db()
    db.entities.ensure_index('td_type')

    from oxtail.matching.normalize import normalize_list
    for entity in entities:
        record = {
            '_id': entity['id'],
            'td_type': entity['type'],
            'td_name': entity['name'],
            'aliases': normalize_list([entity['name']] + entity['aliases'], entity['type'])
        }
        db.entities.save(record, safe=True)
        print "Saved %s as %s" % (record['aliases'][0], record['_id'])