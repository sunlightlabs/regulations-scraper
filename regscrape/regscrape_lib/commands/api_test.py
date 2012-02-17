def run():
    import settings
    
    from regscrape_lib.regs_gwt.regs_client import RegsClient
    client = RegsClient()

    from regscrape_lib.search import parse, search

    docs = parse(search(per_page=4, position=50, client=client), client)

    if len(docs) != 4:
        raise Exception("Wrong number of search results.")
    
    from regscrape_lib.document import scrape_document, scrape_docket
    full_docs = []
    full_dockets = []
    for doc in docs:
        full_doc = scrape_document(doc['document_id'], client)
        full_docs.append(full_doc)

        full_dockets.append(scrape_docket(full_doc['docket_id'], client))
    
    print docs, full_docs, full_dockets
    return {'success': True}