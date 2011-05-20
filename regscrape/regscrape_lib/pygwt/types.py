class GwtList(list):
    @classmethod
    def gwt_deserialize(cls, reader):
        size = reader.read_int()
        
        obj = cls()
        for i in range(size):
            obj.append(reader.read_object())
        
        return obj

class GwtBool(object):
    @classmethod
    def gwt_deserialize(cls, reader):
        return reader.read_int() == 1

from datetime import datetime
class GwtDate(datetime):
    @classmethod
    def gwt_deserialize(cls, reader):
        reader.read_int() # don't know what this is
        return reader.read_int() # this looks like a timestamp in milliseconds

class GwtInt(int):
    @classmethod
    def gwt_deserialize(cls, reader):
        return cls(reader.read_int())

class GwtFloat(float):
    @classmethod
    def gwt_deserialize(cls, reader):
        ret = cls(reader.read_int())
        reader.read_int() # Ruby version ignores this?
        return ret

class GwtDict(dict):
    @classmethod
    def gwt_deserialize(cls, reader):
        size = reader.read_int()
        
        obj = cls()
        for i in range(size):
            key = reader.read_object()
            value = reader.read_object()
            obj[key] = value
        
        return obj

class GwtMultipartString(list):
    @classmethod
    def gwt_deserialize(cls, reader):
        size = reader.read_int()
        a = cls()
        for i in range(size):
            a.append(reader.read_string())
        return a

class GwtString(str):
    @classmethod
    def gwt_deserialize(cls, reader):
        return cls(reader.read_string())

class GxtDict(dict):
    @classmethod
    def gwt_deserialize(cls, reader):
        size = reader.read_int()
        
        obj = cls()
        for i in range(size):
            key = reader.read_string()
            value = reader.read_object()
            obj[key] = value
        
        return obj

class GxtPaginatedResultset(object):
    def __init__(self, offset, total_count, results):
        self.offset = offset
        self.total_count = total_count
        self.results = results
    
    @classmethod
    def gwt_deserialize(cls, reader):
        offset = reader.read_int()
        total_count = reader.read_int()
        results = reader.read_object()
        return cls(offset, total_count, results)

class GxtSortDir(object):
    def __init__(self, direction):
        self.direction = direction
    
    def __eq__(self, other):
        return self.direction == other.direction
    
    def __ne__(self, other):
        return self.direction != other.direction
    
    @classmethod
    def gwt_deserialize(cls, reader):
        return cls(reader.read_int())

class GxtSortInfo(object):
    def __init__(self, field, direction):
        self.direction = direction
        self.field = field
    
    @classmethod
    def gwt_deserialize(cls, reader):
        direction = reader.read_object()
        reader.read_int()
        reader.read_int()
        return cls(None, direction)