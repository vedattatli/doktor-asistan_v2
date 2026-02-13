"""Heatmap template stub."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def render_heatmap_tests_time(spec, df: pd.DataFrame) -> go.Figure:
    if "report_dt" not in df.columns or "test" not in df.columns:
        raise ValueError("heatmap_tests_time icin 'report_dt' ve 'test' kolonlari zorunlu.")

    plot_df = df.copy()
    plot_df["report_dt"] = pd.to_datetime(plot_df["report_dt"], errors="coerce")

    filtre_testler = list(spec.data.series or spec.data.tests)
    if not filtre_testler and spec.data.test:
        filtre_testler = [spec.data.test]
    if filtre_testler:
        plot_df = plot_df[plot_df["test"].isin(filtre_testler)]
    if plot_df.empty:
        raise ValueError("heatmap_tests_time icin secili testlerde veri bulunamadi.")

    status_map = {"NORMAL": 0.0, "DÜŞÜK": -1.0, "YÜKSEK": 1.0}
    value_mode = (spec.data.y or "status").lower()

    if value_mode == "normalized_score":
        tmp = plot_df.copy()
        aralik = (tmp["ref_high"] - tmp["ref_low"]).replace(0, pd.NA)
        orta = (tmp["ref_high"] + tmp["ref_low"]) / 2.0
        tmp["heat_value"] = ((tmp["value"] - orta) / (aralik / 2.0)).astype(float)
        tmp["heat_value"] = tmp["heat_value"].fillna(tmp["status"].map(status_map).fillna(0.0))
    else:
        tmp = plot_df.copy()
        tmp["heat_value"] = tmp["status"].map(status_map)
        if value_mode != "status" and value_mode in tmp.columns:
            tmp["heat_value"] = pd.to_numeric(tmp[value_mode], errors="coerce")
        tmp["heat_value"] = tmp["heat_value"].fillna(0.0)

    pivot = (
        tmp.pivot_table(index="test", columns="report_dt", values="heat_value", aggfunc="mean")
        .sort_index()
        .sort_index(axis=1)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            z=pivot.values,
            coloraxis="coloraxis",
            hovertemplate="Tarih=%{x}<br>Test=%{y}<br>Skor=%{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=spec.title,
        height=spec.output.height,
        template="plotly_white",
        coloraxis={
            "colorscale": [[0.0, "#d62728"], [0.5, "#f0f0f0"], [1.0, "#2ca02c"]],
            "cmin": -1.0,
            "cmax": 1.0,
            "colorbar": {"title": "Durum"},
        },
    )
    fig.update_xaxes(title_text="report_dt")
    fig.update_yaxes(title_text="test")
    return fig
