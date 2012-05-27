import gevent.subprocess
import gevent.monkey
from gevent.pool import Group
import gevent
gevent.monkey.patch_all()

import multiprocessing
import os
import sys
import subprocess

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-V", "--virtualenv", action="store", dest="virtualenv", default=None, help="the virtualenv in which to execute the aggregates")
parser.add_option("-w", "--workers", action="store", type="int", dest="workers", default=multiprocessing.cpu_count(), help="the number of workers to run")

(options, args) = parser.parse_args()

venv = None
if options.virtualenv:
    if options.virtualenv.startswith("/"):
        venv = options.virtualenv
    else:
        venv = os.path.join(os.environ['HOME'], '.virtualenvs', options.virtualenv)
elif 'VIRTUAL_ENV' in os.environ:
    venv = os.environ['VIRTUAL_ENV']

if venv:
    python = os.path.join(venv, 'bin', 'python')
    mincemeat = os.path.join(venv, 'bin', 'mincemeat.py')
else:
    python = sys.executable
    mincemeat = "mincemeat.py"

def master():
    aggregates = os.path.join(os.path.dirname(__file__), 'aggregates.py')
    proc = subprocess.Popen([python, aggregates], stdin=subprocess.PIPE)
    proc.communicate('')

def worker():
    proc = subprocess.Popen([python, mincemeat, 'localhost'], stdin=subprocess.PIPE)
    proc.communicate()

pool = Group()

pool.spawn(master)
gevent.sleep(0.5)

for i in range(options.workers):
    pool.spawn(worker)

pool.join()