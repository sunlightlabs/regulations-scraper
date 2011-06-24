#!/usr/bin/env python

import sys

NO_GEVENT = ['scrape']

def run_command():    
    if len(sys.argv) < 2:
        print 'Usage: ./run.py <command>'
        sys.exit()
    command = sys.argv[1]
    
    if command not in NO_GEVENT:
        from gevent.monkey import patch_all
        patch_all()
    
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
    
    parser = getattr(mod, 'arg_parser', None)
    parse_results = []
    if parser:
        parse_results = parser.parse_args(sys.argv[2:])
    
    from regscrape_lib.util import bootstrap_settings
    bootstrap_settings()
    
    out = run(*parse_results)
    if out:
        print out
