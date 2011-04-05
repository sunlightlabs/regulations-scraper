#!/usr/bin/env python

from bson.code import Code
from pymongo.objectid import ObjectId
import subprocess, os, urlparse, json
from regscrape_lib.util import get_db

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

DB = get_db()

def find_views(**params):
    rule = " && ".join(['this.Views[i].%s == %s' % (item[0], json.dumps(item[1])) for item in params.items()])
    mapfunc = MAP % rule
    
    results = DB.docs.inline_map_reduce(Code(mapfunc), Code(REDUCE), full_response=True)
    
    return DB[results['result']]

def update_view(id, view):
    oid = ObjectId(id)
    
    # can't figure out a way to do this atomically because of bug SERVER-1050
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

# the following is from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    import os
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

# the following is from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
import unicodedata, re

all_chars = (unichr(i) for i in xrange(0x110000))
control_chars = ''.join(c for c in all_chars if unicodedata.category(c) == 'Cc')
# or equivalently and much more efficiently
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))

control_char_re = re.compile('[%s]' % re.escape(control_chars))

def remove_control_chars(s):
    return control_char_re.sub('', s)
