import time
from exceptions import StillNotFound, FoundErrorElement
import xpath

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
                print 'checking error selector'
                error_elements = getattr(browser, func)(error_selector)
                print error_elements
                if error_elements:
                    raise FoundErrorElement()
            count += 1
            if count and count % 10 == 0:
                raise StillNotFound()
            time.sleep(0.5)
    return elements

def pseudoqs_encode(qs_dict):
    return ";".join(["=".join(item) for item in qs_dict.items()])
