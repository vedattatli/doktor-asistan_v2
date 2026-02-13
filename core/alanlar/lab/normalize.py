"""Lab test adlarini kanonik formata normalize eder."""

from __future__ import annotations

import re
from typing import Optional


_TURKISH_ASCII_MAP = str.maketrans(
    {
        "Ç": "C",
        "Ğ": "G",
        "İ": "I",
        "Ö": "O",
        "Ş": "S",
        "Ü": "U",
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


def _sadelestir(metin: str) -> str:
    metin = metin.translate(_TURKISH_ASCII_MAP).upper()
    metin = re.sub(r"\([^)]*\)", " ", metin)
    metin = re.sub(r"[^A-Z0-9#%]+", " ", metin)
    return re.sub(r"\s+", " ", metin).strip()


_TEST_ALIAS = {
    "WBC": "WBC",
    "WBC BEYAZ KURE": "WBC",
    "HGB": "HGB",
    "HCT": "HCT",
    "RBC": "RBC",
    "MCV": "MCV",
    "MCH": "MCH",
    "MCHC": "MCHC",
    "RDW CV": "RDW-CV",
    "RDW SD": "RDW-SD",
    "PLT": "PLT",
    "GRAN#": "GRAN#",
    "GRAN%": "GRAN%",
    "LYMPH#": "LYMPH#",
    "LYMPH%": "LYMPH%",
    "MID#": "MID#",
    "MID%": "MID%",
    "MPV": "MPV",
    "PCT": "PCT",
    "PDW": "PDW",
}


def normalize_test(test_adi: Optional[str]) -> str:
    """
    Test adini kanonik kisa forma cevirir.
    Ornek: "WBC (Beyaz Kure)" -> "WBC"
    """
    if not test_adi:
        return ""

    sadelesmis = _sadelestir(str(test_adi))
    if not sadelesmis:
        return ""

    if sadelesmis in _TEST_ALIAS:
        return _TEST_ALIAS[sadelesmis]

    ilk_token = sadelesmis.split(" ", 1)[0]
    return _TEST_ALIAS.get(ilk_token, ilk_token)


def normalize_test_adi(test_adi: Optional[str]) -> str:
    """
    Geriye dönük uyumluluk için alias.
    """
    return normalize_test(test_adi)
