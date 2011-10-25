#!/usr/bin/env python

from regscrape_lib.processing import *
from optparse import OptionParser
from regscrape_lib.exceptions import *
from gevent.pool import Pool
import sys
import settings
import subprocess, os, urlparse, json
import regscrape_lib
import pymongo

DECODERS = {
    'xml': [
        binary_decoder('html2text', error='The document does not have a content file of type')
    ],
        
    'pdf': [
        binary_decoder('pdftotext', append=['-'], error='PDF file is damaged'),
        binary_decoder('ps2ascii', error='Unrecoverable error'),
#        pdf_ocr
    ],
    
    'msw8': [
        binary_decoder('antiword', error='is not a Word Document'),
        binary_decoder('catdoc', error='The document does not have a content file of type') # not really an error, but catdoc happily regurgitates whatever you throw at it
    ],
    
    'rtf': [
        binary_decoder('catdoc', error='The document does not have a content file of type') # not really an error, as above
    ],
    
    'txt': [
        binary_decoder('cat', error='The document does not have a content file of type') # not really an error, as above
    ],
    
    'msw12': [
        script_decoder('extract_docx.py', error='Failed to decode file')
    ],
    
    'wp8': [
        binary_decoder('wpd2text', error='ERROR')
    ],
}

DECODERS['crtext'] = DECODERS['xml']
DECODERS['html'] = DECODERS['xml']
DECODERS['msw6'] = DECODERS['msw8']
DECODERS['msw'] = DECODERS['msw8']

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
