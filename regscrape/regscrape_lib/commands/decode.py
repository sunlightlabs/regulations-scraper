#!/usr/bin/env python

from regscrape_lib.processing import *
from optparse import OptionParser
from regscrape_lib.exceptions import *
import sys

DECODERS = {
    'xml': [
        binary_decoder('html2text', error='The document does not have a content file of type')
    ],
        
    'pdf': [
        binary_decoder('ps2ascii', error='Unrecoverable error'),
        binary_decoder('pdftotext', error='PDF file is damaged'),
        pdf_ocr
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
}

DECODERS['crtext'] = DECODERS['xml']
DECODERS['msw6'] = DECODERS['msw8']
DECODERS['msw'] = DECODERS['msw8']

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-p", "--pretend", action="store_true", dest="pretend", default=False)
arg_parser.add_option("-t", "--type", action="store", dest="type", default=None)

# runner
def run(options, args):
    if options.pretend:
        print 'Warning: no records will be saved to the database during this run.'
    
    import subprocess, os, urlparse, json
    view_cursor = find_views(downloaded=True, decoded=False, type=options.type) if options.type else find_views(downloaded=True, decoded=False)
    
    for result in view_cursor.find():
        ext = result['value']['view']['file'].split('.')[-1]
        if ext in DECODERS:
            for decoder in DECODERS[ext]:
                try:
                    output = decoder(result['value']['view']['file'])
                except DecodeFailed as failure:
                    reason = failure.message
                    print 'Failed to decode %s using %s%s' % (
                        result['value']['view']['url'],
                        decoder.__str__(),
                        ' %s' % reason if reason else ''
                    )
                    continue

                view = result['value']['view'].copy()
                view['decoded'] = True
                view['text'] = unicode(remove_control_chars(output), 'utf-8', 'ignore')
                if options.pretend:
                    print 'Decoded %s using %s' % (view['url'], decoder.__str__())
                    print view['text']
                else:
                    update_view(result['value']['doc'], view)
                    print 'Decoded and saved %s using %s' % (view['url'], decoder.__str__())
                break
    view_cursor.drop()

if __name__ == "__main__":
    run()
