import os
import json
import hashlib

from core.analiz_motoru import KlinikAnalizMotoru
from core.alanlar.lab.df_uret import parsed_pages_to_df


PARSED_DIR = "data/parsed"


def generate_page_id(file_name: str, page_no: int, rendered_text: str) -> str:
    unique_str = f"{file_name}|p{page_no}|{rendered_text}"
    return hashlib.sha256(unique_str.encode("utf-8")).hexdigest()


def _save_parsed_pages_json(file_name: str, parsed_pages: list[dict]) -> str:
    """
    Her PDF için deterministik parser çıktısını diskte saklar.
    Örn: data/parsed/19.12.2016.pdf.json
    """
    os.makedirs(PARSED_DIR, exist_ok=True)
    out_path = os.path.join(PARSED_DIR, f"{file_name}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed_pages, f, ensure_ascii=False, indent=2)
    return out_path


def ingest_pdf(pdf_path, collection, motor=None):
    """
    PDF'i deterministik parser ile sayfa bazlı tek chunk olarak ekler.
    """
    motor = motor or KlinikAnalizMotoru()
    parsed_pages = motor.pdf_isle(pdf_path)
    file_name = os.path.basename(pdf_path)

    # Grafik katmanı için parser çıktısını JSON olarak sakla.
    _save_parsed_pages_json(file_name, parsed_pages)
    # Grafikler deterministik parser DF'inden beslensin diye dönüşüm hazır.
    parsed_pages_to_df(parsed_pages)

    documents = []
    metadatas = []
    ids = []

    for page_data in parsed_pages:
        rendered_text = (page_data.get("rendered_text") or "").strip()
        if not rendered_text:
            continue

        patient = page_data.get("patient", {})
        page_no = page_data.get("page")
        unique_id = generate_page_id(file_name, page_no, rendered_text)

        documents.append(rendered_text)
        ids.append(unique_id)
        metadatas.append(
            {
                "source": page_data.get("source", file_name),
                "page": page_no,
                "patient_name": patient.get("hasta_adi", "Bilinmiyor"),
                "facility": patient.get("hastane", "Bilinmiyor"),
                "report_date": patient.get("tarih", "Bilinmiyor"),
                "report_time": patient.get("saat", "Bilinmiyor"),
            }
        )

    if documents:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    return len(documents)
