import sys
import csv
from datetime import datetime
from collections import namedtuple
from pymongo import Connection

from duplicates.db import get_comment

F = namedtuple('F', ['csv_column', 'transform'])

def deep_get(key, dict, default=None):
    if '.' in key:
        first, rest = key.split('.', 1)
        return deep_get(rest, dict.get(first, {}), default)
    else:
        return dict.get(key, default)

def getter(key, default=''):
    return lambda d: deep_get(key, d, default)


DOCS_QUERY = {}

DOCS_FIELDS = [
    F('document_id', getter('document_id')),
    F('docket_id', getter('docket_id')),
    F('agency', getter('agency')),
    F('date_posted', getter('details.date_posted', None)),
    F('date_due', getter('details.comments_due', None)),
    F('title', getter('details.title')),
    F('type', getter('details.document_type')),
    F('org_name', getter('details.organization_name')),
    F('on_type', getter('comment_on.type')),
    F('on_id', getter('comment_on.id')),
    F('on_title', getter('comment_on.title')),
    F('text', get_comment)
]


def filter_for_postgres(v):
    if v is None:
        return '\N'
    
    if isinstance(v, datetime):
        return str(v)

    return v.encode('utf8').replace("\.", ".")


def dump_cursor(c, fields, outfile):
    writer = csv.writer(outfile)
    writer.writerow([f.csv_column for f in fields])
    
    for doc in c:
        row = [filter_for_postgres(f.transform(doc)) for f in fields]
        if len(row[-1]) > 130000:
            print("Skipping long row.")
        else:
            writer.writerow(row)
    

if __name__ == '__main__':
    host = sys.argv[1]
    dbname = sys.argv[2]
    outfile = open(sys.argv[3], 'w')
    
    cursor = Connection(host=host)[dbname].docs.find(DOCS_QUERY)
    dump_cursor(cursor, DOCS_FIELDS, outfile)

    
    