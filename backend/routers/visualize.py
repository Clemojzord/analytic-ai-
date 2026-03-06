"""
Analytic AI — Visualize Router
GET /visualize/{dataset_id}/{chart_type}
"""
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from engines.cleaner import load_file
from engines.visualizer import CHART_TYPES, generate_chart
from models.dataset import CleaningReport, Dataset
from models.schemas import ChartResponse

router = APIRouter(prefix="/visualize", tags=["Visualization"])


@router.get("/{dataset_id}/{chart_type}", response_model=ChartResponse)
async def get_chart(
    dataset_id: int,
    chart_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a chart PNG (returned as base64 data URL).

    chart_type options:
    - revenue_trend
    - product_pie
    - branch_bar
    - sales_heatmap
    - segment_scatter
    """
    if chart_type not in CHART_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown chart type '{chart_type}'. Choose from: {CHART_TYPES}",
        )

    # Load dataset
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Prefer cleaned file
    cr_result = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr: CleaningReport | None = cr_result.scalar_one_or_none()
    file_path_str = (cr.cleaned_file_path if cr and cr.cleaned_file_path else ds.file_path)

    if not file_path_str or not Path(file_path_str).exists():
        raise HTTPException(
            status_code=422,
            detail="No data file available. Upload the dataset first.",
        )

    df = load_file(Path(file_path_str))

    try:
        result_dict = generate_chart(df, chart_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {exc}")

    return ChartResponse(**result_dict)


@router.get("/{dataset_id}", response_model=list[ChartResponse])
async def get_all_charts(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate all 5 charts for a dataset at once."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    cr_result = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr: CleaningReport | None = cr_result.scalar_one_or_none()
    file_path_str = (cr.cleaned_file_path if cr and cr.cleaned_file_path else ds.file_path)

    if not file_path_str or not Path(file_path_str).exists():
        raise HTTPException(status_code=422, detail="No data file available.")

    df = load_file(Path(file_path_str))
    charts: list[ChartResponse] = []
    for ct in CHART_TYPES:
        try:
            charts.append(ChartResponse(**generate_chart(df, ct)))
        except Exception:
            pass  # Skip charts that can't be rendered for this dataset

    return charts
