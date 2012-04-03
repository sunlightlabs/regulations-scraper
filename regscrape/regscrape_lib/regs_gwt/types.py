from util import *

class SearchResultPackage(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_object()

class SearchResult(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_object() # agencies
        reader.read_object() # categories
        reader.read_object() # closing-soon?
        reader.read_object() # ?
        documents = reader.read_object() # documents
        reader.read_object()
        reader.read_object() # types
        reader.read_object() # newly posted
        reader.read_object()
        reader.read_int()
        reader.read_int()
        reader.read_int()
        
        return documents

# something of a hack -- we don't want the overhead of having to store the
# agencies when we return search results most of the time, but for actually
# *generating* the local agency list, we do. This class isn't used by default,
# and is identical to the one above, but returns agencies instead of documents.
class AgencySearchResult(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        agencies = reader.read_object() # agencies
        reader.read_object() # categories
        reader.read_object() # closing-soon?
        reader.read_object() # ?
        reader.read_object() # documents
        reader.read_object()
        reader.read_object() # types
        reader.read_object() # newly posted
        reader.read_object()
        reader.read_int()
        reader.read_int()
        reader.read_int()
        
        return agencies

class Agency(object):
    def __init__(self, abbr, num_results, num_results2, name):
        self.abbr = abbr
        self.num_results = num_results
        self.num_results2 = num_results2
        self.name = name
        
    @classmethod
    def gwt_deserialize(cls, reader):
        abbr = reader.read_string() # abbr
        num_results = reader.read_object() # num results
        num_results2 = reader.read_string() # num results
        name = reader.read_string() # name
        return cls(abbr, num_results, num_results, name)

class Category(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class ClosingSoon(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class NewlyPosted(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DimensionCounter(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_object()
        return reader.read_object()

class CommentPeriod(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocumentStatus(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocumentType(object):
    TYPES = ['public_submission', 'other', 'supporting_material', 'notice', 'rule', 'proposed_rule']
    
    @classmethod
    def gwt_deserialize(cls, reader):
        return cls.TYPES[reader.read_int()]

class DocketType(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocumentSummary(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        # Some stuff we don't care about
        reader.read_int()
        
        agency = reader.read_string() # agency_abbreviation
        
        has_attachments = reader.read_object()

        reader.read_int()
        
        allow_comments = reader.read_object() # allow comments
                
        # More stuff we don't care about
        reader.read_object()
        
        comment_due = reader.read_string()
        
        reader.read_string()
        reader.read_int()
        reader.read_string()
        reader.read_string()
        
        docket_id = reader.read_string()
        rule_title = reader.read_string()
        
        reader.read_object()
        
        document_id = reader.read_string()
        
        # Some stuff we don't care about after the document id
        reader.read_object()
        type = reader.read_object()
        
        formats = reader.read_object() # formats
        
        reader.read_object() # boolean
        reader.read_object()
        reader.read_object()
        reader.read_object()
        
        object_id = reader.read_string() # old_internal_id
        
        reader.read_string()
        reader.read_object() # date 3
        
        date_posted = reader.read_string()
        
        reader.read_string()
        reader.read_string() # context
        reader.read_string()
        
        title = reader.read_string()
        
        reader.read_string()
        reader.read_object() # sort info
                
        return exclude(locals(), ['cls', 'reader'])

class DocumentDetailPackage(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_object()

class DocumentDetail(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        attachments = reader.read_object()
        reader.read_int()
        
        comment_on = reader.read_object()
        comment_text = reader.read_string()
        
        reader.read_int()
        docket_id = reader.read_string() # docket ID
        reader.read_object()
        metadata = reader.read_object() # metadata array
        
        formats = reader.read_object() # content types
        
        reader.read_string() # another type?
        reader.read_int()
        
        rin = reader.read_string()
        
        reader.read_int()
        
        topics = reader.read_object()
        agency = reader.read_string() # agency
        document_id = reader.read_string() # document ID
        type = reader.read_object() # type
        
        reader.read_int()
        
        object_id = reader.read_string() # object ID
        title = reader.read_string() # title
        
        return exclude(locals(), ['cls', 'reader'])

class MetadataValue(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_object()

class Metadata(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        full_label = reader.read_string()
        short_label = reader.read_string()
        
        reader.read_int()
        reader.read_string()
        reader.read_string()
        reader.read_string()
        reader.read_int()
        reader.read_string()
        reader.read_int()
        reader.read_int()
        reader.read_int()
        reader.read_string()
        reader.read_string()
        reader.read_object()
        reader.read_int()
        
        value = reader.read_object()['value']
        
        return exclude(locals(), ['cls', 'reader'])

class MetadataUIControlType(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocumentBase(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_string() # seems to always be empty
        
        id = reader.read_string() # ID of the thing being commented on
        type = reader.read_object() # type of the thing being commented on
        
        reader.read_string() # title of the real document, again
        reader.read_string() # seems to always be empty
        
        title = reader.read_string() # title of the thing being commented on
        
        return exclude(locals(), ['cls', 'reader'])

class Attachment(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_string() # seems to always be empty
        
        abstract = reader.read_string() # abstract
        
        reader.read_int()
        reader.read_string() # seems to always be empty
        reader.read_int()
        
        formats = reader.read_object() # content types
        object_id = reader.read_string() # object ID
        
        reader.read_object() # posting restriction?
        reader.read_string() # seems to always be empty
        reader.read_string() # seems to always be empty
        reader.read_int()
        
        title = reader.read_string() # title
        
        return exclude(locals(), ['cls', 'reader'])

class PostingRestriction(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocketFolderMetadataPackage(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_object()

class DocketDetail(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        agency = reader.read_string() # agency
        
        reader.read_int() # always 0
        reader.read_int() # always 0
        reader.read_string() # always blank
        reader.read_string() # always blank
        reader.read_string() # always blank
        
        docket_id = reader.read_string() # docket ID
        
        reader.read_string() # always blank
        
        metadata = reader.read_object() # metadata dict
        
        reader.read_int() # always 0
        reader.read_int() # always 0
        reader.read_int() # always 0
        
        reader.read_string() # some kind of object ID?
        rin = reader.read_string() # rin
        title = reader.read_string() # title

        return exclude(locals(), ['cls', 'reader'])
