from pygwt.types import *

class Client(object):
    procedures = []
    class_map =[]
    
    def __init__(self):
        self.class_map = {
            "java.lang.String": GwtString,
            "java.util.ArrayList": GwtList,
            "java.util.Date": GwtDate,
            "java.lang.Long": GwtFloat,
            "java.util.HashMap": GwtDict,
            "java.lang.Integer": GwtInt,
            "java.lang.Boolean": GwtBool,
            "[Ljava.lang.String;": GwtMultipartString,
            "com.extjs.gxt.ui.client.data.RpcMap":  GxtDict,
            "com.extjs.gxt.ui.client.Style$SortDir":  GxtSortDir,
            "com.extjs.gxt.ui.client.data.SortInfo":  GxtSortInfo,
            "com.extjs.gxt.ui.client.data.BasePagingLoadResult": GxtPaginatedResultset
        }
    
    def python_class_to_java(self, py_class):
        return [key for key in self.class_map.keys() if self.class_map[key] == py_class][0]
    
    def java_class_to_python(self, java_class):
        return self.class_map.get(java_class, None)