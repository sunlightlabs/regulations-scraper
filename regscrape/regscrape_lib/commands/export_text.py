import settings
import datetime
import os
import pymongo
import itertools
import json
from regscrape_lib.util import get_db
import zipfile
import sys

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Filter to only one agency.  Default to all agencies if not specified.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Filter to only one docket.  Default to all dockets if not specified.")

def ensure_directory(directory):
    if not os.path.exists(directory):
        os.mkdir(directory)

def extract(record, keys):
    out = {}
    for key in keys:
        if key in record and record[key]:
            out[key] = record[key]
    return out

dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None

def run(options, args):
    print 'Starting dump...'
    
    query = {'scraped': True, 'deleted': False}
    
    if options.docket:
        query['docket_id'] = options.docket
    if options.agency:
        query['agency'] = options.agency
    print query
    
    db = get_db()
    
    export_dir = os.path.join(settings.DATA_DIR, 'bulk', 'regulations-%s' % str(datetime.datetime.now().date()))
    ensure_directory(export_dir)
        
    for agency, agency_docs in itertools.groupby(db.docs.find(query, sort=[('document_id', pymongo.ASCENDING)]), key=lambda d: d['agency']):
        print 'Starting agency %s...' % agency
        agency_dir = os.path.join(export_dir, agency)
        ensure_directory(agency_dir)
        
        for docket, docket_docs in itertools.groupby(agency_docs, key=lambda d: d['docket_id']):
            print 'Starting docket %s...' % docket
            zip_path = os.path.join(agency_dir, '%s.zip' % docket)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, True) as docket_zip:
                docket_record = list(db.dockets.find({'docket_id': docket}))
                
                if docket_record:
                    docket_zip.writestr(
                        'metadata.json',
                        json.dumps(
                            extract(
                                docket_record[0],
                                ['docket_id', 'title', 'agency', 'rin', 'details', 'year']
                            ),
                            default=dthandler
                        )
                    )
                
                for doc in docket_docs:
                    files = []
                    
                    views = [('view', view) for view in doc['views']]
                    if 'attachments' in doc:
                        for attachment in doc['attachments']:
                            views.extend([('attachment', view) for view in attachment['views']])
                    
                    for type, view in views:
                        file = {'url': view['url']}
                        if view['extracted'] == True:
                            filename = '%s_%s.txt' % (type, view['file'].split('/')[-1].replace('.', '_'))
                            file['filename'] = filename
                            
                            docket_zip.writestr(os.path.join(doc['document_id'], filename), view['text'].encode('utf8'))
                            
                        files.append(file)
                        
                    metadata = extract(
                        doc,
                        ['document_id', 'title', 'agency', 'docket_id', 'type', 'topics', 'details', 'comment_on', 'rin']
                    )
                    metadata['files'] = files
                    
                    docket_zip.writestr(os.path.join(doc['document_id'], 'metadata.json'), json.dumps(metadata, default=dthandler))