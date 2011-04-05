import re
from pymongo import Connection
from BeautifulSoup import BeautifulSoup, Tag, NavigableString
from clustering import NGramSpace, Clustering


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
    

def get_texts():
    c = Connection()
    docs = c.regulations.docs.find()
    return [get_comment(d) for d in docs]

def setup():
    texts = get_texts()
    ngrams = NGramSpace(4)
    parsed = [ngrams.parse(raw) for raw in texts]
    clustering = Clustering(parsed)
    return (texts, parsed, ngrams, clustering)