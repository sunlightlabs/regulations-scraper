GEVENT = False

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-d", "--delete", dest="delete", action="store_true", default=False, help="Delete the search index.")
arg_parser.add_option("-c", "--create", dest="create", action="store_true", default=False, help="Create the search index.")

from regs_models import *
import urllib2, json, os
import rawes

def run(options, args):
    import settings, regs_common

    es = rawes.Elastic(getattr(settings, "ES_HOST", 'thrift://localhost:9500'), timeout=30.0)
    index = getattr(es, settings.ES_INDEX)

    if options.delete:
        index.delete()
        print "Index deleted."

    if options.create:
        mapping_file = os.path.join(os.path.abspath(os.path.dirname(regs_common.__file__)), "data", "es_mapping.json")
        mapping_data = json.load(open(mapping_file))
        index.put(data={'mappings': mapping_data})
        print "Index created."

    stats = es._stats.get()
    print json.dumps(stats, indent=4)

    return stats