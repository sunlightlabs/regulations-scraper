from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

def run(options, args):
    import urllib2, httplib
    import settings
    import os, time, sys
    from regsdotgov.search import search, parsed_search
    from regs_common.transfer import download

    search_args = {}
    id_string = 'all'
    if options.agency and options.docket:
        raise Exception("Specify either an agency or a docket")
    elif options.agency:
        search_args = {'agency': options.agency}
        id_string = 'agency_' + options.agency
    elif options.docket:
        search_args = {'docket': options.docket}
        id_string = 'docket_' + options.docket.replace('-', '_')

    # delete old dumps
    [os.unlink(os.path.join(settings.DUMP_DIR, file)) for file in os.listdir(settings.DUMP_DIR) if file.startswith('dump_%s' % id_string) and file.endswith('.json')]
    
    # keep stats
    stats = {'downloaded': 0, 'failed': 0}
    
    # start new dumps
    position = 0
    total = parsed_search(1, 0, **search_args)['totalNumRecords']
    num_digits = len(str(settings.DUMP_END))
    while position <= total:
        for i in range(3):
            try:
                current_str = (position / settings.DUMP_INCREMENT) + 1
                total_str = '?' if total == 1 else (total / settings.DUMP_INCREMENT) + 1
                print "Downloading page %s of %s..." % (current_str, total_str)
                download(
                    search(settings.DUMP_INCREMENT, position, **search_args),
                    os.path.join(settings.DUMP_DIR, 'dump_%s_%s.json' % (id_string, str(position).zfill(num_digits))),
                )
                stats['downloaded'] += 1
                break
            except (urllib2.HTTPError, httplib.HTTPException) as e:
                if i < 2:
                    if hasattr(e, 'code') and e.code in (503, 429) and 'rate' in e.read().lower():
                        print 'Download failed because of rate limiting; will retry in an hour...'
                        time.sleep(3600)
                    else:
                        print 'Download failed; will retry in 10 seconds...'
                        time.sleep(10)
                else:
                    print 'System troubles; giving up.'
                    raise
        
        position += settings.DUMP_INCREMENT
    
    return stats
