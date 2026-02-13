"""LLM tabanli grafik spec planlayici."""

from __future__ import annotations

import json
import re
from typing import Sequence

import ollama
from pydantic import ValidationError

from core.grafik.spec import ChartSpec


class GrafikPlanlamaHatasi(Exception):
    """Grafik spec planlama asamasinda kullaniciya donulecek hata."""


def _extract_json_payload(text: str) -> str:
    ham = (text or "").strip()
    if not ham:
        raise GrafikPlanlamaHatasi("LLM bos yanit verdi.")

    # Ilk tercih: dogrudan JSON parse.
    try:
        json.loads(ham)
        return ham
    except Exception:
        pass

    # Markdown blok veya ek metin geldiyse ilk JSON objesini ayikla.
    eslesme = re.search(r"\{[\s\S]*\}", ham)
    if not eslesme:
        raise GrafikPlanlamaHatasi("LLM yanitindan gecerli JSON ayiklanamadi.")

    aday = eslesme.group(0)
    try:
        json.loads(aday)
        return aday
    except Exception as exc:
        raise GrafikPlanlamaHatasi(f"LLM JSON parse edilemedi: {exc}") from exc


def plan_chart_spec(user_text: str, df_schema_summary: str, available_tests: Sequence[str]) -> ChartSpec:
    """
    Kullanici isteginden ChartSpec uretir.
    Donus tipi daima valid ChartSpec olmalidir.
    """
    testler = [str(t).strip() for t in available_tests if str(t).strip()]
    if not testler:
        raise GrafikPlanlamaHatasi("Rapor iceriginde kullanilabilir test bulunamadi.")

    system_prompt = f"""
Sen bir grafik planlayicisin. YALNIZCA gecerli bir JSON nesnesi dondur.

KURALLAR:
1) CIKTI SADECE JSON olmalı, aciklama/metin/markdown olamaz.
2) template sadece su enumlardan biri olabilir:
   - trend_refband
   - heatmap_tests_time
   - scatter_correlation
3) test secimleri SADECE su listeden olmali:
   {testler}
4) Eger kullanici trend/degisim istiyorsa trend_refband sec.
5) Eger kullanici dagilim/isi haritasi istiyorsa heatmap_tests_time sec.
6) Eger kullanici iliski/korelasyon istiyorsa scatter_correlation sec.
7) trend_refband icin data.series (liste) doldur.
8) scatter_correlation icin data.x_test ve data.y_test doldur.
9) x alani report_dt olmali.
10) output.engine plotly olmali.
"""

    user_prompt = f"""
KULLANICI ISTEGI:
{user_text}

DF SEMA OZETI:
{df_schema_summary}

JSON olarak ChartSpec dondur.
"""

    try:
        yanit = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            options={"temperature": 0.0},
        )
    except Exception as exc:
        raise GrafikPlanlamaHatasi(f"LLM cagrisi basarisiz: {exc}") from exc

    icerik = (yanit or {}).get("message", {}).get("content", "")
    json_text = _extract_json_payload(icerik)

    try:
        return ChartSpec.model_validate_json(json_text)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(x) for x in first.get("loc", []))
        msg = first.get("msg", "gecersiz spec")
        raise GrafikPlanlamaHatasi(f"Grafik spec dogrulanamadi ({loc}): {msg}") from exc

