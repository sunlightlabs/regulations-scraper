from mongoengine import *

class Docket(Document):
    docket_id = StringField(required=True, primary_key=True)

    title = StringField(required=True)
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
