from pathlib import Path

import pytest

from core.analiz_motoru import KlinikAnalizMotoru
from core.alanlar.lab.df_uret import parsed_pages_to_df
from core.grafik.renderer_plotly import render


PDF_SABIT_PATH = Path("/mnt/data/19.12.2016.pdf")
PDF_FALLBACK_PATH = Path("data/pdfs/19.12.2016.pdf")


@pytest.fixture(scope="module")
def df():
    if PDF_SABIT_PATH.exists():
        pdf_path = PDF_SABIT_PATH
    elif PDF_FALLBACK_PATH.exists():
        pdf_path = PDF_FALLBACK_PATH
    else:
        pytest.skip("Test PDF bulunamadı: /mnt/data/19.12.2016.pdf")

    parsed_pages = KlinikAnalizMotoru().pdf_isle(str(pdf_path))
    return parsed_pages_to_df(parsed_pages)


def test_trend_refband_smoke(df):
    spec = {
        "version": 1,
        "template": "trend_refband",
        "title": "Trend",
        "data": {
            "x": "report_dt",
            "y": "value",
            "series": ["HGB", "MCV"],
        },
        "overlays": {"reference_band": True, "show_points": True},
        "output": {"engine": "plotly", "height": 420},
    }
    fig = render(spec, df)
    assert len(fig.data) >= 1


def test_heatmap_tests_time_smoke(df):
    spec = {
        "version": 1,
        "template": "heatmap_tests_time",
        "title": "Heatmap",
        "data": {
            "x": "report_dt",
            "y": "status",
            "series": ["HGB", "WBC"],
        },
        "overlays": {},
        "output": {"engine": "plotly", "height": 420},
    }
    fig = render(spec, df)
    assert len(fig.data) >= 1


def test_scatter_correlation_smoke(df):
    spec = {
        "version": 1,
        "template": "scatter_correlation",
        "title": "Scatter",
        "data": {
            "x": "report_dt",
            "y": "value",
            "x_test": "HGB",
            "y_test": "MCV",
        },
        "overlays": {"trendline": True},
        "output": {"engine": "plotly", "height": 420},
    }
    fig = render(spec, df)
    assert len(fig.data) >= 1

