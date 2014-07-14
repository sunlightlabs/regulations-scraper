GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing search data with new data.")

from regs_models import *
import urllib2, json, traceback, datetime, zlib, pymongo, pytz, itertools
import rawes, requests, thrift

def run(options, args):
    while True:
        try:
            return add_to_search(options, args)
        except (pymongo.errors.OperationFailure, requests.exceptions.ConnectionError, thrift.transport.TTransport.TTransportException):
            print "Resetting..."
            continue

def add_to_search(options, args):
    import settings

    es = rawes.Elastic(getattr(settings, "ES_HOST", 'thrift://localhost:9500'), timeout=60.0)

    now = datetime.datetime.now()

    querysets = {}
    builders = {}
    metadata = {}

    PER_REQUEST = 200

    ### Dockets ###

    query = {'scraped': 'yes'}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['_id'] = options.docket
    if not options.process_all:
        query['in_search_index'] = False

    querysets['docket'] = Docket.objects(__raw__=query)

    def build_docket(docket):
        print 'preparing docket', docket.id

        # build initial ES document
        es_doc = {
            'title': docket.title,
            'agency': docket.agency,
            'identifiers': [docket.id]
        }

        # add identifiers
        if docket.rin and docket.rin != "Not Assigned":
            es_doc['identifiers'].append(docket.rin)

        return es_doc

    def get_docket_metadata(docket):
        return {'_index': 'regulations', '_type': 'docket', '_id': docket.id}

    builders['docket'] = build_docket
    metadata['docket'] = get_docket_metadata

    ### Documents ###

    query = {'deleted': False, 'scraped': 'yes', '$nor': [{'views.extracted': 'no'},{'attachments.views.extracted':'no'}]}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['docket_id'] = options.docket
    if not options.process_all:
        query['in_search_index'] = False

    querysets['document'] = Doc.objects(__raw__=query)

    def build_document(doc):
        print 'preparing document', doc.id
        if doc.renamed:
            print 'preparing', doc.id
            doc.in_search_index = True
            doc.save()
            return None
        
        # build initial ES document
        es_doc = {
            'docket_id': doc.docket_id if doc.docket_id else doc.id.rsplit("-", 1)[0],
            'comment_on': doc.comment_on.get('document_id', None) if doc.comment_on else None,
            'title': doc.title,
            'agency': doc.agency,
            'posted_date': doc.details['Date_Posted'].replace(tzinfo=pytz.UTC) if 'Date_Posted' in doc.details else None,
            'document_type': doc.type,
            'submitter_organization': doc.details.get('Organization_Name', None),
            'submitter_name': ' '.join(filter(bool, [doc.details.get('First_Name', None), doc.details.get('Middle_Initial', None), doc.details.get('Last_Name', None)])),
            'submitter_entities': doc.submitter_entities,
            'files': [],
            'analyses': [],
            'identifiers': [doc.id]
        }

        # add views (max of 5 to avoid pathological cases)
        for view in doc.views[:5]:
            if not view.content:
                continue
            es_doc['files'].append({
                "title": None,
                "abstract": None,
                "object_id": doc.object_id,
                "file_type": view.type,
                "view_type": "document_view",
                "text": view.as_text()[:100000],
                "entities": view.entities
            })

        # add attachments (max of 10 to avoid pathological cases)
        for attachment in doc.attachments[:10]:
            for view in attachment.views[:5]:
                if not view.content:
                    continue
                es_doc['files'].append({
                    "title": attachment.title,
                    "abstract": attachment.abstract,
                    "object_id": attachment.object_id,
                    "file_type": view.type,
                    "view_type": "attachment_view",
                    "text": view.as_text()[:100000],
                    "entities": view.entities
                })

        # add identifiers
        if doc.rin and doc.rin != "Not Assigned":
            es_doc['identifiers'].append(doc.rin)

        if doc.details.get('Federal_Register_Number', None):
            es_doc['identifiers'].append(doc.details['Federal_Register_Number'])

        if doc.details.get('FR_Citation', None):
            es_doc['identifiers'].append(doc.details['FR_Citation'].replace(' ', ''))

        return es_doc

    def get_document_metadata(doc):
        return {'_index': 'regulations', '_type': 'document', '_id': doc.id, '_parent': doc.docket_id if doc.docket_id else doc.id.rsplit("-", 1)[0]}

    builders['document'] = build_document
    metadata['document'] = get_document_metadata

    ### Actually do everything ###
    def flush(queue, ids, collection):
        # no need to do anything if there aren't any docs to add
        if not ids:
            return
        
        # save current queue to ES
        try:
            es_status = es._bulk.post(data="\n".join(queue))
            print 'saved %s to ES' % ", ".join(ids)
        except rawes.elastic_exception.ElasticException:
            # sometimes the bulk save fails for some reason; fall back to traditional iterative safe if so
            print 'falling back to iterative save...'
            # iterate over the queue pair-wise
            for command, record in itertools.izip(*[iter(queue)]*2):
                meta = json.loads(command)['index']
                params = {'parent': meta['_parent']} if '_parent' in meta else {}

                es_index = getattr(es, meta['_index'])
                es_type = getattr(es_index, meta['_type'])

                es_status = es_type[meta['_id']].put(data=record, params=params)
                print 'saved %s to ES as %s' % (meta['_id'], es_status['_id'])
        
        # update mongo docs
        collection.update({'_id': {'$in': ids}}, {'$set': {'in_search_index': True}}, multi=True, safe=True)

        print "saved %s back to mongo" % ", ".join(ids)
    
    counts = {'docket': 0, 'document': 0}
    for datatype in ('docket', 'document'):
        queue = []
        ids = []
        max_length = PER_REQUEST * 2
        for item in querysets[datatype]:
            record = builders[datatype](item)
            meta = metadata[datatype](item)

            if record:
                queue.append(json.dumps({'index':meta}))
                queue.append(json.dumps(record, default=es.json_encoder))
                ids.append(item.id)

            if len(queue) >= max_length:
                flush(queue, ids, querysets[datatype]._collection)
                counts[datatype] += len(ids)
                queue = []
                ids = []
        flush(queue, ids, querysets[datatype]._collection)
        counts[datatype] += len(ids)

    print "Done adding things to search: %s docket entries and %s document entries." % (counts['docket'], counts['document'])
    return counts