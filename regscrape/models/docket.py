from mongoengine import *

class Docket(Document):
    id = StringField(required=True, primary_key=True)

    title = StringField()
    agency = StringField()
    rin = StringField()
    year = IntField()

    details = DictField()
    stats = DictField()

    scraped = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )

    meta = {
        'allow_inheritance': False,
        'collection': 'dockets'
    }
