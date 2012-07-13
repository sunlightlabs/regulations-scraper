import pymongo
import csv
import datetime

from regscrape.models import *
db = Doc._get_db()

out = csv.DictWriter(open("dockets.csv", "w"), fieldnames=['title', 'docket_id', 'agency', 'fr_docs', 'submitters', 'mentioned', 'num_comments', 'num_public_interest_comments', 'num_bank_comments', 'num_law_firm_comments', 'word_count', 'last_seven'])
out.writeheader()

public_groups = ["ab09bc57f97b483391c483cbbdc479c8", "9c422ba85ac649269ce42804a6827059", "f8a9c531807f4585b1d5c73040b3c0fb", "f90cb1c4490344feba2ca83c2d3dd931", "be74818419c84a87b2b99c173aaea26d", "c58e0c68a7754ee2bd909fa68cecee7a", "2f0920a5271d41a7a85c4a7946775390", "10c585fd7f9d4cd1a82265e151b12f9e", "e31bfef434e9470b9e473d6182f2d021", "174a89892823486aad4538033fe0e8c7", "fb702029157e4c7c887172eba71c66c5", "6e5348b28f7242aab5437e0a34758350", "f89c8e3ab2b44f72971f91b764868231", "219154488de945e781330db65a54e1f4", "c5fe2c9b5a6c46fc8faeb34b8df6524f", "4536032e5d1d47248a5eddb86ce1a7f1", "23a8fb4b1188414ea125e06f34dc7df7", "3b14c79d157c4a8ab7e1bd7fdc589544"]
banks = ["5202316fe79343a09a31e8c6c31ebe3d", "bc1d056e59334c07bb0761b97efa64e4", "793070ae7f5e42c2a76a58663a588f3d", "4e6bc9a6b7dc40d7b9b00d58c0e359db", "8d93cebae445485f9af02676a2d71b3f", "91f9a88888d744da8d433018cf912460", "c28bf9dd2a0b4ac19408b645ecc74a7a", "71c49bc56b3a4d369e727fd22744876a", "597eccfe48784677a437569ff6293097", "9bea23144b304a31a790a6c3a9e5f9e6", "878b4d98431344de88d8fb9757043a95", "8c007e162ca1450cbe7f976732a9a770", "c86403b874ea4d9390574088a2973705", "46ff48813fc34247b8d31e22a13663c5", "1fecb472df7444d3822e784f1a0845e6", "c24ef68246554310aa03888ea10cd9bf", "8376751efebe4687b70c84b7c33e3c74", "31e6e04b59084d5c9b09c102680bcc32", "b6a33d8be4784be58c69e1e487a3ed8b", "162122d165e24747b2d7ebb064d7142f"]
law_firms = ["28f4d347bbae4d738aa3199346cf6850", "555e92b13c6640288ef76ee7c2bae09f", "783f8ace8f5d4a3c8a29c7d02b9a336f"]
one_week = datetime.timedelta(days=7)

for agency in db.dockets.find():
    row = {}
    row['title'] = agency['title'].encode('ascii', errors='ignore')
    row['docket_id'] = agency['_id']
    row['agency'] = agency['agency']

    row['fr_docs'] = "; ".join(["%s (%s)" % (doc['id'], doc['title'].encode('ascii', errors='ignore')) for doc in agency['stats']['fr_docs']])

    row['submitters'] = "; ".join([
        '%s (%s): %s' % (db.entities.find({'_id': item[0]})[0]['aliases'][0].encode('ascii', errors='ignore'), item[0], item[1])
        for item in sorted(agency['stats']['submitter_entities'].items(), key=lambda i: i[1], reverse=True)
    ])

    row['mentioned'] = "; ".join([
        '%s (%s): %s' % (db.entities.find({'_id': item[0]})[0]['aliases'][0].encode('ascii', errors='ignore'), item[0], item[1])
        for item in sorted(agency['stats']['text_entities'].items(), key=lambda i: i[1], reverse=True)
    ])

    row['num_comments'] = agency['stats']['type_breakdown'].get('public_submission', 0)

    row['num_public_interest_comments'] = sum([agency['stats']['submitter_entities'].get(entity, 0) for entity in public_groups])
    row['num_bank_comments'] = sum([agency['stats']['submitter_entities'].get(entity, 0) for entity in banks])
    row['num_law_firm_comments'] = sum([agency['stats']['submitter_entities'].get(entity, 0) for entity in law_firms])

    last_seven = 0
    word_count = 0
    for doc in db.docs.find({'docket_id': agency['_id'], 'type': 'public_submission'}):
        if doc['views']:
            word_count += max([len(View._from_son(view).content.read()) for view in doc['views'] if view['extracted'] == 'yes'] or [0])

        if doc.get('attachments', []):
            for attachment in doc['attachments']:
                if attachment['views']:
                    word_count += max([len(View._from_son(view).content.read()) for view in attachment['views'] if view['extracted'] == 'yes'] or [0])

        date = doc.get('details', {}).get('Date_Posted', None)
        if date and agency['stats']['date_range'][1]:
            if date > agency['stats']['date_range'][1] - one_week:
                last_seven += 1


    row['word_count'] = word_count
    row['last_seven'] = last_seven

    out.writerow(row)
