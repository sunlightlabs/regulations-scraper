from regscrape_lib.processing import *
import subprocess
from gevent.pool import Pool
import gevent
import settings

EXTRACTORS = {
    'xml': [
        binary_extractor('html2text', error='The document does not have a content file of type')
    ],
        
    'pdf': [
        binary_extractor('pdftotext', append=['-'], error='PDF file is damaged'),
        binary_extractor('ps2ascii', error='Unrecoverable error'),
#        pdf_ocr
    ],
    
    'msw8': [
        binary_extractor('antiword', error='is not a Word Document'),
        binary_extractor('catdoc', error='The document does not have a content file of type') # not really an error, but catdoc happily regurgitates whatever you throw at it
    ],
    
    'rtf': [
        binary_extractor('catdoc', error='The document does not have a content file of type') # not really an error, as above
    ],
    
    'txt': [
        binary_extractor('cat', error='The document does not have a content file of type') # not really an error, as above
    ],
    
    'msw12': [
        script_extractor('extract_docx.py', error='Failed to decode file')
    ],
    
    'wp8': [
        binary_extractor('wpd2text', error='ERROR')
    ],
}

EXTRACTORS['crtext'] = EXTRACTORS['xml']
EXTRACTORS['html'] = EXTRACTORS['xml']
EXTRACTORS['msw6'] = EXTRACTORS['msw8']
EXTRACTORS['msw'] = EXTRACTORS['msw8']

# extractor factory
def _get_extractor(status_func, verbose, filename, filetype=None, record=None):
    def extract():
        local_filetype = filetype if filetype else filename.split('.')[-1]
        if local_filetype in EXTRACTORS:
            success = False
            error_message = None
            used_ocr = False
            for extractor in EXTRACTORS[local_filetype]:
                try:
                    output = extractor(filename)
                except ExtractionFailed as failure:
                    reason = str(failure)
                    error_message = 'Failed to extract from %s using %s%s' % (
                        filename,
                        extractor.__str__(),
                        ' %s' % reason if reason else ''
                    )
                    if verbose: print error_message
                    continue
                except ChildTimeout as failure:
                    error_message = 'Failed extracting from %s using %s due to timeout' % (
                        filename,
                        extractor.__str__()
                    )
                    if verbose: print error_message
                    continue
                
                success = True
                text = unicode(remove_control_chars(output), 'utf-8', 'ignore')
                used_ocr = getattr(extractor, 'ocr', False)
                if verbose: print 'Extracted text from %s using %s' % (
                    filename,
                    extractor.__str__()
                )
                
                break

            status_func(
                (success, error_message),
                text if success else None,
                filename,
                local_filetype,
                used_ocr,
                record
            )
    return extract

def bulk_extract(extract_iterable, status_func=None, verbose=False):    
    workers = Pool(getattr(settings, 'EXTRACTORS', 2))
    
    # keep the extractors busy with tasks as long as there are more results
    for extract_record in extract_iterable:
        workers.spawn(_get_extractor(status_func, verbose, *extract_record))
    
    workers.join()
    
    return

def serial_bulk_extract(extract_iterable, status_func=None, verbose=False):
    import subprocess
    import regscrape_lib.processing

    regscrape_lib.processing.POPEN = subprocess.Popen
    
    for extract_record in extract_iterable:
        _get_extractor(status_func, verbose, *extract_record)()

    return