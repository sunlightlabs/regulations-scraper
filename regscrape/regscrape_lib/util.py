import time
from exceptions import StillNotFound, FoundErrorElement
import xpath
import settings
from pymongo import Connection
import os

def get_elements(browser, selector, check=None, optional=False, min_count=1, error_selector=None):
    count = 0
    elements = []
    
    if browser.name == 'chrome':
        selector = xpath.css2xpath(selector)
        func = 'find_elements_by_xpath'
    else:
        func = 'find_elements_by_css_selector'
    while True:
        elements = getattr(browser, func)(selector)
        if (len(elements) >= min_count and (not check or check(elements))) or optional:
            break
        else:
            if error_selector:
                error_elements = getattr(browser, func)(error_selector)
                if error_elements:
                    raise FoundErrorElement()
            count += 1
            if count and count % 10 == 0:
                raise StillNotFound()
            time.sleep(0.5)
    return elements

def pseudoqs_encode(qs_dict):
    return ";".join(["=".join(item) for item in qs_dict.items()])

def get_db():
    db_settings = getattr(settings, 'DB_SETTINGS', {})
    return Connection(**db_settings)[getattr(settings, 'DB_NAME', 'regulations')]

def get_url_for_count(count):
    return "http://%s/#!searchResults;so=ASC;sb=postedDate;%s;rpp=%s;po=%s" % (settings.TARGET_SERVER, pseudoqs_encode(settings.SEARCH), settings.PER_PAGE, count)

def bootstrap_settings():
    if not getattr(settings, 'DOWNLOAD_DIR', False):
        settings.DOWNLOAD_DIR = os.path.join(settings.DATA_DIR, 'downloads')
    
    if not getattr(settings, 'DUMP_DIR', False):
        settings.DUMP_DIR = os.path.join(settings.DATA_DIR, 'dumps')
