from regscrape_lib.util import get_elements
from regscrape_lib.document import scrape_document
from regscrape_lib.exceptions import StillNotFound, Finished, FoundErrorElement
import sys
import settings
from regscrape_lib import logger

def scrape_listing(browser, url=None, visit_first=True):
    logger.info("Scraping listing %s" % url)
    if visit_first:
        browser.get(url)
    
    docs = []
    errors = []
    
    try:
        num_links = len(get_elements(browser, 'a[href*=documentDetail]', min_count=settings.PER_PAGE))
    except StillNotFound:
        try:
            num_links = len(get_elements(browser, 'a[href*=documentDetail]', error_selector='.x-grid-empty'))
        except StillNotFound:
            raise StillNotFound
        except FoundErrorElement:
            raise Finished
    except FoundErrorElement:
        raise Finished
    
    for num in range(num_links):
        doc = None
        id = None
        for i in range(3):
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
        else:
            errors.append({'type': 'document', 'reason': 'scraping failed', 'doc_id': id, 'listing': url, 'position': num})
        
        if browser.name == 'chrome':
            print "getting url"
            browser.get(url)
        else:
            browser.back()
    logger.info('Scraped %s: got %s documents of %s expected, with %s errors' % (url, len(docs), num_links, len(errors)))
    return (docs, errors)

def get_count(browser, url=None, visit_first=True):
    logger.info("Determining result count for listing %s" % url)
    if visit_first:
        browser.get(url)
    
    try:
        count = get_elements(browser, '.largeOrangeText')[0]
    except StillNotFound:
        return False
    
    num = int(count.text.split(' ')[0])
    return num