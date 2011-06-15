from reader import Reader
import re

class Response(object):
    def __init__(self, client, data):
        if getattr(data, 'read', False):
            data = data.read()
        
        data = data.replace('].concat([', ',')
        data = data.replace('],[', ',')
        data = data.replace('])', ']')
        data = data.replace(r'\x', r'\u00')
        
        string_list_start = data.index('[', 5)
        data = '%s%s' % (data[:string_list_start].replace("'", '"'), data[string_list_start:])
        
        if data[:4] == '//OK':
            data = data[4:]
            self.reader = Reader(client, data)
