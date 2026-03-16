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
from core.storage import download_dataframe_from_r2, upload_dataframe_to_r2
from engines.cleaner import clean_dataframe
from models.dataset import CleaningReport, Dataset
from models.user import User
from models.schemas import CleaningReportResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/clean", tags=["Cleaning"])


@router.post("/{dataset_id}", response_model=CleaningReportResponse)
async def clean_dataset(
    dataset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the automated cleaning pipeline on a previously uploaded dataset.
    Normalizes columns, fills nulls, flags outliers, and saves a cleaned CSV back to Firebase.
    """
    # Fetch dataset
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
    )
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    if not ds.file_path:
        raise HTTPException(status_code=422, detail="Dataset has no associated file (DB-imported datasets not yet supported for cleaning).")

    # Load raw file from Firebase
    try:
        df = download_dataframe_from_r2(ds.file_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not load file from storage: {exc}")

    # Run cleaning engine
    from engines.cleaner import CleaningPipeline
    pipeline = CleaningPipeline(df)
    cleaned_df, report = pipeline.run()

    # Log warnings if any
    if report.get("warnings"):
        print(f"DIAGNOSTIC: Cleaning warnings for dataset {dataset_id}: {report['warnings']}")

    # Save cleaned file to Firebase
    cleaned_path = f"cleaned_{dataset_id}.csv"
    try:
        upload_dataframe_to_r2(cleaned_df, cleaned_path, file_format='csv')
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload cleaned data: {exc}")

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
    cr.cleaned_file_path   = cleaned_path

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
