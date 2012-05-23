def run():
    import settings
    
    from regsdotgov.regs_gwt.regs_client import RegsClient
    client = RegsClient()

    from regsdotgov.search import parse, search

    docs = parse(search(per_page=4, position=50, client=client), client)

    if len(docs) != 4:
        raise Exception("Wrong number of search results.")
    
    from regsdotgov.document import scrape_document, scrape_docket
    full_docs = []
    full_dockets = []
    for doc in docs:
        full_doc = scrape_document(doc['document_id'], client)
        full_docs.append(full_doc)

        full_dockets.append(scrape_docket(full_doc['docket_id'], client))
    
    print docs, "\n\n", full_docs, "\n\n", full_dockets
    return {'success': True}