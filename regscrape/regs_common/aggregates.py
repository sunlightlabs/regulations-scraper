import pymongo, bson, json
QUERY = {'deleted': False}
FIELDS = [
    '_id',
    'docket_id',
    'agency',
    'title',
    'details.Date_Posted',
    'details.Comment_Start_Date',
    'details.Comment_Due_Date',
    'type',
    'views.entities',
    'attachments.views.entities',
    'submitter_entities',
    'comment_on.document_id'
]

# class to work around the mincemeat requirement that the data be structured as a dictionary
class MongoSource(object):
    def __init__(self, db, query=QUERY, pretend=False):
        self.cache = {}
        self.db = db
        self.mongo_query = query
        self.pretend = pretend

    def __iter__(self):
        _cache = self.cache

        def gen():
            for doc in self.db.docs.find(self.mongo_query, FIELDS):
                doc_id = str(doc['_id'])
                _cache[doc_id] = doc

                if not self.pretend:
                    self.db.docs.update({'_id': doc_id}, {'$set': {'in_aggregates': True}}, multi=True, safe=True)
                yield doc_id

        return gen()

    def __getitem__(self, key):
        out = self.cache[key]
        del self.cache[key]
        return out

def mapfn(key, document):
    import isoweek
    from collections import defaultdict
    import itertools

    # pre-computed date data
    doc_type = document.get('type', None)
    details = document.get('details', {})
    doc_date = details.get('Date_Posted', None)
    doc_week = isoweek.Week(*(doc_date.isocalendar()[:-1])) if doc_date else None
    doc_week_range = (doc_week.monday().isoformat(), doc_week.sunday().isoformat()) if doc_week else None
    doc_month = doc_date.isoformat()[:7] if doc_date else None
    
    if 'Comment_Start_Date' in details and 'Comment_Due_Date' in details:
        comment_date_range = [details['Comment_Start_Date'].date().isoformat(), details['Comment_Due_Date'].date().isoformat()]
    else:
        comment_date_range = None

    ### COLLECTION: dockets ###
    docket_info = {
        'count': 1,
        'type_breakdown': {str(doc_type): 1},
        'doc_info': {
            'fr_docs': [{
                'date': doc_date.date().isoformat() if doc_date else None,
                'comment_date_range': comment_date_range,
                'type': doc_type,
                'id': document['_id'],
                'title': document['title']
            }] if doc_type in ['notice', 'rule', 'proposed_rule'] else [],
            'supporting_material': [{
                'date': doc_date.date().isoformat() if doc_date else None,
                'title': document['title'],
                'id': document['_id']
            }] if doc_type == 'supporting_material' else [],
            'other': [{
                'date': doc_date.date().isoformat() if doc_date else None,
                'title': document['title'],
                'id': document['_id']
            }] if doc_type == 'other' else []
        },
        'weeks': [(doc_week_range, 1)],
        'date_range': [doc_date, doc_date],
        'text_entities': {},
        'submitter_entities': {}
    }

    ### COLLECTION: agencies ###
    agency_info = {
        'count': 1,
        'date_range': [doc_date, doc_date],
        'months': [(doc_month, 1)],
        'type_breakdown': {str(doc_type): 1},
        'text_entities': {},
        'submitter_entities': {}
    }

    ### COLLECTION: docs (only writes to FR docs, only emits from public submissions) ###
    doc_info = {
        'count': 1,
        'weeks': [(doc_week_range, 1)],
        'date_range': [doc_date, doc_date],
        'text_entities': {},
        'submitter_entities': {},
        'recent_comments': [{
            'date': doc_date.date().isoformat() if doc_date else None,
            'title': document['title'],
            'id': document['_id']
        }] if doc_type == 'public_submission' else []
    }

    # entity data for dockets and agencies
    # text entities
    views = itertools.chain.from_iterable([document.get('views', [])] + [attachment.get('views', []) for attachment in document.get('attachments', [])])
    for view in views:
        for entity in view.get('entities', []):
            docket_info['text_entities'][entity] = 1
            agency_info['text_entities'][entity] = 1
            doc_info['text_entities'][entity] = 1

    # submitters
    for entity in document.get('submitter_entities', []):
        docket_info['submitter_entities'][entity] = 1
        agency_info['submitter_entities'][entity] = 1
        doc_info['submitter_entities'][entity] = 1

    yield ('dockets', document['docket_id']), docket_info
    yield ('agencies', document.get('agency', None)), agency_info

    comment_on_id = document.get('comment_on', {}).get('document_id', None)
    if document['type'] == 'public_submission' and comment_on_id:
        yield ('docs', comment_on_id), doc_info

    ### COLLECTION: entities ###
    entities = set(docket_info['text_entities'].keys())
    entities.update(docket_info['submitter_entities'].keys())

    for entity in entities:
        text_count = docket_info['text_entities'].get(entity, 0)
        submitter_count = docket_info['submitter_entities'].get(entity, 0)
        
        entity_info = {
            'text_mentions': {
                'count': text_count,
                'agencies': {document.get('agency', None): text_count},
                'dockets': {document['docket_id']: text_count},
                'months': [(doc_month, text_count)],
                'agencies_by_month': {document.get('agency', None): [(doc_month, text_count)]},
                'date_range': [doc_date, doc_date] if text_count else [None, None]
            },
            'submitter_mentions': {
                'count': submitter_count,
                'agencies': {document.get('agency', None): submitter_count},
                'dockets': {document['docket_id']: submitter_count},
                'months': [(doc_month, submitter_count)],
                'agencies_by_month': {document.get('agency', None): [(doc_month, submitter_count)]},
                'date_range': [doc_date, doc_date] if submitter_count else [None, None],
                'recent_comments': [{
                    'date': doc_date.date().isoformat() if doc_date else None,
                    'title': document['title'],
                    'id': document['_id']
                }] if doc_type == 'public_submission' and submitter_count else []
            }
        }
        yield ('entities', entity), entity_info


def reducefn(key, documents):
    from collections import defaultdict
    import datetime

    def min_date(*args):
        a = [arg for arg in args if arg is not None]
        if not a:
            return None
        else:
            return min(a)

    def max_date(*args):
        a = [arg for arg in args if arg is not None]
        if not a:
            return None
        else:
            return max(a)
    
    # Mongo loses track of the tuple-vs-list distinction, so fix that if necessary so dict() doesn't break
    def tf_dict(l):
        if not l:
            return {}
        try:
            return dict(l)
        except TypeError:
            return dict([(tuple(k) if type(k) == list else k, v) for k, v in l])

    ### COLLECTION: dockets ###
    if key[0] == 'dockets':
        out = {
            'count': 0,
            'type_breakdown': defaultdict(int),
            'doc_info': {
                'fr_docs': [],
                'supporting_material': [],
                'other': []
            },
            'weeks': defaultdict(int),
            'date_range': [None, None],
            'text_entities': defaultdict(int),
            'submitter_entities': defaultdict(int)
        }
        if documents:
            out['date_range'] = documents[0]['date_range']

        for value in documents:
            out['count'] += value['count']
            
            for doc_type, count in value['type_breakdown'].iteritems():
                out['type_breakdown'][doc_type] += count
            
            for doc_type in ['fr_docs', 'supporting_material', 'other']:
                out['doc_info'][doc_type].extend(value['doc_info'][doc_type])
            
            for week, count in tf_dict(value['weeks']).iteritems():
                out['weeks'][week] += count

            for entity, count in value['text_entities'].iteritems():
                out['text_entities'][entity] += count

            for entity, count in value['submitter_entities'].iteritems():
                out['submitter_entities'][entity] += count

            out['date_range'][0] = min_date(out['date_range'][0], value['date_range'][0])
            out['date_range'][1] = max_date(out['date_range'][1], value['date_range'][1])

        out['doc_info']['fr_docs'] = sorted(out['doc_info']['fr_docs'], key=lambda x: x['date'], reverse=True)
        out['doc_info']['supporting_material'] = sorted(out['doc_info']['supporting_material'], key=lambda x: x['date'], reverse=True)[:3]
        out['doc_info']['other'] = sorted(out['doc_info']['other'], key=lambda x: x['date'], reverse=True)[:3]

        out['weeks'] = sorted(out['weeks'].items(), key=lambda x: x[0][0] if x[0] else datetime.date.min.isoformat())
        return out

    ### COLLECTION: agencies ###
    if key[0] == 'agencies':
        out = {
            'count': 0,
            'type_breakdown': defaultdict(int),
            'months': defaultdict(int),
            'date_range': [None, None],
            'text_entities': defaultdict(int),
            'submitter_entities': defaultdict(int)
        }
        if documents:
            out['date_range'] = documents[0]['date_range']

        for value in documents:
            out['count'] += value['count']
            
            for doc_type, count in value['type_breakdown'].iteritems():
                out['type_breakdown'][doc_type] += count
                        
            for month, count in tf_dict(value['months']).iteritems():
                out['months'][month] += count

            for entity, count in value['text_entities'].iteritems():
                out['text_entities'][entity] += count

            for entity, count in value['submitter_entities'].iteritems():
                out['submitter_entities'][entity] += count

            out['date_range'][0] = min_date(out['date_range'][0], value['date_range'][0])
            out['date_range'][1] = max_date(out['date_range'][1], value['date_range'][1])

        out['months'] = sorted(out['months'].items(), key=lambda x: x[0] if x[0] else datetime.date.min.isoformat())
        return out

    ### COLLECTION: docs ###
    if key[0] == 'docs':
        out = {
            'count': 0,
            'weeks': defaultdict(int),
            'date_range': [None, None],
            'text_entities': defaultdict(int),
            'submitter_entities': defaultdict(int),
            'recent_comments': []
        }
        if documents:
            out['date_range'] = documents[0]['date_range']

        for value in documents:
            out['count'] += value['count']
            
            for week, count in tf_dict(value['weeks']).iteritems():
                out['weeks'][week] += count

            for entity, count in value['text_entities'].iteritems():
                out['text_entities'][entity] += count

            for entity, count in value['submitter_entities'].iteritems():
                out['submitter_entities'][entity] += count

            out['recent_comments'].extend(value['recent_comments'])

            out['date_range'][0] = min_date(out['date_range'][0], value['date_range'][0])
            out['date_range'][1] = max_date(out['date_range'][1], value['date_range'][1])

        out['recent_comments'] = sorted(out['recent_comments'], key=lambda x: x['date'], reverse=True)[:5]
        out['weeks'] = sorted(out['weeks'].items(), key=lambda x: x[0][0] if x[0] else datetime.date.min.isoformat())
        return out

    ### COLLECTION: entities ###
    if key[0] == 'entities':
        out = {
            'text_mentions': {
                'count': 0,
                'agencies': defaultdict(int),
                'dockets': defaultdict(int),
                'months': defaultdict(int),
                'agencies_by_month': defaultdict(lambda: defaultdict(int)),
                'date_range': [None, None]
            },
            'submitter_mentions': {
                'count': 0,
                'agencies': defaultdict(int),
                'dockets': defaultdict(int),
                'months': defaultdict(int),
                'agencies_by_month': defaultdict(lambda: defaultdict(int)),
                'date_range': [None, None],
                'recent_comments': []
            }
        }
        for value in documents:
            for mention_type in ['text_mentions', 'submitter_mentions']:
                out[mention_type]['count'] += value[mention_type]['count']
                for agency, count in value[mention_type]['agencies'].iteritems():
                    if value[mention_type]['agencies'][agency]:
                        out[mention_type]['agencies'][agency] += value[mention_type]['agencies'][agency]
                for docket, count in value[mention_type]['dockets'].iteritems():
                    if value[mention_type]['dockets'][docket]:
                        out[mention_type]['dockets'][docket] += value[mention_type]['dockets'][docket]
                months_dict = tf_dict(value[mention_type]['months'])
                for month, count in months_dict.iteritems():
                    if months_dict[month]:
                        out[mention_type]['months'][month] += months_dict[month]
                for agency, agency_months in value[mention_type]['agencies_by_month'].items():
                    agency_months_dict = tf_dict(value[mention_type]['agencies_by_month'][agency])
                    for month, count in agency_months_dict.iteritems():
                        if agency_months_dict[month]:
                            out[mention_type]['agencies_by_month'][agency][month] += agency_months_dict[month]
                out[mention_type]['date_range'][0] = min_date(out[mention_type]['date_range'][0], value[mention_type]['date_range'][0])
                out[mention_type]['date_range'][1] = max_date(out[mention_type]['date_range'][1], value[mention_type]['date_range'][1])

            out['submitter_mentions']['recent_comments'].extend(value['submitter_mentions']['recent_comments'])

        for mention_type in ['text_mentions', 'submitter_mentions']:
            out[mention_type]['months'] = sorted(out[mention_type]['months'].items(), key=lambda x: x[0] if x[0] else datetime.date.min.isoformat())
            for agency in out[mention_type]['agencies_by_month'].keys():
                out[mention_type]['agencies_by_month'][agency] = sorted(out[mention_type]['agencies_by_month'][agency].items(), key=lambda x: x[0] if x[0] else datetime.date.min.isoformat())
            # hack to make this defaultdict picklable
            out[mention_type]['agencies_by_month'] = tf_dict(out[mention_type]['agencies_by_month'])

        out['submitter_mentions']['recent_comments'] = sorted(out['submitter_mentions']['recent_comments'], key=lambda x: x['date'], reverse=True)[:5]
        
        return out

def run_aggregates(options):
    import settings

    db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]

    conditions = {'deleted': False, 'entities_last_extracted': {'$exists': True}}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['docket_id'] = options.docket
    if not options.process_all:
        conditions['in_aggregates'] = False

    import os, mincemeat, datetime
    db_file = options.resume_db if options.resume_db else '/tmp/test_%s.db' % os.getpid()
    print "Using file %s..." % db_file
    s = mincemeat.BatchSqliteServer(db_file, 1000, resume=bool(options.resume_db))
    s.mapfn = mapfn
    s.reducefn = reducefn
    s.datasource = MongoSource(db, conditions, pretend=options.pretend)

    results = s.run_server()

    stats_last_updated = datetime.datetime.now()
    if options.process_all:
        if options.pretend:
            for key, value in results:
                print key, value
            print 'Results printed.'
        else:
            print 'Writing results'
            for key, value in results:
                collection = key[0]
                _id = key[1]
                if not _id:
                    continue

                try:
                    value['stats_last_updated'] = stats_last_updated
                    db[collection].update(
                        {
                            '_id': _id
                        },
                        {
                            '$set': {'stats': value}
                        },
                        upsert=True,
                        safe=True
                    )
                except bson.errors.InvalidDocument:
                    print 'invalid'
                    print value
                    raise
            print 'Results written.'

            # since we've done everything, we know anything we haven't touched no longer has relevant stats
            print 'Deleting stats on entries that weren\'t updated.'
            for collection in ['dockets', 'docs', 'agencies', 'entities']:
                db[collection].update(
                    {
                        'stats': {'$exists': 1},
                        '$or': [
                            {'stats.stats_last_updated': {'$exists': 0}},
                            {'stats.stats_last_updated': {'$lt': stats_last_updated}}
                        ]
                    },
                    {
                        '$unset': {'stats': 1}
                    },
                    safe=True,
                    multi=True
                )
            print 'Stale stats deleted.'
    else:
        for key, value in results:
            collection = key[0]
            _id = key[1]
            if not _id:
                continue

            original = list(db[collection].find({'_id': _id}))
            if original and 'stats' in original[0] and original[0]['stats']:
                stats = reducefn(key, [original[0]['stats'], value])
            else:
                stats = value

            if options.pretend:
                print key, stats
            else:
                stats['stats_last_updated'] = stats_last_updated
                try:
                    db[collection].update(
                        {
                            '_id': _id
                        },
                        {
                            '$set': {'stats': stats}
                        },
                        upsert=True,
                        safe=True
                    )
                except bson.errors.InvalidDocument:
                    print 'invalid'
                    print stats
                    raise
        if options.pretend:
            print 'Incorporated results printed.'
        else:
            print 'Results incorporated.'