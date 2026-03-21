"""
Analytic AI — Pydantic Response Schemas
"""
from typing import Any
from pydantic import BaseModel


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


class DatasetResponse(BaseModel):
    id: int
    name: str
    file_path: str | None = None
    status: str
    row_count: int | None = None
    message: str | None = None


class UploadResponse(BaseModel):
    dataset_id: int
    filename: str
    row_count: int
    column_count: int
    columns: list[str]
    message: str


class AnalyticsResponse(BaseModel):
    dataset_id: int
    summary: dict[str, Any]
    message: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None = None
