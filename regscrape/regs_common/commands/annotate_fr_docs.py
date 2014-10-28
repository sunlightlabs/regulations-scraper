#!/usr/bin/env python

GEVENT = False

from regs_common.exceptions import *
from regs_models import *
from optparse import OptionParser

import json, urllib, urllib2, os, re, datetime

from pyquery import PyQuery as pq
import dateutil.parser
import jellyfish

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket_id", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-s", "--source", dest="source", action="store", type="string", default=None, help="Specify a scraping source to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing FR data with new data.")

HEADER_MATCHER = re.compile(r"^[\*\s]*Federal Register[\*\s]*/ Vol. (\d+).*")
NUMBER = re.compile("^(\d+)$")
THREE_MONTHS = datetime.timedelta(days=90)

def fr_citation_from_view(view):
    view_text = view.as_text()
    lines = view_text.split("\n")

    # look for a page header
    header_match = [HEADER_MATCHER.match(l) for l in lines]
    header_lines = [(i, m.groups()[0]) for i, m in enumerate(header_match) if m]

    # now, for each, the page number will come either on the preceding or following line depending whether it's a left or right page
    number_match = {i: filter(bool, [NUMBER.match(lines[n].replace('*', '').strip()) for n in (i - 1, i + 1)]) for i, l in header_lines}

    header_lines_n = [(i, l, number_match[i][0].groups()[0]) for i, l in header_lines if number_match[i]]

    if header_lines_n:
        return "%s FR %s" % (header_lines_n[0][1], header_lines_n[0][2])

    return None

_fr_ids = {}
def fr_id_for_agency(agency):
    if agency in _fr_ids:
        return _fr_ids[agency]
    
    agency_obj = Agency.objects.get(id=agency)
    _fr_ids[agency] = agency_obj.fr_id if agency_obj.fr_id else None
    return _fr_ids[agency]

def levenshtein_ratio(s1, s2):
    s = len(s1) + len(s2)
    return (s - jellyfish.levenshtein_distance(s1.encode('utf8'), s2.encode('utf8'))) / float(s)

def guess_fr_num(doc):
    # if it's title-less or has a very short title, don't bother
    if not doc.title or len(doc.title) < 10:
        return None

    query = {'conditions[term]': doc.title}
    
    aid = fr_id_for_agency(doc.agency)
    if aid:
        query['conditions[agency_ids][]'] = str(aid)

    has_date = 'Date_Posted' in doc.details
    if has_date:
        # bracket the FR date by three months in either direction because sometimes they don't match
        query['conditions[publication_date][gte]'] = (doc.details['Date_Posted'] - THREE_MONTHS).strftime("%m/%d/%Y")
        query['conditions[publication_date][lte]'] = (doc.details['Date_Posted'] + THREE_MONTHS).strftime("%m/%d/%Y")

    # do search
    results = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/articles?" + urllib.urlencode(query)))
    if results['count']:
        # first annotate each with its title's distance to the real title, how far in time it is from the real time
        for result in results['results']:
            result['similarity'] = levenshtein_ratio(result['title'], doc.title)
            
            if has_date:
                real_date = dateutil.parser.parse(result['publication_date'])
                result['time_apart'] = abs(doc.details['Date_Posted'] - real_date)

        # then strip out all the ones that aren't at least 75% similar
        candidates = [result for result in results['results'] if result['similarity'] > 0.75]
        if not candidates:
            return None

        # then sort by how far away in time they are, if there are dates, or the distance otherwise
        if has_date:
            sorted_candidates = sorted(candidates, key=lambda r: r['time_apart'])
        else:
            sorted_candidates = sorted(candidates, key=lambda r: r['similarity'], reverse=True)

        return candidates[0]['document_number']

def fr_num_from_cite(fr_cite, title):
    # construct a query
    query = {'conditions[term]': fr_cite}

    # do search -- has to be by HTML because there doesn't seem to be a way to do citation searches via the API
    page = pq(url="https://www.federalregister.gov/articles/search?" + urllib.urlencode(query))
    links = page('.matching_citation_document h4 a')

    if not links:
        return None

    items = [(link.attr('href'), link.text()) for link in links.items()]

    # we order only by name because all results are on the same page and will therefore be from the same date
    sorted_items = sorted(items, key=lambda l: levenshtein_ratio(l[1], title), reverse=True)

    # the document number is the thing before the last slash
    return sorted_items[0][0].split("/")[-2]

def run(options, args):
    query = {'type__in': ['notice', 'proposed_rule', 'rule']}

    for filter_type in ('agency', 'docket_id', 'source'):
        filter_attr = getattr(options, filter_type)
        if filter_attr:
            query[filter_type] = filter_attr

    frn, frc, g, nd = 0, 0, 0, 0
    for doc in Doc.objects(**query):
        if 'fr_data' in doc.annotations and not options.process_all:
            continue
        
        fr_num = None
        fr_cite = None

        if 'Federal_Register_Number' in doc.details:
            print doc.id, 'FR num', doc.details['Federal_Register_Number'].encode('utf8')
            frn += 1

            # try fetching now; maybe we're done, but we can always try one of the other tactics if this doesn't work
            fr_num = doc.details['Federal_Register_Number'].encode('utf8')
            try:
                doc.annotations['fr_data'] = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/articles/" + fr_num))
                doc.save()
                print 'Succeeded with %s via FR number' % doc.id
                continue
            except:
                fr_num = None

        if 'Federal_Register_Citation' in doc.details:
            print doc.id, 'FR cite', doc.details['Federal_Register_Citation'].encode('utf8')
            frc += 1
            fr_cite = doc.details['Federal_Register_Citation'].encode('utf8')
            fr_num = fr_num_from_cite(fr_cite, doc.title)
            if fr_num:
                # try again
                try:
                    doc.annotations['fr_data'] = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/articles/" + fr_num))
                    doc.save()
                    print 'Succeeded with %s via FR citation' % doc.id
                    continue
                except:
                    fr_cite = None
                    fr_num = None
            else:
                fr_cite = None

        if not fr_num and not fr_cite:
            # does it have a PDF copy of the Federal Register version of the thing?
            views = None
            att = [a for a in doc.attachments if 'Federal Register' in a.title]
            if att:
                views = [v for v in att[0].views if v.type == 'pdf']

            if not views:
                views = [v for v in doc.views if v.type == 'xpdf']
            
            if views:
                fr_cite = fr_citation_from_view(views[0])

            if fr_cite:
                print doc.id, 'FR cite (by PDF)', fr_cite
                frc += 1

                fr_num = fr_num_from_cite(fr_cite, doc.title)
                if fr_num:
                    # try again
                    try:
                        doc.annotations['fr_data'] = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/articles/" + fr_num))
                        doc.save()
                        print 'Succeeded with %s via FR citation (PDF)' % doc.id
                        continue
                    except:
                        fr_cite = None
                        fr_num = None
                else:
                    fr_cite = None

            else:
                # last chance -- we guess from the title alone
                fr_num = guess_fr_num(doc)
                if fr_num:
                    # try again
                    try:
                        doc.annotations['fr_data'] = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/articles/" + fr_num))
                        doc.save()
                        g += 1
                        print 'Succeeded with %s via title guessing' % doc.id
                        continue
                    except:
                        fr_cite = None
                        fr_num = None
                else:
                    doc.annotations['fr_data'] = None
                    doc.save()
                    print doc.id, 'No dice'
                    nd += 1
    print frn, frc, g, nd