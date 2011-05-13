from regscrape_lib.util import get_elements
from regscrape_lib.document import scrape_document
from regscrape_lib.exceptions import StillNotFound, Finished, FoundErrorElement
import sys
import settings
from regscrape_lib import logger

def scrape_listing(browser, url=None, visit_first=True, ids_only=False, check_func=None):
    logger.info("Scraping listing %s" % url)
    if visit_first:
        browser.get(url)
    
    docs = []
    errors = []
    
    try:
        links = get_elements(browser, 'a[href*=documentDetail]', min_count=settings.PER_PAGE)
        num_links = len(links)
    except StillNotFound:
        try:
            links = get_elements(browser, 'a[href*=documentDetail]', error_selector='.x-grid-empty')
            num_links = len(links)
        except StillNotFound:
            raise StillNotFound
        except FoundErrorElement:
            raise Finished
    except FoundErrorElement:
        raise Finished
    
    if ids_only:
        for link in links:
            docs.append(link.get_attribute('href').split('=')[1])
        return (docs, errors)
    
    for num in range(num_links):
        doc = None
        id = None
        doc_error = None
        skip = False
        for i in range(3):
            try:
                link = get_elements(browser, 'a[href*=documentDetail]', min_count=num_links)[num]
                href = link.get_attribute('href')
                id = href.split('=')[1]
                
                if check_func:
                    already_have = check_func(id)
                    if already_have:
                        skip = True
                        break
                
                link.click()
                
                doc = scrape_document(browser, id, False)
                break
            except StillNotFound:
                browser.get(url)
            except:
                doc_error = {'type': 'document', 'reason': str(sys.exc_info()[0]), 'doc_id': id, 'listing': url, 'position': num}
                break
        
        if doc:
            docs.append(doc)
        elif not skip:
            doc_error = {'type': 'document', 'reason': 'scraping failed', 'doc_id': id, 'listing': url, 'position': num}
        
        if doc_error:
            errors.append(doc_error)
        
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
        count = get_elements(browser, '.largeOrangeText', check=lambda elements: len(elements) > 0 and str(elements[0].text.split(' ')[0]).isdigit())[0]
    except StillNotFound:
        return False
    
    num = int(count.text.split(' ')[0])
    return num