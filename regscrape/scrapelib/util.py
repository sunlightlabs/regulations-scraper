import time

def get_elements(browser, selector, check=None, optional=False):
    count = 0
    elements = []
    while True:
        elements = browser.find_elements_by_css_selector(selector)
        if (elements and (not check or check(elements))) or optional:
            break
        else:
            count += 1
            if count and count % 10 == 0:
                browser.refresh()
            time.sleep(0.5)
    return elements