"""
Analytic AI — Analytics Router
GET /analytics/{dataset_id} — compute KPIs from a cleaned dataset
"""
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.storage import download_dataframe_from_r2
from models.dataset import Dataset
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/{dataset_id}")
async def get_analytics(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute summary statistics / KPIs for a dataset."""
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
    )
    ds = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Prefer cleaned file
    file_key = ds.file_path
    if ds.cleaning_report and ds.cleaning_report.cleaned_file_path:
        file_key = ds.cleaning_report.cleaned_file_path

    try:
        df = download_dataframe_from_r2(file_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not load data: {exc}")

    # Build summary for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Filter out internal outlier flag columns
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]

    summary = {}
    for col in numeric_cols:
        s = df[col].dropna()
        summary[col] = {
            "count": int(s.count()),
            "sum": round(float(s.sum()), 2),
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "std": round(float(s.std()), 2),
        }

    return {
        "dataset_id": dataset_id,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": len(numeric_cols),
        "summary": summary,
        "message": f"Computed analytics for {len(numeric_cols)} numeric columns.",
    }
