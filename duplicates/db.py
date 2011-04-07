import re
from pymongo import Connection
from BeautifulSoup import BeautifulSoup, Tag, NavigableString
from clustering import NGramSpace, Clustering


DOCUMENT_URL = 'http://www.regulations.gov/#!documentDetail;D='

class Document(object):
    
    def __init__(self, mongo_doc, ngrams):
        self.mongo_doc = mongo_doc
        self.comment = get_comment(mongo_doc)
        self.parsed = ngrams.parse(self.comment)
        self.url = DOCUMENT_URL + mongo_doc['Document ID']
        self.title = mongo_doc['Details'].get('Title', '') if 'Details' in mongo_doc else ''
    
    def __str__(self):
        return "%s\n%s\n%s" % (self.title, self.url, self.comment) 
        
def extract_html_comment(comment):
    soup = BeautifulSoup(comment)
    
    comment_header = soup.find('h2', text='General Comment').parent
        
    comment = ''

    for node in comment_header.findNextSiblings():
        if node.name == 'h2':
            break
        
        comment += ''.join(strip_tags(node))
        
    return comment

def extract_comment(comment):
    pattern = 'Comments? ?(?:\*+|:)(.*?)(?:===+.*)?$'
    match = re.search(pattern, comment, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    return comment.strip()
    

def strip_tags(node):
    if type(node) is NavigableString:
        return str(node)
    else:
        return ''.join(map(strip_tags, node.contents))


VIEW_PREFERENCE = ['crtext', 'msw8', 'pdf']

def get_comment(doc):
    for label in VIEW_PREFERENCE:
        views = [v.get('Text', '') for v in doc.get('Views', []) if v.get('Type', '') == label and v.get('Decoded')]
        if views:
            return extract_comment(views[0])
    
    return ''
    

def get_texts(ngrams):
    c = Connection()
    docs = c.regulations.docs.find()
    return [Document(d, ngrams) for d in docs]

def setup():
    ngrams = NGramSpace(4)
    docs = get_texts(ngrams)
    clustering = Clustering([doc.parsed for doc in docs])
    return (clustering, docs)

