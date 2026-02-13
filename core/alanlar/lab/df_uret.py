"""analiz_motoru ciktilarindan DataFrame ureterek grafik katmanina hazirlar."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .normalize import normalize_test


def parsed_pages_to_df(parsed_pages: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    analiz_motoru.pdf_isle(...) cikti listesini satir bazli DataFrame'e cevirir.
    """
    kayitlar: List[Dict[str, Any]] = []

    for page_obj in parsed_pages or []:
        patient = page_obj.get("patient", {})
        page_no = page_obj.get("page")
        source = page_obj.get("source", "Bilinmiyor")

        for row in page_obj.get("rows", []):
            kayitlar.append(
                {
                    "report_dt": patient.get("tarih", "Bilinmiyor"),
                    "test": normalize_test(row.get("test", "")),
                    "value": row.get("value"),
                    "unit": row.get("unit"),
                    "ref_low": row.get("ref_low"),
                    "ref_high": row.get("ref_high"),
                    "status": row.get("status"),
                    "page": page_no,
                    "source": source,
                    "patient_name": patient.get("hasta_adi", "Bilinmiyor"),
                    "facility": patient.get("hastane", "Bilinmiyor"),
                }
            )

    sutunlar = [
        "report_dt",
        "test",
        "value",
        "unit",
        "ref_low",
        "ref_high",
        "status",
        "page",
        "source",
        "patient_name",
        "facility",
    ]

    if not kayitlar:
        return pd.DataFrame(columns=sutunlar)

    df = pd.DataFrame(kayitlar)
    for col in ["value", "ref_low", "ref_high"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["report_dt"] = pd.to_datetime(df["report_dt"], format="%d.%m.%Y", errors="coerce")
    return df
