import time

def get_elements(browser, selector, check=None, optional=False, min_count=1):
    count = 0
    elements = []
    while True:
        elements = browser.find_elements_by_css_selector(selector)
        if (len(elements) >= min_count and (not check or check(elements))) or optional:
            break
        else:
            count += 1
            if count and count % 10 == 0:
                browser.refresh()
            time.sleep(0.5)
    return elements
