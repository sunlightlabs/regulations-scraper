from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

def run(options, args):
    import models
    from collections import defaultdict

    db = models.Docket._get_db()
    new = 0
    
    print 'Starting docket query...'

    conditions = {}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['id'] = options.docket

    # there's no way to do this aggregation without a map-reduce in Mongo 2.0, so do it on the Python side for now
    # once 2.2 is final, this can trivially be replaced with a $group + $addToSet pipeline using the new aggregation framework
    dockets = defaultdict(set)
    for doc in db.docs.find(conditions, fields=['docket_id', 'agency']):
        dockets[doc['docket_id']].add(doc['agency'])

    for docket_id, agencies in dockets.iteritems():
        if docket_id:
            agency = list(agencies)[0] if len(agencies) == 1 else sorted(agencies, key=lambda a: docket_id.startswith(a), reverse=True)[0]
            try:
                docket = models.Docket(id=docket_id, agency=agency)
                docket.save(force_insert=True)
                new += 1
            except:
                # we already have this one
                pass
    
    total = len(dockets.keys())
    print 'Iterated over %s dockets, of which %s were new.' % (total, new)
    
    return {'total': total, 'new': new}
