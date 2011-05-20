import urllib2
import settings
import os

REQUEST_URL = "5|0|16|http://www.regulations.gov/Regs/|75CD5EB90A794C02DBA8438ADEE62406|com.gwtplatform.dispatch.client.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|ad32c7a6667647aed89c64eb3011d9f5ae1cf26b66f844f3ede9deda3035350c.e38Sb3aKaN8Oe34KbO0|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/1476158501|java.util.ArrayList/3821976829||gov.egov.erule.regs.shared.models.DataFetchSettings/1603506619|java.lang.Integer/3438268394|docketId|DESC|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|0|9|10|0|11|11|10|0|3|10|0|12|13|0|14|15|13|%s|13|%s|11|11|11|16|0|1|0|"

def pump(input, output, chunk_size):
    while True:
        chunk = input.read(chunk_size)
        if not chunk: break
        output.write(chunk)

def run():
    position = settings.DUMP_START
    num_digits = len(str(settings.DUMP_END))
    while position <= settings.DUMP_END:
        print "Downloading page %s of %s..." % ((position / settings.DUMP_INCREMENT) + 1, ((settings.DUMP_END - settings.DUMP_START) / settings.DUMP_INCREMENT) + 1)
        download = urllib2.urlopen(urllib2.Request(
            'http://www.regulations.gov/Regs/dispatch/LoadSearchResultsAction',
            REQUEST_URL % (settings.DUMP_INCREMENT, position),
            {'Content-Type': 'text/x-gwt-rpc; charset=utf-8'}
        ))
        
        output_file = open(os.path.join(settings.DUMP_DIR, 'dump_%s.gwt' % str(position).zfill(num_digits)), 'wb')
        
        pump(download, output_file, 16 * 1024)
        
        output_file.close()
        
        position += settings.DUMP_INCREMENT
