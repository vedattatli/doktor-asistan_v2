"""Scatter correlation template stub."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def render_scatter_correlation(spec, df: pd.DataFrame) -> go.Figure:
    if "report_dt" not in df.columns or "test" not in df.columns or "value" not in df.columns:
        raise ValueError("scatter_correlation icin report_dt/test/value kolonlari zorunlu.")

    x_test = spec.data.x_test
    y_test = spec.data.y_test
    if not x_test or not y_test:
        seri = list(spec.data.series or spec.data.tests)
        if len(seri) >= 2:
            x_test, y_test = seri[0], seri[1]
        else:
            raise ValueError("scatter_correlation icin data.x_test ve data.y_test zorunlu.")

    tmp = df.copy()
    tmp["report_dt"] = pd.to_datetime(tmp["report_dt"], errors="coerce")
    tmp = tmp[tmp["test"].isin([x_test, y_test])]
    if tmp.empty:
        raise ValueError(f"scatter_correlation icin secili testler bulunamadi: {x_test}, {y_test}")

    pair_df = (
        tmp.groupby(["report_dt", "test"], as_index=False)["value"]
        .mean()
        .pivot(index="report_dt", columns="test", values="value")
    )

    if x_test not in pair_df.columns or y_test not in pair_df.columns:
        raise ValueError("x_test/y_test serilerinden biri veri setinde yok.")

    pair_df = pair_df[[x_test, y_test]].dropna().sort_index()
    if pair_df.empty:
        raise ValueError("scatter_correlation icin ortak tarihli veri bulunamadi.")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=pair_df[x_test],
            y=pair_df[y_test],
            mode="markers",
            name=f"{x_test} vs {y_test}",
            marker={"size": 10, "color": "#1f77b4", "line": {"width": 1, "color": "#111"}},
            text=[dt.strftime("%Y-%m-%d") for dt in pair_df.index],
            hovertemplate="Tarih=%{text}<br>X=%{x:.3f}<br>Y=%{y:.3f}<extra></extra>",
        )
    )

    if getattr(spec.overlays, "trendline", False) and len(pair_df) >= 2:
        x_vals = pair_df[x_test].to_numpy(dtype=float)
        y_vals = pair_df[y_test].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        x_line = np.linspace(float(np.min(x_vals)), float(np.max(x_vals)), 50)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="Trendline",
                line={"color": "#d62728", "width": 2},
            )
        )

    fig.update_layout(
        title=spec.title,
        height=spec.output.height,
        template="plotly_white",
    )
    fig.update_xaxes(title_text=x_test)
    fig.update_yaxes(title_text=y_test)
    return fig
