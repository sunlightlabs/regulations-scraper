from mongoengine import *

class Agency(Document):
    id = StringField(required=True, primary_key=True)
    name = StringField()

    rdg_participating = BooleanField(default=False)

    stats = DictField()

    meta = {
        'allow_inheritance': False,
        'collection': 'agencies'
    }
