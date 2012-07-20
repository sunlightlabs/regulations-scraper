from mongoengine import *

class Agency(Document):
    abbreviation = StringField(required=True, primary_key=True)
    name = StringField()

    stats = DictField()

    meta = {
        'allow_inheritance': False,
        'collection': 'agencies'
    }
