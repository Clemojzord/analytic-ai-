"""
Analytic AI — Analytics Router
GET /analytics/{dataset_id}
GET /datasets
GET /datasets/{dataset_id}
"""
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from engines.analytics import compute_kpis
from engines.cleaner import load_file
from models.dataset import CleaningReport, Dataset, KPISnapshot
from models.schemas import DatasetPreview, DatasetResponse, KPIResponse, MonthlyRevenue

router = APIRouter(tags=["Analytics & Datasets"])


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all uploaded datasets."""
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


@router.get("/datasets/{dataset_id}", response_model=DatasetPreview)
async def preview_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Get a preview of a dataset (first 20 rows + column list)."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Determine which file to load
    cr_result = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr: CleaningReport | None = cr_result.scalar_one_or_none()
    file_path_str = (cr.cleaned_file_path if cr and cr.cleaned_file_path else ds.file_path)

    rows: list = []
    columns: list = []
    if file_path_str:
        fp = Path(file_path_str)
        if fp.exists():
            df = load_file(fp)
            columns = df.columns.tolist()
            rows = df.head(20).fillna("").astype(str).to_dict(orient="records")

    return DatasetPreview(
        id=ds.id,
        name=ds.name,
        status=ds.status,
        row_count=ds.row_count,
        columns=columns,
        preview=rows,
    )


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a dataset and its associated files."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if ds.file_path:
        Path(ds.file_path).unlink(missing_ok=True)

    await db.delete(ds)


@router.get("/analytics/{dataset_id}", response_model=KPIResponse)
async def get_analytics(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """
    Compute KPIs for a dataset.
    If already computed, returns cached snapshot.
    Uses cleaned file if available, else raw file.
    """
    # Load dataset
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Check for existing KPI snapshot
    snap_result = await db.execute(
        select(KPISnapshot).where(KPISnapshot.dataset_id == dataset_id)
    )
    snap: KPISnapshot | None = snap_result.scalar_one_or_none()

    # Determine file path (prefer cleaned)
    cr_result = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr: CleaningReport | None = cr_result.scalar_one_or_none()
    file_path_str = (cr.cleaned_file_path if cr and cr.cleaned_file_path else ds.file_path)

    if not file_path_str or not Path(file_path_str).exists():
        raise HTTPException(
            status_code=422,
            detail="No data file found. Upload and optionally clean the dataset first."
        )

    df = load_file(Path(file_path_str))
    kpis = compute_kpis(df)

    # Persist / update KPI snapshot
    if snap is None:
        snap = KPISnapshot(dataset_id=dataset_id)
        db.add(snap)

    snap.total_revenue  = kpis.get("total_revenue")
    snap.profit_margin  = kpis.get("profit_margin_pct")
    snap.growth_rate    = kpis.get("mom_growth_rate_pct")
    snap.top_product    = kpis.get("top_product")
    snap.top_branch     = kpis.get("top_branch")
    snap.clv            = kpis.get("estimated_clv_annual")
    snap.monthly_data   = kpis.get("monthly_revenue", [])
    snap.full_kpis      = kpis
    ds.status = "analyzed"

    monthly = [
        MonthlyRevenue(**m)
        for m in kpis.get("monthly_revenue", [])
    ]

    return KPIResponse(
        dataset_id=dataset_id,
        total_revenue=snap.total_revenue,
        profit_margin=snap.profit_margin,
        growth_rate=snap.growth_rate,
        top_product=snap.top_product,
        top_branch=snap.top_branch,
        clv=snap.clv,
        monthly_revenue=monthly,
        full_kpis=kpis,
        currency="KES",
    )
