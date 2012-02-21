#!/usr/bin/env python

import settings
MIN_SIZE = getattr(settings, 'MIN_DOWNLOAD_SIZE', 1024)

def run():
    # global imports hack so we don't mess up gevent loading
    global bulk_download, settings, subprocess, os, urlparse, sys, traceback, datetime, pymongo
    from regscrape_lib.processing import find_views, update_view, find_attachment_views, update_attachment_view
    from regscrape_lib.transfer import bulk_download
    import subprocess, os, urlparse, sys, traceback, datetime
    import pymongo
    
    return {
        'document_views': run_for_view_type('document views', find_views, update_view),
        'attachment_views': run_for_view_type('attachment views', find_attachment_views, update_attachment_view)
    }

def run_for_view_type(view_label, find_func, update_func):
    print 'Preparing download of %s.' % view_label
    
    views = find_func(downloaded=False, query={'deleted': False})
    workers = Pool(getattr(settings, 'DOWNLOADERS', 5))
    
    # track stats -- no locks because yay for cooperative multitasking
    stats = {'downloaded': 0, 'failed': 0}
    
    def download_generator():
        while True:
            result = views.next()

            filename = result['view']['url'].split('/')[-1]
            
            qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
            save_name = '%s.%s' % (qs['objectId'], qs['contentType'])
            save_path = os.path.join(settings.DOWNLOAD_DIR, newname)

            yield (result['view']['url'], save_path, result)
        except pymongo.errors.OperationFailure:
            # occasionally pymongo seems to lose track of the cursor for some reason, so reset the query
            views = find_func(downloaded=False, query={'deleted': False})
            continue
        except StopIteration:
            break
    
    def status_func(status, url, filename, result):
        if status[0]:
            result['view']['downloaded'] = True
            result['view']['file'] = filename
            result['view']['extracted'] = False
            stats['downloaded'] += 1
        else:
            result['view']['downloaded'] = "failed"
            result['view']['failure_reason'] = status[1]
            stats['failed'] += 1
        update_func(**result)
    
    bulk_download(download_generator(), status_func, verbose=True, min_size=MIN_SIZE)

    print 'Done with %s.' % view_label
    
    return stats

if __name__ == "__main__":
    run()
