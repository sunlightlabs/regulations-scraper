#!/usr/bin/env python

from regscrape_lib.util import get_db
import operator

def run():
    db = get_db()
    
    data = list(db.docs.find())
    doc_count = len(data)
    print 'Total document count: %s' % doc_count
    
    all_downloaded = [item for item in data if reduce(operator.and_, [view['Downloaded'] for view in item['Views'] if 'Downloaded' in view], True)]
    none_downloaded = [item for item in data if reduce(operator.and_, [not view['Downloaded'] for view in item['Views'] if 'Downloaded' in view], True)]
    all_decoded = [item for item in data if reduce(operator.and_, [view['Decoded'] for view in item['Views'] if 'Decoded' in view], True)]
    none_decoded = [item for item in data if reduce(operator.and_, [not view['Decoded'] for view in item['Views'] if 'Decoded' in view], True)]
    
    print 'Documents where all views were downloaded: %s' % len(all_downloaded)
    print 'Documents where no views were downloaded: %s' % len(none_downloaded)
    print 'Documents where all downloaded views were decoded: %s' % len(all_decoded)
    print 'Documents where no downloaded views were decoded: %s' % len(none_decoded)
    
    nd_content_types = set(reduce(operator.add, [[view['Type'] for view in doc['Views']] for doc in none_decoded]))
    print 'Content types present in views of non-decoded documents: %s' % ', '.join(nd_content_types)
