GEVENT = False

from regs_models import *
import datetime

def run():
    for docket in Docket.objects(source="sec_cftc", scraped="no"):
        now = datetime.datetime.now()
        if not docket.title:
            candidates = list(Doc.objects(docket_id=docket.id, type__in=("rule", "proposed_rule", "notice")))
            candidates = sorted(candidates, key=lambda c: c.details.get('Date_Posted', now))
            
            # also consider type "other", but they're worse
            worse_candidates = list(Doc.objects(docket_id=docket.id, type="other"))
            worse_candidates = sorted(worse_candidates, key=lambda c: c.details.get('Date_Posted', now))

            candidates = candidates + worse_candidates

            if candidates:
                ctitle = candidates[0].title
            else:
                ctitle = docket.id
            
            print "For docket %s, proposing title: %s" % (docket.id, ctitle)
            
            docket.title = ctitle
        
        docket.scraped = 'yes'
        
        docket.save()