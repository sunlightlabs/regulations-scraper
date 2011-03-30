#!/usr/bin/env python

from regscrape_lib.processing import *

DECODERS = {
    'xml': [{
        'bin': 'html2text'
    }],
        
    'pdf': [{
        'bin': 'pdftotext',
        'error': 'PDF file is damaged'
    },
    {
        'bin': 'ps2ascii',
        'error': 'Unrecoverable error'
    }],
    
    'msw8': [{
        'bin': 'antiword',
        'error': 'is not a Word Document'
    },
    {
        'bin': 'catdoc',
        'error': 'The document does not have a content file of type' # not really an error, but catdoc happily regurgitates whatever you throw at it
    }],
    
    'rtf': [{
        'bin': 'catdoc',
        'error': 'The document does not have a content file of type' # not really an error, as above
    }],
    
    'txt': [{
        'bin': 'cat',
        'error': 'The document does not have a content file of type' # not really an error, as above
    }],
}

DECODERS['crtext'] = DECODERS['xml']

def run():
    import subprocess, os, urlparse, json
    view_cursor = find_views(Downloaded=True, Decoded=False)
    
    for result in view_cursor.find():
        ext = result['value']['view']['File'].split('.')[-1]
        if ext in DECODERS:
            for decoder in DECODERS[ext]:
                interpreter = subprocess.Popen([decoder['bin'], result['value']['view']['File']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output, error = interpreter.communicate()
                
                if not output.strip() or ('error' in decoder and decoder['error'] in output):
                    print 'Failed to decode %s using %s' % (result['value']['view']['URL'], decoder['bin'])
                    continue
                else:
                    view = result['value']['view'].copy()
                    view['Decoded'] = True
                    view['Text'] = unicode(remove_control_chars(output), 'utf-8', 'ignore')
                    update_view(result['value']['doc'], view)
                    print 'Decoded and saved %s using %s' % (view['URL'], decoder['bin'])
                    break

if __name__ == "__main__":
    run()
