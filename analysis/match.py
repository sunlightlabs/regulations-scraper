
import csv
import sys

from oxtail.matching import match


if __name__ == '__main__':
    infile = sys.argv[1]
    outfile = sys.argv[2]
    
    reader = csv.DictReader(open(infile, 'r'))
    writer = csv.writer(open(outfile, 'w'))
    writer.writerow(['document_id, entity_id'])
    
    for row in reader:
        for entity_id in match(row['text']).keys():
            writer.writerow([row['document_id'], entity_id])