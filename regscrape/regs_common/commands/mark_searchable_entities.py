GEVENT = False

def run():
    from regs_models import Entity

    print "Updating entity search index..."

    # mark the ones that should be searchable but aren't as searchable
    Entity.objects(__raw__={
        'td_type': 'organization',
        'stats.count': {'$gt': 0},
        'searchable': False
    }).update(set__searchable=True, safe_update=True, multi=True)

    # mark the ones that are searchable but shouldn't be unsearchable
    Entity.objects(__raw__={
        '$or': [
            {'td_type': {'$ne': 'organization'}},
            {'stats.count': {'$not': {'$gt': 0}}}
        ],
        'searchable': True
    }).update(set__searchable=False, safe_update=True, multi=True)

    print "Update complete."