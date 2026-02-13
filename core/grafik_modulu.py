# core/grafik_modulu.py
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


PARSED_DIR = "data/parsed"


def ensure_parsed_dir() -> str:
    os.makedirs(PARSED_DIR, exist_ok=True)
    return PARSED_DIR


def save_parsed_json(pdf_basename: str, parsed_pages: List[Dict[str, Any]]) -> str:
    """
    Parser çıktısını JSON olarak kaydeder.
    pdf_basename: '19.12.2016.pdf' gibi
    """
    ensure_parsed_dir()
    out_path = os.path.join(PARSED_DIR, pdf_basename + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed_pages, f, ensure_ascii=False, indent=2)
    return out_path


def list_parsed_jsons() -> List[str]:
    ensure_parsed_dir()
    files = [f for f in os.listdir(PARSED_DIR) if f.endswith(".json")]
    files.sort()
    return files


def load_parsed_json(filename: str) -> List[Dict[str, Any]]:
    path = os.path.join(PARSED_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parsed_pages_to_df(parsed_pages: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    JSON (sayfa listesi) -> satır bazlı DataFrame
    """
    rows: List[Dict[str, Any]] = []
    for page_obj in parsed_pages:
        page_no = page_obj.get("page")
        src = page_obj.get("source", "Bilinmiyor")
        patient = page_obj.get("patient", {})

        for r in page_obj.get("rows", []):
            rows.append({
                "source": src,
                "page": page_no,
                "patient_name": patient.get("hasta_adi", "Bilinmiyor"),
                "facility": patient.get("hastane", "Bilinmiyor"),
                "report_date": patient.get("tarih", "Bilinmiyor"),
                "report_time": patient.get("saat", "Bilinmiyor"),
                "test": r.get("test"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "ref_low": r.get("ref_low"),
                "ref_high": r.get("ref_high"),
                "status": r.get("status"),
            })

    df = pd.DataFrame(rows)

    # tip düzeltmeleri (grafik için)
    for col in ["value", "ref_low", "ref_high"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # tarih parse (trend grafiği için)
    def _parse_date(x: Any) -> Optional[datetime]:
        try:
            return datetime.strptime(str(x), "%d.%m.%Y")
        except Exception:
            return None

    df["report_dt"] = df["report_date"].apply(_parse_date)
    return df
