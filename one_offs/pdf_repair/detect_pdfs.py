GEVENT = False

def run():
    from regs_models import Doc
    import json
    from regs_common.processing import *
    
    problems = set()
    for finder in [find_views, find_attachment_views]:
        for view_d in finder(mode="html", type="pdf", extracted="yes"):
            content = view_d['view'].content.read()
            if not content:
                print "Weird:", view_d['doc']
            elif html_is_empty(content):
                print "Problem:", view_d['doc']
                problems.add(view_d['doc'])
            else:
                print "OK:", view_d['doc']
    
    print "%s problems" % len(problems)
    outfile = open("/tmp/problems.json", "w")
    json.dump(sorted(list(problems)), outfile)