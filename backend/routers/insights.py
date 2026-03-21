"""
Analytic AI — Insights Router
GET /insights/{dataset_id} — AI-generated business insights
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

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/{dataset_id}")
async def get_insights(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate data-driven business insights from a dataset."""
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
    insights = []

    # Data quality insight
    null_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
    insights.append({
        "type": "data_quality",
        "title": "Data Quality Score",
        "description": f"Your data has {100 - null_pct:.1f}% completeness across {len(df.columns)} columns and {len(df)} rows.",
        "score": round(100 - null_pct, 1),
    })

    # Top performer insight (highest mean column)
    if numeric_cols:
        means = {col: float(df[col].mean()) for col in numeric_cols}
        top_col = max(means, key=means.get)
        insights.append({
            "type": "top_metric",
            "title": f"Highest Average: {top_col}",
            "description": f"The column '{top_col}' has the highest average value of {means[top_col]:,.2f}.",
            "value": means[top_col],
        })

        # Volatility insight (highest std/mean ratio)
        volatility = {}
        for col in numeric_cols:
            mean_val = df[col].mean()
            if mean_val != 0:
                volatility[col] = abs(df[col].std() / mean_val)
        if volatility:
            most_volatile = max(volatility, key=volatility.get)
            insights.append({
                "type": "volatility",
                "title": f"Most Variable: {most_volatile}",
                "description": f"'{most_volatile}' shows the highest variability (CV={volatility[most_volatile]:.2f}). Consider investigating outliers.",
                "coefficient_of_variation": round(volatility[most_volatile], 2),
            })

    return {
        "dataset_id": dataset_id,
        "insight_count": len(insights),
        "insights": insights,
        "message": f"Generated {len(insights)} insight(s) from your data.",
    }
