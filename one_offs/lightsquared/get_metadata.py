from optparse import OptionParser
arg_parser = OptionParser()

def run(options, args):
    import zipfile, sys, datetime, re, json
    from lxml import etree

    if len(args) > 0:
        wbk_path = args[0]
    else:
        print "Specify file"
        sys.exit(0)
    
    wbk = zipfile.ZipFile(wbk_path, 'r')
    sheet = wbk.open("content.xml", 'r')

    document = etree.parse(sheet)

    ns_map = {'table': "urn:oasis:names:tc:opendocument:xmlns:table:1.0"}
    bools = {'Y': True, 'N': False}
    date_re = re.compile(r'\d{2}/\d{2}/\d{4}')
    date_handler = lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else None
    link_re = re.compile(r'of:=HYPERLINK\("(?P<url>[\w:/?=\.]*)";"(?P<title>[\w\s\(\)]*)"\)')

    rows = document.findall("//table:table-row", ns_map)

    # handle the first row
    fields = []
    for cell in rows[0].findall("table:table-cell", ns_map):
        text_nodes = cell.getchildren()
        if text_nodes and text_nodes[0].text:
            fields.append(text_nodes[0].text.lower().replace(' ', '_'))
    
    out = []
    for row in rows[1:]:
        row_data = {'documents': []}
        cells = row.findall("table:table-cell", ns_map)
        for i in xrange(len(cells)):
            cell = cells[i]

            text_nodes = cell.getchildren()
            if "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula" in cell.keys():
                # looks like a link
                hyperlink = cell.attrib["{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula"]
                match = link_re.match(hyperlink)
                if not match:
                    print hyperlink
                    print 'failed to parse link %s' % hyperlink
                    sys.exit()
                row_data['documents'].append(match.groupdict())
            elif text_nodes and text_nodes[0].text:
                # looks like plain text
                text = text_nodes[0].text

                # fix dates
                if date_re.match(text):
                    text = datetime.datetime.strptime(text, '%m/%d/%Y').date()
                
                # fix booleans:
                if text in bools:
                    text = bools[text]
                
                row_data[fields[i]] = text
        
        if len(row_data.keys()) > 1:
            out.append(row_data)

    print json.dumps(out, default=date_handler, indent=4)