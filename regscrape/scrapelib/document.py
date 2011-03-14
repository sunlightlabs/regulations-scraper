#!/usr/bin/env python

import urllib, urlparse

from scrapelib.util import get_elements

FORMAT_OVERRIDES = {'html': 'xml', 'doc': 'msw8'}

def scrape_document(browser, id, visit_first=True):
    if visit_first:
        browser.get('http://localhost:8088/#!documentDetail;D=%s' % id)
    
    out = {}
    # document id
    doc_id = get_elements(browser, '#mainContentTop .Gsqk2cPB + .gwt-InlineLabel', lambda elements: len(elements) > 0 and elements[0].text == id)
    out['Document ID'] = doc_id[0].text
    
    # document type, etc.
    comment_on_type = get_elements(browser, '#mainContentTop .gwt-InlineHyperlink', optional=True)
    if comment_on_type:
        comment_on = {
            'Type': comment_on_type[0].text,
            'ID': comment_on_type[0].get_attribute('href').split('=')[1],
        }
        comment_on_label = get_elements(browser, '#mainContentTop .gwt-InlineHyperlink + .gwt-InlineLabel')
        comment_on['Title'] = comment_on_label[0].text
        
        out['Comment On'] = comment_on
    
    # Docket info
    docket_id = get_elements(browser, '#mainContentTop .Gsqk2cBO a.gwt-Anchor')
    out['Docket ID'] = docket_id[0].text
    
    topics = get_elements(browser, '#mainContentTop > span:last-child')
    if topics[0].get_attribute('class') == 'Gsqk2cDO':
        out['Topics'] = []
    else:
        out['Topics'] = topics[0].text.split(', ')
    
    # Details
    get_elements(browser, '#mainContentBottom .gwt-DisclosurePanel a.header')[0].click()
    
    details = {}
    cells = get_elements(browser, '#mainContentBottom .gwt-DisclosurePanel table.Gsqk2cJC tr td')
    for idx in range(0, len(cells), 2):
        title = cells[idx].text[:-1]
        content = cells[idx + 1].text
        details[title] = content
    out['Details'] = details
    
    # Attachments
    preview_url = get_elements(browser, '#mainContentBottom .gwt-Frame')[0].get_attribute('src')
    out['Preview URL'] = preview_url
    
    views = []
    
    url = urlparse.urlparse(preview_url)
    qs = dict(urlparse.parse_qsl(url.query))
    qs['disposition'] == 'attachment'
    
    view_buttons = get_elements(browser, '#mainContentBottom .gwt-Image.Gsqk2cPN')
    for button in view_buttons:
        title = button.get_attribute('title')
        format = title.split(' ')[-1]
        download_format = format
        if format in FORMAT_OVERRIDES:
            download_format = FORMAT_OVERRIDES[format]
        
        qs['contentType'] = download_format    
        views.append({
            'Type': format,
            'URL': 'http://www.regulations.gov/contentStreamer?%s' % urllib.urlencode(qs),
            'Downloaded': False
        })
    
    out['Views'] = views
    
    attachment_links = get_elements(browser, '#mainContentBottom .Gsqk2cNN a.gwt-InlineHyperlink, #mainContentBottom .Gsqk2cNN img.gwt-Image', optional=True)
    if attachment_links:
        attachments = []
        for idx in range(0, len(attachment_links), 2):
            attachments.append({
                'Document ID': attachment_links[idx].text,
                'Type': attachment_links[idx + 1].get_attribute('title').split(' ')[-1]
            })
        out['Attachments'] = attachments
    
    return out
