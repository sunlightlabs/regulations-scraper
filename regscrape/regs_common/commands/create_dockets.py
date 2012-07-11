def run():
    import models
    
    db = models.Docket._get_db()
    new = 0
    
    print 'Starting docket query...'
    docket_ids = db.docs.distinct('docket_id')
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
