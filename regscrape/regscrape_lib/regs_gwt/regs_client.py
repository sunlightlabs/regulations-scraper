from regs_gwt.types import *
from pygwt.client import *

class RegsClient(Client):
    def __init__(self):
        super(RegsClient, self).__init__()
        
        self.domain = 'www.regulations.gov'
        self.js_url = 'http://www.regulations.gov/Regs/'
        
        self.class_map.update({
            'gov.egov.erule.regs.shared.action.LoadSearchResultsResult': SearchResultPackage,
            'gov.egov.erule.regs.shared.models.SearchResultModel': SearchResult,
            'gov.egov.erule.regs.shared.models.Agency': Agency,
            'gov.egov.erule.regs.shared.models.DimensionCounterFilter': DimensionCounter,
            'gov.egov.erule.regs.shared.models.CommentPeriod': CommentPeriod,
            'gov.egov.erule.regs.shared.models.DocumentSummaryModel': DocumentSummary,
            'gov.egov.erule.regs.shared.resources.SharedConstants$DOCUMENT_STATUS': DocumentStatus,
            'gov.egov.erule.regs.shared.models.DocumentType': DocumentType
        })
