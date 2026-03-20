"""
Analytic AI — Visualize Router
GET /visualize/{dataset_id} — generate chart data from a dataset
"""
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.storage import download_dataframe_from_r2
from models.dataset import Dataset
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/visualize", tags=["Visualization"])


@router.get("/{dataset_id}")
async def get_chart_data(
    dataset_id: int,
    chart_type: str = Query("bar", description="Chart type: bar, line, pie"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return chart-ready data for the frontend to render."""
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
    category_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    charts = []
    for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
        chart = {
            "column": col,
            "type": chart_type,
            "values": df[col].dropna().head(50).tolist(),
        }
        # If there's a category column, use it as labels
        if category_cols:
            chart["labels"] = df[category_cols[0]].head(50).astype(str).tolist()
        else:
            chart["labels"] = list(range(min(50, len(df))))
        charts.append(chart)

    return {
        "dataset_id": dataset_id,
        "chart_type": chart_type,
        "charts": charts,
        "message": f"Generated {len(charts)} chart(s) for dataset.",
    }
