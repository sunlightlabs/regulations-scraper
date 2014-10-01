import json, re, urlparse
from dateutil.parser import parse as parse_date
import datetime

import settings
from regs_models import *
from regs_common.util import *

GEVENT = False

type_mappings = {
    "notice": "notice",
    "other": "other",
    "proposed_rule": "proposed_rule",
    "public_submission": "public_submission",
    "rule": "rule",
    "General CFTC": "other",
    "Industry Filing": "other",
    "Orders and Other Announcements": "other",
    "Press Release": "other",
    "Privacy Act Systems": "other",
    "Proposed Rule": "proposed_rule",
    "Public Information Collection": "notice",
    "Sunshine Act": "other",
    "concept": "notice",
    "final": "rule",
    "interim-final-temp": "rule",
    "interp": "notice",
    "other": "other",
    "petitions": "other",
    "policy": "other",
    "proposed": "proposed_rule",
    # FIXME: this is terrible; should actually figure out what it is
    "Federal Register Release": "notice",
}
file_mapping = {
    'pdf': 'xpdf',
    'html': 'html',
    'htm': 'html'
}

def docket_record_to_model(record, agency):
    dkt = Docket()
    
    dkt.id = "%s-X-%s" % (agency, record['id'])
    dkt.agency = agency
    dkt.details['Source_ID'] = record['id']

    if 'title' in record and record['title']:
        dkt.title = record['title']

    if record.get('url', None):
        dkt['details']['Source_URL'] = record['url']

    dkt.source = 'sec_cftc'
    dkt.scraped = 'no'

    return dkt

def view_from_url(url):
    view = View()
    # strip fragments
    view.url = re.sub(r"#.*", "", url).strip()

    ext_matches = re.findall(r"\.([A-Za-z]+)$", view.url)
    if ext_matches:
        view.type = file_mapping.get(ext_matches[0], ext_matches[0])
    else:
        view.type = 'html'

    view.object_id = crockford_hash(view.url)

    return view

def fr_doc_record_to_model(record, agency):
    doc = Doc()
    
    if record['file_info']:
        file_info = record['file_info'][0]
        file_id = file_info['parent' if 'parent' in file_info else 'id']
    else:
        file_id = crockford_hash(record['id'])
    
    doc.docket_id = "%s-X-%s" % (agency, file_id)
    doc.id = "%s-%s" % (doc.docket_id, record['id'])

    doc.type = type_mappings[record['doctype']]

    if 'title' in record:
        doc.title = record['title']
    else:
        doc.title = record['id']

    doc.agency = agency
    doc.source = 'sec_cftc'
    doc.scraped = 'yes'

    doc.details = {k.replace(" ", "_").replace(".", ""): v for k, v in record.get("details", {}).iteritems()}
    if record.get('date', None) and record['date'].strip():
        doc.details['Date_Posted'] = parse_date(record['date'].strip())

    if record.get('description', None):
        doc.abstract = record['description']

    doc.fr_doc = doc.type in ('rule', 'proposed_rule', 'notice')

    doc.created = datetime.datetime.now()

    if record.get('url', None):
        doc.views.append(view_from_url(record['url']))

    for att in record.get('attachments', []):
        attachment = Attachment()
        attachment.title = att['title']
        for v in att['views']:
            view = view_from_url(v['url'])
            if 'type' in v:
                view.type = v['type']
            attachment.views.append(view)
        if attachment.views:
            attachment.object_id = attachment.views[0].object_id
        doc.attachments.append(attachment)

    return doc


def comment_record_to_model(record, agency, docket_id):
    doc = Doc()
    
    doc.docket_id = docket_id
    doc.id = "%s-%s" % (doc.docket_id, record['id'])

    doc.type = type_mappings[record['doctype']]

    if 'title' in record:
        doc.title = record['title']
    else:
        parts = []
        if 'First Name' in record['details']:
            parts.append(record['details']['First Name'] + (" " + record['details']['Last Name']) if 'Last Name' in record['details'] else "")
        if 'Organization Name' in record['details']:
            parts.append(record['details']['Organization Name'])
    
    if not doc.title:
        doc.title = record['id']

    doc.agency = agency
    doc.source = 'sec_cftc'
    
    if agency == 'CFTC' and 'comments.cftc.gov' in (record.get('url', '') or ''):
        doc.scraped = 'no'
    else:
        doc.scraped = 'yes'
    
    doc.details = {k.replace(" ", "_"): v for k, v in record.get("details", {}).iteritems()}
    if record.get('date', None) and record['date'].strip():
        try:
            doc.details['Date_Posted'] = parse_date(record['date'].strip())
        except:
            pass

    if record.get('description', None):
        doc.abstract = record['description']

    doc.fr_doc = doc.type in ('rule', 'proposed_rule', 'notice')

    doc.created = datetime.datetime.now()

    if record.get('url', None):
        doc.views.append(view_from_url(record['url']))

    for att in record.get('attachments', []):
        attachment = Attachment()
        attachment.title = att['title']
        attachment.views.append(view_from_url(att['url']))
        attachment.object_id = attachment.views[0].object_id
        doc.attachments.append(attachment)

    return doc

def run():
    for agency in ('CFTC', 'SEC'):
        lagency = agency.lower()

        all_dockets = {}
        dockets_for_saving = []

        # first deal with the docket file
        dockets = json.load(open(os.path.join(settings.DUMP_DIR, "%s_dockets.json" % lagency)))
        docket_dir = os.path.join(settings.DUMP_DIR, "%s_dockets" % lagency)

        for record in dockets.itervalues():
            print "Processing docket %s in %s..." % (record['id'], agency) 
            
            dkt = docket_record_to_model(record, agency)
            all_dockets[dkt.id] = dkt

            if 'parent' in record:
                dkt.details['Parent'] = record['parent']
            else:
                dockets_for_saving.append(dkt)

        # next deal with the FR documents
        doc_by_identifier = {}
        cftc_ancient_mapping = {}
        all_fr_docs = []

        fr_docs = json.load(open(os.path.join(settings.DUMP_DIR, "%s_fr_docs.json" % lagency)))
        for doc in fr_docs:
            if 'id' not in doc and 'url' in doc:
                doc['id'] = crockford_hash(doc['url'])

            if 'doctype' not in doc:
                doc['doctype'] = 'Federal Register Release'

            print "Processing FR doc %s in %s..." % (doc['id'], agency) 
            dc = fr_doc_record_to_model(doc, agency)
            for identifier in (doc['id'], dc.details.get('Federal_Register_Number', None), dc.details.get('Federal_Register_Citation', None)):
                if identifier:
                    doc_by_identifier[identifier] = dc

            # treat ancient CFTC FR docs specially because they'll show up again in the listing, so don't double count
            if agency == 'CFTC' and doc['strategy'] == 'ancient':
                if 'Federal_Register_Citation' in dc.details:
                    cftc_ancient_mapping[dc.details['Federal_Register_Citation'].split(" FR ")[-1]] = dc
            else:
                all_fr_docs.append(dc)

        # now deal with the regular documents
        all_comments = []
        for dkt in all_dockets.itervalues():
            json_file = os.path.join(docket_dir, "%s.json" % dkt.details['Source_ID'])
            if not os.path.exists(json_file):
                continue
            records = json.load(open(json_file))

            for comment_record in records['comments']:
                if 'doctype' not in comment_record:
                    comment_record['doctype'] = 'public_submission'

                if 'id' not in comment_record and 'url' in comment_record:
                    comment_record['id'] = crockford_hash(comment_record['url'])

                print "Processing comment %s in %s..." % (comment_record['id'], dkt.id) 
                cmt = comment_record_to_model(comment_record, agency, dkt.details['Parent'] if 'Parent' in dkt.details else dkt.id)
                
                if comment_record.get('release', None):
                    release = comment_record['release'][0]
                    if release in doc_by_identifier:
                        cmt.comment_on = {'document_id': doc_by_identifier[release].id}

                if 'Federal Register Page' in comment_record:
                    cmt.title = cftc_ancient_mapping[comment_record['details']['Federal Register Page']].title

                all_comments.append(cmt)

        print len(all_dockets), len(all_fr_docs), len(all_comments)
        
        for dkt in dockets_for_saving:
            dkt.save()
        
        for fr_doc in all_fr_docs:
            fr_doc.save()
        
        for cmt in all_comments:
            cmt.save()
