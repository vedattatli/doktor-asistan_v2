import re

import ollama


YOK_MESAJI = "Dokümanda bu bilgi yok. İstersen PDF'yi kontrol edelim."
KAYNAK_RE = re.compile(r"\[Kaynak:\s*.+?\|\s*Sayfa:\s*.+?\]", flags=re.IGNORECASE)
UZAKDOGU_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
HASTA_ADI_RE = re.compile(r"HASTA:\s*([^|]+)", flags=re.IGNORECASE)
DURUM_ICON_RE = re.compile(r"[✅⬇️⬆️❔]")
STOPWORDS = {
    "ve",
    "veya",
    "ile",
    "bir",
    "bu",
    "şu",
    "hangi",
    "nedir",
    "ne",
    "kaç",
    "mi",
    "mı",
    "mu",
    "mü",
    "durumu",
    "değeri",
    "sonucu",
    "hastanın",
    "hasta",
}


def _soru_tokenlari(soru: str) -> list[str]:
    adaylar = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9#%.-]+", (soru or "").lower())
    return [a for a in adaylar if len(a) > 1 and a not in STOPWORDS]


def _kaynak_satiri_uret(soru: str, context_docs, context_metas, max_satir: int = 2) -> str | None:
    tokenlar = _soru_tokenlari(soru)
    adaylar = []

    for doc, meta in zip(context_docs, context_metas):
        kaynak = (meta or {}).get("source", "Bilinmeyen")
        sayfa = (meta or {}).get("page", "?")
        for ham_satir in (doc or "").splitlines():
            satir = (ham_satir or "").strip()
            if not satir or satir.startswith("--- HASTA:"):
                continue
            if len(satir) < 8:
                continue
            if re.fullmatch(r"[\d\W_]+", satir):
                continue

            alt = satir.lower()
            if tokenlar:
                skor = sum(1 for t in tokenlar if t in alt)
                if skor == 0:
                    continue
                adaylar.append((1, skor, satir, kaynak, sayfa))
                continue

            klinik_sinyal = any(
                anahtar in alt for anahtar in ("test:", "sonuç:", "sonuc:", "hasta:", "tarih:")
            )
            oncelik = 2 if klinik_sinyal else 1
            adaylar.append((oncelik, 0, satir, kaynak, sayfa))

    if not adaylar:
        return None

    adaylar.sort(key=lambda x: (x[0], x[1]), reverse=True)
    secilen = []
    gorulen = set()
    for _, _, satir, kaynak, sayfa in adaylar:
        anahtar = (satir, kaynak, sayfa)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        secilen.append(f"{satir}\n[Kaynak: {kaynak} | Sayfa: {sayfa}]")
        if len(secilen) >= max_satir:
            break

    if not secilen:
        return None
    return _kisa_yanit_bicimle("\n".join(secilen))


def _soru_contextte_gorunuyor_mu(soru: str, context_docs) -> bool:
    tokenlar = _soru_tokenlari(soru)
    if not tokenlar:
        return False
    butun_context = "\n".join([str(d) for d in context_docs]).lower()
    return any(t in butun_context for t in tokenlar)


def _ilk_kaynak(context_metas) -> tuple[str, str]:
    for meta in context_metas or []:
        if isinstance(meta, dict):
            return str(meta.get("source", "Bilinmeyen")), str(meta.get("page", "?"))
    return "Bilinmeyen", "?"


def _hasta_adi_bul(context_docs) -> str | None:
    for doc in context_docs or []:
        eslesme = HASTA_ADI_RE.search(str(doc))
        if eslesme:
            hasta = eslesme.group(1).strip()
            if hasta and hasta.lower() != "bilinmiyor":
                return hasta
    return None


def _soruyu_kisalt(soru: str, max_uzunluk: int = 48) -> str:
    temiz = (soru or "").strip()
    if not temiz:
        return "istenen bilgi"
    if len(temiz) <= max_uzunluk:
        return temiz
    return temiz[: max_uzunluk - 1].rstrip() + "…"


def _evidence_first_yok_cevabi(soru: str, context_docs, context_metas) -> str:
    if not context_docs:
        return YOK_MESAJI
    hasta = _hasta_adi_bul(context_docs)
    kaynak, sayfa = _ilk_kaynak(context_metas)

    ilk_satir = "Rapor bir laboratuvar çıktısı."
    if hasta:
        ilk_satir = f"Rapor bir laboratuvar çıktısı; hastanın adı {hasta} görünüyor."
    bulgu_satiri = None
    ornek_bulgu = _kaynak_satiri_uret("", context_docs, context_metas, max_satir=1)
    if ornek_bulgu:
        ornek_metin = next(
            (
                satir.strip()
                for satir in ornek_bulgu.splitlines()
                if satir.strip() and not KAYNAK_RE.search(satir)
            ),
            "",
        )
        u = (ornek_metin or "").upper()
        if ornek_metin and (
            u.startswith("TEST:")
            or "SONUÇ:" in u
            or "SONUC:" in u
        ):
            if len(ornek_metin) > 120:
                ornek_metin = ornek_metin[:119] + "…"
            bulgu_satiri = f"Örnek bulgu: {ornek_metin}"
    ikinci_satir = f"Ancak '{_soruyu_kisalt(soru)}' bilgisi bu raporda yer almıyor."
    kaynak_satiri = f"[Kaynak: {kaynak} | Sayfa: {sayfa}]"
    satirlar = [ilk_satir]
    if bulgu_satiri:
        satirlar.append(bulgu_satiri)
    satirlar.extend([ikinci_satir, kaynak_satiri])
    return "\n".join(satirlar)


def _kisa_yanit_bicimle(metin: str) -> str:
    satirlar = []
    for satir in (metin or "").splitlines():
        temiz = DURUM_ICON_RE.sub("", satir).strip()
        if temiz:
            satirlar.append(temiz)

    if not satirlar:
        return ""

    kaynaklar = [s for s in satirlar if KAYNAK_RE.search(s)]
    govde = [s for s in satirlar if not KAYNAK_RE.search(s)]
    secilen = govde[:3]
    if kaynaklar:
        secilen.append(kaynaklar[0])
    return "\n".join(secilen[:4])


def _chunk_icerigi(chunk) -> str:
    if isinstance(chunk, dict):
        return (((chunk or {}).get("message", {}) or {}).get("content") or "")
    if isinstance(chunk, str):
        return chunk
    return ""


def _stream_chunk(mesaj: str) -> dict:
    return {"message": {"content": mesaj}}


def _stream_mesaji(mesaj: str):
    return iter([_stream_chunk(mesaj)])


def _guardrail_sonucu(query: str, icerik: str, context_docs, context_metas, fallback: str | None) -> str:
    temiz = (icerik or "").strip()
    evidence_yok = _evidence_first_yok_cevabi(query, context_docs, context_metas)
    if not temiz:
        return fallback or evidence_yok

    if UZAKDOGU_RE.search(temiz):
        return fallback or evidence_yok

    if "dokümanda bu bilgi yok" in temiz.lower():
        if _soru_contextte_gorunuyor_mu(query, context_docs):
            return fallback or evidence_yok
        return evidence_yok


    if not KAYNAK_RE.search(temiz):
        return fallback or evidence_yok

    return _kisa_yanit_bicimle(temiz)


def generate_answer(query, context_docs, context_metas, *, stream: bool = False):
    """
    LLM ile cevap üretir; cevap kaynak formatını bozarsa deterministik source satırlarına düşer.
    """
    if not context_docs:
        return _stream_mesaji(YOK_MESAJI) if stream else YOK_MESAJI

    context_blocks = []
    for doc, meta in zip(context_docs, context_metas):
        kaynak = (meta or {}).get("source", "Bilinmeyen")
        sayfa = (meta or {}).get("page", "?")
        context_blocks.append(f"[KAYNAK: {kaynak} | SAYFA: {sayfa}]\n{doc}")
    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""
Sen klinik rapor asistanısın.

KURALLAR:
1. SADECE aşağıdaki doğrulanmış context'ten cevap ver.
2. Context dışında genel tıbbi bilgi, yorum veya tahmin üretme.
3. Yanıt TÜRKÇE olmalı. İngilizce veya başka dil kullanma.
4. Her yanıtın sonunda en az bir kaynak satırı olmalı:
   [Kaynak: dosya | Sayfa: no]
5. İstenen bilgi context'te yoksa sadece şu cümleyi ver:
   "{YOK_MESAJI}"

DOĞRULANMIŞ CONTEXT:
{context_str}
"""

    fallback = _kaynak_satiri_uret(query, context_docs, context_metas)

    if stream:
        try:
            ham_stream = ollama.chat(
                model="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                stream=True,
                options={"temperature": 0.0},
            )
            parcalar = []
            tam_icerik = ""
            for parca in ham_stream:
                if isinstance(parca, dict):
                    parcalar.append(parca)
                elif isinstance(parca, str):
                    parcalar.append(_stream_chunk(parca))
                else:
                    continue
                tam_icerik += _chunk_icerigi(parca)
        except Exception:
            return _stream_mesaji(fallback or YOK_MESAJI)

        guvenli = _guardrail_sonucu(query, tam_icerik, context_docs, context_metas, fallback)
        if guvenli != (tam_icerik or "").strip():
            return _stream_mesaji(guvenli)
        if not parcalar:
            return _stream_mesaji(guvenli)
        return iter(parcalar)

    try:
        yanit = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            stream=False,
            options={"temperature": 0.0},
        )
        icerik = ((yanit or {}).get("message", {}) or {}).get("content", "")
    except Exception:
        return fallback or YOK_MESAJI

    return _guardrail_sonucu(query, icerik, context_docs, context_metas, fallback)
