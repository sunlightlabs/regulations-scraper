import urllib2
import settings
import os
from regscrape_lib.regs_gwt.regs_client import RegsClient

REQUEST_URL = "7|0|18|http://www.regulations.gov/Regs/|AE99DC4BDDCC371389782BAA86C49040|com.gwtplatform.dispatch.client.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|b3b2d5ead02eac084b75806fe23a8742a940d1a115fb412d62d5a7e175cb90dd.e38Sb3aKaN8Oe34Pay0|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/1556278353|java.util.ArrayList/3821976829||gov.egov.erule.regs.shared.models.DataFetchSettings/1603506619|java.lang.Integer/3438268394|docketId|DESC|postedDate|ASC|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|0|9|10|0|11|11|11|10|0|3|10|0|12|13|0|14|15|13|%s|13|%s|16|17|11|18|0|1|0|"

def pump(input, output, chunk_size):
    while True:
        chunk = input.read(chunk_size)
        if not chunk: break
        output.write(chunk)

def run():
    client = RegsClient()
    position = settings.DUMP_START
    num_digits = len(str(settings.DUMP_END))
    while position <= settings.DUMP_END:
        print "Downloading page %s of %s..." % ((position / settings.DUMP_INCREMENT) + 1, ((settings.DUMP_END - settings.DUMP_START) / settings.DUMP_INCREMENT) + 1)
        download = urllib2.urlopen(urllib2.Request(
            'http://www.regulations.gov/dispatch/LoadSearchResultsAction',
            REQUEST_URL % (settings.DUMP_INCREMENT, position),
            client.headers
        ))
        
        output_file = open(os.path.join(settings.DUMP_DIR, 'dump_%s.gwt' % str(position).zfill(num_digits)), 'wb')
        
        pump(download, output_file, 16 * 1024)
        
        output_file.close()
        
        position += settings.DUMP_INCREMENT
