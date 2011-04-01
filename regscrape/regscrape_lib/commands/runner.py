#!/usr/bin/env python

import sys

def run_command():
    if len(sys.argv) < 2:
        print 'Usage: ./run.py <command>'
        sys.exit()
    command = sys.argv[1]

    try:
        parent_mod = __import__('regscrape_lib.commands', fromlist=[command])
        mod = getattr(parent_mod, command)
    except ImportError:
        print 'No such command: %s' % command
        sys.exit()
    
    run = getattr(mod, 'run', False)
    if not run or not callable(run):
        print 'Command %s is not runnable' % command
        sys.exit()
    
    out = run()
    if out:
        print out