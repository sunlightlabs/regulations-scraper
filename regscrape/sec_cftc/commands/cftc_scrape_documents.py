GEVENT = False

import urllib2, re, json, os, sys, operator, string, urlparse
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings
from optparse import OptionParser

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False)
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-s", "--strategy", dest="strategy", action="store", type="string", default=None, help="Restrict scraping to a single strategy.")

parser = etree.HTMLParser()

def fix_spaces(text):
    return re.sub(u"[\s\xa0]+", " ", text)

def parse_current_docket(docket_record):
    # grab the file with the URL mangled slightly to grab 100k records
    docket_file = urllib2.urlopen(docket_record['url'] + "&ctl00_ctl00_cphContentMain_MainContent_gvCommentListChangePage=1_100000").read()
    page = pq(etree.fromstring(docket_file, parser))

    docket = dict(docket_record)

    docket['title'] = pq('.dyn_wrap h1').text().strip()
    assert docket['title'], 'no title found'

    headers = [item.text().strip() for item in page('.rgMasterTable thead th').items()]

    docket['comments'] = []

    # check if there's a no-records message
    if len(page('.rgMasterTable .rgNoRecords')):
        return docket
    
    for row in page('.rgMasterTable tbody tr').items():
        tds = row.find('td')
        cell_text = [item.text().strip() for item in tds.items()]
        cdata = dict(zip(headers, cell_text))
        
        link = pq(tds[-1]).find('a')

        doc = {
            'url': urlparse.urljoin(docket['url'], link.attr('href')),
            'details': {},
            'release': [fix_spaces(cdata['Release'])],
            'date': cdata['Date Received'],
            'type': 'public_submission',
        }

        vc_matches = re.findall(r"ViewComment\.aspx\?id=(\d+)", doc['url'])
        if vc_matches:
            doc['id'] = vc_matches[0]
            doc['subtype'] = 'comment'
            detail_columns = ['Organization', 'First Name', 'Last Name']
        else:
            ep_matches = re.findall(r"ViewExParte\.aspx\?id=(\d+)", doc['url'])
            if ep_matches:
                doc['id'] = "EP-%s" % ep_matches[0]
                doc['subtype'] = 'exparte'
                detail_columns = ['Organization']
            else:
                assert False, "expected either comment or exparte link: %s" % doc['url']

        for rdg_label, cftc_label in (('Organization Name', 'Organization'), ('First Name', 'First Name'), ('Last Name', 'Last Name')):
            if cftc_label in detail_columns and cdata[cftc_label]:
                doc['details'][rdg_label] = cdata[cftc_label]

        docket['comments'].append(doc)

    assert len(docket['comments']) < 100000, "we probably exceeded one page"

    # then strip out all the ones that aren't about this document
    release = fix_spaces(page('a[id*=rptReleases_hlReleaseLink]').text().strip())
    docket['comments'] = [comment for comment in docket['comments'] if comment['release'][0] == release]

    return docket

def parse_old_docket(docket_record):
    docket_file = urllib2.urlopen(docket_record['url']).read()
    page = pq(etree.fromstring(docket_file, parser))

    docket = dict(docket_record)

    release = page('ul.text p a').text().strip()
    if not re.match("\d+ FR \d+", release):
        release = None
    
    # hackery to get the title
    para_lines = [chunk.strip() for chunk in page('ul.text p a').parent().html().split("</a>")[-1].replace("&#13;", " ").split("<br />") if chunk.strip()]
    docket['title'] = para_lines[0]

    docket['comments'] = []

    for row in page('.list-release .row').items():
        date = row('.column-date').text().strip()
        if not date:
            # this is an FR document
            item = row('.column-item')
            label = item.text().strip()
            assert re.match('\d+ FR \d+', label), "Expected FR citation, got: %s" % label

            link = item.find('a')
            frnum = re.findall("[A-Z0-9-]+", link.attr('href').rsplit("/", 1)[-1])
            assert frnum, "expected FR num"
            doc = {
                'id': frnum[0],
                'title': label,
                'details': {
                    'Federal Register Citation': label,
                    'Federal Register Number': frnum[0]
                },
                'url': urlparse.urljoin(docket_record['url'], link.attr('href')),
                'doctype': 'Federal Register Release'
            }
        else:
            # this is a comment
            desc = row('.column-comment, .column-item')
            link = desc('a')
            link_label = link.text().strip()

            ll_is_id = re.match("^[A-Z]{2}\d+$", link_label)
            
            doc = {
                'date': date,
                'url': urlparse.urljoin(docket_record['url'], link.attr('href')),
                'title': re.split(r"<br ?/?>", desc.html().strip())[1].strip() if ll_is_id else link_label,
                'details': {}
            }
            if ll_is_id:
                doc['id'] = link_label
            if release:
                doc['release'] = [release]
            pages = row('.column-pages')
            if len(pages):
                doc['details']['Pages'] = pages.text().strip()

        docket['comments'].append(doc)

    return docket

def parse_ancient_docket(docket_record):
    return docket_record

def parse_sirt_docket(docket_record):
    return docket_record


def run(options, args):
    dockets = json.load(open(os.path.join(settings.DUMP_DIR, "cftc_dockets.json")))

    stats = {'fetched': 0, 'skipped': 0}

    docket_dir = os.path.join(settings.DUMP_DIR, "cftc_dockets")
    if not os.path.exists(docket_dir):
        os.mkdir(docket_dir)

    for i, docket in enumerate(dockets.itervalues()):
        if options.docket and docket['id'] != options.docket:
            continue

        if options.strategy and docket['strategy'] != options.strategy:
            continue

        if 'url' in docket:
            print 'Fetching %s...' % docket['id']
            print i, json.dumps(docket)
            fetched = globals()['parse_%s_docket' % docket['strategy']](docket)

            if options.verbose:
                print json.dumps(fetched, indent=4)

            outfile = open(os.path.join(docket_dir, "%s.json" % docket['id']), "wb")
            json.dump(fetched, outfile, indent=4)
            outfile.close()

            stats['fetched'] += 1
        else:
            print 'Skipping %s.' % docket['id']
            stats['skipped'] += 1

    print "Fetched %s dockets; skipped %s dockets." % (stats['fetched'], stats['skipped'])
    return stats