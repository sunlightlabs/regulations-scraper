import time
from exceptions import StillNotFound
import xpath

def get_elements(browser, selector, check=None, optional=False, min_count=1):
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
            count += 1
            if count and count % 10 == 0:
                raise StillNotFound()
            time.sleep(0.5)
    return elements
