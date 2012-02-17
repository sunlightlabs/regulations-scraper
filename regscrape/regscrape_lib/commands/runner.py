#!/usr/bin/env python

import sys, optparse, json

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
    
    if getattr(mod, 'GEVENT', True):
        from gevent.monkey import patch_all
        patch_all()

    run = getattr(mod, 'run', False)
    if not run or not callable(run):
        print 'Command %s is not runnable' % command
        sys.exit()
    
    parser = getattr(mod, 'arg_parser', None)
    parser_defined = parser is not None
    
    if not parser:
        parser = optparse.OptionParser()
    parser.add_option('--parsable', dest='parsable', action='store_true', default=False, help='Output JSON instead of human-readable messages.')
    parse_results = parser.parse_args(sys.argv[2:])
    
    if parse_results[0].parsable:
        # disable standard output by monkey-patching sys.stdout
        dev_null = open('/dev/null', 'w')
        real_stdout = sys.stdout
        sys.stdout = dev_null
    
    from regscrape_lib.util import bootstrap_settings
    bootstrap_settings()
    
    out = run(*(parse_results if parser_defined else []))
    
    if parse_results[0].parsable:
        # turn stdout back on so we can print output
        sys.stdout = real_stdout
        # but disable stderr so we can avoid that stupid gevent thing
        sys.stderr = dev_null
        
        if out:
            print json.dumps(out)
