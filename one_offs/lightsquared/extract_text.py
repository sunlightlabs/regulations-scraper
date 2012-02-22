from optparse import OptionParser
arg_parser = OptionParser()

def run(options, args):
    import json, os
    from regscrape_lib.extraction import serial_bulk_extract

    if len(args) > 1:
        metadata_path = args[0]
        out_path = args[1]
    else:
        print "Specify files"
        sys.exit(0)
    
    input = json.load(open(metadata_path, 'r'))

    file_path = os.path.dirname(metadata_path)

    def extract_generator():
        for record in input:
            for document in record['documents']:
                yield (os.path.join(file_path, document['filename']), 'pdf', document)
    
    def status_func(status, text, filename, filetype, used_ocr, record):
        if status[0]:
            record['text'] = text
        else:
            record['text'] = None
            record['extraction_error'] = status[1]
    
    serial_bulk_extract(extract_generator(), status_func, verbose=True)
    
    date_handler = lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else None
    open(out_path, 'w').write(json.dumps(input, default=date_handler, indent=4))