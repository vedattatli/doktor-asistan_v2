def query_db(collection, query, n_results=6, filter_meta=None):
    """
    Soruya en uygun sayfa chunk'larını getirir.
    Prompt tarafında sayfa bilgisini görünür kılmak için meta korunur.
    """
    try:
        results = collection.query(query_texts=[query], n_results=n_results, where=filter_meta)
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        return documents, metadatas
    except Exception as e:
        print(f"DB sorgu hatası: {e}")
        return [], []
