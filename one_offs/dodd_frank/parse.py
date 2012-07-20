import subprocess
import sys

dockets = [docket.strip() for docket in open(sys.argv[1])]

for docket in dockets:
    try:
        p = subprocess.Popen(["./run.py", 'rdg_parse_api', '-d', docket, '-A'])
        p.communicate()
    except:
        print "failed %s" % docket