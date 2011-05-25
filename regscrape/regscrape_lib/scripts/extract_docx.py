#!/usr/bin/env python

# extracts text from docx files using the docx module by Mike MacCana

from docx import *
import sys

if __name__ == '__main__':
    try:
        document = opendocx(sys.argv[1])
    except:
        sys.stderr.write('Failed to decode file\n')
        exit()
    
    ## Fetch all the text out of the document we just created
    paratextlist = getdocumenttext(document)
    
    # Make explicit unicode version
    newparatextlist = []
    for paratext in paratextlist:
        newparatextlist.append(paratext.encode("utf-8"))
    
    ## Print our documnts test with two newlines under each paragraph
    sys.stdout.write('\n\n'.join(newparatextlist))