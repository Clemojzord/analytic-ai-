"""
Analytic AI — Dataset & CleaningReport Models
"""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="datasets")
    cleaning_report = relationship("CleaningReport", back_populates="dataset", uselist=False, lazy="selectin")

    def __repr__(self):
        return f"<Dataset id={self.id} name={self.name} status={self.status}>"


class CleaningReport(Base):
    __tablename__ = "cleaning_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), unique=True, index=True)

    rows_before: Mapped[int] = mapped_column(Integer, default=0)
    rows_after: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)
    nulls_filled: Mapped[int] = mapped_column(Integer, default=0)
    outliers_flagged: Mapped[int] = mapped_column(Integer, default=0)
    columns_renamed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    type_conversions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cleaned_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    dataset = relationship("Dataset", back_populates="cleaning_report")

    def __repr__(self):
        return f"<CleaningReport dataset_id={self.dataset_id} rows={self.rows_before}→{self.rows_after}>"
