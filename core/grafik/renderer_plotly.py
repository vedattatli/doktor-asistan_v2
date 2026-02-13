"""Spec validate edip guvenli template dispatch ile Plotly Figure uretir."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from pydantic import ValidationError

from core.alanlar.lab.normalize import normalize_test_adi
from core.grafik.spec import ChartSpec, ChartTemplate
from core.grafik.templates import TEMPLATE_REGISTRY


class GrafikRenderHatasi(Exception):
    """Kullaniciya gosterilebilir, okunabilir render hatasi."""


def _spec_validate(spec: ChartSpec | dict[str, Any]) -> ChartSpec:
    if isinstance(spec, ChartSpec):
        return spec
    try:
        return ChartSpec.model_validate(spec)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(x) for x in first.get("loc", []))
        msg = first.get("msg", "gecersiz spec")
        raise GrafikRenderHatasi(f"Grafik spec gecersiz ({loc}): {msg}") from exc


def _df_validate(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        raise GrafikRenderHatasi("Girdi veri tipi pandas.DataFrame olmalidir.")
    if df.empty:
        raise GrafikRenderHatasi("Grafik cizilemedi: veri tablosu bos.")

    gerekli = {spec.data.x}
    if spec.data.y != "normalized_score":
        gerekli.add(spec.data.y)
    eksik = [col for col in gerekli if col not in df.columns]
    if eksik:
        raise GrafikRenderHatasi(f"Grafik cizilemedi: eksik kolon(lar): {', '.join(eksik)}")

    if spec.data.test or spec.data.tests:
        if "test" not in df.columns:
            raise GrafikRenderHatasi("Grafik cizilemedi: 'test' kolonu yok.")

        filtreler = set(spec.data.tests)
        if spec.data.test:
            filtreler.add(spec.data.test)
        filtreler = {normalize_test_adi(item) for item in filtreler}

        filtreli = df[df["test"].astype(str).map(normalize_test_adi).isin(filtreler)]
        if filtreli.empty:
            raise GrafikRenderHatasi(
                f"Grafik cizilemedi: secili test(ler) veri setinde bulunamadi ({', '.join(sorted(filtreler))})."
            )
        return filtreli

    return df


def render(spec: ChartSpec | dict[str, Any], df: pd.DataFrame) -> go.Figure:
    """
    Spec -> validator -> template registry -> Figure
    """
    spec_model = _spec_validate(spec)
    gecerli_df = _df_validate(df, spec_model)

    template_key = ChartTemplate(spec_model.template.value)
    template_fn = TEMPLATE_REGISTRY.get(template_key)
    if template_fn is None:
        raise GrafikRenderHatasi(f"Desteklenmeyen template: {spec_model.template.value}")

    try:
        fig = template_fn(spec_model, gecerli_df)
    except GrafikRenderHatasi:
        raise
    except Exception as exc:
        raise GrafikRenderHatasi(f"Grafik render hatasi: {exc}") from exc

    if not isinstance(fig, go.Figure):
        raise GrafikRenderHatasi("Template gecersiz sonuc dondu: Plotly Figure bekleniyordu.")
    return fig
