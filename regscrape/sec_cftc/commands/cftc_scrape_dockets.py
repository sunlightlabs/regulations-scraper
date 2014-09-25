GEVENT = False

import urllib2, re, json, os
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings

parser = etree.HTMLParser()

def fix_spaces(text):
    return re.sub(u"[\s\xa0]+", " ", text)

def parse_current_listing(year):
    page_data = urllib2.urlopen(year['url']).read()
    page = pq(etree.fromstring(page_data, parser))

    # iterate over fr doc groups
    for row in page('.row .column-item').items():
        top_level = row.children()
        doctype = row.find('p span[id*=ReleaseType]').text().strip()

        main_link = row.find('p a[id*=ReleaseLink]')
        main_link_text = main_link.text().strip()
        assert len(main_link) == 1, "found more than one main link"
        
        paras = []
        for possible_title in main_link.parent().nextAll('p').items():
            pt = possible_title.text().strip()
            if pt:
                paras.append(pt)

        doc = {
            'doctype': doctype,
            'title': fix_spaces(paras[0]) if doctype != "General CFTC" else main_link_text,
            'url': main_link.attr('href'),
            'description': (fix_spaces(paras[1]) if len(paras) > 1 else None) if doctype != "General CFTC" else fix_spaces(paras[0]),
            'details': {}
        }


        if re.match("\d+ FR \d+", main_link_text):
            doc['details']['Federal Register Citation'] = main_link_text

        fr_num_match = re.match('http://www.cftc.gov/LawRegulation/FederalRegister/[A-Za-z]+/(?P<fr_num>([A-Z0-9]+-)?(19|20)\d{2}-\d+)(-\d+)?.html', doc['url'])
        if fr_num_match:
            doc['details']['Federal Register Number'] = fr_num_match.groupdict()['fr_num']


        print doc

def parse_old_listing(year):
    pass

def parse_ancient_listing(year):
    pass

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

    for year in get_year_urls(current_only=True):
        print year
        globals()['parse_%s_listing' % year['strategy']](year)
        # year_data = parse_year(year, doctype)
    #     fr_docs += year_data['fr_docs']
    #     for key, value in year_data['files'].iteritems():
    #         files[key].update(value)
    # print "Retrieved info on %s key documents and %s dockets." % (len(fr_docs), len(files))

    
    # for data, filename in ((fr_docs, "sec_fr_docs.json"), (files, "sec_dockets.json")):
    #     outfile = open(os.path.join(settings.DUMP_DIR, filename), "w")
    #     json.dump(data, outfile, indent=4)
    #     outfile.close()

    return {'fr_docs': len(fr_docs), 'dockets': len(files)}