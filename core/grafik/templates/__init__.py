"""Plotly template registry."""

from core.grafik.spec import ChartTemplate

from .heatmap_tests_time import render_heatmap_tests_time
from .scatter_correlation import render_scatter_correlation
from .trend_refband import render_trend_refband

TEMPLATE_REGISTRY = {
    ChartTemplate.TREND_REFBAND: render_trend_refband,
    ChartTemplate.HEATMAP_TESTS_TIME: render_heatmap_tests_time,
    ChartTemplate.SCATTER_CORRELATION: render_scatter_correlation,
}

__all__ = ["TEMPLATE_REGISTRY"]
