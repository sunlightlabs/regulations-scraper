GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing search data with new data.")

from regs_models import *
import urllib2, json, traceback, datetime, zlib, pymongo, pytz
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

    es = rawes.Elastic(getattr(settings, "ES_HOST", 'thrift://localhost:9500'), timeout=30.0)

    now = datetime.datetime.now()


    ### Dockets ###

    query = {'scraped': 'yes'}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['_id'] = options.docket
    if not options.process_all:
        query['in_search_index'] = False

    print "Adding dockets..."

    for docket in Docket.objects(__raw__=query):
        print 'trying', docket.id

        # build initial ES document
        es_doc = {
            'title': docket.title,
            'agency': docket.agency,
            'identifiers': [docket.id]
        }

        # add identifiers
        if docket.rin and docket.rin != "Not Assigned":
            es_doc['identifiers'].append(docket.rin)

        # save to es
        es_status = es.regulations.docket[str(docket.id)].put(data=es_doc)
        print 'saved %s to ES as %s' % (docket.id, es_status['_id'])

        # update main mongo doc
        docket.in_search_index = True

        # save back to Mongo
        docket.save()
        print "saved %s back to mongo" % docket.id


    ### Documents ###

    query = {'deleted': False, 'scraped': 'yes', '$nor': [{'views.extracted': 'no'},{'attachments.views.extracted':'no'}]}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['docket_id'] = options.docket
    if not options.process_all:
        query['in_search_index'] = False

    print "Adding documents..."

    for doc in Doc.objects(__raw__=query):
        print 'trying', doc.id
        if doc.renamed:
            print 'renamed', doc.id
            doc.in_search_index = True
            doc.save()
            continue
        
        # build initial ES document
        es_doc = {
            'docket_id': doc.docket_id,
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
            es_doc['identifiers'].append(doc.details['FR_Citation'].replate(' ', ''))

        # save to es
        es_status = es.regulations.document[str(doc.id)].put(data=es_doc, params={'parent': doc.docket_id})
        print 'saved %s to ES as %s' % (doc.id, es_status['_id'])

        # update main mongo doc
        doc.in_search_index = True

        # save back to Mongo
        doc.save()
        print "saved %s back to mongo" % doc.id