"""
Analytic AI — Cloudflare R2 Storage Integration
"""
import io
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from core.config import settings

# Initialize Boto3 S3 Client for Cloudflare R2
def get_s3_client():
    if not settings.R2_ACCOUNT_ID:
        # Prevent crashing if credentials aren't loaded yet
        return None
    
    return boto3.client(
        's3',
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


async def upload_file_to_r2(file: UploadFile, remote_filename: str) -> str:
    """Uploads a FastAPI UploadFile to R2 Storage and returns the public URL/path."""
    s3 = get_s3_client()
    if not s3:
        raise ValueError("R2 Storage client is not configured.")

    content = await file.read()
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=remote_filename,
        Body=content,
        ContentType=file.content_type or 'application/octet-stream'
    )
    
    return remote_filename


def download_dataframe_from_r2(remote_filename: str) -> pd.DataFrame:
    """Downloads a CSV or Excel file from R2 into a Pandas DataFrame."""
    s3 = get_s3_client()
    if not s3:
        print("DIAGNOSTIC: R2 client initialization FAILED (missing credentials)")
        raise ValueError("R2 Storage client is not configured.")
    
    # Diagnostic: Log client details safely
    print(f"DIAGNOSTIC: Attempting download from R2 Bucket: {settings.R2_BUCKET_NAME}, Key: {remote_filename}")
    print(f"DIAGNOSTIC: S3 Client Endpoint: {s3._endpoint}")

    try:
        response = s3.get_object(Bucket=settings.R2_BUCKET_NAME, Key=remote_filename)
        content = response['Body'].read()
    except Exception as e:
        print(f"DIAGNOSTIC: R2 download failed with error: {str(e)}")
        raise

    if remote_filename.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(io.BytesIO(content))
    
    # Enhanced robust CSV parsing
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']
    delimiters = [None, ',', ';', '\t', '|', ':']
    
    for sep in delimiters:
        for encoding in encodings:
            try:
                # Use a new BytesIO for each attempt
                buffer = io.BytesIO(content)
                df = pd.read_csv(
                    buffer,
                    encoding=encoding,
                    sep=sep,
                    engine='python' if sep is None else 'c',
                    on_bad_lines='skip',
                    skip_blank_lines=True,
                    low_memory=False
                )
                if not df.empty:
                    print(f"DIAGNOSTIC: Successfully parsed CSV with sep='{sep}', encoding='{encoding}'")
                    return df
            except Exception:
                continue
    
    # Final fallback for extremely broken files
    try:
        print("DIAGNOSTIC: All standard CSV parsing failed. Attempting broad fallback.")
        return pd.read_csv(
            io.BytesIO(content), 
            on_bad_lines='skip', 
            encoding_errors='replace',
            sep=None,
            engine='python'
        )
    except Exception as e:
        print(f"DIAGNOSTIC: Final CSV fallback failed: {e}")
        raise ValueError(f"Failed to parse file even with all fallback methods: {e}")


def upload_dataframe_to_r2(df: pd.DataFrame, remote_filename: str, file_format: str = 'csv') -> str:
    """Uploads a Pandas DataFrame directly to R2 Storage."""
    s3 = get_s3_client()
    if not s3:
        raise ValueError("R2 Storage client is not configured.")

    buffer = io.BytesIO()
    
    if file_format == 'csv':
        df.to_csv(buffer, index=False)
        content_type = 'text/csv'
    elif file_format == 'xlsx':
        df.to_excel(buffer, index=False)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'xlsx'.")
    
    buffer.seek(0)
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=remote_filename,
        Body=buffer.getvalue(),
        ContentType=content_type
    )
    
    return remote_filename


def get_r2_file_url(remote_filename: str) -> str:
    """Returns a short-lived signed URL for downloading a file from R2."""
    s3 = get_s3_client()
    if not s3:
        raise ValueError("R2 Storage client is not configured.")

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.R2_BUCKET_NAME, 'Key': remote_filename},
            ExpiresIn=3600
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return ""
