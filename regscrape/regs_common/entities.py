def all_aliases():
    import itertools
    from regs_common.util import get_db
    db = get_db()

    return itertools.chain.from_iterable(
        itertools.imap(
            lambda entity: [(alias, entity['_id']) for alias in entity['aliases']],
            db.entities.find()
        )
    )

def load_trie_from_mongo():
    from oxtail import matching

    matching._entity_trie = matching.build_token_trie(
        all_aliases(),
        matching._blacklist
    )