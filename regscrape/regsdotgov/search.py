import urllib2
from pygwt.response import Response

REQUEST_DATA = "7|0|14|http://www.regulations.gov/Regs/|C006AEC3A690AD65DC608DB5A8DBA002|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|6dfecc389e4d86b4e63e6b459bfa29e673a88555d93b469fc5ed362134c31079.e38Sb3aKaN8Oe3uRai0|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/2202288755|java.util.ArrayList/4159755760||gov.egov.erule.regs.shared.models.DataFetchSettings/3659460086|java.lang.Integer/3438268394|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|0|9|0|10|0|11|11|11|11|10|0|3|10|0|12|13|%s|13|%s|11|11|14|1|1|0|"
FILTERED_REQUEST_DATA = {
    'agency': "7|0|16|http://www.regulations.gov/Regs/|C006AEC3A690AD65DC608DB5A8DBA002|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|afc0dc8034150b895be382fee05843c5149cfa1f773f9885aa6d180fd7f2d5af.e38Sc3uTa3qQe34Qa350|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/2202288755|java.util.ArrayList/4159755760||gov.egov.erule.regs.shared.models.Agency/3251642055|{agency}|java.lang.Integer/3438268394|gov.egov.erule.regs.shared.models.DataFetchSettings/3659460086|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|0|9|0|10|0|11|11|11|11|10|1|12|13|14|0|11|11|3|10|0|15|14|%s|14|%s|11|11|16|1|1|0|",
    'docket': "7|0|16|http://www.regulations.gov/Regs/|C006AEC3A690AD65DC608DB5A8DBA002|com.gwtplatform.dispatch.shared.DispatchService|execute|java.lang.String/2004016611|com.gwtplatform.dispatch.shared.Action|afc0dc8034150b895be382fee05843c5149cfa1f773f9885aa6d180fd7f2d5af.e38Sc3uTa3qQe34Qa350|gov.egov.erule.regs.shared.action.LoadSearchResultsAction/125242584|gov.egov.erule.regs.shared.models.SearchQueryModel/2202288755|java.util.ArrayList/4159755760|{docket}||gov.egov.erule.regs.shared.models.DocumentType/2460330259|gov.egov.erule.regs.shared.models.DataFetchSettings/3659460086|java.lang.Integer/3438268394|java.lang.Boolean/476441737|1|2|3|4|2|5|6|7|8|1|9|0|10|0|11|12|12|12|10|5|13|4|13|5|13|3|13|1|13|2|3|10|0|14|15|%s|15|%s|12|12|16|1|1|0|"
}

def search(per_page, position, client, **args):
    request_data = FILTERED_REQUEST_DATA[args.keys()[0]].format(**args) if args else REQUEST_DATA
    return urllib2.urlopen(urllib2.Request(
        'http://www.regulations.gov/dispatch/LoadSearchResultsAction',
        request_data % (per_page, position),
        client.headers
    ))

def parse(file, client):
    data = open(file) if type(file) in (unicode, str) else file
    
    response = Response(client, data)
    return response.reader.read_object()

# convenience function that strings them together
def parsed_search(per_page, position, client=None, **args):
    if not client:
        from regs_gwt.regs_client import RegsClient
        client = RegsClient()

    return parse(search(per_page, position, client, **args), client)

# use the search with an overridden client to get the agencies instead of the documents
def get_agencies():
    from regs_gwt.regs_client import RegsClient
    from regs_gwt.types import AgencySearchResult

    class AgencyClient(RegsClient):
        def __init__(self):
            super(AgencyClient, self).__init__()
            self.class_map.update({
                'gov.egov.erule.regs.shared.models.SearchResultModel': AgencySearchResult
            })

    return parsed_search(1, 0, AgencyClient())