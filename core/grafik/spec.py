"""Grafik JSON spec semasi ve validasyon kurallari."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.alanlar.lab.normalize import normalize_test_adi


class ChartTemplate(str, Enum):
    TREND_REFBAND = "trend_refband"
    HEATMAP_TESTS_TIME = "heatmap_tests_time"
    SCATTER_CORRELATION = "scatter_correlation"


ALLOWED_COLUMNS = {
    "source",
    "page",
    "patient_name",
    "facility",
    "report_date",
    "report_time",
    "report_dt",
    "test_raw",
    "test",
    "value",
    "unit",
    "ref_low",
    "ref_high",
    "status",
    "normalized_score",
}

# Baslangic whitelist; gerektikce alan bazli genisletilebilir.
ALLOWED_TESTS = {
    "WBC",
    "HGB",
    "HCT",
    "RBC",
    "MCV",
    "MCH",
    "MCHC",
    "RDW-CV",
    "RDW-SD",
    "PLT",
    "GRAN#",
    "GRAN%",
    "LYMPH#",
    "LYMPH%",
    "MID#",
    "MID%",
    "MPV",
    "PCT",
    "PDW",
}


def _validate_test_adi(test_adi: str) -> str:
    kanonik = normalize_test_adi(test_adi)
    if kanonik not in ALLOWED_TESTS:
        raise ValueError(f"desteklenmeyen test adi: {test_adi}")
    return kanonik


def _validate_column(col: Optional[str]) -> Optional[str]:
    if col is None:
        return None
    if col not in ALLOWED_COLUMNS:
        raise ValueError(f"desteklenmeyen kolon: {col}")
    return col


class ChartData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: str = "report_dt"
    y: str = "value"
    group_by: Optional[str] = None
    test: Optional[str] = None
    tests: list[str] = Field(default_factory=list)
    series: list[str] = Field(default_factory=list)
    x_test: Optional[str] = None
    y_test: Optional[str] = None

    @field_validator("x", "y", "group_by")
    @classmethod
    def _kolon_whitelist(cls, v: Optional[str]) -> Optional[str]:
        return _validate_column(v)

    @field_validator("test")
    @classmethod
    def _tek_test_whitelist(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_test_adi(v)

    @field_validator("tests")
    @classmethod
    def _coklu_test_whitelist(cls, v: Iterable[str]) -> list[str]:
        return [_validate_test_adi(item) for item in v]

    @field_validator("series")
    @classmethod
    def _seri_test_whitelist(cls, v: Iterable[str]) -> list[str]:
        return [_validate_test_adi(item) for item in v]

    @field_validator("x_test", "y_test")
    @classmethod
    def _xy_test_whitelist(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_test_adi(v)


class ChartOverlays(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_band: bool = True
    show_ref_band: bool = True
    show_points: bool = True
    annotate_status: bool = False
    trendline: bool = False


class ChartOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "plotly"
    height: int = Field(default=480, ge=240, le=1400)

    @field_validator("engine")
    @classmethod
    def _engine_kisitla(cls, v: str) -> str:
        if v != "plotly":
            raise ValueError("yalnizca plotly engine desteklenir")
        return v


class ChartSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    template: ChartTemplate
    title: str
    data: ChartData
    overlays: ChartOverlays = Field(default_factory=ChartOverlays)
    output: ChartOutput = Field(default_factory=ChartOutput)

    @field_validator("version")
    @classmethod
    def _version_kisitla(cls, v: int) -> int:
        if v != 1:
            raise ValueError("yalnizca spec version=1 desteklenir")
        return v


def parse_chart_spec(payload: dict[str, Any] | str) -> ChartSpec:
    """
    Dict veya JSON string alip ChartSpec'e donusturur.
    ValidationError oldugu gibi disari aktarilir.
    """
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload
    return ChartSpec.model_validate(data)
