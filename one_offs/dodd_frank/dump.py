import subprocess
import sys

dockets = [docket.strip() for docket in open(sys.argv[1])]

for docket in dockets:
    p = subprocess.Popen(["./run.py", 'rdg_dump_api', '-d', docket])
    p.communicate()