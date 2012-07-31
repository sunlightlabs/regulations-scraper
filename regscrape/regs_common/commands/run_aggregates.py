GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing MR data with new data.")

from aggregates import run_aggregates
import multiprocessing
import time

from mincemeat import Client, DEFAULT_PORT

def run_client():
    client = Client()
    client.password = ""
    client.conn('localhost', DEFAULT_PORT)

def run(options, args):
    import models
    from collections import defaultdict
        
    print 'Running aggregates...'

    num_workers = multiprocessing.cpu_count()

    pool = multiprocessing.Pool(num_workers + 1)
    pool.apply_async(run_aggregates, [options])

    time.sleep(5)

    for i in range(num_workers):
        pool.apply_async(run_client)

    pool.close()
    pool.join()

    print "Aggregates complete."
    
    return {'success': True}
