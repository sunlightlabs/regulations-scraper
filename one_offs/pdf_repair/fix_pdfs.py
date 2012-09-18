GEVENT = False

from regs_models import Doc
import json
import itertools

def split_seq(iterable, size):
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))

all_ids = json.load(open("/tmp/problems.json"))
for ids in split_seq(all_ids, 1000):
    for doc in Doc.objects(id__in=ids):
        for view in doc.views:
            if view.type == "pdf" and view.mode == "html" and view.extracted == "yes":
                view.extracted = "no"
                view.content.delete()
        for attachment in doc.attachments:
            for view in attachment.views:
                if view.type == "pdf" and view.mode == "html" and view.extracted == "yes":
                    view.extracted = "no"
                    view.content.delete()
        doc.in_search_index = False
        doc.in_cluster_db = False
        doc.entities_last_extracted = None
        
        print "Repaired %s" % doc.id
        doc.save()