#!/usr/bin/env python

import settings
MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")

def run(options, args):
    # global imports hack so we don't mess up gevent loading
    global bulk_download, settings, subprocess, os, urlparse, sys, traceback, datetime, pymongo
    from regs_common.processing import find_views, update_view, find_attachment_views, update_attachment_view
    from regs_common.transfer import bulk_download
    import subprocess, os, urlparse, sys, traceback, datetime
    import pymongo
    
    return {
        'document_views': run_for_view_type('document views', find_views, update_view, options),
        'attachment_views': run_for_view_type('attachment views', find_attachment_views, update_attachment_view, options)
    }

def run_for_view_type(view_label, find_func, update_func, options):
    print 'Preparing download of %s.' % view_label

    query = {'deleted': False}
    if options.agency:
        query['agency'] = options.agency
    if options.docket:
        query['docket_id'] = options.docket
    
    views = find_func(downloaded="no", query=query)
    
    # track stats -- no locks because yay for cooperative multitasking
    stats = {'downloaded': 0, 'failed': 0}
    
    # hack around stupid Python closure behavior
    v_array = [views]
    def download_generator():
        while True:
            try:
                result = v_array[0].next()
                                
                save_name = '%s.%s' % (result['view'].object_id, result['view'].type)
                save_path = os.path.join(settings.DOWNLOAD_DIR, save_name)
                
                yield (result['view'].url(), save_path, result)
            except pymongo.errors.OperationFailure:
                # occasionally pymongo seems to lose track of the cursor for some reason, so reset the query
                v_array[0] = find_func(downloaded="no", query=query)
                continue
            except StopIteration:
                break
    
    def status_func(status, url, filename, result):
        if status[0]:
            result['view'].downloaded = "yes"
            result['view'].file_path = filename
            stats['downloaded'] += 1
        else:
            result['view'].downloaded = "failed"
            stats['failed'] += 1
        update_func(**result)
    
    bulk_download(download_generator(), status_func, verbose=True, min_size=MIN_SIZE)

    print 'Done with %s.' % view_label
    
    return stats

if __name__ == "__main__":
    run()
