GEVENT = False

from regs_models import *

from optparse import OptionParser
arg_parser = OptionParser()
arg_parser.add_option("-U", "--update", dest="update", action="store_true", default=False, help="Check if entities already existing before creating (slower)")

def run(options, args):
    import settings

    # if we're updating
    if options.update:
        print "Preparing to update existing entities; retrieving current entity list..."
        current = set((e.id for e in Entity.objects()))
        print "Entities retrieved."
    else:
        print "Constructing new entity list."

    # grab a dictionary
    word_file = getattr(settings, 'WORD_FILE', '/usr/share/dict/words')
    english_words = set([word.strip() for word in open(word_file, 'r') if word and word[0] == word[0].lower()])

    from influenceexplorer import InfluenceExplorer
    api = InfluenceExplorer(settings.API_KEY, getattr(settings, 'AGGREGATES_API_BASE_URL', "http://transparencydata.com/api/1.0/"))

    entities = []
    for type in ['individual', 'organization', 'politician']:
        count = api.entities.count(type)
        for i in range(0, count, 10000):
            entities.extend(api.entities.list(i, i + 10000, type))

    from oxtail.matching.normalize import normalize_list
    for entity in entities:
        record = {
            'id': entity['id'],
            'td_type': entity['type'],
            'td_name': entity['name'],
            'aliases': normalize_list([entity['name']] + entity['aliases'], entity['type'])
        }
        record['filtered_aliases'] = [alias for alias in record['aliases'] if alias.lower() not in english_words]
                
        if options.update and record['id'] in current:
            Entity.objects(id=record['id']) \
                  .update(safe_update=True, set__td_type=record['td_type'], set__td_name=record['td_name'], set__aliases=record['aliases'], set__filtered_aliases=record['filtered_aliases'])
            print "Updated %s as existing record %s" % (record['aliases'][0], record['id'])
        else:
            db_entity = Entity(**record)
            db_entity.save()
            print "Saved %s as new record %s" % (record['aliases'][0], record['id'])