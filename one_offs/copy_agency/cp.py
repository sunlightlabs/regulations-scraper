import sys
import pymongo
import gridfs

source_db = pymongo.Connection(port=27019).regulations
dest_db = pymongo.Connection().regulations_demo

source_fs = gridfs.GridFS(source_db, 'files')
dest_fs = gridfs.GridFS(dest_db, 'files')

agency = sys.argv[1]

for doc in source_db.docs.find({'agency': agency}):
    print "Copying document %s..." % doc['_id']

    for attachment in [doc] + doc.get('attachments', []):
        for view in attachment.get('views', []):
            content_id = view.get('content', None)
            if content_id and source_fs.exists(content_id) and not dest_fs.exists(content_id):
                print "Copying file %s..." % content_id
                dest_fs.put(source_fs.get(content_id), _id=content_id)
    dest_db.docs.save(doc)