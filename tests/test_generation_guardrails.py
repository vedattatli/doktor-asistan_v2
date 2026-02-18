from core.generation import YOK_MESAJI, generate_answer


def test_generate_answer_context_yoksa_sabit_mesaj():
    sonuc = generate_answer("HGB nedir?", [], [])
    assert sonuc == YOK_MESAJI


def test_generate_answer_kaynak_yoksa_deterministik_fallback(monkeypatch):
    def _fake_chat(**kwargs):
        return {"message": {"content": "HGB değeri normal görünüyor."}}

    monkeypatch.setattr("core.generation.ollama.chat", _fake_chat)
    docs = ["TEST: HGB | SONUÇ: 14.1 g/dL | REF: 11-16 | DURUM: NORMAL ✅"]
    metas = [{"source": "19.12.2016.pdf", "page": 1}]

    sonuc = generate_answer("HGB durumu nedir?", docs, metas)
    assert "TEST: HGB" in sonuc
    assert "[Kaynak: 19.12.2016.pdf | Sayfa: 1]" in sonuc


def test_generate_answer_yok_derse_ama_contextte_geciyorsa_fallback(monkeypatch):
    def _fake_chat(**kwargs):
        return {"message": {"content": "Dokümanda bu bilgi yok. İstersen PDF'yi kontrol edelim."}}

    monkeypatch.setattr("core.generation.ollama.chat", _fake_chat)
    docs = ["TEST: WBC | SONUÇ: 4.89 10^9/L | REF: 4-10 | DURUM: NORMAL ✅"]
    metas = [{"source": "19.12.2016.pdf", "page": 2}]

    sonuc = generate_answer("WBC kaç?", docs, metas)
    assert sonuc != YOK_MESAJI
    assert "WBC" in sonuc
    assert "[Kaynak: 19.12.2016.pdf | Sayfa: 2]" in sonuc


def test_generate_answer_dil_karisimi_olursa_fallback(monkeypatch):
    def _fake_chat(**kwargs):
        return {"message": {"content": "血液 result normal."}}

    monkeypatch.setattr("core.generation.ollama.chat", _fake_chat)
    docs = ["TEST: MCV | SONUÇ: 79.1 fL | REF: 82-95 | DURUM: DÜŞÜK ⬇️"]
    metas = [{"source": "19.12.2016.pdf", "page": 1}]

    sonuc = generate_answer("MCV durumu?", docs, metas)
    assert "TEST: MCV" in sonuc
    assert "[Kaynak: 19.12.2016.pdf | Sayfa: 1]" in sonuc
