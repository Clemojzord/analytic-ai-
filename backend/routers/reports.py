"""
Analytic AI — Reports Router
GET /reports/{dataset_id}/pdf — generate PDF report
GET /reports/{dataset_id}/excel — generate Excel report
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.storage import download_dataframe_from_r2
from models.dataset import Dataset
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{dataset_id}/excel")
async def generate_excel_report(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download an Excel summary report."""
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

    import uuid
    report_name = f"analytic_ai_report_{dataset_id}_{uuid.uuid4().hex[:8]}.xlsx"
    report_path = settings.output_dir / report_name

    with pd.ExcelWriter(str(report_path), engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)

        # Summary sheet
        numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not c.startswith("_")]
        if numeric_cols:
            summary = df[numeric_cols].describe().round(2)
            summary.to_excel(writer, sheet_name="Summary")

    return FileResponse(
        path=str(report_path),
        filename=report_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/{dataset_id}/pdf")
async def generate_pdf_report(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download a PDF summary report."""
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

    import uuid
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    report_name = f"analytic_ai_report_{dataset_id}_{uuid.uuid4().hex[:8]}.pdf"
    report_path = settings.output_dir / report_name

    doc = SimpleDocTemplate(str(report_path), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Analytic AI — Report for '{ds.name}'", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Rows: {len(df)} | Columns: {len(df.columns)}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Summary table
    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not c.startswith("_")]
    if numeric_cols:
        summary = df[numeric_cols].describe().round(2)
        table_data = [["Stat"] + list(summary.columns)]
        for idx in summary.index:
            row = [idx] + [str(v) for v in summary.loc[idx].values]
            table_data.append(row)

        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(t)

    doc.build(elements)

    return FileResponse(
        path=str(report_path),
        filename=report_name,
        media_type="application/pdf",
    )
