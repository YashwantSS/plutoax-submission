from typing import Literal

from pydantic import BaseModel, Field


class EnvReading(BaseModel):
    month: str = Field(examples=["Mar-23"])
    area: str = Field(examples=["Compression IV"])
    reference_document: str = Field(examples=["Executed BMRs"])
    temperature_c: dict[str, float] = Field(description="min/max Celsius")
    relative_humidity_pct: dict[str, float] = Field(description="min/max % RH")
    differential_pressure_mm_wc: dict[str, float] = Field(description="min/max mm WC")
    page: int | None = None


class DocumentIngestResult(BaseModel):
    document_id: str
    rows_ingested: int
    stored_path: str


class DocumentRowsSummary(BaseModel):
    document_id: str
    row_count: int
    rows: list[EnvReading]


class QueryAnswer(BaseModel):
    document_id: str
    month: str | None = None
    area: str | None = None
    reference_document: str = "Executed BMRs"
    reading: EnvReading | None = None
    message: str | None = None


class QueryBody(BaseModel):
    document_id: str
    question: str


class ExtractPhaseResult(BaseModel):
    agent: Literal["extract"] = "extract"
    rows_extracted: int
    stored_path: str


class ValidationIssueItem(BaseModel):
    row_index: int
    month: str
    area: str
    reference_document: str
    issues: list[str]


class ValidatePhaseResult(BaseModel):
    agent: Literal["validate"] = "validate"
    rows_checked: int
    rows_valid: int
    rows_invalid: int
    issues: list[ValidationIssueItem]


class MonthMidpointStatsModel(BaseModel):
    month: str
    reference_document: str
    sample_count: int
    mean_of_midpoint_temp_c: float
    median_of_midpoint_temp_c: float
    mode_of_midpoint_temp_c: list[float]
    mean_of_midpoint_rh_pct: float
    median_of_midpoint_rh_pct: float
    mode_of_midpoint_rh_pct: list[float]
    mean_of_midpoint_dp_mm_wc: float
    median_of_midpoint_dp_mm_wc: float
    mode_of_midpoint_dp_mm_wc: list[float]


class AnalyzePhaseResult(BaseModel):
    agent: Literal["analyze"] = "analyze"
    reference_document: str
    monthly: list[MonthMidpointStatsModel]


class FullPipelineResult(BaseModel):
    """Three-agent pipeline output: extract → validate → analyze."""

    document_id: str
    extract: ExtractPhaseResult
    validate: ValidatePhaseResult
    analyze: AnalyzePhaseResult


class ReprocessBody(BaseModel):
    document_id: str
    reference_document: str = "Executed BMRs"
