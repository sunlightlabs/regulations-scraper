#import cjson
import json
import re

class Reader(object):
    def __init__(self, client, json_body):
        self.client = client
#        parsed = cjson.decode(json_body)
        parsed = json.loads(json_body)
        
        self.version = parsed[-1]
        self.string_table = parsed[-3]
        self.data = parsed[:-3]
        
        self.max_prior_string_location = 0
        self.objects = []
    
    def read_int(self):
        return self.data.pop()
    
    def read_string(self, position=None):
        if not position:
            position = self.read_int()
        
        if position > (self.max_prior_string_location + 1):
            raise Exception('trying to read %s, which is too far ahead; max seen thus far is %s!' % (position, self.max_prior_string_location))
        
        if position > self.max_prior_string_location:
            self.max_prior_string_location += 1
        
        val = self.string_table[position - 1]
        
        return val
    
    def read_object(self):
        num = self.read_int()
        
        if num < 0:
            obj = self.objects[-1 - num]
        elif num > 0:
            java_class = self.read_string(num)
            java_class = re.sub(r'/\d+', '', java_class)
            python_class = self.client.java_class_to_python(java_class)
            
            if python_class:
                placeholder_position = len(self.objects)
                self.objects.append("PLACEHOLDER of type %s" % java_class)
                
                obj = python_class.gwt_deserialize(self)
                self.objects[placeholder_position] = obj
            else:
                raise Exception("unknown java class %s" % java_class)
            
        elif num == 0:
            obj = None
        
        return obj
