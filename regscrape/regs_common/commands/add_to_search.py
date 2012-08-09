GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing search data with new data.")

from regs_models import *
import urllib2, json, traceback, datetime, zlib, pymongo
import pyes

def run(options, args):
    while True:
        try:
            return add_to_search(options, args)
        except (pymongo.errors.OperationFailure, pyes.exceptions.NoServerAvailable):
            print "Resetting..."
            continue

def add_to_search(options, args):
    es = pyes.ES(['localhost:9500'], timeout=30.0)

    now = datetime.datetime.now()

    query = {'deleted': False, 'scraped': 'yes', '$nor': [{'views.extracted': 'no'},{'attachments.views.extracted':'no'}]}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['docket_id'] = options.docket
    if not options.process_all:
        query['in_search_index'] = False

    for doc in Doc.objects(__raw__=query):
        print 'trying', doc.id
        if doc.renamed:
            print 'renamed', doc.id
            continue
        
        # build initial ES document
        es_doc = {
            'docket_id': doc.docket_id,
            'comment_on': doc.comment_on.get('document_id', None) if doc.comment_on else None,
            'title': doc.title,
            'agency': doc.agency,
            'posted_date': doc.details.get('Date_Posted', None),
            'document_type': doc.type,
            'submitter_organization': doc.details.get('Organization_Name', None),
            'submitter_name': ' '.join(filter(bool, [doc.details.get('First_Name', None), doc.details.get('Middle_Initial', None), doc.details.get('Last_Name', None)])),
            'submitter_entities': doc.submitter_entities,
            'files': []
        }

        # add views
        for view in doc.views:
            if not view.content:
                continue
            es_doc['files'].append({
                "title": None,
                "abstract": None,
                "object_id": doc.object_id,
                "file_type": view.type,
                "view_type": "document_view",
                "text": view.as_text(),
                "entities": view.entities
            })

        # add attachments
        for attachment in doc.attachments:
            for view in attachment.views:
                if not view.content:
                    continue
                es_doc['files'].append({
                    "title": attachment.title,
                    "abstract": attachment.abstract,
                    "object_id": attachment.object_id,
                    "file_type": view.type,
                    "view_type": "attachment_view",
                    "text": view.as_text(),
                    "entities": view.entities
                })

        # save to es
        es_status = es.index(es_doc, 'regulations', 'document', id=str(doc.id))
        print 'saved %s to ES as %s' % (doc.id, es_status['_id'])

        # update main mongo doc
        doc.in_search_index = True

        # save back to Mongo
        doc.save()
        print "saved %s back to mongo" % doc.id