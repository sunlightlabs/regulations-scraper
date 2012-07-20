import pymongo
import csv

db = pymongo.Connection().regulations_models

out = csv.DictWriter(open("agencies.csv", "w"), fieldnames=['agency', 'submitters', 'mentioned'])
out.writeheader()

for agency in db.agencies.find():
    row = {}
    row['agency'] = agency['_id']

    #row['fr_docs'] = ";".join(["%s (%s)" % (doc['id'], doc['title']) for doc in agency['stats']['fr_docs']])

    row['submitters'] = "; ".join([
        '%s (%s): %s' % (db.entities.find({'_id': item[0]})[0]['aliases'][0], item[0], item[1])
        for item in sorted(agency['stats']['submitter_entities'].items(), key=lambda i: i[1], reverse=True)
    ])

    row['mentioned'] = "; ".join([
        '%s (%s): %s' % (db.entities.find({'_id': item[0]})[0]['aliases'][0], item[0], item[1])
        for item in sorted(agency['stats']['text_entities'].items(), key=lambda i: i[1], reverse=True)
    ])

    out.writerow(row)
