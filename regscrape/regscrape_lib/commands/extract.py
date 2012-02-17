#!/usr/bin/env python

from regscrape_lib.exceptions import *
from optparse import OptionParser

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-p", "--pretend", action="store_true", dest="pretend", default=False)
arg_parser.add_option("-t", "--type", action="store", dest="type", default=None)

# decoder factory
def get_decoder(result, options, update_func, stats):
    def decode():
        ext = result['view']['file'].split('.')[-1]
        if ext in DECODERS:
            for decoder in DECODERS[ext]:
                try:
                    output = decoder(result['view']['file'])
                except DecodeFailed as failure:
                    reason = str(failure)
                    print 'Failed to decode %s using %s%s' % (
                        result['view']['url'],
                        decoder.__str__(),
                        ' %s' % reason if reason else ''
                    )
                    continue
                except ChildTimeout as failure:
                    print 'Failed decoding %s using %s due to timeout' % (
                        result['view']['url'],
                        decoder.__str__()
                    )
                    continue
                
                result['view']['extracted'] = True
                result['view']['text'] = unicode(remove_control_chars(output), 'utf-8', 'ignore')
                result['view']['ocr'] = getattr(decoder, 'ocr', False)
                if options.pretend:
                    print 'Decoded %s using %s' % (result['view']['file'], decoder.__str__())
                else:
                    # since we're adding potentially tons of text here, there's a chance of making the document too big
                    try:
                        update_func(**result)
                        print 'Decoded and saved %s using %s' % (result['view']['file'], decoder.__str__())
                        stats['extracted'] += 1
                    except (pymongo.errors.OperationFailure, pymongo.errors.InvalidDocument):
                        print 'Decoded %s using %s but failed to save due to oversized document.' % (result['view']['file'], decoder.__str__())
                        stats['failed'] += 1
                        
                        if not 'oversized' in stats:
                            stats['oversized'] = []
                        stats['oversized'].append(result['view']['url'])
                break
        if not result['view'].get('extracted', False):
            result['view']['extracted'] = 'failed'
            if not options.pretend:
                # this shouldn't make the document too big, so don't bother with handling that case for now
                update_func(**result)
                print 'Saved failure to decode %s' % result['view']['file']
            stats['failed'] += 1
    return decode

# runner
def run(options, args): 
    global Pool, sys, settings, subprocess, os, urlparse, json, regscrape_lib, pymongo, DECODERS
    from regscrape_lib.processing import *
    from regscrape_lib.extraction import DECODERS
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
    if options.pretend:
        print 'Warning: no records will be saved to the database during this run.'
    
    print 'Preparing text extraction of %s.' % view_label
    
    find_conditions = {
        'downloaded': True,
        'extracted': False,
        'query': settings.FILTER
    }
    if options.type:
        find_conditions['type'] = options.type
    
    views = find_func(**find_conditions)
    workers = Pool(settings.DECODERS)
    
    # track stats -- no locks because yay for cooperative multitasking
    stats = {'extracted': 0, 'failed': 0}
    
    # keep the decoders busy with tasks as long as there are more results
    while True:
        try:
            result = views.next()
        except pymongo.errors.OperationFailure:
            # occasionally pymongo seems to lose track of the cursor for some reason, so reset the query
            views = find_func(**find_conditions)
            continue
        except StopIteration:
            break
        
        workers.spawn(get_decoder(result, options, update_func, stats))
    workers.join()
    
    print 'Done with %s.' % view_label
    
    return stats

if __name__ == "__main__":
    run()
