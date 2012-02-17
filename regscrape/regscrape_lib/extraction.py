from regscrape_lib.processing import *

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