from pymongo import Connection
from BeautifulSoup import BeautifulSoup, Tag, NavigableString

def extract_comment(filename):
    soup = BeautifulSoup(open(filename, 'r'))
    
    comment_header = soup.find('h2', text='General Comment').parent
        
    comment = ''

    for node in comment_header.findNextSiblings():
        if node.name == 'h2':
            break
        
        comment += ''.join(strip_tags(node))
        
    return comment
   
    
def strip_tags(node):
    if type(node) is NavigableString:
        return str(node)
    else:
        return ''.join(map(strip_tags, node.contents))


def get_texts():
    c = Connection()
    docs = c.regulations.docs.find()
    texts = list()
    for d in docs:
        for v in d.get('Views', []):
            if v.get('Decoded', False):
                texts.append(v.get('Text', ''))

    return texts