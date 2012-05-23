#!/usr/bin/env python

import sys, optparse, json

def run_command():    
    if len(sys.argv) < 2:
        print 'Usage: ./run.py <command>'
        sys.exit()
    command = sys.argv[1]
    
    if command.endswith('.py'):
        mod_name = command.split('/').pop().rsplit('.', 1)[0]
        import imp
        try:
            mod = imp.load_source(mod_name, command)
        except ImportError:
            print 'Could not load custom command: %s' % command
            sys.exit()
    else:
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
    
    dev_null = open('/dev/null', 'w')
    if parse_results[0].parsable:
        # disable standard output by monkey-patching sys.stdout
        real_stdout = sys.stdout
        sys.stdout = dev_null
    
    from regscrape_lib.util import bootstrap_settings
    bootstrap_settings()
    
    out = run(*(parse_results if parser_defined else []))
    
    if parse_results[0].parsable:
        # turn stdout back on so we can print output
        sys.stdout = real_stdout
        
        if out:
            print json.dumps(out)
    
    # no matter what, nuke stderr on exit so we can avoid that stupid gevent thing
    sys.stderr = dev_null
