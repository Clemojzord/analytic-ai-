"""
Analytic AI — Insights Router
GET /insights/{dataset_id}
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from engines.analytics import compute_kpis
from engines.cleaner import load_file
from engines.insight_gen import generate_insights
from models.dataset import CleaningReport, Dataset, KPISnapshot
from models.schemas import InsightItem, InsightsResponse

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/{dataset_id}", response_model=InsightsResponse)
async def get_insights(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """
    Generate automated business insights for a dataset.
    Runs the KPI engine + rule-based insight generator.
    Returns a list of insights + executive summary.
    """
    # Fetch dataset
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Get file path (prefer cleaned)
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

    # Check for cached KPIs
    snap_result = await db.execute(
        select(KPISnapshot).where(KPISnapshot.dataset_id == dataset_id)
    )
    snap: KPISnapshot | None = snap_result.scalar_one_or_none()

    kpis = snap.full_kpis if (snap and snap.full_kpis) else compute_kpis(df)

    raw = generate_insights(kpis)

    return InsightsResponse(
        dataset_id=dataset_id,
        insights=[InsightItem(**i) for i in raw["insights"]],
        executive_summary=raw["executive_summary"],
        generated_at=datetime.utcnow(),
    )
