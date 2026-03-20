"""
Analytic AI — Clean Router
POST /clean/{dataset_id}
"""
import json
import traceback
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


def _load_dataframe(file_path: str) -> pd.DataFrame:
    """
    Load a DataFrame from R2 storage, with local-file fallback.
    Handles dirty CSVs with multiple encoding/delimiter attempts.
    """
    import io

    # 1) Try R2 download first
    try:
        return download_dataframe_from_r2(file_path)
    except Exception as r2_err:
        print(f"DIAGNOSTIC: R2 download failed ({r2_err}), trying local fallback...")

    # 2) Fallback: read from local uploads directory
    local_path = settings.upload_dir / file_path
    if not local_path.exists():
        raise FileNotFoundError(
            f"File '{file_path}' not found in R2 or locally at {local_path}"
        )

    content = local_path.read_bytes()
    ext = local_path.suffix.lower()

    if ext in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(content))

    # Robust CSV parsing — try multiple encodings and delimiters
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1", "utf-16"]
    delimiters = [None, ",", ";", "\t", "|"]

    for sep in delimiters:
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    io.BytesIO(content),
                    encoding=encoding,
                    sep=sep,
                    engine="python" if sep is None else "c",
                    on_bad_lines="skip",
                    skip_blank_lines=True,
                    low_memory=False,
                )
                if not df.empty and len(df.columns) > 1:
                    print(f"DIAGNOSTIC: Local CSV parsed with sep='{sep}', encoding='{encoding}'")
                    return df
            except Exception:
                continue

    # Final fallback
    try:
        return pd.read_csv(
            io.BytesIO(content),
            on_bad_lines="skip",
            encoding_errors="replace",
            sep=None,
            engine="python",
        )
    except Exception as e:
        raise ValueError(f"Could not parse file with any method: {e}")


@router.post("/{dataset_id}", response_model=CleaningReportResponse)
async def clean_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the automated cleaning pipeline on a previously uploaded dataset.
    Normalizes columns, fills nulls, flags outliers, and saves a cleaned CSV.
    """
    # Fetch dataset
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
    )
    ds: Dataset | None = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    if not ds.file_path:
        raise HTTPException(
            status_code=422,
            detail="Dataset has no associated file.",
        )

    # Load raw file (R2 first, local fallback)
    try:
        df = _load_dataframe(ds.file_path)
    except Exception as exc:
        print(f"DIAGNOSTIC: Failed to load dataset {dataset_id}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=422,
            detail=f"Could not load file: {exc}",
        )

    # Run cleaning engine
    from engines.cleaner import CleaningPipeline

    try:
        pipeline = CleaningPipeline(df)
        cleaned_df, report = pipeline.run()
    except Exception as exc:
        print(f"DIAGNOSTIC: Cleaning failed for dataset {dataset_id}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleaning pipeline error: {exc}",
        )

    # Log warnings if any
    if report.get("warnings"):
        print(f"DIAGNOSTIC: Cleaning warnings for dataset {dataset_id}: {report['warnings']}")

    # Save cleaned file (R2 first, local fallback)
    cleaned_path = f"cleaned_{dataset_id}.csv"
    try:
        upload_dataframe_to_r2(cleaned_df, cleaned_path, file_format="csv")
    except Exception as exc:
        print(f"DIAGNOSTIC: R2 upload failed ({exc}), saving locally...")
        try:
            local_out = settings.output_dir / cleaned_path
            cleaned_df.to_csv(str(local_out), index=False)
            print(f"DIAGNOSTIC: Saved cleaned file locally at {local_out}")
        except Exception as local_exc:
            print(f"DIAGNOSTIC: Local save also failed: {local_exc}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save cleaned data: {exc}",
            )

    # Ensure columns_renamed and type_conversions are JSON-serializable dicts of strings
    columns_renamed = {str(k): str(v) for k, v in report.get("columns_renamed", {}).items()}
    type_conversions = {str(k): str(v) for k, v in report.get("type_conversions", {}).items()}

    # Persist cleaning report
    existing = await db.execute(
        select(CleaningReport).where(CleaningReport.dataset_id == dataset_id)
    )
    cr = existing.scalar_one_or_none()
    if cr is None:
        cr = CleaningReport(dataset_id=dataset_id)
        db.add(cr)

    cr.rows_before = report["rows_before"]
    cr.rows_after = report["rows_after"]
    cr.duplicates_removed = report["duplicates_removed"]
    cr.nulls_filled = report["nulls_filled"]
    cr.outliers_flagged = report["outliers_flagged"]
    cr.columns_renamed = columns_renamed
    cr.type_conversions = type_conversions
    cr.cleaned_file_path = cleaned_path

    # Update dataset status
    ds.status = "cleaned"
    ds.row_count = len(cleaned_df)

    await db.commit()

    return CleaningReportResponse(
        dataset_id=dataset_id,
        rows_before=report["rows_before"],
        rows_after=report["rows_after"],
        rows_removed=report["rows_removed"],
        duplicates_removed=report["duplicates_removed"],
        nulls_filled=report["nulls_filled"],
        outliers_flagged=report["outliers_flagged"],
        columns_renamed=columns_renamed,
        type_conversions=type_conversions,
        message=(
            f"Cleaned successfully. "
            f"Removed {report['rows_removed']} rows, "
            f"filled {report['nulls_filled']} nulls, "
            f"flagged {report['outliers_flagged']} outliers."
        ),
    )
