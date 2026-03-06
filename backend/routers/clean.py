"""
Analytic AI — Clean Router
POST /clean/{dataset_id}
"""
import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from engines.cleaner import clean_dataframe, load_file, save_cleaned
from models.dataset import CleaningReport, Dataset
from models.schemas import CleaningReportResponse

router = APIRouter(prefix="/clean", tags=["Cleaning"])


@router.post("/{dataset_id}", response_model=CleaningReportResponse)
async def clean_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """
    Run the automated cleaning pipeline on a previously uploaded dataset.
    Normalizes columns, fills nulls, flags outliers, and saves a cleaned CSV.
    """
    # Fetch dataset
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    if not ds.file_path:
        raise HTTPException(status_code=422, detail="Dataset has no associated file (DB-imported datasets not yet supported for cleaning).")

    # Load raw file
    file_path = Path(ds.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk.")

    try:
        df = load_file(file_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not load file: {exc}")

    # Run cleaning engine
    cleaned_df, report = clean_dataframe(df)

    # Save cleaned file
    cleaned_path = settings.output_dir / f"cleaned_{dataset_id}.csv"
    save_cleaned(cleaned_df, cleaned_path)

    # Persist cleaning report
    existing = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr = existing.scalar_one_or_none()
    if cr is None:
        cr = CleaningReport(dataset_id=dataset_id)
        db.add(cr)

    cr.rows_before         = report["rows_before"]
    cr.rows_after          = report["rows_after"]
    cr.duplicates_removed  = report["duplicates_removed"]
    cr.nulls_filled        = report["nulls_filled"]
    cr.outliers_flagged    = report["outliers_flagged"]
    cr.columns_renamed     = report["columns_renamed"]
    cr.type_conversions    = report["type_conversions"]
    cr.cleaned_file_path   = str(cleaned_path)

    # Update dataset status
    ds.status = "cleaned"
    ds.row_count = len(cleaned_df)

    return CleaningReportResponse(
        dataset_id=dataset_id,
        rows_before=report["rows_before"],
        rows_after=report["rows_after"],
        rows_removed=report["rows_removed"],
        duplicates_removed=report["duplicates_removed"],
        nulls_filled=report["nulls_filled"],
        outliers_flagged=report["outliers_flagged"],
        columns_renamed=report["columns_renamed"],
        type_conversions=report["type_conversions"],
        message=(
            f"Cleaned successfully. "
            f"Removed {report['rows_removed']} rows, "
            f"filled {report['nulls_filled']} nulls, "
            f"flagged {report['outliers_flagged']} outliers."
        ),
    )
