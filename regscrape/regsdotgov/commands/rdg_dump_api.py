def run():
    import urllib2
    import settings
    import os, time, sys
    from regsdotgov.regs_gwt.regs_client import RegsClient
    from regsdotgov.search import search
    from regs_common.transfer import download
    
    # delete old dumps
    [os.unlink(os.path.join(settings.DUMP_DIR, file)) for file in os.listdir(settings.DUMP_DIR) if file.endswith('.gwt')]
    
    # keep stats
    stats = {'downloaded': 0, 'failed': 0}
    
    # start new dumps
    client = RegsClient()
    position = settings.DUMP_START
    num_digits = len(str(settings.DUMP_END))
    while position <= settings.DUMP_END:
        for i in range(3):
            try:
                print "Downloading page %s of %s..." % ((position / settings.DUMP_INCREMENT) + 1, ((settings.DUMP_END - settings.DUMP_START) / settings.DUMP_INCREMENT) + 1)
                download(
                    search(settings.DUMP_INCREMENT, position, client),
                    os.path.join(settings.DUMP_DIR, 'dump_%s.gwt' % str(position).zfill(num_digits)),
                )
                stats['downloaded'] += 1
                break
            except urllib2.HTTPError:
                if i < 2:
                    print 'Download failed; will retry in 10 seconds...'
                    time.sleep(10)
                else:
                    print 'System troubles; giving up.'
                    raise
        
        position += settings.DUMP_INCREMENT
    
    return stats
