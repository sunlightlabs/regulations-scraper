
import csv
import re
import os
import sys
import cPickle

from clustering import Clustering
from ngrams import NGramSpace 

def extract_row(row, pdf_path, ngrams):
    text = _get_text(row, pdf_path)
    date = row['DateTime Submitted']
    if row['Middle Initial']:
        name = " ".join([row['First Name'], row['Middle Initial'], row['Last Name']])
    else:
        name = " ".join([row['First Name'], row['Last Name']])
    org = row['Organization']
    
    return Document(name, org, date, text, ngrams)

        
def _get_text(row, pdf_path):
    source_file = row['File Name']
    if source_file in ('', 'NULL'):
        return row['Comment Text']
    else:
        if source_file.lower().endswith('.pdf'):
            stripped = source_file[:-4]
        elif source_file.lower().endswith('pdf'):
            stripped = source_file[:-3]
        else:
            stripped = source_file
            
        extraction = " ".join(open(os.path.join(pdf_path, stripped + '.txt'), 'r'))
        # as a sanity check, assure that there are at least 5 words
        if len(re.split('\W+', extraction)) > 5:
            return extraction
        else:
            return ''


class Document(object):
    
    def __init__(self, name, org, date, text, ngrams):
        self.name = name
        self.org = org
        self.date = date
        self.text = text
        self.parsed = ngrams.parse(self.text)
        
    def __str__(self):
        return "%s (%s)\n%s" % (self.name, self.org, self.text) 


def setup(source, pdf_path):
    ngrams = NGramSpace(4)
    print "parsing documents at %s..." % source
    docs = [extract_row(row, pdf_path, ngrams) for row in csv.DictReader(open(source, 'r'))]
    print "clustering %d documents..." % len(docs)
    clustering = Clustering([doc.parsed for doc in docs])
    return (clustering, docs)


if __name__ == '__main__':
    (clustering, docs) = setup(sys.argv[1], sys.argv[2])
    print "\nWriting clustering to %s..." % sys.argv[3]
    cPickle.dump((clustering, docs), open(sys.argv[3], 'wb'), cPickle.HIGHEST_PROTOCOL)
    
