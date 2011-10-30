from fabric.api import *
from ssh_util import *
from collections import OrderedDict
import os, sys, json

VERBOSE = False

TASKS = [
    ('local', ['dump_api']),
    ('remote', ['parse_api', '-m 8']),
    ('remote', ['scrape', '-m 8']),
    ('local', ['download']),
    ('remote', ['extract']),
    ('local', ['create_dockets']),
    ('remote', ['scrape_dockets', '-m 8'])
]

ADMINS = []
EMAIL_SENDER = ''
EMAIL_API_KEY = ''
LOCK_DIR = '/tmp'

try:
    from local_settings import *
except:
    pass

def send_email(recipients, subject, message):
    from postmark import PMMail
    message = PMMail(
        to = ','.join(recipients),
        subject = '[regs] %s' % subject,
        text_body = message,
        api_key = EMAIL_API_KEY,
        sender = EMAIL_SENDER
    )
    message.send(test=False)

def run_local(command):
    os.chdir(os.path.expanduser('~/regulations-scraper/regscrape'))
    out = local(' '.join([sys.executable, command]), capture=True)
    return out

def run_remote(command):
    with cd('~/regulations-scraper/regscrape'):
        with prefix('source ~/.virtualenvs/scraper/bin/activate'):
            return run(command)

def handle_completion(message, results):
    output = '%s\nComplete results:\n%s' % (message, json.dumps(results, indent=4))
    print output
    
    if ADMINS:
        send_email(ADMINS, message, output)

def acquire_lock():
    lock_path = os.path.join(LOCK_DIR, 'regs.lock')
    if os.path.exists(lock_path):
        raise RuntimeError("Can't acquire lock.")
    else:
        lock = open(lock_path, 'w')
        lock.write(str(os.getpid()))
        lock.close()

def release_lock():
    lock_path = os.path.join(LOCK_DIR, 'regs.lock')
    os.unlink(lock_path)

@hosts(ssh_config('scraper'))
def run_regs(start_with='dump_api'):
    try:
        # use a lock file to keep multiple instances from trying to run simultaneously, which, among other things, consumes all of the memory on the high-CPU instance
        acquire_lock()
    except:
        print 'Unable to acquire lock.'
        if ADMINS:
            send_email(ADMINS, "Aborting: can't acquire lock", "Can't start processing due to inability to acquire lock.")
        
        sys.exit(1)
    
    tasks = TASKS[[i for i in range(len(TASKS)) if TASKS[i][1][0] == start_with][0]:] # eep! finds the thing to start with, then takes the subset of TASKS from then on
    runners = {
        'remote': run_remote,
        'local': run_local
    }
    results = OrderedDict()
    for func, command in tasks:
        try:
            output = runners[func](' '.join(['./run.py'] + command + ['--parsable']))
            try:
                results[command[0]] = json.loads(output)
            except ValueError:
                results[command[0]] = 'unable to decode results'
            if VERBOSE and ADMINS:
                send_email(ADMINS, 'Results of %s' % command[0], 'Results of %s:\n%s' % (command[0], json.dumps(results[command[0]], indent=4)))
        except SystemExit:
            results[command[0]] = 'failed'
            handle_completion('Aborting at step: %s' % command[0], results)
            sys.exit(1)
    handle_completion('All steps completed.', results)

    release_lock()
