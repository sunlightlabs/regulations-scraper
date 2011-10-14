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
    out = local(command, capture=True)
    return out

def run_remote(command):
    with cd('~/regulations-scraper/regscrape'):
        with prefix('source ~/.virtualenvs/scraper/bin/activate'):
            return run('which python')

def handle_completion(message, results):
    output = '%s\nComplete results:\n%s' % (message, json.dumps(results, indent=4))
    print output
    
    if ADMINS:
        send_email(ADMINS, message, output)

@hosts(ssh_config('scraper'))
def run_regs(start_with='dump_api'):
    tasks = TASKS[[i for i in range(len(TASKS)) if TASKS[i][1][0] == start_with][0]:] # eep! finds the thing to start with, then takes the subset of TASKS from then on
    runners = {
        'remote': run_remote,
        'local': run_local
    }
    results = OrderedDict()
    for func, command in tasks:
        try:
            output = runners[func](' '.join(['./run.py'] + command + ['--parsable']))
            results[command[0]] = json.loads(output)
            if VERBOSE and ADMINS:
                send_email(ADMINS, 'Results of %s' % command[0], 'Results of %s:\n%s' % (command[0], json.dumps(results, indent=4)))
        except SystemExit:
            results[command[0]] = 'failed'
            handle_completion('Aborting at step: %s' % command[0], results)
            sys.exit(1)
    handle_completion('All steps completed.', results)
