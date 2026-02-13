def query_db(collection, query, n_results=6):
    """
    Soruya en uygun sayfa chunk'larını getirir.
    Prompt tarafında sayfa bilgisini görünür kılmak için meta korunur.
    """
    try:
        results = collection.query(query_texts=[query], n_results=n_results)
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        return documents, metadatas
    except Exception as e:
        print(f"DB sorgu hatası: {e}")
        return [], []
