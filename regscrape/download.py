#!/usr/bin/env python

MAP = """
function() {
    if (this.Views) {
        for (var i = 0; i < this.Views.length; i++) {
            if (!this.Views[i].Downloaded) {
                emit(this.Views[i].URL, {doc: this._id, url: this.Views[i].URL, type: this.Views[i].Type})
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

def run():
    from pymongo import Connection
    from bson.code import Code
    from pymongo.objectid import ObjectId
    import subprocess, os, urlparse
    
    # initial database pass
    db = Connection().regulations
    results = db.docs.map_reduce(Code(MAP), Code(REDUCE))
    
    f = open('/data/downloads/downloads.dat', 'w')
    for result in results.find():
        f.write(result['value']['url'])
        f.write('\n')
    f.close()
    
    # download
    proc = subprocess.Popen(['puf', '-xg', '-P', '/data/downloads', '-i', '/data/downloads/downloads.dat'])
    proc.wait()
    
    # database check pass
    for result in results.find():
        filename = result['value']['url'].split('/')[-1]
        fullpath = os.path.join('/data/downloads', filename)
        
        qs = dict(urlparse.parse_qsl(filename.split('?')[-1]))
        newname = '%s.%s' % (qs['objectId'], qs['contentType'])
        newfullpath = os.path.join('/data/downloads', newname)
        
        if os.path.exists(fullpath):
            # rename file to something more sensible
            os.rename(fullpath, newfullpath)
        
        if os.path.exists(newfullpath):
            # update database record to point to file
            
            # can't figure out a way to do this automically because of bug SERVER-1050
            db.docs.update({
                '_id': ObjectId(result['value']['doc'])
            },
            {
                '$pull': { "Views": {"URL": result['value']['url']}}
            }, safe=True)
            db.docs.update({
                '_id': ObjectId(result['value']['doc'])
            },
            {
                '$push': { "Views": {"URL": result['value']['url'], "Downloaded": True, "Type": result['value']['type'], "File": newfullpath, "Decoded": False}}
            }, safe=True)

if __name__ == "__main__":
    run()
