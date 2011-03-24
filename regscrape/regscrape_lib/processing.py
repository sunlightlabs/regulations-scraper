#!/usr/bin/env python

from pymongo import Connection
from bson.code import Code
from pymongo.objectid import ObjectId
import subprocess, os, urlparse, json

MAP = """
function() {
    if (this.Views) {
        for (var i = 0; i < this.Views.length; i++) {
            if (%s) {
                emit(this.Views[i].URL, {doc: this._id, view: this.Views[i]})
            }
        }
    }
}
"""

REDUCE = """
function(key, values) {
    return values[0];
}
"""

DB = Connection().regulations

def find_views(**params):
    rule = " && ".join(['this.Views[i].%s == %s' % (item[0], json.dumps(item[1])) for item in params.items()])
    mapfunc = MAP % rule
    
    results = DB.docs.map_reduce(Code(mapfunc), Code(REDUCE))
    
    return results

def update_view(id, view):
    oid = ObjectId(id)
    
    # can't figure out a way to do this automically because of bug SERVER-1050
    DB.docs.update({
        '_id': oid
    },
    {
        '$pull': { "Views": {"URL": view['URL']}}
    }, safe=True)
    DB.docs.update({
        '_id': oid
    },
    {
        '$push': { "Views": view}
    }, safe=True)
