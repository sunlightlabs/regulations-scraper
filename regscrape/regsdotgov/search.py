import urllib2
import json
import datetime
from regs_common.util import listify
from regs_models import *

from settings import RDG_API_KEY, DDG_API_KEY
ARG_NAMES = {
    'agency': 'a',
    'docket': 'dktid'
}

FR_DOC_TYPES = set(['notice', 'rule', 'proposed_rule'])

def _v1_search(per_page, position, **args):
    url_args = {
        'api_key': RDG_API_KEY,
        'rpp': per_page,
        'po': position
    }

    for key, value in args.items():
        url_args[ARG_NAMES[key]] = value
    
    return urllib2.urlopen(
        "http://regulations.gov/api/documentsearch/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    )

def _v3_search(per_page, position, **args):
    url_args = {
        'api_key': DDG_API_KEY,
        'rpp': per_page,
        'po': position
    }

    for key, value in args.items():
        url_args[ARG_NAMES.get(key, key)] = value
    
    url = "http://api.data.gov/regulations/beta/documents.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    req = urllib2.Request(url, headers={'Accept': 'application/json,*/*'})
    return urllib2.urlopen(req)

search = _v3_search

def parse(file):
    data = open(file) if type(file) in (unicode, str) else file
    return json.load(data)

def _v1_iter_parse(file):
    data = parse(file)
    return iter(listify(data['searchresult']['documents']['document']))

def _v3_iter_parse(file):
    data = parse(file)
    return iter(data['documents'])

iter_parse = _v3_iter_parse

def result_to_model(doc, now=None):
    now = now if now is not None else datetime.datetime.now()

    return Doc(**{
        'id': doc['documentId'],
        'title': unicode(doc.get('title', '')),
        'docket_id': doc['docketId'],
        'agency': doc['agencyAcronym'],
        'type': DOC_TYPES[doc['documentType']],
        'fr_doc': DOC_TYPES[doc['documentType']] in FR_DOC_TYPES,
        'last_seen': now,
        'created': now
    })

# convenience function that strings them together
def parsed_search(per_page, position, client=None, **args):
    return parse(search(per_page, position, **args))

# use the search with an overridden client to get the agencies instead of the documents
def get_agencies():
    raise Exception("Haven't written this one yet")