#!/usr/bin/env python

from regscrape_lib.util import get_db
import operator

def run():
    db = get_db()
    
    data = list(db.docs.find())
    doc_count = len(data)
    print 'Total document count: %s' % doc_count
    
    all_downloaded = [item for item in data if reduce(operator.and_, [view['downloaded'] for view in item['views'] if 'downloaded' in view], True)]
    none_downloaded = [item for item in data if reduce(operator.and_, [not view['downloaded'] for view in item['views'] if 'downloaded' in view], True)]
    all_decoded = [item for item in data if reduce(operator.and_, [view['decoded'] for view in item['views'] if 'decoded' in view], True)]
    none_decoded = [item for item in data if reduce(operator.and_, [not view['decoded'] for view in item['views'] if 'decoded' in view], True)]
    
    print 'Documents where all views were downloaded: %s' % len(all_downloaded)
    print 'Documents where no views were downloaded: %s' % len(none_downloaded)
    print 'Documents where all downloaded views were decoded: %s' % len(all_decoded)
    print 'Documents where no downloaded views were decoded: %s' % len(none_decoded)
    
    nd_content_types = set(reduce(operator.add, [[view['type'] for view in doc['views']] for doc in none_decoded]))
    print 'Content types present in views of non-decoded documents: %s' % ', '.join(nd_content_types)
