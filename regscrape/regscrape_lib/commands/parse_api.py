from regs_gwt.regs_client import RegsClient
from pygwt.response import Response
import os
import settings

def run():
    files = [file for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
    client = RegsClient()
    all_docs = []
    
    for file in files:
        data = open(os.path.join(settings.DUMP_DIR, file))
    
        response = Response(client, data)
        documents = response.reader.read_object()
        
        all_docs += [document.document_id for document in documents]
        
        del response
    
    all_docs = set(all_docs)
    print all_docs
    print len(all_docs)
