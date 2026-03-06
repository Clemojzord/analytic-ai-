"""
Analytic AI — Pydantic Schemas
Request / Response models for the API
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Dataset ──────────────────────────────────────────────────

class DatasetBase(BaseModel):
    name: str
    source_type: str = "csv"


class DatasetCreate(DatasetBase):
    pass


class ColumnMeta(BaseModel):
    name: str
    dtype: str
    null_count: int
    unique_count: int
    sample_values: list[Any]


class DatasetResponse(BaseModel):
    id: int
    name: str
    source_type: str
    status: str
    row_count: int
    col_count: int
    columns_meta: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetPreview(BaseModel):
    id: int
    name: str
    status: str
    row_count: int
    columns: list[str]
    preview: list[dict[str, Any]]   # first 20 rows


# ── Upload ────────────────────────────────────────────────────

class UploadDBRequest(BaseModel):
    connection_string: str = Field(..., description="SQLAlchemy DB URL, e.g. postgresql://user:pass@host/db")
    table_name: str = Field(..., description="Table to import")
    dataset_name: Optional[str] = None


class UploadResponse(BaseModel):
    dataset_id: int
    name: str
    rows: int
    columns: list[str]
    preview: list[dict[str, Any]]
    message: str


# ── Cleaning ──────────────────────────────────────────────────

class CleaningReportResponse(BaseModel):
    dataset_id: int
    rows_before: int
    rows_after: int
    rows_removed: int
    duplicates_removed: int
    nulls_filled: int
    outliers_flagged: int
    columns_renamed: dict[str, str]
    type_conversions: dict[str, str]
    message: str


# ── Analytics ─────────────────────────────────────────────────

class MonthlyRevenue(BaseModel):
    period: str
    revenue: float
    growth_rate: Optional[float] = None


class KPIResponse(BaseModel):
    dataset_id: int
    total_revenue: Optional[float] = None
    profit_margin: Optional[float] = None
    growth_rate: Optional[float] = None
    top_product: Optional[str] = None
    top_branch: Optional[str] = None
    clv: Optional[float] = None
    monthly_revenue: list[MonthlyRevenue] = []
    full_kpis: dict[str, Any] = {}
    currency: str = "KES"


# ── Visualization ─────────────────────────────────────────────

class ChartResponse(BaseModel):
    chart_type: str
    format: str = "png"
    data_url: str   # base64 encoded PNG  "data:image/png;base64,..."
    title: str


# ── Insights ──────────────────────────────────────────────────

class InsightItem(BaseModel):
    category: str
    severity: str  # info | warning | critical
    text: str
    metric: Optional[str] = None
    value: Optional[float] = None


class InsightsResponse(BaseModel):
    dataset_id: int
    insights: list[InsightItem]
    executive_summary: str
    generated_at: datetime


# ── Reports ───────────────────────────────────────────────────

class ReportResponse(BaseModel):
    dataset_id: int
    format: str
    file_url: str
    file_size_kb: float
    generated_at: datetime
