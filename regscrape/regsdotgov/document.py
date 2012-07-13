import re
import urllib2
import json
from regs_common.exceptions import DoesNotExist
from pytz import timezone
import datetime
from settings import RDG_API_KEY
from models import *
from regs_common.util import listify

DATE_FORMAT = re.compile('^(?P<month>\w+) (?P<day>\d{2}) (?P<year>\d{4}), at (?P<hour>\d{2}):(?P<minute>\d{2}) (?P<ampm>\w{2}) (?P<timezone>[\w ]+)$')
DOCUMENT_REQUEST_URL = "7|0|10|http://www.regulations.gov/Regs/|C006AEC3A690AD65DC608DB5A8DBA002|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|6dfecc389e4d86b4e63e6b459bfa29e673a88555d93b469fc5ed362134c31079.e38Sb3aKaN8Oe3uRai0|gov.egov.erule.regs.shared.action.LoadDocumentDetailAction/1304900391|d|%s|1|2|3|4|2|5|6|7|8|9|10|"

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

def get_document(id):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    return urllib2.urlopen(
        "http://regulations.gov/api/getdocument/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    )

FORMAT_PARSER = re.compile(r"http://www\.regulations\.gov/api/contentStreamer\?objectId=(?P<object_id>[0-9a-z]+)&disposition=attachment&contentType=(?P<type>[0-9a-z]+)")
def make_view(format):
    match = FORMAT_PARSER.match(format).groupdict()
    return View(**match)

NON_LETTERS = re.compile('[^a-zA-Z]+')
def scrape_document(id):
    raw = json.load(get_document(id))

    if 'error' in raw:
        raise DoesNotExist

    doc = raw['document']
    
    out = {
        # basic metadata
        'id': doc['documentId'],
        'title': doc['title'],
        'agency': doc['agencyId'],
        'docket_id': doc['docketId'],
        'type': doc['documentType'].lower().replace(' ', '_'),
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
    if 'commentOn' in doc and doc['commentOn'] and 'documentId' in doc['commentOn'] and doc['commentOn']['documentId']:
        out['commentOn'] = {
            'agency': doc['commentOn']['agencyId'],
            'title': doc['commentOn']['title'],
            'type': doc['commentOn']['documentType'].lower().replace(' ', '_'),
            'fr_doc': doc['commentOn']['frDoc'],
            'document_id': doc['commentOn']['documentId']
        }
    
    if 'commentText' in doc and doc['commentText']:
        out['abstract'] = doc['commentText']
    
    if 'attachments' in doc and doc['attachments']:
        attachments = []
        for attachment in listify(doc['attachments']['attachment']):
            attachment = Attachment(**{
                'title': attachment['title'],
                'abstract': attachment['abstract'],
                'views': [make_view(format) for format in listify(attachment['fileFormats'])] if 'fileFormats' in attachment and attachment['fileFormats'] else []
            })
            if attachment.views:
                attachment.object_id = attachment.views[0].object_id
            attachments.append(attachment)
        out['attachments'] = attachments
    
    if 'rin' in doc and doc['rin']:
        out['rin'] = doc['rin']
    
    return Doc(**out)

DOCKET_REQUEST_URL = "7|0|9|http://www.regulations.gov/Regs/|C006AEC3A690AD65DC608DB5A8DBA002|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|6dfecc389e4d86b4e63e6b459bfa29e673a88555d93b469fc5ed362134c31079.e38Sb3aKaN8Oe3uRai0|gov.egov.erule.regs.shared.action.LoadDocketFolderMetadataAction/386901167|%s|1|2|3|4|2|5|6|7|8|9|"
DOCKET_YEAR_FINDER = re.compile("[_-](\d{4})[_-]")

def get_docket(id):
    url_args = {
        'api_key': RDG_API_KEY,
        'D': id
    }
    
    return urllib2.urlopen(
        "http://regulations.gov/api/getdocket/v1.json?" + '&'.join(['%s=%s' % arg for arg in url_args.items()])
    )

def scrape_docket(id):
    raw = json.load(get_docket(id))

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