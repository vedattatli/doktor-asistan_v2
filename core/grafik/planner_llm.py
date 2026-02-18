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


def _fallback_title(payload: dict, user_text: str, available_tests: Sequence[str]) -> str:
    template = str(payload.get("template") or "trend_refband")
    secili_testler = []
    for alan in ["test", "x_test", "y_test"]:
        deger = payload.get("data", {}).get(alan)
        if isinstance(deger, str) and deger.strip():
            secili_testler.append(deger.strip())
    for alan in ["tests", "series"]:
        degerler = payload.get("data", {}).get(alan) or []
        if isinstance(degerler, list):
            secili_testler.extend([str(x).strip() for x in degerler if str(x).strip()])

    secili_testler = [t for t in secili_testler if t]
    if not secili_testler and available_tests:
        secili_testler = list(available_tests[:2])

    if template == "scatter_correlation" and len(secili_testler) >= 2:
        return f"{secili_testler[0]} - {secili_testler[1]} Korelasyon"
    if template == "heatmap_tests_time":
        return "Test Zaman Isı Haritası"
    if secili_testler:
        return f"{', '.join(secili_testler[:2])} Trendi"

    soru = (user_text or "").strip()
    return soru[:60] if soru else "Laboratuvar Grafiği"


def _fallback_spec(user_text: str, available_tests: Sequence[str]) -> dict:
    secili = list(available_tests[:2]) if available_tests else []
    if not secili and available_tests:
        secili = [available_tests[0]]
    return {
        "version": 1,
        "template": "trend_refband",
        "title": f"{', '.join(secili)} Trendi" if secili else "Laboratuvar Grafiği",
        "data": {
            "x": "report_dt",
            "y": "value",
            "series": secili or list(available_tests[:1]),
        },
        "overlays": {"reference_band": True, "show_points": True},
        "output": {"engine": "plotly", "height": 480},
    }


def plan_chart_spec(user_text: str, df_schema_summary: str, available_tests: Sequence[str]) -> ChartSpec:
    """
    Kullanici isteginden ChartSpec uretir.
    Donus tipi daima valid ChartSpec olmalidir.
    """
    testler = [str(t).strip() for t in list(available_tests or []) if str(t).strip()]
    if not testler:
        try:
            return ChartSpec.model_validate(_fallback_spec(user_text, []))
        except ValidationError as exc:
            raise GrafikPlanlamaHatasi(
                "Grafik planı oluşturulamadı. Lütfen grafik için test adı belirt."
            ) from exc

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
        payload = json.loads(json_text)
    except Exception as exc:
        raise GrafikPlanlamaHatasi(f"LLM JSON parse edilemedi: {exc}") from exc

    if not isinstance(payload, dict):
        payload = {}

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        payload["title"] = _fallback_title(payload, user_text, testler)

    try:
        return ChartSpec.model_validate(payload)
    except ValidationError:
        try:
            return ChartSpec.model_validate(_fallback_spec(user_text, testler))
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(x) for x in first.get("loc", []))
            msg = first.get("msg", "gecersiz spec")
            raise GrafikPlanlamaHatasi(f"Grafik spec dogrulanamadi ({loc}): {msg}") from exc
