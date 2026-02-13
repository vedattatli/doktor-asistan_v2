from pathlib import Path

import pytest

from core.analiz_motoru import KlinikAnalizMotoru
from core.alanlar.lab.df_uret import parsed_pages_to_df


PDF_SABIT_PATH = Path("/mnt/data/19.12.2016.pdf")
PDF_FALLBACK_PATH = Path("data/pdfs/19.12.2016.pdf")


@pytest.fixture(scope="module")
def pdf_path():
    if PDF_SABIT_PATH.exists():
        return PDF_SABIT_PATH
    if PDF_FALLBACK_PATH.exists():
        return PDF_FALLBACK_PATH
    pytest.skip("Test PDF bulunamadı: /mnt/data/19.12.2016.pdf")


def test_parsed_pages_to_df_hgb_wbc(pdf_path):
    parsed_pages = KlinikAnalizMotoru().pdf_isle(str(pdf_path))
    df = parsed_pages_to_df(parsed_pages)

    gerekli_kolonlar = {
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
    }
    assert gerekli_kolonlar.issubset(df.columns)
    assert (df["test"] == "HGB").any()
    assert (df["test"] == "WBC").any()

