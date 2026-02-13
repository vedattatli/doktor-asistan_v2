"""Trend + referans band template (baslangic implementasyonu)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def render_trend_refband(spec, df: pd.DataFrame) -> go.Figure:
    """
    Trend + referans band + anormal nokta vurgusu.
    - series testleri: spec.data.series
    - x: report_dt
    - y: value
    """
    x_col = spec.data.x
    y_col = spec.data.y

    fig = go.Figure()

    if x_col not in df.columns:
        raise ValueError(f"x kolonu bulunamadi: {x_col}")
    if y_col not in df.columns:
        raise ValueError(f"y kolonu bulunamadi: {y_col}")
    if "test" not in df.columns:
        raise ValueError("trend_refband icin 'test' kolonu zorunlu.")

    filtre_testler = list(spec.data.series or spec.data.tests)
    if not filtre_testler and spec.data.test:
        filtre_testler = [spec.data.test]
    if not filtre_testler:
        filtre_testler = sorted(df["test"].dropna().astype(str).unique().tolist())

    plot_df = df[df["test"].isin(filtre_testler)].copy()
    if plot_df.empty:
        raise ValueError("trend_refband icin secili testlerde veri bulunamadi.")

    plot_df[x_col] = pd.to_datetime(plot_df[x_col], errors="coerce")
    plot_df = plot_df.sort_values([x_col, "test"])

    ref_band_aktif = getattr(spec.overlays, "reference_band", False) or getattr(
        spec.overlays, "show_ref_band", False
    )

    for test_adi in filtre_testler:
        tdf = plot_df[plot_df["test"] == test_adi].copy()
        if tdf.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=tdf[x_col],
                y=tdf[y_col],
                mode="lines+markers" if spec.overlays.show_points else "lines",
                name=test_adi,
            )
        )

        if ref_band_aktif and {"ref_low", "ref_high"}.issubset(tdf.columns):
            band_df = tdf.dropna(subset=["ref_low", "ref_high"])
            if not band_df.empty:
                fig.add_trace(
                    go.Scatter(
                        x=band_df[x_col],
                        y=band_df["ref_high"],
                        mode="lines",
                        line={"width": 0},
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=band_df[x_col],
                        y=band_df["ref_low"],
                        mode="lines",
                        line={"width": 0},
                        fill="tonexty",
                        fillcolor="rgba(0, 170, 120, 0.15)",
                        name=f"{test_adi} ref band",
                        hoverinfo="skip",
                    )
                )

        if "status" in tdf.columns:
            anormal = tdf[tdf["status"].isin(["DÜŞÜK", "YÜKSEK"])]
            if not anormal.empty:
                renkler = ["#d62728" if s == "YÜKSEK" else "#ff7f0e" for s in anormal["status"]]
                fig.add_trace(
                    go.Scatter(
                        x=anormal[x_col],
                        y=anormal[y_col],
                        mode="markers",
                        marker={"size": 10, "color": renkler, "line": {"width": 1, "color": "#111"}},
                        name=f"{test_adi} anormal",
                    )
                )

    fig.update_layout(title=spec.title, height=spec.output.height, template="plotly_white")
    fig.update_xaxes(title_text=x_col)
    fig.update_yaxes(title_text=y_col)
    return fig
