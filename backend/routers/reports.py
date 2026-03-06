"""
Analytic AI — Reports Router
GET /reports/{dataset_id}/pdf
GET /reports/{dataset_id}/excel
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from engines.analytics import compute_kpis
from engines.cleaner import load_file
from engines.insight_gen import generate_insights
from engines.reporter import generate_excel, generate_pdf
from models.dataset import CleaningReport, Dataset, KPISnapshot

router = APIRouter(prefix="/reports", tags=["Reports"])


async def _load_context(dataset_id: int, db: AsyncSession):
    """Shared helper: load dataset + df + kpis + insights."""
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
        raise HTTPException(status_code=422, detail="No data file found. Upload first.")

    import pandas as pd
    df = load_file(Path(file_path_str))

    snap_result = await db.execute(
        select(KPISnapshot).where(KPISnapshot.dataset_id == dataset_id)
    )
    snap: KPISnapshot | None = snap_result.scalar_one_or_none()
    kpis = snap.full_kpis if (snap and snap.full_kpis) else compute_kpis(df)
    insights = generate_insights(kpis)

    return ds, df, kpis, insights


@router.get("/{dataset_id}/pdf")
async def download_pdf(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Generate and download a branded PDF business intelligence report."""
    ds, df, kpis, insights = await _load_context(dataset_id, db)

    filename = f"analytic_ai_report_{dataset_id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = settings.output_dir / filename

    try:
        generate_pdf(
            dataset_name=ds.name,
            kpis=kpis,
            insights=insights,
            output_path=output_path,
            df_preview=df,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        filename=f"AnalyticAI_{ds.name.replace(' ','_')}_Report.pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{dataset_id}/excel")
async def download_excel(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Generate and download a multi-sheet Excel report (KPIs + monthly + insights + data)."""
    ds, df, kpis, insights = await _load_context(dataset_id, db)

    filename = f"analytic_ai_report_{dataset_id}_{uuid.uuid4().hex[:8]}.xlsx"
    output_path = settings.output_dir / filename

    try:
        generate_excel(
            dataset_name=ds.name,
            kpis=kpis,
            insights=insights,
            output_path=output_path,
            df_cleaned=df,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {exc}")

    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"AnalyticAI_{ds.name.replace(' ','_')}_Report.xlsx",
    )
