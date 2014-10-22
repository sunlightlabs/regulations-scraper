GEVENT = False

import urllib2, re, json, os, sys, operator, string
from pyquery import PyQuery as pq
from lxml import etree
from collections import OrderedDict, defaultdict
import settings
from optparse import OptionParser

from regs_common.util import crockford_hash

# arguments
arg_parser = OptionParser()
arg_parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False)
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

parser = etree.HTMLParser()

def canonicalize_url(url):
    return "http://www.sec.gov%s" % url if url.startswith("/") else url

DATE = r"(?P<date>(January|February|March|April|May|Jun.|June|July|August|Sept.|September|October|November|December) \d+[, ]+\d+)"
OLD_RECORD = re.compile(r"^(?P<title>.*),?( dated)? " + DATE + "[,\.]?( \d+ ?)?( ?[\[\(]((?!File ?[Nn]ames?).)*[\]\)].?)? \(+ ?((File ?[Nn]ames?)|(Attached File[0-9# ]+)): ?[^\)]+\)?( ?\(Attachment: (?P<attachment>.*)\))?.*?$", flags=re.MULTILINE)
def parse_old_record(text):
    record = OLD_RECORD.match(text)
    return record.groupdict() if record else None

def parse_old_record_dateless(text):
    record = re.match(r"^(?P<title>.*) \(File name: ?[^\)]+\)$", text, flags=re.MULTILINE)
    return record.groupdict() if record else None

def strip_filename(text):
    return re.sub("\(File name:.*\)", "", text).strip()

def strip_parenthesized_phrases(text):
    return re.sub("\(.*\)", "", text, flags=re.MULTILINE).strip()

def parse_table(table, release_no=None):
    records = defaultdict(list)

    # is it subdivided into headings?
    if len(table.find('h2')):
        # use the headings to decide what section we're in
        heading = None
    else:
        # things aren't listed separately, so instead decide by title
        heading = True

    # sometimes there's a breakage where a row tag isn't properly closed and you end up with rows inside other rows; if that happens, fix it before proceeding
    nested_rows = table.find('tr tr')
    if len(nested_rows):
        for nrow in list(nested_rows.items()):
            nparent = nrow.parent()
            while True:
                if nparent.parent().is_('table'):
                    break
                nparent = nparent.parent()

            nrow.remove()
            nparent.after(nrow)

    rows = table.find('tr')

    # now iterate over the rows, first finding headings and then classifying the comments under them
    for row in rows:
        prow = pq(row)
        row_heading = prow.find('h2')
        if len(row_heading):
            heading = row_heading.text()
            if heading not in ('Submitted Comments', 'Meetings with SEC Officials'):
                # try and guess what it is
                if "meeting" in heading.lower():
                    heading = 'Meetings with SEC Officials'
                elif "comments" in heading.lower():
                    heading = 'Submitted Comments'
                elif heading.startswith('Data Set'):
                    heading = 'Other'
                else:
                    assert False, "unrecognized category type: %s" % heading

        elif len(prow.find('hr')):
            # this is a horizontal rule row
            continue

        elif prow.text().startswith("Comments have been received"):
            # it's a bulk submission
            link = prow.find('a')

            if len(link) == 1:
                doc = {
                    'title': link.text(),
                    'url': canonicalize_url(link.attr('href')),
                    'num_received': int(prow.text().split(":")[-1].strip().replace(',', ''), 10)
                }
                if release_no:
                    doc['release'] = release_no
                records['Submitted Comments'].append(doc)
            else:
                # there should be a list
                form_rows = prow.find('ul li')
                assert len(form_rows) > 0, "there should be some form letter items"
                records['Submitted Comments'].extend(parse_form_rows(form_rows, release_no))
        elif heading:
            # we've already seen a heading, so this should be a regular comment
            cells = prow.find('td')

            if cells.text().strip() == "":
                # sometimes there are blank rows for no reason
                continue

            links = cells.eq(1).find('a[href]')
            link = links.eq(0)

            doc = {
                'date': cells.eq(0).text(),
                'title': link.text(),
                'url': canonicalize_url(link.attr('href'))
            }
            if release_no:
                doc['release'] = release_no

            if len(links) > 1:
                doc['attachments'] = []
                for link in links[1:]:
                    plink = pq(link)
                    doc['attachments'].append({
                        'title': plink.text(),
                        'url': canonicalize_url(plink.attr('href'))
                    })
                assert len(doc['attachments']) <= 10, "whoa, too many attachments"
            
            if heading is True:
                # decide by title
                records['Meetings with SEC Officials' if doc['title'].lower().startswith('memorandum') else 'Submitted Comments'].append(doc)
            else:
                records[heading].append(doc)
    return records

def parse_form_rows(form_rows, release_no=None):
    out = []
    for _tr in form_rows:
        tr = pq(_tr)
        tlink = tr.find('a[href]')
        assert len(tlink) == 1, "expected one form letter link"

        # get the number of submissions
        count = tr.text().split(":")[1]
        # cut extra cruft
        count = re.sub(r"[^0-9]", "", count)

        doc = {
            'title': tlink.text(),
            'url': canonicalize_url(tlink.attr('href')),
            'num_received': int(count, 10)
        }
        if release_no:
            doc['release'] = release_no
        out.append(doc)
    return out

def parse_list(rowlist, release_no=None):
    assert len(rowlist) >= 1, "there aren't any lists"

    records = defaultdict(list)

    rows = rowlist.children().filter('li')
    for row in rows:
        prow = pq(row)
        text = prow.text()
        text = re.sub("\s+", " ", text)

        # another stupid special case
        text = text.replace("Novemer", "November")

        if text.startswith("Comments have been received") or text.startswith("Comments received from individuals"):
            # this is a header for the bulk submissions; grab its children
            form_table = prow.nextAll('ul').eq(0).find('table')
            if not len(form_table):
                # maybe it's in this element
                form_table = prow.find('ul').find('table')

            form_rows = form_table.find('tr')

            if not form_rows:
                # maybe a different list structure?
                form_rows = prow.find('ol li')

            if not form_rows:
                # yet anothre list structure
                form_rows = [pq(x) for x in prow.find('ul').html().replace("<br/>", "\n\n\n").strip().split("\n\n\n")]
            
            assert len(form_rows) > 0, "expected to find at least one form letter"
            
            # FIXME: make this a function, to fix {"url": "http://www.sec.gov/comments/s7-25-06/s72506.shtml", "id": "S7-25-06"}
            records['Submitted Comments'].extend(parse_form_rows(form_rows, release_no))
            continue

        bulk_match = re.match("^Comments of (?P<count>\d+) [Ii]ndividuals.*", text)
        if bulk_match:
            # this is another type of bulk label
            blink = prow.find('a')
            assert len(blink) == 1, "expected one form letter link"
            doc = {
                'title': strip_filename(text),
                'url': canonicalize_url(blink.attr('href')),
                'num_received': int(bulk_match.groupdict()['count'].strip(), 10)
            }
            if release_no:
                doc['release'] = release_no
            records['Submitted Comments'].append(doc)
            continue

        if len(prow.find('a')) == 0:
            # not sure what this is, but if it has no links in it, it's not a comment
            continue

        rgroup = parse_old_record(text)
        if not rgroup:
            # maybe there's no date?
            rgroup = parse_old_record_dateless(text)
            
            if not rgroup and "NOTE!" in text:
                # special case http://www.sec.gov/rules/proposed/s73397.shtml, which treats PDFs as a miracle and provides explanatory links
                rgroup = {
                    'date': re.findall(DATE, text, flags=re.MULTILINE)[0][0],
                    'title': strip_parenthesized_phrases(text)
                }
                prow.find('a').eq(0).remove()

        assert rgroup, "no record found: %s" % text

        if 'attachment' in rgroup and rgroup['attachment']:
            # do some surgery on the row to distinguish between the main link and the attachment link
            html = prow.html()
            row_parts = re.split("(\(Attachment:.*\))", html)

            prow = pq("<div>")
            prow.html(row_parts[0])

            arow = pq("<div>")
            arow.html(row_parts[1])
        
        links = prow.find('a')
        assert len(links) > 0, "there aren't any links for this record"

        doc = {
            'title': rgroup['title'],
            'url': canonicalize_url(links.eq(0).attr('href'))
        }
        if 'date' in rgroup:
            doc['date'] = rgroup['date']
        if release_no:
            doc['release'] = release_no

        if 'attachment' in rgroup and rgroup['attachment']:
            # deal with the previously found attachment
            alink = arow.find('a[href]')
            assert len(alink) == 1, "expected one attachment link"

            doc['attachments'] = [{
                'title': strip_filename(rgroup['attachment']),
                'url': canonicalize_url(alink.attr('href'))
            }]

        if len(links) > 1:
            # some other links are in there and they're not in the expected attachment format, so just bolt them on with stupid names
            if 'attachments' not in doc:
                doc['attachments'] = []
            for link in links[1:]:
                palink = pq(link)
                doc['attachments'].append({
                    'title': palink.text().strip(" []()"),
                    'url': canonicalize_url(palink.attr('href'))
                })
            assert len(doc['attachments']) <= 10, "whoa, too many attachments"

        if rgroup['title'].lower().startswith("memorandum"):
            records['Meetings with SEC Officials'].append(doc)
        else:
            records['Submitted Comments'].append(doc)
    return records

META_SPLITTER = re.compile(r"((;|,| and )+)")
LEGAL_META_TYPES = ('Release No.', 'File No.', 'Release Nos.', 'File Nos.', 'International Series Release No.')
def parse_chunk(chunk):
    docket = {}

    title = chunk('h1')
    assert len(title) == 1, "there's more than one title"
    docket['title'] = title.text()

    meta = chunk('h2 i')

    if len(meta) == 0:
        # on some old releases it's an h4 instead, so make it an h2
        h4s = chunk('h4')
        for _h4 in h4s:
            h4 = pq(_h4)
            if len(h4.find('i')):
                h2 = pq("<h2>")
                h2.html(h4.html())
                h4.after(h2)
                h4.remove()
        meta = chunk('h2 i')

    # check if it's multiple broken metadata bits
    mhtml = meta.eq(0).html()
    if len(meta) and "<br/>" in meta.html():
        # go crazy and rearrange the page to put related things together
        mparts = mhtml.split("<br/>")
        for part in mparts:
            new_meta = pq("<h2>")

            # find the right part of the page
            h4s = chunk('h4')
            assert len(h4s) == len(mparts), "expect chunks to match headers"

            for _h4 in h4s:
                h4 = pq(_h4)
                rule_type = h4.text().replace(" Comments", "").strip()
                if rule_type in part:
                    new_meta.html("<i>" + part.replace(rule_type, "").strip() + "</i>")
                    h4.after(new_meta)

        meta.eq(0).remove()

        meta = chunk('h2 i')

    mtext = meta.eq(0).text()
    docket['details'] = {}
    
    if mtext:
        # special case a weird behavior on some old pages where there's no delimeter between metadata types
        weird_break_match = re.findall(r"[A-Z0-9-]?\d+ [A-Z][a-z]+", mtext)
        for wbm in weird_break_match:
            new_wbm = wbm.replace(" ", "; ")
            mtext = mtext.replace(wbm, new_wbm)

        # another special case
        missing_number_space = re.findall(r"Nos?.\d", mtext)
        for mns in missing_number_space:
            new_mns = mns.replace(".", ". ")
            mtext = mtext.replace(mns, new_mns)

        # and another one
        mtext = mtext.replace("- ", "-")
        
        mdata = [item for item in META_SPLITTER.split(mtext.lstrip("{([").rstrip("])}")) if not META_SPLITTER.match(item)]
        
        # sometimes the meta block ends up inside the title; fix that if it happened
        if mtext in docket['title']:
            docket['title'] = docket['title'].replace(mtext, "").strip()

        current_item = None
        for item in mdata:
            parts = item.strip().rsplit(" ", 1)
            if len(parts) == 2:
                current_item = parts[0]
                current_item = current_item.replace("Nos.", "No.").replace("Number", "No.").replace("Rel.", "Release").strip()

                # if it's all caps, fix its capitalization
                if " " in current_item and re.match(r"^[A-Z\. ]+$", current_item):
                    current_item = string.capwords(current_item)

                # if it's just Rel. but the thing looks like a release number, fix it
                if current_item == "Release" and re.match(r"^[0-9]+-[0-9]+$", parts[1].strip()):
                    current_item = "Release No."

                if current_item == "International Series No.":
                    current_item = "International Series Release No."

                assert current_item in LEGAL_META_TYPES, "Unrecognized meta type: %s" % current_item
                docket['details'][current_item] = [parts[1].strip()]
            elif len(parts) == 1:
                # this may be a continuation of the last one
                assert re.match(r"^[A-Z0-9-]+$", parts[0]), "Unrecognized meta component: %s" % parts[0]
                if not current_item:
                    current_item = "Release No."
                    docket['details'][current_item] = []
                docket['details'][current_item].append(parts[0])

    # now grab the table that lists all the things
    table = chunk('table[cellpadding="4"]')

    if len(table) == 1:
        # this is the new-style format
        # there might be more than one group even though there's just one table
        if len(table.find('h2 a[href]')) > 0:
            # there is; damn -- fake it
            trs = table.find('tr')
            section_heads = [i for i, tr in enumerate(trs) if len(pq(tr).find('h2')) > 0]
            section_heads.append(len(trs))

            out = []
            for i in range(len(section_heads) - 1):
                section = trs[section_heads[i]:section_heads[i + 1]]
                new_table = pq("<table cellpadding='4'>")
                details_h2 = pq("<h2>")
                for _tr in section:
                    tr = pq(_tr)
                    tr_h2 = tr.find('h2')
                    if len(tr_h2):
                        ntr = tr.clone()
                        ntr.find('h2').html("Submitted Comments")

                        details = dict(docket['details'])
                        for link in tr.find('h2 a'):
                            link_contents = pq(link).html().rsplit(" ", 1)
                            assert link_contents[0] in LEGAL_META_TYPES, "Unrecognized fake meta type: %s" % link_contents[0]
                            details[link_contents[0]] = [link_contents[1].strip()]

                        details_h2.html("<i>[%s]</i>" % "; ".join([" ".join([k, ", ".join(v)]) for k, v in details.items()]))
                        new_table.append(ntr)
                    else:
                        new_table.append(tr.clone())

                synth_chunk = pq("<div>")
                
                for el in [table.prevAll('h1')[-1], details_h2, new_table]:
                    if el is not None:
                        synth_chunk.append(pq(el).clone())
                
                out += parse_chunk(synth_chunk)
            return out
        else:
            # this is the typical case
            records = parse_table(table.eq(0), docket['details'].get('Release No.', None))
    elif len(table) > 1:
        # occasionally there's more than one table per title, so if this happens we fake it to make it look like there's just one
        out = []
        for i in range(len(table)):
            t = table.eq(i)
            synth_chunk = pq("<div>")
            
            for el in [t.prevAll('h1')[-1], t.prevAll('h2')[-1] if mtext else None, t]:
                if el is not None:
                    synth_chunk.append(pq(el).clone())
            
            out += parse_chunk(synth_chunk)
        return out
    else:
        # this is the old-style format
        if len(meta) <= 1:
            rowlist = chunk.children().filter('ul')
            
            if len(rowlist) == 0:
                # maybe there are li's but no ul's; if so, reparent.
                lis = chunk.children().filter('li')
                if len(lis):
                    rowlist = pq("<ul>")
                    rowlist.append(lis)
                    
                    # make sure the last one doesn't have any bullshit in it if the markup is broken
                    pq(lis[-1]).find('table').remove()

            records = parse_list(rowlist)
        else:
            # again, sometimes there are multiple groups, as with tables. Fake it.
            out = []
            for i in range(len(meta)):
                h = meta.eq(i)
                synth_chunk = pq("<div>")
                
                hparent = h.parent()
                for el in [hparent.prevAll('h1')[-1], hparent, hparent.nextAll('ul')[0]]:
                    if el is not None:
                        synth_chunk.append(pq(el).clone())
                
                out += parse_chunk(synth_chunk)
            return out

    docket['comments'] = records
    
    return [docket]

def fetch_docket(docket_record):
    docket_file = urllib2.urlopen(docket_record['url']).read()

    # fix a tag-closure problem, first spotted in http://www.sec.gov/comments/s7-14-08/s71408.shtml
    docket_file = re.sub("</tr\s+<tr", "</tr><tr", docket_file)

    page = pq(etree.fromstring(docket_file, parser))

    docket = dict(docket_record)

    titles = list(page('td[rowspan] h1'))
    
    if len(titles) == 0:
        # maybe there's an h2 masquerading as an h1
        for h2 in page('td[rowspan] h2'):
            ph2 = pq(h2)
            if ph2.text().startswith("Comments on"):
                # found it!
                h1 = pq("<h1>")
                h1.html(ph2.html())

                ph2.after(h1)
                ph2.remove()

                titles = h1
                break

    assert len(titles) > 0, "there aren't any titles"
    siblings = pq(titles[0]).parent().children()
    positions = [i for i in range(len(siblings)) if siblings[i] in titles]
    positions.append(len(siblings))

    chunks = [pq("<div>").append(pq(siblings[positions[i]:positions[i + 1]])) for i in range(len(positions) - 1)]
    
    docket['comment_groups'] = reduce(operator.add, [parse_chunk(chunk) for chunk in chunks])

    return flatten_docket(docket)

def flatten_docket(in_docket):
    out_cmts = []
    docket = dict(in_docket)

    for group in in_docket['comment_groups']:
        for heading, listing in group['comments'].iteritems():
            for comment in listing:
                if heading == "Other":
                    comment['doctype'] = 'other'
                else:
                    comment['doctype'] = 'public_submission'
                    if 'Comments' in heading:
                        comment['subtype'] = 'comment'
                    elif 'Meetings' in heading:
                        comment['subtype'] = 'exparte'
                    else:
                        assert False, 'unrecognized header type'

                if 'File No.' in group['details']:
                    comment['file'] = group['details']['File No.']

                # assign an ID if there isn't one
                if 'id' not in comment and 'url' in comment and comment['url']:
                    id_matches = re.findall("/[a-z]?\d+-(\d+).[a-z]+$", comment['url'])
                    if id_matches:
                        comment['id'] = id_matches[-1]
                    else:
                        comment['id'] = crockford_hash(comment['url'])

                out_cmts.append(comment)

    titles = [group['title'] for group in in_docket['comment_groups'] if 'title' in group]
    if titles:
        docket['title'] = titles[0]

    del docket['comment_groups']
    docket['comments'] = out_cmts

    return docket


def run(options, args):
    dockets = json.load(open(os.path.join(settings.DUMP_DIR, "sec_dockets.json")))

    stats = {'fetched': 0, 'skipped': 0}

    docket_dir = os.path.join(settings.DUMP_DIR, "sec_dockets")
    if not os.path.exists(docket_dir):
        os.mkdir(docket_dir)

    for i, docket in enumerate(dockets.itervalues()):
        if options.docket and docket['id'] != options.docket:
            continue

        if 'url' in docket:
            print 'Fetching %s...' % docket['id']
            print i, json.dumps(docket)
            fetched = fetch_docket(docket)

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