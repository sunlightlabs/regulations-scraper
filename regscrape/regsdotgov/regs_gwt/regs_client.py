from regs_gwt.types import *
from pygwt.client import *

class RegsClient(Client):
    def __init__(self):
        super(RegsClient, self).__init__()
        
        self.domain = 'www.regulations.gov'
        self.js_url = 'http://www.regulations.gov/Regs/'
        self.gwt_permutation = '84DE24481783ADA97BBE752EAB730C0C'
        
        self.class_map.update({
            'gov.egov.erule.regs.shared.action.LoadSearchResultsResult': SearchResultPackage,
            'gov.egov.erule.regs.shared.models.SearchResultModel': SearchResult,
            'gov.egov.erule.regs.shared.models.Agency': Agency,
            'gov.egov.erule.regs.shared.models.Category': Category,
            'gov.egov.erule.regs.shared.models.ClosingSoon': ClosingSoon,
            'gov.egov.erule.regs.shared.models.NewlyPosted': NewlyPosted,
            'gov.egov.erule.regs.shared.models.DimensionCounterFilter': DimensionCounter,
            'gov.egov.erule.regs.shared.models.CommentPeriod': CommentPeriod,
            'gov.egov.erule.regs.shared.models.DocumentSummaryModel': DocumentSummary,
            'gov.egov.erule.regs.shared.resources.SharedConstants$DOCUMENT_STATUS': DocumentStatus,
            'gov.egov.erule.regs.shared.models.DocumentType': DocumentType,
            'gov.egov.erule.regs.shared.models.DocketType': DocketType,
            'gov.egov.erule.regs.shared.action.LoadDocumentDetailResult': DocumentDetailPackage,
            'gov.egov.erule.regs.shared.models.DocumentDetailModel': DocumentDetail,
            'gov.egov.erule.regs.shared.models.MetadataValueModel': MetadataValue,
            'gov.egov.erule.regs.shared.models.MetadataModel': Metadata,
            'gov.egov.erule.regs.shared.models.MetadataModel$UiControlType': MetadataUIControlType,
            'gov.egov.erule.regs.shared.models.DocumentBase': DocumentBase,
            'gov.egov.erule.regs.shared.models.AttachmentModel': Attachment,
            'gov.egov.erule.regs.shared.resources.SharedConstants$POSTING_RESTRICTION': PostingRestriction,
            'gov.egov.erule.regs.shared.action.LoadDocketFolderMetadataResult': DocketFolderMetadataPackage,
            'gov.egov.erule.regs.shared.models.DocketDetailModel': DocketDetail,
        })
        
        self.headers = {
            'Content-Type': "text/x-gwt-rpc; charset=utf-8",
            'X-GWT-Module-Base': self.js_url,
            'X-GWT-Permutation': self.gwt_permutation,
        }
