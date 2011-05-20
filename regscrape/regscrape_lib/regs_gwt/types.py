class SearchResultPackage(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_object()

class SearchResult(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_object() # agencies
        reader.read_object()
        documents = reader.read_object()
        return documents

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
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int()

class DocumentSummary(object):
    def __init__(self, document_id, object_id, formats):
        self.document_id = document_id
        self.object_id = object_id
        self.formats = formats
    
    @classmethod
    def gwt_deserialize(cls, reader):
        # Some stuff we don't care about
        reader.read_int()
        reader.read_string() # agency_abbreviation
        
        reader.read_object() # allow comments
        
        # More stuff we don't care about
        reader.read_object() # date 1
        reader.read_string()
        reader.read_object() # date 2
        reader.read_string()
        reader.read_string() # docket_number
        reader.read_string() # document_title
        
        document_id = reader.read_string()
        
        # Some stuff we don't care about after the document id
        reader.read_object()
        reader.read_object()
        formats = reader.read_object() # formats
        reader.read_object() # boolean
        object_id = reader.read_string() # old_internal_id
        reader.read_string()
        reader.read_object() # date 3
        reader.read_string()
        reader.read_string() # context
        reader.read_string()
        reader.read_int() # seems to always be 0
        reader.read_int() # seems to always be 1
        reader.read_object()
        
        return cls(document_id, object_id, formats)
