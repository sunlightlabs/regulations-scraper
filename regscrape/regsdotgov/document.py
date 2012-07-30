import re
import urllib2, urllib3
import json
from regs_common.exceptions import DoesNotExist
from pytz import timezone
import datetime
from settings import RDG_API_KEY
from models import *
from regs_common.util import listify

DATE_FORMAT = re.compile('^(?P<month>\w+) (?P<day>\d{2}) (?P<year>\d{4}), at (?P<hour>\d{2}):(?P<minute>\d{2}) (?P<ampm>\w{2}) (?P<timezone>[\w ]+)$')

def check_date(value):
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

def get_document(id, cpool=None):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    url = "http://regulations.gov/api/getdocument/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    if cpool:
        return cpool.urlopen("GET", url, preload_content=False)
    else:
        return urllib2.urlopen(url)

FORMAT_PARSER = re.compile(r"http://www\.regulations\.gov/api/contentStreamer\?objectId=(?P<object_id>[0-9a-z]+)&disposition=attachment&contentType=(?P<type>[0-9a-z]+)")
def make_view(format):
    match = FORMAT_PARSER.match(format).groupdict()
    match['url'] = 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (match['object_id'], match['type'])
    return View(**match)

NON_LETTERS = re.compile('[^a-zA-Z]+')
def scrape_document(id, cpool=None):
    raw = json.load(get_document(id, cpool))

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
            'title': doc['commentOn']['title'],
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

DOCKET_YEAR_FINDER = re.compile("[_-](\d{4})[_-]")

def get_docket(id, cpool=None):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    url = "http://regulations.gov/api/getdocket/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    if cpool:
        return cpool.urlopen("GET", url, preload_content=False)
    else:
        return urllib2.urlopen(url)

def scrape_docket(id, cpool=None):
    raw = json.load(get_docket(id, cpool))

    if 'error' in raw:
        raise DoesNotExist

    docket = raw['docket']

    out = {
        'id': docket['docketId'],
        'agency': docket['agencyId'],
        'title': docket['title'],
        
        # details
        'details': dict(
            [(NON_LETTERS.sub('_', meta['@name']), check_date(meta['$'])) for meta in listify(docket['metadata']['entry'])]
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