GEVENT = False

import urllib2, re, json, os, urlparse
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings

from regs_common.util import crockford_hash

def next_node(n):
    siblings = n.parent().contents()
    pos = [i for i in range(len(siblings)) if siblings[i] == n[0]][0]
    return siblings.eq(pos + 1)

def until_break_or_end(n):
    siblings = n.parent().contents()
    pos = [i for i in range(len(siblings)) if siblings[i] == n[0]][0]
    after = pq(siblings[pos + 1:])
    end = [j for j in range(len(after)) if getattr(after[j], 'tag', None) == 'br']
    if end:
        return pq(after[0:end[0]])
    else:
        return after

def prev_x_or_first(n, x):
    if type(x) != set:
        x = set([x])

    siblings = n.parent().contents()
    pos = [i for i in range(len(siblings)) if siblings[i] == n[0]][0]
    before = pq(siblings[:pos])
    end = [j for j in range(len(before) - 1, -1, -1) if getattr(before[j], 'tag', None) in x]
    if end:
        return pq(before[end[0]])
    else:
        return before.eq(0)

def parse_filing(filing):
    pass

def canonicalize_url(url):
    return "http://www.sec.gov%s" % url if url.startswith("/") else url

def get_file_number(url):
    # find the file number in the URL
    number = re.findall(r"((s\d+-)?\d+-\d+)", url)
    if number:
        return number[0][0].upper()
    else:
        # try an alternate strategy
        number = re.findall(r"(s?\d{4,5}).shtml", url)
        if number:
            if len(number[0]) == 6:
                return "S%s-%s-%s" % (number[0][1], number[0][2:4], number[0][4:6])
            elif len(number[0]) == 5:
                return "S%s-%s-%s" % (number[0][1], number[0][2:3], number[0][3:5])
            elif len(number[0]) == 4:
                return "%s-%s" % (number[0][0], number[0][1:])
            else:
                raise Exception, "digit count incorrect"
        else:
            return None

LINK_TYPES = {
    'xml': 'frxml',
    'pdf': 'pdf',
    'text': 'txt',
    'html': 'html'
}

def parse_year(year, doctype):
    fr_docs = []
    files = defaultdict(dict)

    rows = year('td[rowspan] table[cellpadding="4"] tr')
    for row in rows.items():
        if len(row.find('b.blue')):
            # this is an FR document, not a header or whatever
            cells = row.find('td')
            doc_link = cells.eq(0).find('a[href]')
            details = cells.eq(2)

            detail_titles = details.find('b i')

            comment_link = details.find('i a')

            all_links = details.find('a')

            doc = {
                'id': doc_link.html(),
                'date': cells.eq(1).html(),
                'title': details('b.blue').text(),
                'doctype': doctype,
                'details': {},
                'attachments': [],
                'file_info': OrderedDict()
            }

            for t in detail_titles.items():
                label = t.html()
                if not label:
                    continue
                label = label.strip().rstrip(':')
                
                if label == "See also":
                    links = [pq(x) for x in until_break_or_end(t.parent()) if getattr(x, 'tag', None) == 'a']
                    see_also = []
                    for l in links:
                        if l.text().lower() in ('comments', 'comments received'):
                            # this is a link to a comments page
                            purl = l.attr('href')
                            number = get_file_number(purl)
                            if number:
                                if number not in doc['file_info']:
                                    doc['file_info'][number] = {}
                                doc['file_info'][number]['url'] = canonicalize_url(purl)
                        else:
                            see_also.append({'label': l.text(), 'url': canonicalize_url(l.attr('href'))})
                    doc['details'][label] = see_also
                elif label == "Additional Materials":
                    materials = []
                    for el in t.parent().nextAll():
                        tag = getattr(el, 'tag', None)
                        if tag in ('i', 'b'):
                            # we're done
                            break
                        elif tag == 'a':
                            mlink = pq(el)
                            mlabel = mlink.text()

                            if mlabel == "Federal Register version":
                                # we're done again
                                break

                            materials.append({
                                'url': canonicalize_url(mlink.attr('href')),
                                'label': mlabel
                            })
                    doc['details'][label] = materials
                else:
                    bold = t.parent()
                    if bold.hasClass('blue'):
                        # this isn't a detail label at all, but rather part of the title; skip it
                        continue
                    
                    next = next_node(bold)[0]
                    if hasattr(next, "strip"):
                        text = next.strip()

                        if label.startswith("File No"):
                            text = next_node(t.parent())[0].strip()
                            numbers = re.findall(r"((S\d+-)?\d+-\d+)", text)
                            for number in numbers:
                                doc['file_info'][number[0]] = {}
                        else:
                            doc['details'][label] = text
                    else:
                        # this is a weird one that we're not going to try and handle
                        pass

            if len(comment_link):
                for cl in comment_link:
                    pcl = pq(cl)
                    if pcl.html() == "are available":
                        purl = pcl.attr('href')
                        # find the file number in the URL
                        number = get_file_number(purl)
                        if number:
                            if number not in doc['file_info']:
                                doc['file_info'][number] = {}
                            doc['file_info'][number]['url'] = canonicalize_url(purl)

            for link in all_links:
                plink = pq(link)
                link_label = plink.text().strip()
                if link_label == "HTML":
                    # found a new-style one
                    # walk backwards until we get to an italic
                    i = prev_x_or_first(plink, set(['b', 'i']))
                    # now walk forwards until the end
                    line = pq([i] + [el for el in until_break_or_end(i) if str(el).strip()])
                    
                    # sanity check
                    if line[0].text().rstrip(":") == "Federal Register":
                        # we're good

                        fr_cite = pq(line[1]).text()
                        if "FR" in fr_cite:
                            # the second block generally should have the FR number
                            doc['details']['Federal Register Citation'] = re.sub(r"(^[\s\(]+)|([\s\):]+$)", "", fr_cite)
                        else:
                            fr_cite = None

                        # the FR number is in the HTML URL
                        fr_match = re.findall(r".*federalregister.gov.*/(\d{4}-\d+)/.+", plink.attr('href'))
                        if fr_match:
                            doc['details']['Federal Register Number'] = fr_match[0]
                        
                        attachment = {
                            'title': ('Federal Register (%s)' % doc['details']['Federal Register Citation']) if fr_cite else "Federal Register version",
                            'views': []
                        }
                        fr_links = [tag for tag in line if getattr(tag, 'tag', None) == 'a']
                        for fl in fr_links:
                            pfl = pq(fl)
                            ltype = pfl.text().strip().lower()
                            attachment['views'].append({
                                'url': canonicalize_url(pfl.attr('href')),
                                'type': LINK_TYPES[ltype] if ltype in LINK_TYPES else pfl.attr('href').split('.')[-1]
                            })

                        doc['attachments'].append(attachment)
                    else:
                        print line[0].text()
                        assert False, "What strange sorcery is this? Expected FR link"
                elif link_label in ("Federal Register version", "Federal Register PDF"):
                    # found an old-style one
                    doc['attachments'].append({
                        'title': 'Federal Register version',
                        'views': [{'url': canonicalize_url(plink.attr('href')), 'type': 'pdf'}]
                    })

            if len(doc_link):
                doc['url'] = canonicalize_url(doc_link.attr('href'))
            else:
                # there's some weird old stuff that has things split into multiple pages
                attachment = {
                    'title': 'Document pages',
                    'views': []
                }
                for bold in details.find('b'):
                    pbold = pq(bold)
                    if pbold.text().strip() == "File names:":
                        all_names = until_break_or_end(pbold)
                        for el in all_names:
                            if getattr(el, 'tag', None) == 'a':
                                url = pq(el).attr('href')
                                attachment['views'].append({
                                    'url': canonicalize_url(url),
                                    'type': url.split(".")[-1]
                                })
                doc['attachments'].append(attachment)
                doc['id'] = cells.eq(0).text()


            file_list = []
            for key, value in doc['file_info'].iteritems():
                value['id'] = key
                file_list.append(value)

                files[key].update(value)

            doc['file_info'] = file_list

            print "Parsed %s %s..." % (doc['doctype'], doc['id'])
            fr_docs.append(doc)

    return {'fr_docs': fr_docs, 'files': files}

parser = etree.HTMLParser()
def get_years(doctype, current_only=False):
    years = []

    # grab the current year
    current = urllib2.urlopen("http://www.sec.gov/rules/%s.shtml" % doctype).read()
    cyear = pq(etree.fromstring(current, parser))
    years.append(cyear)

    if current_only:
        return years

    # grab the other years
    links = cyear('#archive-links a')
    for link in links.items():
        href = link.attr('href')
        if re.match(r'.*[a-z]+\d{4}\.shtml', href):
            old = urllib2.urlopen(canonicalize_url(href)).read()
            oyear = pq(etree.fromstring(old, parser))
            years.append(oyear)

    return years

def get_spotlight_files():
    out = {}
    for spotlight_type, spot_url in (("Dodd-Frank Act", "http://www.sec.gov/spotlight/regreformcomments.shtml"), ("JOBS Act", "https://www.sec.gov/spotlight/jobsactcomments.shtml")):
        spot_file = urllib2.urlopen(spot_url).read()
        page = pq(etree.fromstring(spot_file, parser))

        for link in page('a[href*="comments/df"],a[href*="comments/other"],a[href*="comments/jobs"]').items():
            href = urlparse.urljoin(spot_url, link.attr('href'))
            dkt = {
                'url': href,
                'id': crockford_hash(href)[:5],
                'type': 'nonrulemaking',
                'subtype': spotlight_type
            }
            out[dkt['id']] = dkt
    return out

def run():
    fr_docs = []
    files = defaultdict(dict)

    # get proposed, interim final, and final
    for doctype in ('proposed', 'interim-final-temp', 'final', 'concept', 'interp', 'policy', 'other', 'petitions'):
        years = get_years(doctype)

        for year in years:
            year_data = parse_year(year, doctype)
            fr_docs += year_data['fr_docs']
            for key, value in year_data['files'].iteritems():
                files[key].update(value)
                files[key]['type'] = 'rulemaking'
    
    # get Dodd-Frank non-rulemaking dockets
    for key, value in get_spotlight_files().iteritems():
        files[key].update(value)

    print "Retrieved info on %s key documents and %s dockets." % (len(fr_docs), len(files))

    
    for data, filename in ((fr_docs, "sec_fr_docs.json"), (files, "sec_dockets.json")):
        outfile = open(os.path.join(settings.DUMP_DIR, filename), "w")
        json.dump(data, outfile, indent=4)
        outfile.close()

    return {'fr_docs': len(fr_docs), 'dockets': len(files)}