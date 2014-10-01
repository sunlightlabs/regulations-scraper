import urllib2, urllib3
import subprocess
from gevent.pool import Pool
from gevent import Timeout
import greenlet
import settings
import datetime
import sys
import traceback
import time

def pump(input, output, chunk_size):
    size = 0
    while True:
        chunk = input.read(chunk_size)
        if not chunk: break
        output.write(chunk)
        size += len(chunk)
    return size

def download(url, output_file, post_data=None, headers=None):
    transfer = urllib2.urlopen(urllib2.Request(url, post_data, headers if headers else {}), timeout=10) if type(url) in (unicode, str) else url
    
    out = open(output_file, 'wb')
    size = pump(transfer, out, 16 * 1024)
    out.close()
    
    return size

def download_wget(url, output_file):
    proc = subprocess.Popen(['wget', '-nv', url, '-O', output_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    out = proc.communicate('')
    if 'URL:' in out[0] and os.path.exists(output_file):
        return os.stat(output_file).st_size
    elif 'ERROR' in out[0]:
        error_match = re.match('.*ERROR (\d{3}): (.*)', out[0].strip().replace('\n', ' '))
        if error_match:
            error_groups = error_match.groups()
            raise urllib2.HTTPError(url, error_groups[0], error_groups[1], {}, None)
    raise Exception("Something went wrong with the download.")

# pooled and timed-out versions of the transfer code
def tpump(input, output, chunk_size):
    size = 0
    while True:
        try:
            timeout = Timeout.start_new(5)
            chunk = input.read(chunk_size)
            timeout.cancel()
        except Timeout:
            input.release_conn()
            raise

        if not chunk: break
        output.write(chunk)
        size += len(chunk)
    return size

def download_pooled(url, output_file):
    transfer = CPOOL.urlopen("GET", url, timeout=10, preload_content=False)
    if transfer.status != 200:
        raise urllib2.HTTPError(url, transfer.status, transfer.reason, transfer.headers, None)

    out = open(output_file, 'wb')
    size = tpump(transfer, out, 16 * 1024)
    out.close()

    return size

def _get_downloader(status_func, download_func, retries, verbose, min_size, url, filename, record=None):
    def download_file():
        for try_num in xrange(retries):
            if verbose: print 'Downloading %s (try #%d, downloader %s)...' % (url, try_num, hash(greenlet.getcurrent()))
            
            download_succeeded = False
            download_message = None
            size = 0
            try:
                start = datetime.datetime.now()
                size = download_func(url, filename)
                download_succeeded = True
                elapsed = datetime.datetime.now() - start
            except urllib2.HTTPError as e:
                if verbose: print 'Download of %s failed due to error %s.' % (url, e.code)
                download_message = e.code
                
                if int(e.code) == 429:
                    if verbose: print 'Error occurred due to rate limiting; waiting 10 minutes.'
                    time.sleep(600)
            except Timeout as e:
                if verbose: print 'Download of %s timed out.' % url
            except:
                exc = sys.exc_info()
                if verbose: print traceback.print_tb(exc[2])
            
            if download_succeeded:
                if size >= min_size:
                    # print status
                    ksize = int(round(size/1024.0))
                    if verbose: print 'Downloaded %s to %s: %sk in %s seconds (%sk/sec)' % (url, filename, ksize, elapsed.seconds, round(float(ksize)/elapsed.seconds * 10)/10 if elapsed.seconds > 0 else '--')
                    break
                else:
                    download_succeeded = False
                    download_message = "Resulting file was smaller than the minimum file size."
                    if verbose: print download_message
        
        status_func(
            (download_succeeded, download_message),
            url,
            filename,
            record
        )
    return download_file


def bulk_download(download_iterable, status_func=None, retries=3, verbose=False, min_size=0):
    workers = Pool(getattr(settings, 'DOWNLOADERS', 5))
    
    # keep the downloaders busy with tasks as long as there are more results
    for download_record in download_iterable:
        workers.spawn(_get_downloader(status_func, download, retries, verbose, min_size, *download_record))
    
    workers.join()
    
    return

CPOOL = None
def pooled_bulk_download(download_iterable, status_func=None, retries=5, verbose=False, min_size=0):
    num_downloaders = getattr(settings, 'DOWNLOADERS', 5)
    global CPOOL
    if not CPOOL:
        CPOOL = urllib3.PoolManager(num_pools=2, maxsize=num_downloaders * 2)

    workers = Pool(num_downloaders)
    
    # keep the downloaders busy with tasks as long as there are more results
    for download_record in download_iterable:
        workers.spawn(_get_downloader(status_func, download_pooled, retries, verbose, min_size, *download_record))
    
    workers.join()
    
    return