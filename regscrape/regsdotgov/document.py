import re
import urllib2, urllib3
import json
from regs_common.exceptions import DoesNotExist, RateLimitException
from pytz import timezone
import dateutil.parser
import datetime
from settings import RDG_API_KEY, DDG_API_KEY
from regs_models import *
from regs_common.util import listify
from name_cleaver import IndividualNameCleaver

DATE_FORMAT = re.compile('^(?P<month>\w+) (?P<day>\d{2}) (?P<year>\d{4}), at (?P<hour>\d{2}):(?P<minute>\d{2}) (?P<ampm>\w{2}) (?P<timezone>[\w ]+)$')

def check_date(value):
    if not value:
        return value
    
    # is it a date?
    date_match = DATE_FORMAT.match(value)
    if date_match:
        fields = date_match.groupdict()
        try:
            tz = timezone('US/%s' % fields['timezone'].split(' ')[0])
        except:
            tz = timezone('US/Eastern')
        
        value = datetime.datetime.strptime(
            '%s %s %s %s %s %s' % (fields['month'], fields['day'], fields['year'], fields['hour'], fields['minute'], fields['ampm']),
            '%B %d %Y %I %M %p'
        ).replace(tzinfo=tz)
    
    return value

RATE_CODES = set([503, 429])
def ddg_request(url, cpool=None):
    if cpool:
        response = cpool.urlopen("GET", url, headers={'Accept': 'application/json,*/*'}, preload_content=False)
        if response.status in RATE_CODES:
            if 'rate' in response.read().lower():
                raise RateLimitException()
        return response
    else:
        req = urllib2.Request(url, headers={'Accept': 'application/json,*/*'})
        try:
            response = urllib2.urlopen(req)
            return response
        except urllib2.HTTPError as e:
            if e.code in RATE_CODES and 'rate' in e.read().lower():
                raise RateLimitException()
            raise

def _v1_get_document(id, cpool=None):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    url = "http://regulations.gov/api/getdocument/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    if cpool:
        return cpool.urlopen("GET", url, preload_content=False)
    else:
        return urllib2.urlopen(url)

def _v2_get_document(id, cpool=None):
    url_args = {
        'api_key': DDG_API_KEY,
        'D': id
    }
    
    url = "http://api.data.gov/regulations/v2/document.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    return ddg_request(url, cpool)

def _v3_get_document(id, cpool=None):
    url_args = {
        'api_key': DDG_API_KEY,
        'documentId': id
    }
    
    url = "http://api.data.gov/regulations/beta/document.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    return ddg_request(url, cpool)

FORMAT_PARSER = re.compile(r"http://www\.regulations\.gov/api/contentStreamer\?objectId=(?P<object_id>[0-9a-z]+)&disposition=attachment&contentType=(?P<type>[0-9a-z]+)")
def make_view(format):
    match = FORMAT_PARSER.match(format).groupdict()
    match['url'] = 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (match['object_id'], match['type'])
    return View(**match)

NON_LETTERS = re.compile('[^a-zA-Z]+')
def _v1_scrape_document(id, cpool=None):
    raw = json.load(_v1_get_document(id, cpool))

    if 'error' in raw:
        raise DoesNotExist

    doc = raw['document']
    
    out = {
        # basic metadata
        'id': doc['documentId'],
        'title': unicode(doc.get('title', '')),
        'agency': doc['agencyId'],
        'docket_id': doc['docketId'],
        'type': DOC_TYPES[doc['documentType']],
        'topics': listify(doc['topics']) if 'topics' in doc and any(doc['topics']) else [],
        'fr_doc': doc['frDoc'],
        'scraped': 'yes',
        'deleted': False,
        
        # details
        'details': dict(
            [(NON_LETTERS.sub('_', meta['@name']), check_date(meta['$'])) for meta in listify(doc['metadata']['entry'])]
        ) if doc['metadata'] and 'entry' in doc['metadata'] else {},
        
        # views
        'views': [make_view(format) for format in listify(doc['fileFormats'])] if 'fileFormats' in doc and doc['fileFormats'] else []
    }
    if out['views']:
        out['object_id'] = out['views'][0].object_id
    
    # conditional fields
    if 'commentOn' in doc and doc['commentOn'] and \
        'documentId' in doc['commentOn'] and doc['commentOn']['documentId'] and \
        'documentType' in doc['commentOn'] and doc['commentOn']['documentType']:
        out['comment_on'] = {
            'agency': doc['commentOn']['agencyId'],
            'title': unicode(doc['commentOn']['title']),
            'type': DOC_TYPES[doc['commentOn']['documentType']],
            'fr_doc': doc['commentOn']['frDoc'],
            'document_id': doc['commentOn']['documentId']
        }
    
    if 'commentText' in doc and doc['commentText']:
        out['abstract'] = unicode(doc['commentText'])
    
    if 'attachments' in doc and doc['attachments']:
        attachments = []
        for attachment in listify(doc['attachments']['attachment']):
            attachment = Attachment(**{
                'title': unicode(attachment.get('title', '')),
                'abstract': unicode(attachment.get('abstract', '')),
                'views': [make_view(format) for format in listify(attachment['fileFormats'])] if 'fileFormats' in attachment and attachment['fileFormats'] else []
            })
            if attachment.views:
                attachment.object_id = attachment.views[0].object_id
            attachments.append(attachment)
        out['attachments'] = attachments
    
    if 'rin' in doc and doc['rin']:
        out['rin'] = doc['rin']
    
    return Doc(**out)

DOC_DETAILS_SPECIAL = set(('title', 'docketId', 'docketTitle', 'docketType', 'documentId', 'documentType', 'agencyName', 'agencyAcronym', 'submitterName', 'rin', 'comment', 'attachmentCount', 'numItemsRecieved'))
DOC_DETAIL_NAMES = {'docSubType': 'Document_Subtype', 'trackingNumber': 'Tracking_Number', 'cfrPart': 'CFR', 'organization': 'Organization_Name', 'zip': 'ZIP_Postal_Code', 'commentCategory': 'Category', 'govAgencyType': 'Government_Agency_Type'}
INCONSISTENT_DOC_TYPES = dict(DOC_TYPES, **{'PROPOSED_RULES': 'proposed_rule', 'RULES': 'rule', 'NOTICES': 'notice'})
def _v2v3_scrape_document(id, cpool=None):
    doc2 = json.load(_v2_get_document(id, cpool))
    doc3 = json.load(_v3_get_document(id, cpool))

    if 'code' in doc3:
        raise DoesNotExist

    # pull out what used to be called 'details'
    details = {}
    special = {}
    detail_template = set(['label', 'value'])
    for key, contents in doc3.iteritems():
        if type(contents) is dict and set(contents.keys()) == detail_template:
            if key in DOC_DETAILS_SPECIAL:
                special[key] = contents['value']
            else:
                detail_name = DOC_DETAIL_NAMES.get(key, NON_LETTERS.sub('_', contents['label']))
                details[detail_name] = contents['value']

    # deal with submitter name
    if 'submitterName' in special:
        parsed = IndividualNameCleaver(special['submitterName']).parse()
        if parsed.first is not None:
            details['First_Name'] = parsed.first
        if parsed.last is not None:
            details['Last_Name'] = parsed.last
        if parsed.middle is not None:
            middle = NON_LETTERS.sub('', parsed.middle)
            details['Middle_Name' if len(middle) > 1 else 'Middle_Initial'] = parsed.middle

    # deal with date types
    for new_label, old_label in (('commentDueDate', 'Comment_Due_Date'), ('commentStartDate', 'Comment_Start_Date'), ('postedDate', 'Date_Posted'), ('receivedDate', 'Received_Date'), ('effectiveDate', 'Effective_Date'), ('postMarkDate', 'Post_Mark_Date')):
        if new_label in doc3 and doc3[new_label]:
            details[old_label] = dateutil.parser.parse(doc3[new_label])

    # a couple of special cases
    if 'status' in doc3:
        details['Status'] = doc3['status']
    
    out = {
        # basic metadata
        'id': special['documentId'],
        'title': unicode(special.get('title', '')),
        'agency': special.get('agencyAcronym', ''),
        'docket_id': special.get('docketId', ''),
        'type': INCONSISTENT_DOC_TYPES[special['documentType']],
        'topics': doc3.get('topics', []),
        'scraped': 'yes',
        'deleted': False,
        
        # details
        'details': details,
        
        # views
        'views': [make_view(format) for format in doc2['renditionTypes']] if 'renditionTypes' in doc2 and doc2['renditionTypes'] else []
    }
    out['fr_doc'] = out['type'] in set(('rule', 'proposed_rule', 'notice'))
    if out['views']:
        out['object_id'] = out['views'][0].object_id
    
    # conditional fields
    if 'commentOnDoc' in doc3 and doc3['commentOnDoc'] and \
        'documentId' in doc3['commentOnDoc'] and doc3['commentOnDoc']['documentId'] and \
        'documentType' in doc3['commentOnDoc'] and doc3['commentOnDoc']['documentType']:
        out['comment_on'] = {
            'agency': doc3['commentOnDoc']['documentId'].split('-')[0],
            'title': unicode(doc3['commentOnDoc']['title']),
            'type': INCONSISTENT_DOC_TYPES[doc3['commentOnDoc']['documentType']],
            'document_id': doc3['commentOnDoc']['documentId']
        }
        out['comment_on']['fr_doc'] =  out['comment_on']['type'] in set(('rule', 'proposed_rule', 'notice'))
    
    if 'comment' in special and special['comment']:
        out['abstract'] = unicode(special['comment'])
    
    if 'attachments' in doc2 and doc2['attachments']:
        attachments = []
        for attachment in doc2['attachments']:
            attachment = Attachment(**{
                'title': unicode(attachment.get('title', '')),
                'abstract': unicode(attachment.get('abstract', '')),
                'views': [make_view(format) for format in attachment['formats']] if 'formats' in attachment and attachment['formats'] else []
            })
            if attachment.views:
                attachment.object_id = attachment.views[0].object_id
            attachments.append(attachment)
        out['attachments'] = attachments
    
    if 'rin' in special and special['rin']:
        out['rin'] = special['rin']
    
    return Doc(**out)

scrape_document = _v2v3_scrape_document



DOCKET_YEAR_FINDER = re.compile("[_-](\d{4})[_-]")

def _v1_get_docket(id, cpool=None):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    url = "http://regulations.gov/api/getdocket/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    if cpool:
        return cpool.urlopen("GET", url, preload_content=False)
    else:
        return urllib2.urlopen(url)

def _v3_get_docket(id, cpool=None):
    url_args = {
        'api_key': DDG_API_KEY,
        'docketId': id
    }
    
    url = "http://api.data.gov/regulations/beta/docket.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    return ddg_request(url, cpool)

def _v1_scrape_docket(id, cpool=None):
    raw = json.load(_v1_get_docket(id, cpool))

    if 'error' in raw:
        raise DoesNotExist

    docket = raw['docket']

    out = {
        'id': docket['docketId'],
        'agency': docket['agencyAcronym'],
        'title': unicode(docket['title']),
        
        # details
        'details': dict(
            [(NON_LETTERS.sub('_', meta['@name']), check_date(meta.get('$', None))) for meta in listify(docket['metadata']['entry'])]
        ) if docket['metadata'] and 'entry' in docket['metadata'] else {},
        
        'scraped': "yes",
    }
    
    if 'rin' in docket and docket['rin']:
        out['rin'] = docket['rin']
    
    year_match = DOCKET_YEAR_FINDER.search(id)
    if year_match and year_match.groups():
        out['year'] = int(year_match.groups()[0])
    else:
        out['year'] = None
        print 'Couldn\'t determine a date for docket %s' % id
    
    return Docket(**out)

DOCKET_DETAILS_SPECIAL = set(('agency', 'agencyAcronym'))
DOCKET_DETAIL_NAMES = {}
def _v3_scrape_docket(id, cpool=None):
    docket = json.loads(_v3_get_docket(id, cpool).read())

    if 'code' in docket:
        raise DoesNotExist

    # pull out what used to be called 'details'
    details = {}
    special = {}
    detail_template = set(['label', 'value'])
    for key, contents in docket.iteritems():
        if type(contents) is dict and set(contents.keys()) == detail_template:
            if key in DOCKET_DETAILS_SPECIAL:
                special[key] = contents['value']
            else:
                detail_name = DOCKET_DETAIL_NAMES.get(key, NON_LETTERS.sub('_', contents['label']))
                details[detail_name] = contents['value']

    out = {
        'id': docket['docketId'],
        'agency': docket.get('agencyAcronym', ''),
        'title': unicode(docket['title']),
        
        # details
        'details': details,
        
        'scraped': "yes",
    }
    
    if 'rin' in docket and docket['rin']:
        out['rin'] = docket['rin']
    
    year_match = DOCKET_YEAR_FINDER.search(id)
    if year_match and year_match.groups():
        out['year'] = int(year_match.groups()[0])
    else:
        out['year'] = None
        print 'Couldn\'t determine a date for docket %s' % id
    
    return Docket(**out)

scrape_docket = _v3_scrape_docket