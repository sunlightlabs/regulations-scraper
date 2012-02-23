import urllib2
from pygwt.response import Response

REQUEST_DATA = "7|0|13|http://www.regulations.gov/Regs/|25E7F431559001DE380DFAB488A0FFF6|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|d7efef8dd2931272e36bb277fb8113eaf60ef39be99c8a6a483f2f7d44e7790b.e38Sb3aKaN8Oe3qLc40|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/836584709|java.util.ArrayList/4159755760||gov.egov.erule.regs.shared.models.DataFetchSettings/3659460086|java.lang.Integer/3438268394|1|2|3|4|2|5|6|7|8|0|9|0|10|0|11|11|11|10|0|3|10|0|12|13|%s|13|%s|11|11|11|1|0|"

def search(per_page, position, client):
    return urllib2.urlopen(urllib2.Request(
        'http://www.regulations.gov/dispatch/LoadSearchResultsAction',
        REQUEST_DATA % (per_page, position),
        client.headers
    ))

def parse(file, client):
    data = open(file) if type(file) in (unicode, str) else file
    
    response = Response(client, data)
    return response.reader.read_object()

# convenience function that strings them together
def parsed_search(per_page, position, client=None):
    if not client:
        from regs_gwt.regs_client import RegsClient
        client = RegsClient()
    
    return parse(search(per_page, position, client), client)