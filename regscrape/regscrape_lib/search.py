import urllib2
from pygwt.response import Response

REQUEST_DATA = "7|0|16|http://www.regulations.gov/Regs/|EE162F2711190E6CD0518A2E3BCBE3B7|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|ff10867777b6f75719206038823d99b6746cca2d2be51d662fc95f3ae0092516.e38Sc3uTa3qQe3aRby0|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/1556278353|java.util.ArrayList/4159755760||gov.egov.erule.regs.shared.models.DataFetchSettings/1603506619|java.lang.Integer/3438268394|docketId|DESC|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|0|9|10|0|11|11|11|10|0|3|10|0|12|13|0|14|15|13|%s|13|%s|11|11|11|16|0|1|0|"

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