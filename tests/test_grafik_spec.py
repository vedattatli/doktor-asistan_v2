import pytest
from pydantic import ValidationError

from core.grafik.spec import ChartSpec


def _ornek_spec():
    return {
        "version": 1,
        "template": "trend_refband",
        "title": "HGB Trend",
        "data": {
            "x": "report_dt",
            "y": "value",
            "test": "HGB",
        },
        "overlays": {
            "show_ref_band": True,
            "show_points": True,
        },
        "output": {
            "engine": "plotly",
            "height": 420,
        },
    }


def test_spec_parse_ok():
    spec = ChartSpec.model_validate(_ornek_spec())
    assert spec.template.value == "trend_refband"
    assert spec.data.x == "report_dt"
    assert spec.output.engine == "plotly"


def test_spec_wrong_template_reddedilir():
    bad = _ornek_spec()
    bad["template"] = "invalid_template"
    with pytest.raises(ValidationError):
        ChartSpec.model_validate(bad)


def test_spec_unknown_field_reddedilir():
    bad = _ornek_spec()
    bad["serbest_alan"] = "yasak"
    with pytest.raises(ValidationError):
        ChartSpec.model_validate(bad)

