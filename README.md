# Doktor Asistanı v2

Tıbbi laboratuvar raporlarını yerel olarak analiz eden, soru-cevap ve görselleştirme yapan masaüstü uygulaması. **Hasta verisi makineden hiç çıkmaz** — dil modeli dahil tüm işlem yerelde çalışır.

## Ne yapıyor

PDF laboratuvar raporlarındaki tahlil satırlarını ayrıştırır, saklar ve iki şey sunar:

**Soru-cevap** — Yalnızca dokümandan doğrulanmış bağlamı kullanarak cevap üretir. Model bağlamda olmayan bir bilgiyi uydurursa cevap üretilmez.

**Grafik** — Tahlil değerlerinin zaman içindeki seyrini görselleştirir. Dil modeli grafiği doğrudan çizmez; hangi grafiğin uygun olduğunu yapılandırılmış bir plan olarak önerir (pydantic ile şema doğrulaması), çizimi kod yapar. Plan geçersizse yedek planlayıcı devreye girer. Böylece grafikler halüsinasyona kapalıdır.

## v1'den farkı

v1 ile ortak kod tabanı yoktur — v2 sıfırdan yazılmıştır.

| | v1 | v2 |
|---|---|---|
| Kapsam | Genel tıbbi doküman (lab, patoloji, radyoloji, epikriz) | Yalnızca laboratuvar raporları |
| Ayrıştırma | OCR + LLM tabanlı | pdfplumber ile deterministik |
| Vektör deposu | TF-IDF + opsiyonel embedding | ChromaDB |
| Görselleştirme | Yok | Plotly, şema doğrulamalı plan |
| Ölçek | ~6.000 satır | ~1.900 satır |

v2, kapsamı daraltıp derinleştiren bir yeniden yazımdır.

## Teknoloji

Python · Streamlit · Ollama (yerel LLM) · ChromaDB · pdfplumber · Plotly · pydantic · pytest

## Çalıştırma

Ollama'nın kurulu ve çalışıyor olması gerekir.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
pytest
```

11 test.
