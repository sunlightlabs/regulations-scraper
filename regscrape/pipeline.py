import settings
import pymongo
import json
import sys
import os
import subprocess
import time
import signal
import datetime

DEFAULT_SEQUENCE = [
    'rdg_dump_api',
    'rdg_parse_api',
    'rdg_scrape',
    'rdg_download',
    'extract',
    'create_dockets',
    'rdg_scrape_dockets'
]
OVERRIDE_SEQUENCES = {}
FLAGS = {
    'scrape': ['-m', '8'],
    'scrape_dockets': ['-m', '8']
}

running = {}

db = pymongo.Connection(**settings.DB_SETTINGS)[settings.DB_NAME]
pid = os.getpid()

enabled = True
def sigint_handler(signum, frame):
    global enabled
    enabled = False
    print "Caught SIGINT; will exit after current tasks are complete."
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)

def preexec_function():
    # Ignore the SIGINT signal by setting the handler to the standard
    # signal handler SIG_IGN.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

# start by resetting failures
for agency_record in db.pipeline.find():
    sequence = OVERRIDE_SEQUENCES.get(agency_record['_id'], DEFAULT_SEQUENCE)
    completed = agency_record['completed']
    failed_idxs = [i for i in xrange(len(sequence)) if sequence[i] in completed and type(completed[sequence[i]]) != dict]
    if failed_idxs:
        print "Resetting everything for agency %s after command %s" % (agency_record['_id'], sequence[failed_idxs[0]])
        for command in sequence[failed_idxs[0]:]:
            if command in completed:
                print "Resetting %s" % command
                del completed[command]
        db.pipeline.update({'_id': agency_record['_id']}, {'$set': {'completed': completed}}, safe=True)

while True:
    now = str(datetime.datetime.now())
    print "[%s] TICK %s" % (now, pid)

    # book-keep already started processes
    for command, info in running.items():
        agency, proc = info
        if proc.poll() is not None:
            print "[%s] %s has finished command %s" % (now, agency, command)
            results = proc.stdout.read()
            try:
                parsed = json.loads(results)
            except ValueError:
                parsed = "parse_failure"

            db.pipeline.update({'_id': agency}, {'$set': {('completed.' + command): parsed}}, safe=True)
            del running[command]

    # start up new ones as necessary, assuming we're still going
    if enabled:
        for agency_record in db.pipeline.find().sort('count'):
            agency = agency_record['_id']

            sequence = OVERRIDE_SEQUENCES.get(agency, DEFAULT_SEQUENCE)
            completed = agency_record['completed'].keys()
            to_do = [command for command in sequence if command not in completed]

            if not to_do:
                continue

            next = to_do[0]
            if next not in running:
                full_command = [sys.executable, './run.py', next] + FLAGS.get(next, []) + ['-a', agency, '--parsable']
                proc = subprocess.Popen(full_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=preexec_function)
                running[next] = (agency, proc)
                print '[%s] %s has started command %s' % (now, agency, next)

    if not running.keys():
        print 'Nothing left to do; exiting.'
        break

    time.sleep(2)