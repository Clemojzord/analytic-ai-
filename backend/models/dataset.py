"""
Analytic AI — SQLAlchemy ORM Models
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="csv")  # csv|excel|db
    status: Mapped[str] = mapped_column(String(50), default="raw")  # raw|cleaned|analyzed
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    col_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relations
    cleaning_report: Mapped[Optional["CleaningReport"]] = relationship(
        back_populates="dataset", uselist=False, cascade="all, delete-orphan"
    )
    kpi_snapshot: Mapped[Optional["KPISnapshot"]] = relationship(
        back_populates="dataset", uselist=False, cascade="all, delete-orphan"
    )


class CleaningReport(Base):
    __tablename__ = "cleaning_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), unique=True)
    rows_before: Mapped[int] = mapped_column(Integer, default=0)
    rows_after: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)
    nulls_filled: Mapped[int] = mapped_column(Integer, default=0)
    outliers_flagged: Mapped[int] = mapped_column(Integer, default=0)
    columns_renamed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    type_conversions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    cleaned_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="cleaning_report")


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), unique=True)
    total_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_product: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    clv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    monthly_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    full_kpis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="kpi_snapshot")
