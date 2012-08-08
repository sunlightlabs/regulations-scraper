GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-a", "--agency", dest="agency", action="store", type="string", default=None, help="Specify an agency to which to limit the dump.")
arg_parser.add_option("-d", "--docket", dest="docket", action="store", type="string", default=None, help="Specify a docket to which to limit the dump.")
arg_parser.add_option("-A", "--all", dest="process_all", action="store_true", default=False, help="Replace existing MR data with new data.")

import multiprocessing

def run_client():
    from mincemeat import Client, DEFAULT_PORT
    import time
    import socket
    import os

    print "[%s] Starting worker" % os.getpid()
    while True:
        time.sleep(2)
        try:
            client = Client()
            client.password = ""
            client.conn('localhost', DEFAULT_PORT)
            return
        except socket.error as v:
            if v.errno == 54:
                print "[%s] Caught a socket error 54; resetting worker" % os.getpid()
            else:
                print "[%s] Caught a socket error %s; giving up" % (os.getpid(), v.errno)
                return

def run(options, args):
    print 'Running aggregates...'

    num_workers = multiprocessing.cpu_count()

    pool = multiprocessing.Pool(num_workers)

    for i in range(num_workers):
        pool.apply_async(run_client)

    from aggregates import run_aggregates
    run_aggregates(options)

    pool.terminate()

    print "Aggregates complete."
    
    return {'success': True}
