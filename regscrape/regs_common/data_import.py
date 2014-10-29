import pymongo
import gridfs
import settings

def copy_data(source_db_name, dest_db_name, query):
    source = pymongo.Connection(**settings.DB_SETTINGS)[source_db_name]
    dest = pymongo.Connection(**settings.DB_SETTINGS)[dest_db_name]

    source_gridfs = gridfs.GridFS(source, collection='files')
    dest_gridfs = gridfs.GridFS(dest, collection='files')

    for doc in source.docs.find(query):
        print 'Copying doc %s...' % doc['_id']

        # flip some flags
        doc['stats'] = {}
        doc['in_aggregates'] = False
        doc['in_cluster_db'] = False
        doc['in_search_index'] = False

        dest.docs.save(doc)

        file_ids = []
        for view in doc.get('views', []):
            if view.get('content', None):
                file_ids.append(view['content'])
        
        for attachment in doc.get('attachments', []):
            for view in attachment.get('views', []):
                if view.get('content', None):
                    file_ids.append(view['content'])

        for fid in file_ids:
            print "Copying file %s" % fid

            # delete out of the dest in case it's already there
            dest_gridfs.delete(fid)

            # then read out from the old one
            fdata = source_gridfs.get(fid).read()

            # ... and write to the new one
            dest_gridfs.put(fdata, _id=fid)

        print "Done."

    dkt_query = dict(query)
    if "docket_id" in dkt_query:
        dkt_query['_id'] = dkt_query['docket_id']
        del dkt_query['docket_id']

    for dkt in source.dockets.find(dkt_query):
        print 'Copying docket %s...' % dkt['_id']

        # flip some flags
        dkt['stats'] = {}
        dkt['in_search_index'] = False

        if 'source' not in dkt:
            dkt['source'] = 'regulations.gov'

        dest.dockets.save(dkt)

        print "Done."