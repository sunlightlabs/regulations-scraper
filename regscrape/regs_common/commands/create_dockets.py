from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

def run(options, args):
    import models
    
    db = models.Docket._get_db()
    new = 0
    
    print 'Starting docket query...'

    conditions = {}
    if options.agency:
        conditions['agency'] = options.agency
    if options.docket:
        conditions['id'] = options.docket

    docket_ids = db.docs.find(conditions).distinct('docket_id') if conditions.keys() else db.docs.distinct('docket_id')
    for docket_id in docket_ids:
        try:
            docket = models.Docket(id=docket_id)
            docket.save(force_insert=True)
            new += 1
        except:
            # we already have this one
            pass
    
    print 'Iterated over %s dockets, of which %s were new.' % (len(docket_ids), new)
    
    return {'total': len(docket_ids), 'new': new}
