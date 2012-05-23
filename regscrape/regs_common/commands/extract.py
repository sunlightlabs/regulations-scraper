#!/usr/bin/env python

from regscrape_lib.exceptions import *
from optparse import OptionParser

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-t", "--type", action="store", dest="type", default=None)

# runner
def run(options, args): 
    global Pool, sys, settings, subprocess, os, urlparse, json, regscrape_lib, pymongo, serial_bulk_extract
    from regscrape_lib.processing import find_views, update_view, find_attachment_views, update_attachment_view
    from regscrape_lib.extraction import serial_bulk_extract
    from gevent.pool import Pool
    import sys
    import settings
    import subprocess, os, urlparse, json
    import regscrape_lib
    import pymongo

    return {
        'document_views': run_for_view_type('document views', find_views, update_view, options),
        'attachment_views': run_for_view_type('attachment views', find_attachment_views, update_attachment_view, options)
    }

def run_for_view_type(view_label, find_func, update_func, options):
    print 'Preparing text extraction of %s.' % view_label
    
    find_conditions = {
        'downloaded': True,
        'extracted': False,
        'query': getattr(settings, 'FILTER', {})
    }
    if options.type:
        find_conditions['type'] = options.type
    
    # track stats -- no locks because yay for cooperative multitasking
    stats = {'extracted': 0, 'failed': 0}

    views = find_func(**find_conditions)

    # same yucky hack as in downloads
    v_array = [views]
    def extract_generator():
        while True:
            try:
                result = v_array[0].next()
                yield (result['view']['file'], None, result)
            except pymongo.errors.OperationFailure:
                # occasionally pymongo seems to lose track of the cursor for some reason, so reset the query
                v_array[0] = find_func(**find_conditions)
                continue
            except StopIteration:
                break

    def status_func(status, text, filename, filetype, used_ocr, result):
        if status[0]:
            result['view']['extracted'] = True
            result['view']['text'] = text
            result['view']['ocr'] = used_ocr
            try:
                update_func(**result)
                print 'Extracted and saved text from %s' % filename
                stats['extracted'] += 1
            except (pymongo.errors.OperationFailure, pymongo.errors.InvalidDocument):
                print 'Extracted text from %s but failed to save due to oversized document.' % filename
                stats['failed'] += 1
                
                if not 'oversized' in stats:
                    stats['oversized'] = []
                stats['oversized'].append(result['view']['url'])
        else:
            result['view']['extracted'] = 'failed'
            update_func(**result)
            print 'Saved failure to decode %s' % result['view']['file']
            stats['failed'] += 1
        update_func(**result)
    
    serial_bulk_extract(extract_generator(), status_func, verbose=True)

    print 'Done with %s.' % view_label
    
    return stats

if __name__ == "__main__":
    run()
