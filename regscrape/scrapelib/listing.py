from scrapelib.util import get_elements
from scrapelib.document import scrape_document
from scrapelib.exceptions import StillNotFound
import sys

def scrape_listing(browser, url=None, visit_first=True):
    if visit_first:
        browser.get(url)
    
    docs = []
    errors = []
    num_links = len(get_elements(browser, 'a[href*=documentDetail]'))
    for num in range(num_links):
        for i in range(3):
            id = None
            try:
                link = get_elements(browser, 'a[href*=documentDetail]', min_count=num_links)[num]
                href = link.get_attribute('href')
                id = href.split('=')[1]
                
                link.click()
                
                doc = scrape_document(browser, id, False)
                break
            except StillNotFound:
                browser.get(url)
            except:
                errors.append({'type': 'document', 'reason': str(sys.exc_info()[0]), 'doc_id': id, 'listing': url, 'position': num})
                break
        
        if doc:
            docs.append(doc)
            print doc
        else:
            errors.append({'type': 'document', 'reason': 'scraping failed', 'doc_id': id, 'listing': url, 'position': num})
        
        browser.back()
    print 'got %s docs' % len(docs)
    return (docs, errors)