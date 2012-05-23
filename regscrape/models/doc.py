from mongoengine import *

class View(EmbeddedDocument):
    # data
    type = StringField(required=True)
    url = URLField(required=True)
    
    content = FileField(collection_name='files')
    mode = StringField(
        default="text",
        choices=["text", "html"]
    )
    
    search_path = StringField()

    # flags
    downloaded = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    extracted = StringField(
        default="no",
        choices=["no", "failed_extraction", "failed_ocr", "yes"]
    )
    ocr=BooleanField(default=False)

    meta = {
        'allow_inheritance': False,
    }


class Attachment(EmbeddedDocument):
    # data
    title = StringField(required=True)
    object_id = StringField()
    abstract = StringField()

    # sub-docs
    views = ListField(field=View)

    meta = {
        'allow_inheritance': False,
    }


class Doc(Document):
    # data
    title = StringField(required=True)
    agency = StringField(required=True)
    docket_id = StringField(required=True)
    type = StringField(
        required=True,
        choices=['public_submission', 'other', 'supporting_material', 'notice', 'rule', 'proposed_rule']
    )
    topics = ListField()
    object_id = StringField()
    details = DictField()

    abstract = StringField()
    rin = StringField()
    comment_on = DictField(default=None)

    # sub-docs
    views = ListField(field=View)
    attachments = ListField(field=Attachment)

    # flags
    deleted = BooleanField(default=False)
    scraped = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    in_search_index = BooleanField(default=False)

    meta = {
        'allow_inheritance': False,
        'collection': 'docs'
    }

    source = StringField(required=True, default="requlations.gov")