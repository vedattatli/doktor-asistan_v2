import ollama

def generate_answer(query, context_docs, context_metas):
    """
    LLM ile sadece doğrulanmış context'e dayanarak cevap üretir.
    """
    if not context_docs:
        return "Dokümanda bu bilgi yok. İstersen PDF'yi kontrol edelim."

    context_blocks = []
    for doc, meta in zip(context_docs, context_metas):
        kaynak = meta.get("source", "Bilinmeyen")
        sayfa = meta.get("page", "?")
        context_blocks.append(f"[KAYNAK: {kaynak} | SAYFA: {sayfa}]\n{doc}")
    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""
Sen klinik rapor asistanısın.

KURALLAR:
1. SADECE aşağıdaki doğrulanmış context'ten cevap ver.
2. Context dışında genel tıbbi bilgi ekleme, yorum ekleme, tahmin üretme.
3. İstenen bilgi context'te yoksa yalnızca şu cümleyi ver:
   "Dokümanda bu bilgi yok. İstersen PDF'yi kontrol edelim."
4. Kaynak belirtirken [Kaynak: dosya | Sayfa: no] formatını kullan.
5. Türkçe yaz.

DOĞRULANMIŞ CONTEXT:
{context_str}
"""

    stream = ollama.chat(
        model="qwen2.5:7b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        stream=True,
        options={"temperature": 0.0},
    )

    return stream
