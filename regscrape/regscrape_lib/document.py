import re
import urllib2
from regscrape_lib.pygwt.response import Response
from pytz import timezone
import datetime

DATE_FORMAT = re.compile('^(?P<month>\w+) (?P<day>\d{2}) (?P<year>\d{4}), at (?P<hour>\d{2}):(?P<minute>\d{2}) (?P<ampm>\w{2}) (?P<timezone>[\w ]+)$')
DOCUMENT_REQUEST_URL = "7|0|10|http://www.regulations.gov/Regs/|25E7F431559001DE380DFAB488A0FFF6|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|e2f277cdcbcdf9a6b0ef8c8a000d83de6df5a5f04d21d523ad7c83d889640418.e38Sb3aKaN8Oe3qLc40|gov.egov.erule.regs.shared.action.LoadDocumentDetailAction/1304900391|d|%s|1|2|3|4|2|5|6|7|8|9|10|"

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

def get_document(id, client):
    download = urllib2.urlopen(urllib2.Request(
        'http://www.regulations.gov/dispatch/LoadDocumentDetailAction',
        DOCUMENT_REQUEST_URL % id,
        {
            'Content-Type': "text/x-gwt-rpc; charset=utf-8",
            'X-GWT-Module-Base': client.js_url,
            'X-GWT-Permutation': '534129813C1882BA14066C262A32047D',
        }
    ), timeout=15)

    response = Response(client, download)
    return response.reader.read_object()

def scrape_document(id, client):
    raw = get_document(id, client)
    
    out = {
        # basic metadata
        'document_id': raw['document_id'],
        'title': raw['title'],
        'agency': raw['agency'],
        'docket_id': raw['docket_id'],
        'type': raw['type'],
        'topics': raw['topics'] if any(raw['topics']) else [],
        'object_id': raw['object_id'],
        'scraped': True,
        'deleted': False,
        
        # details
        'details': dict(
            [(meta['short_label'], check_date(meta['value'])) for meta in raw['metadata']]
        ) if raw['metadata'] else {},
        
        # views
        'views': [{
            'type': format,
            'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (raw['object_id'], format),
            'downloaded': False,
            'extracted': False,
            'ocr': False
        } for format in raw['formats']] if raw['formats'] else []
    }
    
    # conditional fields
    if 'comment_on' in raw and raw['comment_on']:
        out['comment_on'] = raw['comment_on']
    
    if 'comment_text' in raw and raw['comment_text']:
        out['abstract'] = raw['comment_text']
    
    if 'attachments' in raw and raw['attachments']:
        out['attachments'] = [{
            'title': attachment['title'],
            'abstract': attachment['abstract'],
            'object_id': attachment['object_id'],
            'views': [{
                'type': format,
                'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (attachment['object_id'], format),
                'downloaded': False,
                'extracted': False,
                'ocr': False
            } for format in attachment['formats']] if attachment['formats'] else []
        } for attachment in raw['attachments']]
    
    if 'rin' in raw and raw['rin']:
        out['rin'] = raw['rin']
    
    return out

DOCKET_REQUEST_URL = "7|0|9|http://www.regulations.gov/Regs/|25E7F431559001DE380DFAB488A0FFF6|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|e2f277cdcbcdf9a6b0ef8c8a000d83de6df5a5f04d21d523ad7c83d889640418.e38Sb3aKaN8Oe3qLc40|gov.egov.erule.regs.shared.action.LoadDocketFolderMetadataAction/386901167|%s|1|2|3|4|2|5|6|7|8|9|"
DOCKET_YEAR_FINDER = re.compile("[_-](\d{4})[_-]")

def get_docket(id, client):
    download = urllib2.urlopen(urllib2.Request(
        'http://www.regulations.gov/dispatch/LoadDocketFolderMetadataAction',
        DOCKET_REQUEST_URL % id,
        {
            'Content-Type': "text/x-gwt-rpc; charset=utf-8",
            'X-GWT-Module-Base': client.js_url,
            'X-GWT-Permutation': '534129813C1882BA14066C262A32047D',
        }
    ))

    response = Response(client, download)
    return response.reader.read_object()

def scrape_docket(id, client):
    raw = get_docket(id, client)

    out = {
        '_id': raw['docket_id'],
        'agency': raw['agency'],
        'title': raw['title'],
        
        # details
        'details': dict(
            [(meta['short_label'], check_date(meta['value'])) for meta in raw['metadata']]
        ) if raw['metadata'] else {},
        
        'scraped': True,
    }
    
    if 'rin' in raw and raw['rin']:
        out['rin'] = raw['rin']
    
    year_match = DOCKET_YEAR_FINDER.search(id)
    if year_match and year_match.groups():
        out['year'] = int(year_match.groups()[0])
    else:
        out['year'] = None
        print 'Couldn\'t determine a date for docket %s' % id
    
    return out