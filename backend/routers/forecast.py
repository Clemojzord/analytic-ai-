"""
Analytic AI — Forecast Router
POST /forecast/{dataset_id} — simple time-series forecasting
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

router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.post("/{dataset_id}")
async def forecast_dataset(
    dataset_id: int,
    periods: int = 6,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a simple linear-trend forecast for the first numeric column.
    """
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
    )
    ds = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_key = ds.file_path
    if ds.cleaning_report and ds.cleaning_report.cleaned_file_path:
        file_key = ds.cleaning_report.cleaned_file_path

    try:
        df = download_dataframe_from_r2(file_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not load data: {exc}")

    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not c.startswith("_")]
    if not numeric_cols:
        raise HTTPException(status_code=422, detail="No numeric columns available for forecasting.")

    target_col = numeric_cols[0]
    values = df[target_col].dropna().values

    if len(values) < 3:
        raise HTTPException(status_code=422, detail=f"Not enough data points in '{target_col}' for forecasting.")

    # Simple linear regression forecast
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values, 1)
    slope, intercept = coeffs

    future_x = np.arange(len(values), len(values) + periods)
    forecast_values = (slope * future_x + intercept).tolist()

    return {
        "dataset_id": dataset_id,
        "target_column": target_col,
        "historical_count": len(values),
        "forecast_periods": periods,
        "forecast": [round(v, 2) for v in forecast_values],
        "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat",
        "message": f"Generated {periods}-period forecast for '{target_col}'.",
    }
