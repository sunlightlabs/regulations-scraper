from optparse import OptionParser
arg_parser = OptionParser()

def run(options, args):
    import json, os
    from regscrape_lib.transfer import bulk_download

    if len(args) > 1:
        metadata_path = args[0]
        out_path = args[1]
    else:
        print "Specify files"
        sys.exit(0)
    
    input = json.load(open(metadata_path, 'r'))

    download_path = os.path.join(os.path.dirname(metadata_path), 'downloads')

    def download_generator():
        for record in input:
            for document in record['documents']:
                num = document['url'].split('=').pop() + '.pdf'
                yield (document['url'], os.path.join(download_path, num), document)
    
    def status_func(status, url, filename, record):
        if status[0]:
            record['filename'] = 'downloads/' + filename.split('downloads/').pop()
        else:
            record['filename'] = False
            record['download_error'] = status[1]
    
    bulk_download(download_generator(), status_func, retries=2, verbose=True)
    
    date_handler = lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else None
    open(out_path, 'w').write(json.dumps(input, default=date_handler, indent=4))