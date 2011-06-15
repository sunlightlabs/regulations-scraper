from regs_gwt.types import *
from pygwt.client import *

class RegsClient(Client):
    def __init__(self):
        super(RegsClient, self).__init__()
        
        self.domain = 'www.regulations.gov'
        self.js_url = 'http://www.regulations.gov/Regs/'
        self.gwt_permutation = '96ED140EA002EA7F0224967DBF229721'
        
        self.class_map.update({
            'gov.egov.erule.regs.shared.action.LoadSearchResultsResult': SearchResultPackage,
            'gov.egov.erule.regs.shared.models.SearchResultModel': SearchResult,
            'gov.egov.erule.regs.shared.models.Agency': Agency,
            'gov.egov.erule.regs.shared.models.DimensionCounterFilter': DimensionCounter,
            'gov.egov.erule.regs.shared.models.CommentPeriod': CommentPeriod,
            'gov.egov.erule.regs.shared.models.DocumentSummaryModel': DocumentSummary,
            'gov.egov.erule.regs.shared.resources.SharedConstants$DOCUMENT_STATUS': DocumentStatus,
            'gov.egov.erule.regs.shared.models.DocumentType': DocumentType,
            'gov.egov.erule.regs.shared.models.DocketType': DocketType,
        })
        
        self.headers = {
            'Content-Type': "text/x-gwt-rpc; charset=utf-8",
            'X-GWT-Module-Base': self.js_url,
            'X-GWT-Permutation': self.gwt_permutation,
        }
