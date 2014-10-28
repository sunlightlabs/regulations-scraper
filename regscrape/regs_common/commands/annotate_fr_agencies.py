GEVENT = False

from regs_models import *
import json, urllib2

def run():
    fr_data = json.load(urllib2.urlopen("https://www.federalregister.gov/api/v1/agencies.json"))

    fr_dict = {r['short_name']: r for r in fr_data if r['short_name']}

    for agency in Agency.objects():
        if agency.id in fr_dict:
            agency.fr_id = fr_dict[agency.id]['id']
            agency.save()
            print "Saved %s with ID %s" % (agency.name, agency.fr_id)