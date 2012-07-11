from mongoengine import *

class View(EmbeddedDocument):
    # data
    type = StringField(required=True)
    object_id = StringField()
    url = URLField(required=True)
    
    content = FileField(collection_name='files')
    mode = StringField(
        default="text",
        choices=["text", "html"]
    )
    
    file_path = StringField()

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

    def url(self):
        return 'http://www.regulations.gov/contentStreamer?objectId=%s&disposition=inline&contentType=%s' % (self.object_id, self.type)


class Attachment(EmbeddedDocument):
    # data
    title = StringField(required=True)
    object_id = StringField()
    abstract = StringField()

    # sub-docs
    views = ListField(field=EmbeddedDocumentField(View))

    meta = {
        'allow_inheritance': False,
    }


class Doc(Document):
    id = StringField(required=True, primary_key=True)

    # data
    title = StringField(required=True)
    agency = StringField(required=True)
    docket_id = StringField(required=True)
    type = StringField(
        required=True,
        choices=['public_submission', 'other', 'supporting_material', 'notice', 'rule', 'proposed_rule']
    )
    topics = ListField(field=StringField())
    object_id = StringField()
    details = DictField()

    abstract = StringField()
    rin = StringField()
    comment_on = DictField(default=None)

    submitter_entities = ListField(field=StringField())

    # sub-docs
    views = ListField(field=EmbeddedDocumentField(View))
    attachments = ListField(field=EmbeddedDocumentField(Attachment))

    # flags
    deleted = BooleanField(default=False)
    scraped = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    renamed = BooleanField(default=False)
    in_search_index = BooleanField(default=False)
    in_aggregates = BooleanField(default=False)
    fr_doc = BooleanField(default=False)
    
    # dates
    created = DateTimeField()
    last_seen = DateTimeField()
    entities_last_extracted = DateTimeField()

    meta = {
        'allow_inheritance': False,
        'collection': 'docs'
    }

    source = StringField(required=True, default="requlations.gov")