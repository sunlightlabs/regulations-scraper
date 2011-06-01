import sys
import csv
from datetime import datetime
from collections import namedtuple
from pymongo import Connection

from duplicates.db import get_comment

F = namedtuple('F', ['csv_column', 'transform'])

QUERY = {}

FIELDS = [
    # (mongo field, CSV field, tranform)
    F('document_id', lambda d: d.get('document_id', '')),
    F('docket_id', lambda d: d.get('docket_id', '')),
    F('agency', lambda d: d.get('agency', '')),
    F('date', lambda d: d['details'].get('date_posted', None) if 'details' in d else None),
    F('text', get_comment)
]


def filter_for_postgres(v):
    if v is None:
        return 'None'
    
    if isinstance(v, datetime):
        return str(v)

    return v.encode('utf8').replace("\.", ".")


def dump_cursor(c, fields, outfile):
    writer = csv.writer(outfile)
    writer.writerow([f.csv_column for f in fields])
    
    for doc in c:
        row = [filter_for_postgres(f.transform(doc)) for f in fields]
        if len(row[4]) > 130000:
            print("Skipping long row.")
        else:
            writer.writerow(row)


if __name__ == '__main__':
    dbname = sys.argv[1]
    outfile = open(sys.argv[2], 'w')
    
    cursor = Connection()[dbname].docs.find(QUERY)
    
    dump_cursor(cursor, FIELDS, outfile)