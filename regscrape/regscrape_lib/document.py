#!/usr/bin/env python

import urllib, urlparse, json, re, datetime, sys

from regscrape_lib.util import get_elements
from pytz import timezone

from regscrape_lib import logger
import settings

from regscrape_lib.exceptions import StillNotFound, DoesNotExist

FORMAT_OVERRIDES = {'html': 'xml', 'doc': 'msw8', 'crtxt': 'crtext'}

NON_LETTERS = re.compile('[^\w]')

DATE_FORMAT = re.compile('^(?P<month>\w+) (?P<day>\d{2}) (?P<year>\d{4}), at (?P<hour>\d{2}):(?P<minute>\d{2}) (?P<ampm>\w{2}) (?P<timezone>[\w ]+)$')

def scrape_document(browser, id, visit_first=True, document={}):
    if visit_first:
        browser.get('http://%s/#!documentDetail;D=%s' % (settings.TARGET_SERVER, id))
    
    # document id
    try:
        doc_id = get_elements(browser, '#mainContentTop .Gsqk2cPB + .gwt-InlineLabel', lambda elements: len(elements) > 0 and elements[0].text == id)
    except StillNotFound as s:
        # maybe there's no such document?
        title = get_elements(browser, '#mainContentTop > h4', lambda elements: len(elements) > 0 and elements[0].text.strip() == 'Document does not exist')
        if title:
            raise DoesNotExist
        else:
            raise s
    
    document['document_id'] = doc_id[0].text
    
    # document type, etc.
    comment_on_type = get_elements(browser, '#mainContentTop .gwt-InlineHyperlink', optional=True)
    if comment_on_type:
        comment_on = {
            'type': comment_on_type[0].text,
            'id': comment_on_type[0].get_attribute('href').split('=')[1],
        }
        comment_on_label = get_elements(browser, '#mainContentTop .gwt-InlineHyperlink + .gwt-InlineLabel')
        comment_on['title'] = comment_on_label[0].text
        
        document['comment_on'] = comment_on
    
    # Docket info
    docket_id = get_elements(browser, '#mainContentTop .Gsqk2cBO a.gwt-Anchor')
    document['docket_id'] = docket_id[0].text
    
    topics = get_elements(browser, '#mainContentTop > span:last-child')
    if topics[0].get_attribute('class') == 'Gsqk2cDO':
        document['topics'] = []
    else:
        document['topics'] = topics[0].text.split(', ')
    
    # Details
    get_elements(browser, '#mainContentBottom .gwt-DisclosurePanel a.header')[0].click()
    
    details = {}
    cells = get_elements(browser, '#mainContentBottom .gwt-DisclosurePanel table.Gsqk2cJC tr td')
    for idx in range(0, len(cells), 2):
        title = NON_LETTERS.sub('_', cells[idx].text[:-1].replace('.', '').lower())
        content = cells[idx + 1].text.strip()
        
        # is it a date?
        date_match = DATE_FORMAT.match(content)
        if date_match:
            fields = date_match.groupdict()
            try:
                tz = timezone('US/%s' % fields['timezone'].split(' ')[0])
            except:
                tz = timezone('US/Eastern')
            
            content = datetime.datetime.strptime(
                '%s %s %s %s %s %s' % (fields['month'], fields['day'], fields['year'], fields['hour'], fields['minute'], fields['ampm']),
                '%B %d %Y %I %M %p'
            ).replace(tzinfo=tz)
            
        details[title] = content
    document['details'] = details
    
    # Attachments
    preview_url = get_elements(browser, '#mainContentBottom .gwt-Frame')[0].get_attribute('src')
    document['preview_url'] = preview_url
    
    views = []
    
    url = urlparse.urlparse(preview_url)
    qs = dict(urlparse.parse_qsl(url.query))
    qs['disposition'] == 'attachment'
    
    if 'views' not in document:
        view_selector = '#mainContentBottom > div > .gwt-Image'
        view_buttons = get_elements(browser, view_selector, optional=True)
        view_data = []
        try:
            view_data = json.loads(browser.execute_script("""
                return JSON.stringify(
                    Array.prototype.slice.call(document.querySelectorAll('%s')).map(function(el) {
                        return el.__listener.Gc.e.b.e.slice(-1)[0][0].g.b[0]
                    })
                )
            """ % view_selector))
        except:
            pass
        
        if len(view_data) == len(view_buttons):
            for view in view_data:
                views.append({
                    'type': view['d'],
                    'url': 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (view['c'], view['d']),
                    'downloaded': False
                })
        else:
            # fallback to old-style guessing with a warning
            logger.warn("Falling back to old-style URL guessing on document %s" % id)
            
            for button in view_buttons:
                title = button.get_attribute('title')
                format = title.split(' ')[-1]
                download_format = format
                if format in FORMAT_OVERRIDES:
                    download_format = FORMAT_OVERRIDES[format]
                
                qs['contentType'] = download_format    
                views.append({
                    'type': download_format,
                    'url': 'http://www.regulations.gov/contentStreamer?%s' % urllib.urlencode(qs),
                    'downloaded': False
                })
        
        document['views'] = views
    
    attachment_links = get_elements(browser, '#mainContentBottom .Gsqk2cNN a.gwt-InlineHyperlink, #mainContentBottom .Gsqk2cNN img.gwt-Image', optional=True)
    if attachment_links:
        attachments = []
        for idx in range(0, len(attachment_links), 2):
            attachments.append({
                'document_id': attachment_links[idx].text,
                'type': attachment_links[idx + 1].get_attribute('title').split(' ')[-1]
            })
        document['attachments'] = attachments
    
    document['scraped'] = True
    
    return document
