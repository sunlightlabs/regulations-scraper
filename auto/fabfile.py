from fabric.api import *
from ssh_util import *
from collections import OrderedDict
import os, sys, json, datetime

VERBOSE = False

TASKS_ALWAYS = [
    ('local', ['rdg_scrape']),
    ('local', ['rdg_download']),
    ('local', ['extract']),
    ('local', ['create_dockets']),
    ('local', ['rdg_scrape_dockets']),
    ('local', ['match_text']),
    ('local', ['add_to_search']),
]

TASK_SETS = {
    'major': [
        ('local', ['rdg_dump_api']),
        ('local', ['rdg_parse_api']),
    ] + TASKS_ALWAYS + [
        ('local', ['run_aggregates', '-A']),
        ('remote', ['analyze_regs', '-F']),
    ],

    'minor': [
        ('local', ['rdg_simple_update']),
    ] + TASKS_ALWAYS + [
        ('local', ['run_aggregates']),
        ('remote', ['analyze_regs', '-F']),
    ]
}

ADMINS = []
EMAIL_SENDER = ''
EMAIL_API_KEY = ''
LOCK_DIR = '/tmp'
LOG_DIR = '/var/log/scrape'

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
    with cd('~/sparerib'):
        with prefix('source ~/.virtualenvs/sparerib_pypy/bin/activate'):
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

@hosts(ssh_config('regs-fe'))
def run_regs(start_with=None, end_with=None, task_set=None):
    try:
        # use a lock file to keep multiple instances from trying to run simultaneously, which, among other things, consumes all of the memory on the high-CPU instance
        acquire_lock()
    except:
        print 'Unable to acquire lock.'
        if ADMINS:
            send_email(ADMINS, "Aborting: can't acquire lock", "Can't start processing due to inability to acquire lock.")
        
        sys.exit(1)

    # get some logging stuff ready
    now = datetime.datetime.now()
    today = now.date().isoformat()
    month = today.rsplit('-', 1)[0]
    month_log_path = os.path.join(LOG_DIR, month)
    if not os.path.exists(month_log_path):
        os.mkdir(month_log_path)

    if not (task_set and task_set in TASK_SETS):
        # is it Sunday?
        is_sunday = now.weekday() == 6

        # have we run already today?
        run_already = len([log_file for log_file in os.listdir(month_log_path) if log_file.startswith(today)]) > 0

        if is_sunday and not run_already:
            task_set = 'major'
        else:
            task_set = 'minor'
    all_tasks = TASK_SETS[task_set]

    print 'Starting task set "%s"...' % task_set
    
    start_with = start_with if start_with is not None else all_tasks[0][1][0]
    end_with = end_with if end_with is not None else all_tasks[-1][1][0]
    
    first_task_idx = [i for i in range(len(all_tasks)) if all_tasks[i][1][0] == start_with][0]
    last_task_idx = [i for i in range(len(all_tasks)) if all_tasks[i][1][0] == end_with][0]
    tasks = all_tasks[first_task_idx:(last_task_idx+1)]
    runners = {
        'remote': run_remote,
        'local': run_local
    }
    results = OrderedDict()
    for func, command in tasks:
        try:
            output = runners[func](' '.join(['./run.py' if func == 'local' else './manage.py'] + command + ['--parsable']))
            try:
                results[command[0]] = json.loads(output)
            except ValueError:
                results[command[0]] = {'raw_results': output}
            if VERBOSE and ADMINS:
                send_email(ADMINS, 'Results of %s' % command[0], 'Results of %s:\n%s' % (command[0], json.dumps(results[command[0]], indent=4)))
        except SystemExit:
            results[command[0]] = 'failed'
            handle_completion('Aborting at step: %s' % command[0], results)
            sys.exit(1)
    handle_completion('All steps completed.', results)

    logfile = open(os.path.join(month_log_path, now.isoformat() + ".json"), "w")
    logfile.write(json.dumps(results, indent=4))
    logfile.close()

    release_lock()
