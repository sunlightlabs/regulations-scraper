GEVENT = False

import urllib2, re, json, os, sys, operator, string, urlparse, urllib, cookielib
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings
from optparse import OptionParser

from regs_common.util import crockford_hash
from regs_common.exceptions import ExtractionFailed

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
                'details': {},
                'doctype': 'public_submission'
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

def is_ancient_label(text):
    return re.match("[A-Z ]+:", text)

def parse_ancient_docket(docket_record):
    page_url = docket_record['url']
    
    docket = dict(docket_record)
    docket['comments'] = []

    while True:
        page_data = urllib2.urlopen(page_url).read()
        page = pq(etree.fromstring(page_data, parser))

        groups = []
        group = []
        first_divider = False
        for table in page('table').items():
            divider = table.find('font[color*="#808000"]')
            if len(divider) and re.match(r".*-{10,}.*", divider.text()):
                if not first_divider:
                    first_divider = True
                    continue
                if group:
                    groups.append(group)
                    group = []
            elif first_divider:
                group.append(table)

        for group in groups:
            cells = pq([g[0] for g in group]).find('td')

            doc = {
                'title': fix_spaces(" ".join([item.text() for item in pq([g[0] for g in group[1:]]).find('td[align=left] b font').items()])),
                'details': {},
                'url': None,
            }

            for i in range(len(cells)):
                text = fix_spaces(cells.eq(i).text().strip())
                if is_ancient_label(text):
                    next_text = fix_spaces(cells.eq(i + 1).text().strip())
                    next_text = next_text if not is_ancient_label(next_text) else None

                    if next_text:
                        if text == "DOCUMENT:":
                            # we need yet another cell
                            doc['id'] = next_text + fix_spaces(cells.eq(i + 2).text().strip())

                            if 'CL' in doc['id']:
                                doc['doctype'] = 'public_submission'
                            elif 'NC' in doc['id']:
                                doc['doctype'] = 'other'
                            elif 'FR' in doc['id']:
                                ltitle = doc['title'].lower()
                                if 'proposed' in ltitle:
                                    doc['doctype'] = 'proposed_rule'
                                elif 'final' in ltitle:
                                    doc['doctype'] = 'rule'
                                else:
                                    doc['doctype'] = 'notice'
                        elif text == "DATE:":
                            doc['date'] = next_text
                        elif text == "FR PAGE:" and "N/A" not in next_text.upper():
                            doc['details']['Federal Register Page'] = next_text
                        elif text == "PAGES:":
                            doc['details']['Pages'] = next_text
                        elif text == "PDF SIZE:":
                            doc['details']['PDF Size'] = next_text
                        elif text == "PDF LINK:":
                            link = cells.eq(i + 1).find('a')
                            if len(link):
                                doc['url'] = urlparse.urljoin(page_url, link.attr('href'))
            docket['comments'].append(doc)

        # grab the 'next' link
        next_link = [a for a in page('a[href*=foi]').items() if 'Next' in a.text()]
        if next_link:
            next_url = urlparse.urljoin(page_url, next_link[0].attr('href'))
            if next_url != page_url:
                page_url = next_url
            else:
                # apparently sometimes "next" points to the current page -- bail if so
                break
        else:
            break
    return docket

def parse_sirt_docket(docket_record):
    # okay, this one requires loading a paginated version, then checking a box that says "show all" to get everything...
    # which is arduous and stupid because it's a yucky ASP app.

    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    initial = pq(opener.open(docket_record['url']).read())

    error_header = initial("h4")
    if len(error_header) and "sorry" in error_header.text().lower():
        raise ExtractionFailed("This URL doesn't work.")

    formdata = urllib.urlencode((
            ('__EVENTTARGET', 'ctl00$cphContentMain$GenericWebUserControl$ShowAllCheckBox'),
            ('__EVENTARGUMENT', ''),
            ('__LASTFOCUS', ''),
            ('__VIEWSTATE', initial('#__VIEWSTATE').val()),
            ('__EVENTVALIDATION', initial('#__EVENTVALIDATION').val()),
            ('ctl00$masterScriptManager', ''),
            ('ctl00$cphContentMain$GenericWebUserControl$ShowAllCheckBox', 'on')
        ))

    page = pq(opener.open(docket_record['url'], data=formdata).read())

    docket = dict(docket_record)

    details = dict([re.split(r"\s*:\s*", row.strip()) for row in re.split(r"<br ?/?>", page('h5.QueryTitle').html()) if row.strip()])

    if 'details' not in docket:
        docket['details'] = {}

    if 'Filing Description' in details:
        docket['title'] = details['Filing Description']

    if 'Organization' in details:
        docket['details']['Organization Name'] = details['Organization']

    if 'Status' in details:
        docket['details']['Status'] = details['Status']

    docket['comments'] = []

    for link in page('.gradient-style tr td a').items():
        doc = {
            'url': urlparse.urljoin(docket_record['url'], link.attr('href')),
            'title': fix_spaces(link.text().strip()),
            'details': {},
        }
        doc['doctype'] = 'public_submission' if 'comment' in doc['title'].lower() else 'other'
        doc['id'] = crockford_hash(doc['url'])

        docket['comments'].append(doc)

    return docket


def run(options, args):
    dockets = json.load(open(os.path.join(settings.DUMP_DIR, "cftc_dockets.json")))

    stats = {'fetched': 0, 'skipped': 0, 'failed': 0}

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
            try:
                fetched = globals()['parse_%s_docket' % docket['strategy']](docket)
            except ExtractionFailed:
                print "FAILED to scrape docket data for %s" % docket['id']
                stats['failed'] += 1
                continue

            if options.verbose:
                print json.dumps(fetched, indent=4)

            outfile = open(os.path.join(docket_dir, "%s.json" % docket['id']), "wb")
            json.dump(fetched, outfile, indent=4)
            outfile.close()

            stats['fetched'] += 1
        else:
            print 'Skipping %s.' % docket['id']
            stats['skipped'] += 1

    print "Fetched %s dockets; skipped %s dockets; failed on %s dockets." % (stats['fetched'], stats['skipped'], stats['failed'])
    return stats