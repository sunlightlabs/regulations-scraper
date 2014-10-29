GEVENT = False

from regs_models import *

import settings
import rawes

def run():
    es = rawes.Elastic(getattr(settings, "ES_HOST", 'thrift://localhost:9500'), timeout=60.0)
    index = getattr(es, settings.ES_INDEX)

    records = {
        'sec_cftc': {},
        'regulations.gov': {}
    }

    for doc in Doc.objects(type__in=['notice', 'proposed_rule', 'rule'], agency__in=['SEC', 'CFTC']):
        # first check the annotation
        if 'fr_data' in doc.annotations and doc.annotations['fr_data']:
            #print 'annotation', doc.source, doc.id, doc.annotations['fr_data']['document_number']
            records[doc.source][doc.annotations['fr_data']['document_number']] = doc
        elif 'Federal_Register_Number' in doc.details:
            #print 'detail', doc.source, doc.id, doc.details['Federal_Register_Number']
            frn = doc.details['Federal_Register_Number']
            # trim leading zeros from the second part
            if "-" in frn:
                frnp = frn.split("-")
                frn = "-".join(frnp[:-1] + [frnp[-1].lstrip('0')])
            records[doc.source][frn] = doc

    overlap = records['sec_cftc'].viewkeys() & records['regulations.gov'].viewkeys()
    for frid in overlap:
        winner = records['sec_cftc'][frid]
        loser = records['regulations.gov'][frid]

        winner_dkt = Docket.objects.get(id=winner.docket_id)
        loser_dkt = Docket.objects.get(id=loser.docket_id)

        for w, l in ((winner, loser), (winner_dkt, loser_dkt)):
            replaces = set(w.suppression.get('replaces', []))
            replaces.add(l.id)
            w.suppression['replaces'] = list(replaces)

            replaced_by = set(l.suppression.get('replaced_by', []))
            replaced_by.add(w.id)
            l.suppression['replaced_by'] = list(replaced_by)

            l.save()
            w.save()

        try:
            index.docket.delete(loser_dkt.id)
            index.document.delete(loser.id)
        except:
            pass

        print '%s suppresses %s' % (winner.id, loser.id)