GEVENT = False

import urllib2, re, json, os, urlparse
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
from optparse import OptionParser
import settings

from regs_common.util import crockford_hash
from regs_models import *

# FIXME: split this out
from sec_cftc.commands.sec_cftc_import import view_from_url

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False)
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-D", "--document", dest="document", action="store", type="string", default=None, help="Specify a document to which to limit the dump.")

def run(options, args):
    query = {'scraped': 'no', 'source': 'sec_cftc', 'agency': 'CFTC', 'views__downloaded': 'yes'}

    if options.docket:
        query['docket_id'] = options.docket

    if options.document:
        query['id'] = options.document

    parser = etree.HTMLParser()
    for doc in Doc.objects(**query):
        print "Processing %s..." % doc.id
        page_data = open(doc.views[0].file_path).read()
        page = pq(etree.fromstring(page_data, parser))
        
        text = page('.dyn_wrap div.ClearBoth').html().strip()
        full_text = "<html><body>%s</body></html>" % text
        
        if doc.views[0].content:
            doc.views[0].content.delete()
        
        doc.views[0].content.new_file()
        doc.views[0].content.write(full_text.encode('utf8'))
        doc.views[0].content.close()
        
        doc.views[0].extracted = 'yes'
        print "Found and wrote text."
        
        print "attachment"
        attachment_link = page('.dyn_wrap a[id*=StaticLink]')
        if attachment_link:
            att_url = urlparse.urljoin(doc.views[0].url, attachment_link.attr('href').strip())
            
            att = Attachment()
            att.title = page('.dyn_wrap a[id*=AssetAttachment]').text().strip()
            
            att_view = view_from_url(att_url)
            if 'pdf' in att_url.lower():
                att_view.type = 'xpdf'
            att.views.append(att_view)
            att.object_id = att_view.object_id
            
            doc.attachments = [att]
            
            print "Found and saved attachment %s." % att_url
        else:
            print "No attachment found."
        
        doc.scraped = 'yes'        
        doc.save()