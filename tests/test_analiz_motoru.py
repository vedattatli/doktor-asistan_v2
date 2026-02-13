from pathlib import Path

import pytest

from core.analiz_motoru import KlinikAnalizMotoru


PDF_SABIT_PATH = Path("/mnt/data/19.12.2016.pdf")
PDF_FALLBACK_PATH = Path("data/pdfs/19.12.2016.pdf")


@pytest.fixture(scope="module")
def pdf_path():
    if PDF_SABIT_PATH.exists():
        return PDF_SABIT_PATH
    if PDF_FALLBACK_PATH.exists():
        return PDF_FALLBACK_PATH
    pytest.skip("Test PDF bulunamadı: /mnt/data/19.12.2016.pdf")


@pytest.fixture(scope="module")
def parsed_pages(pdf_path):
    motor = KlinikAnalizMotoru()
    sayfalar = motor.pdf_isle(str(pdf_path))
    assert sayfalar, "PDF parse sonucu boş geldi."
    return sayfalar


def _satir_bul(parsed_pages, test_adi, page=None):
    for sayfa in parsed_pages:
        if page is not None and sayfa["page"] != page:
            continue
        for satir in sayfa["rows"]:
            if satir["test"].upper() == test_adi.upper():
                return satir
    raise AssertionError(f"{test_adi} satırı bulunamadı.")


def test_ust_bilgiler(parsed_pages):
    patient = parsed_pages[0]["patient"]
    assert patient["hasta_adi"] == "ENES AKTÜRK"
    assert patient["hastane"] == "ÖZEL ERCİYES HASTANESİ"
    assert patient["tarih"] == "19.12.2016"
    assert patient["saat"] == "01:12"


def test_hedef_lab_satirlari(parsed_pages):
    hgb = _satir_bul(parsed_pages, "HGB")
    assert hgb["value"] == pytest.approx(14.1)
    assert hgb["ref_low"] == pytest.approx(11.0)
    assert hgb["ref_high"] == pytest.approx(16.0)
    assert hgb["status"] == "NORMAL"

    gran_pct = _satir_bul(parsed_pages, "GRAN%")
    assert gran_pct["value"] == pytest.approx(41.4)
    assert gran_pct["ref_low"] == pytest.approx(50.0)
    assert gran_pct["ref_high"] == pytest.approx(70.0)
    assert gran_pct["status"] == "DÜŞÜK"

    lymph_pct = _satir_bul(parsed_pages, "Lymph%")
    assert lymph_pct["value"] == pytest.approx(51.0)
    assert lymph_pct["ref_low"] == pytest.approx(20.0)
    assert lymph_pct["ref_high"] == pytest.approx(40.0)
    assert lymph_pct["status"] == "YÜKSEK"

    mcv = _satir_bul(parsed_pages, "MCV")
    assert mcv["value"] == pytest.approx(79.1)
    assert mcv["ref_low"] == pytest.approx(82.0)
    assert mcv["ref_high"] == pytest.approx(95.0)
    assert mcv["status"] == "DÜŞÜK"

    rdw_cv = _satir_bul(parsed_pages, "RDW-CV")
    assert rdw_cv["value"] == pytest.approx(11.4)
    assert rdw_cv["ref_low"] == pytest.approx(11.5)
    assert rdw_cv["ref_high"] == pytest.approx(14.5)
    assert rdw_cv["status"] == "DÜŞÜK"

    wbc = _satir_bul(parsed_pages, "WBC", page=2)
    assert wbc["value"] == pytest.approx(4.89)
    assert wbc["ref_low"] == pytest.approx(4.0)
    assert wbc["ref_high"] == pytest.approx(10.0)
    assert wbc["status"] == "NORMAL"


def test_rendered_text_hgb_durum(parsed_pages):
    tum_render = "\n".join(s["rendered_text"] for s in parsed_pages)
    assert "TEST: HGB | SONUÇ: 14.1 g/dL | REF: 11-16 | DURUM: NORMAL ✅" in tum_render
