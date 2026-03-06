"""
Analytic AI — Upload Router
POST /upload/csv, /upload/excel, /upload/db
"""
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from engines.cleaner import load_file
from models.dataset import Dataset
from models.schemas import UploadDBRequest, UploadResponse

router = APIRouter(prefix="/upload", tags=["Upload"])


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _df_to_response(dataset_id: int, name: str, df: pd.DataFrame) -> UploadResponse:
    return UploadResponse(
        dataset_id=dataset_id,
        name=name,
        rows=len(df),
        columns=df.columns.tolist(),
        preview=df.head(5).fillna("").astype(str).to_dict(orient="records"),
        message=f"Dataset uploaded successfully ({len(df):,} rows, {len(df.columns)} columns).",
    )


async def _save_dataset(db: AsyncSession, name: str, source_type: str,
                        file_path: str | None, df: pd.DataFrame) -> int:
    """Persist dataset metadata to DB and return the new ID."""
    columns_meta = {
        col: {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
            "sample": df[col].dropna().head(3).astype(str).tolist(),
        }
        for col in df.columns
    }
    ds = Dataset(
        name=name,
        source_type=source_type,
        status="raw",
        row_count=len(df),
        col_count=len(df.columns),
        columns_meta=columns_meta,
        file_path=file_path,
    )
    db.add(ds)
    await db.flush()  # get assigned ID
    return ds.id


async def _persist_file(file: UploadFile) -> Path:
    """Save uploaded file to the uploads directory."""
    ext = Path(file.filename or "upload.csv").suffix or ".csv"
    dest = settings.upload_dir / f"{uuid.uuid4().hex}{ext}"
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
        )
    dest.write_bytes(content)
    return dest


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/csv", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to upload"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV file and register it as a new dataset."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    dest = await _persist_file(file)
    try:
        df = load_file(dest)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")

    ds_id = await _save_dataset(db, file.filename or "upload.csv", "csv", str(dest), df)
    return _df_to_response(ds_id, file.filename or "upload.csv", df)


@router.post("/excel", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_excel(
    file: UploadFile = File(..., description="Excel file (.xlsx or .xls)"),
    db: AsyncSession = Depends(get_db),
):
    """Upload an Excel file and register it as a new dataset."""
    if not any((file.filename or "").lower().endswith(ext) for ext in (".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are accepted.")

    dest = await _persist_file(file)
    try:
        df = load_file(dest)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not parse Excel: {exc}")

    ds_id = await _save_dataset(db, file.filename or "upload.xlsx", "excel", str(dest), df)
    return _df_to_response(ds_id, file.filename or "upload.xlsx", df)


@router.post("/db", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_from_db(
    body: UploadDBRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Connect to an external database and import a table as a dataset.
    Provide a SQLAlchemy-compatible connection string, e.g.:
      postgresql://user:pass@localhost:5432/mydb
    """
    try:
        import sqlalchemy as sa
        ext_engine = sa.create_engine(body.connection_string)
        with ext_engine.connect() as conn:
            df = pd.read_sql_table(body.table_name, con=conn)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not connect or read table '{body.table_name}': {exc}",
        )

    name = body.dataset_name or f"{body.table_name}_import"
    ds_id = await _save_dataset(db, name, "db", None, df)
    return _df_to_response(ds_id, name, df)
