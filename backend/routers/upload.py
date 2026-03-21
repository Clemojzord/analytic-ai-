"""
Analytic AI — Upload Router
POST /upload — CSV/Excel file upload
"""
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.storage import upload_file_to_r2
from models.dataset import Dataset
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CSV or Excel file. Saves it to R2 storage and creates a Dataset record.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # Accept common data file extensions (relaxed for mobile uploads)
    ext = Path(file.filename).suffix.lower()
    allowed = {".csv", ".xlsx", ".xls", ".tsv"}
    if ext not in allowed:
        # Try MIME type fallback
        mime = (file.content_type or "").lower()
        if "csv" not in mime and "excel" not in mime and "spreadsheet" not in mime:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(allowed)}",
            )

    # Generate unique remote filename
    unique_id = uuid.uuid4().hex
    remote_name = f"{unique_id}{ext or '.csv'}"

    # Save locally first for row counting
    content = await file.read()
    local_path = settings.upload_dir / remote_name
    local_path.write_bytes(content)

    # Quick parse to get metadata
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(local_path)
        else:
            import io
            # Robust CSV reading (same logic as storage.py)
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(
                        io.BytesIO(content),
                        encoding=encoding,
                        sep=None,
                        engine="python",
                        on_bad_lines="skip",
                    )
                    if not df.empty:
                        break
                except Exception:
                    continue
            else:
                df = pd.DataFrame()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=422, detail="File appears to be empty or unparseable.")

    # Upload to R2
    try:
        await file.seek(0)  # reset for re-read
    except Exception:
        pass

    try:
        # Upload raw bytes directly
        import boto3, io
        from core.storage import get_s3_client
        s3 = get_s3_client()
        if s3:
            s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=remote_name,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
            )
    except Exception as exc:
        print(f"DIAGNOSTIC: R2 upload failed: {exc}. Dataset saved locally only.")

    # Create Dataset record
    ds = Dataset(
        user_id=current_user.id,
        name=file.filename,
        file_path=remote_name,
        status="uploaded",
        row_count=len(df),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)

    return {
        "dataset_id": ds.id,
        "filename": file.filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "message": f"Uploaded '{file.filename}' — {len(df)} rows, {len(df.columns)} columns.",
    }
