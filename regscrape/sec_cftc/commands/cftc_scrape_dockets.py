GEVENT = False

import urllib2, urlparse, re, json, os, sys
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings

from regs_common.util import crockford_hash

parser = etree.HTMLParser()

def fix_spaces(text):
    return re.sub(u"[\s\xa0]+", " ", text)

def check_date(date):
    assert re.match("^\d+/\d+/\d+$", date), "expected date of form MM/DD/YYYY"

def file_obj_from_url(url, existing_files=None):
    # current style
    matches = re.findall(r"CommentList.aspx\?id=(\d+)", url)
    if matches:
        return {
            'url': url,
            'id': matches[0],
            'strategy': 'current'
        }

    # SIRT
    matches = re.match(r".*sirt.aspx\?.*Topic=(?P<topic>[A-Za-z0-9]+).*&Key=(?P<key>\d+).*", url)
    if matches:
        gd = matches.groupdict()
        out = {
            'url': 'http://sirt.cftc.gov/sirt/sirt.aspx?Topic=%s&Key=%s' % (gd['topic'], gd['key']),
            'id': "SIRT-%s-%s" % (crockford_hash(gd['topic'])[:4], gd['key']),
            'strategy': 'sirt'
        }
        if existing_files:
            non_sirt = [f for f in existing_files if f['strategy'] != 'sirt']
            if non_sirt:
                out['parent'] = non_sirt[0]['id']
        return out
    elif 'sirt.cftc.gov' in url:
        # this is broken input, but there's nothing we can do about it
        return None

    # old style
    matches = re.findall(r"http://www.cftc.gov/LawRegulation/PublicComments/([A-Z0-9-]+)", url)
    if matches:
        return {
            'url': url,
            'id': "OS-%s" % matches[0],
            'strategy': 'old'
        }
    
    assert matches, "no ID found: %s" % url

def expand_comment_link(url, domain="comments.cftc.gov"):
    if "://" in url:
        return url
    elif url.startswith("/"):
        return "http://%s%s" % (domain, url)
    else:
        return "http://%s/PublicComments/%s" % (domain, url)

def parse_current_listing(year):
    page_data = urllib2.urlopen(year['url']).read()
    page = pq(etree.fromstring(page_data, parser))

    docs = []

    # iterate over fr doc groups
    for row in page('.row .column-item').items():
        top_level = row.children()
        doctype = row.find('p span[id*=ReleaseType]').text().strip()

        main_link = row.find('p a[id*=ReleaseLink]')
        main_link_text = main_link.text().strip()
        main_link_url = expand_comment_link(main_link.attr('href'))
        assert len(main_link) == 1, "found more than one main link"
        
        paras = []
        for possible_title in main_link.parent().nextAll('p').items():
            pt = possible_title.text().strip()
            if pt:
                paras.append(pt)

        doc = {
            'doctype': doctype,
            'title': fix_spaces(paras[0]) if doctype != "General CFTC" else main_link_text,
            'url': None,
            'description': (fix_spaces(paras[1]) if len(paras) > 1 else None) if doctype != "General CFTC" else fix_spaces(paras[0]),
            'details': {},
            'file_info': [],
            'year': year['year'],
            'strategy': 'current'
        }

        pdf_link = row.find('p a[id*=PDFLink]')
        if len(pdf_link):
            doc['pdf_link'] = pdf_link.attr('href')

        if re.match("\d+ FR \d+", main_link_text):
            doc['details']['Federal Register Citation'] = main_link_text

        fr_num_match = re.match('http://www.cftc.gov/LawRegulation/FederalRegister/[A-Za-z]+/(?P<fr_num>([A-Z0-9]+-)?(19|20)\d{2}-\d+)(-\d+)?.html', main_link_url)
        if fr_num_match:
            doc['details']['Federal Register Number'] = fr_num_match.groupdict()['fr_num']
            doc['id'] = doc['details']['Federal Register Number']

        if doctype == "General CFTC":
            doc['id'] = main_link_url.split("/")[-1].upper()

        open_date = row.find('div[id*=DateWrapper] div[id*=OpenDate]')
        if len(open_date):
            odate = open_date.text().split(":")[-1].strip()
            check_date(odate)

            doc['date'] = odate
            doc['details']['Comment Start Date'] = odate

        closing_date = row.find('div[id*=DateWrapper] div[id*=ClosingDate]')
        if len(closing_date):
            cdate = closing_date.text().split(":")[-1].strip()
            check_date(cdate)

            doc['details']['Comment Due Date'] = cdate

        see_also = row.find('div[style*=border]')
        if len(see_also):
            doc['details']['See also'] = []
        for sa_row in see_also.items():
            sa_link = sa_row.find('a[id*=ReleaseLink]')
            assert len(sa_link) == 1, "expected one release link; found %s" % len(sa_link)

            doc['details']['See also'].append({
                'url': expand_comment_link(sa_link.attr('href')),
                'label': sa_link.text().strip()
            })

        view_comments_link = row.find('a[id*=ViewComment]')
        assert len(view_comments_link) <= 1, "Too many comment links"
        if len(view_comments_link):
            url = expand_comment_link(view_comments_link.attr('href'))
            assert 'sirt.cftc.gov' in url or 'CommentList.aspx' in url, 'unrecognized URL type'
            obj = file_obj_from_url(url, doc['file_info'])
            if obj:
                doc['file_info'].append(obj)

        if 'sirt.cftc.gov' in main_link_url:
            # this is a link to a listing of documents, not to a document, so add it to the file_info listing if it's not already in there
            if main_link_url not in [fi['url'] for fi in doc['file_info']]:
                obj = file_obj_from_url(main_link_url, doc['file_info'])
                if obj:
                    doc['file_info'].append(obj)
            doc['id'] = main_link_text.replace(" ", "")
        else:
            doc['url'] = main_link_url


        docs.append(doc)
    return docs

def parse_old_listing(year):
    page_data = urllib2.urlopen(year['url']).read()
    page = pq(etree.fromstring(page_data, parser))

    docs = []

    # iterate over fr doc groups
    for row in page('.row .column-item').items():
        links = row.find('a[href]')
        assert len(links) in (1, 2), "Unexpected number of links: %s" % len(links)

        paras = [para.strip() for para in re.split("\n[ ]*\n", re.sub("<br ?/>", "\n", re.sub("\s+", " ", row.html())).strip())]

        # what kind of link the first link is decides what we do with the rest of it
        first_url = links.eq(0).attr('href')

        doctypes = re.findall(r"Comment File for ([^<\n]+)", paras[0])
        if 'PublicComments' in first_url:
            # it should have two links total, one to the comment list and one to the FR doc
            assert len(links) == 2, "Unexpected number of links: %s" % len(links)
            second_link = links.eq(1)
            second_link_text = second_link.text().strip()

            doc = {
                'doctype': doctypes[0].strip() if doctypes else None,
                'url': expand_comment_link(second_link.attr('href'), domain="www.cftc.gov"),
                'details': {},
                'file_info': [],
                'year': year['year'],
                'strategy': 'old'
            }

            if re.match("\d+ FR \d+", second_link_text):
                doc['title'] = fix_spaces(paras[1])
                doc['description'] = None

                doc['details']['Federal Register Citation'] = second_link_text
                fr_matches = re.findall("^http://www.cftc.gov/LawRegulation/FederalRegister/([A-Za-z0-9-]+)$", doc['url'])
                if fr_matches:
                    doc['details']['Federal Register Number'] = fr_matches[0].upper()
                    doc['id'] = doc['details']['Federal Register Number']
            else:
                # deal with this weird press release situation
                doc['title'] = second_link_text
                doc['description'] = paras[0].split("</a>")[-1].strip()

            obj = file_obj_from_url(expand_comment_link(first_url, domain="www.cftc.gov"))
            if obj:
                doc['file_info'].append(obj)

        elif 'sirt.cftc.gov' in first_url or 'services.cftc.gov' in first_url:
            # it should have just one link, to the document listing
            assert len(links) == 1, "Unexpected number of links: %s" % len(links)
            doc = {
                'doctype': doctypes[0].strip() if doctypes else None,
                'description': None,
                'url': None,
                'details': {},
                'file_info': [file_obj_from_url(first_url)],
                'id': links.eq(0).text().strip(),
                'year': year['year'],
                'strategy': 'old'
            }
            for para in paras:
                if para.startswith("Description:"):
                    doc['title'] = para.split(":", 1)[1].strip()
                elif "Filing Type: " in para:
                    ft = re.findall(r"Filing Type: ([^\n]+)", para, flags=re.MULTILINE)
                    doc['details']['Filing Type'] = ft[0]

        for date_type, label in (('Comment Start Date', 'Comments Open Date'), ('Comment Due Date', 'Comments Closing Date'), ('Extended Comment Due Date', 'Comments Extended Date')):
            date_match = re.findall(label + ": (\d+/\d+/\d+)", paras[-1], flags=re.MULTILINE)
            if date_match:
                doc['details'][date_type] = date_match[0]
                if date_type == "Comment Start Date":
                    doc['date'] = date_match[0]

        docs.append(doc)

    return docs

def is_ancient_label(text):
    return re.match("[A-Z ]+:", text)

def parse_ancient_listing(year):
    page_url = year['url']
    docs = []
    while True:
        page_data = urllib2.urlopen(page_url).read()
        page = pq(etree.fromstring(page_data, parser))

        groups = []
        group = []
        for table in page('table').items():
            divider = table.find('font[color*="#808000"]')
            if len(divider) and re.match(r".*-{10,}.*", divider.text()):
                if group:
                    groups.append(group)
                    group = []
            else:
                group.append(table)
        
        for group in (groups[1:] if page_url == year['url'] else groups):
            cells = pq([g[0] for g in group]).find('td')

            doc = {
                'title': fix_spaces(" ".join([item.text() for item in cells.find('b font').items()])),
                'id': cells.eq(0).text().strip().replace("--", "-"),
                'details': {},
                'file_info': [],
                'url': None,
                'year': year['year'],
                'strategy': 'ancient'
            }

            for i in range(len(cells)):
                text = fix_spaces(cells.eq(i).text().strip())
                if is_ancient_label(text):
                    next_text = fix_spaces(cells.eq(i + 1).text().strip())
                    next_text = next_text if not is_ancient_label(next_text) else None

                    if text == "FR CITE:":
                        fr_match = re.match(r"(?P<fr1>\d+) FR (?P<fr2>\d+)? ?\((?P<date>[A-Za-z]+ \d+ ?, \d+)\)", next_text)
                        if not fr_match:
                            # try it backwards because everything is terrible
                            fr_match = re.match(r"FR (?P<fr1>\d+) (?P<fr2>\d+) \((?P<date>[A-Za-z]+ \d+, \d+)\)", next_text)
                        
                        if fr_match:
                            fr_gd = fr_match.groupdict()
                            if 'fr1' in fr_gd and 'fr2' in fr_gd:
                                doc['details']['Federal Register Citation'] = "%s FR %s" % (fr_gd['fr1'], fr_gd['fr2'])
                            doc['date'] = doc['details']['Comment Start Date'] = fr_gd['date']
                        elif "Press Release" in next_text:
                            doc['details']['Press Release Number'] = next_text.split(" ")[-1]
                        else:
                            assert False, "No FR match found"
                    elif text == "CLOSES:":
                        doc['details']['Comment Due Date'] = next_text
                    elif text == "EXTENDED:" and next_text:
                        doc['details']['Extended Comment Due Date'] = next_text
                    elif text == "LINK TO FILE:":
                        doc['file_info'].append({
                            'url': urlparse.urljoin(page_url, cells.eq(i + 1).find('a').attr('href')),
                            'id': "AS-%s" % doc['id'],
                            'strategy': 'ancient',
                            'title': doc['title']
                        })

            docs.append(doc)

        # grab the 'next' link
        next_link = [a for a in page('a[href*=report]').items() if 'Next' in a.text()]
        if next_link:
            page_url = urlparse.urljoin(page_url, next_link[0].attr('href'))
        else:
            break

    return docs

def get_year_urls(current_only=False):
    # start by grabbing the current ones
    overview = urllib2.urlopen("http://comments.cftc.gov/PublicComments/ReleasesWithComments.aspx?Type=ListAll").read()
    opage = pq(etree.fromstring(overview, parser))
    
    years = []

    for link in opage('.bc-press-search[id*=Years] a').items():
        if "Year=" in link.attr('href'):
            record = {
                'year': int(link.text()),
                'url': 'http://comments.cftc.gov/PublicComments/%s' % link.attr('href'),
                'strategy': 'current'
            }
            assert record['year'] >= 2010 and record['year'] <= 2020, "failed year sanity check"
            years.append(record)
    assert len(years) >= 5, "Not enough years"

    # the older stuff isn't likely to change, so hard-code it
    for year in range(2009, 2006, -1):
        years.append({
            'year': year,
            'url': 'http://www.cftc.gov/LawRegulation/PublicComments/%s/index.htm' % year,
            'strategy': 'old'
        })

    for year in range(2006, 1997, -1):
        years.append({
            'year': year,
            'url': 'http://www.cftc.gov/foia/foiweb_%scomment_report_1.htm' % year,
            'strategy': 'ancient'
        })

    if current_only:
        return years[:1]

    return years
    

def run():
    fr_docs = []
    files = defaultdict(dict)

    for year in get_year_urls(current_only=False):
        print "Parsing %s with strategy %s" % (year['year'], year['strategy'])
        docs = globals()['parse_%s_listing' % year['strategy']](year)
        fr_docs += docs

        for doc in docs:
            for dfile in doc['file_info']:
                files[dfile['id']].update(dfile)

    print "Retrieved info on %s key documents and %s dockets." % (len(fr_docs), len(files))

    
    for data, filename in ((fr_docs, "cftc_fr_docs.json"), (files, "cftc_dockets.json")):
        outfile = open(os.path.join(settings.DUMP_DIR, filename), "w")
        json.dump(data, outfile, indent=4)
        outfile.close()

    return {'fr_docs': len(fr_docs), 'dockets': len(files)}