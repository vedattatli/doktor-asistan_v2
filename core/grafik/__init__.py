"""Spec tabanli deterministik grafik altyapisi."""

from .renderer_plotly import GrafikRenderHatasi, render
from .spec import ChartSpec, ChartTemplate

__all__ = ["ChartSpec", "ChartTemplate", "GrafikRenderHatasi", "render"]

