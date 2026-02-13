import pandas as pd
import pytest

from core.grafik.renderer_plotly import GrafikRenderHatasi, render


def _spec():
    return {
        "version": 1,
        "template": "trend_refband",
        "title": "Smoke",
        "data": {"x": "report_dt", "y": "value", "test": "HGB"},
        "overlays": {},
        "output": {"engine": "plotly", "height": 380},
    }


def test_renderer_bos_df_hata_verir():
    with pytest.raises(GrafikRenderHatasi, match="bos"):
        render(_spec(), pd.DataFrame())

