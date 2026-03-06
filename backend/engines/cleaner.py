"""
Analytic AI — Data Cleaning Engine
Pandas-powered automated cleaning pipeline
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run the full auto-cleaning pipeline on a DataFrame.
    Returns (cleaned_df, report_dict).
    """
    report: dict[str, Any] = {
        "rows_before": len(df),
        "duplicates_removed": 0,
        "nulls_filled": 0,
        "outliers_flagged": 0,
        "columns_renamed": {},
        "type_conversions": {},
    }

    # 1. Normalize column names
    df, report["columns_renamed"] = _normalize_columns(df)

    # 2. Remove entirely blank rows
    blank_before = len(df)
    df = df.dropna(how="all")
    report["blank_rows_removed"] = blank_before - len(df)

    # 3. Remove duplicates
    dup_before = len(df)
    df = df.drop_duplicates()
    report["duplicates_removed"] = dup_before - len(df)

    # 4. Infer and convert data types
    df, report["type_conversions"] = _infer_types(df)

    # 5. Fill missing values
    df, report["nulls_filled"] = _fill_missing(df)

    # 6. Outlier detection (IQR) — flag, don't drop
    df, report["outliers_flagged"] = _flag_outliers(df)

    # 7. Currency / KES normalization
    df = _normalize_currency(df)

    report["rows_after"] = len(df)
    report["rows_removed"] = report["rows_before"] - report["rows_after"]

    return df, report


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Lowercase column names, replace spaces/special chars with underscores."""
    rename_map: dict[str, str] = {}
    new_cols: list[str] = []

    for col in df.columns:
        clean = str(col).strip().lower()
        clean = re.sub(r"[^a-z0-9]+", "_", clean)
        clean = re.sub(r"_+", "_", clean).strip("_")
        if clean != col:
            rename_map[col] = clean
        new_cols.append(clean)

    df.columns = new_cols
    return df, rename_map


def _infer_types(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Try to cast columns to a more specific dtype."""
    conversions: dict[str, str] = {}

    for col in df.columns:
        original_dtype = str(df[col].dtype)

        # Skip already numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        # Try datetime
        if any(kw in col for kw in ("date", "time", "created", "updated", "period")):
            try:
                df[col] = pd.to_datetime(df[col], errors="raise")
                conversions[col] = f"{original_dtype} → datetime"
                continue
            except Exception:
                pass

        # Try numeric — strip common currency symbols
        series_str = df[col].astype(str).str.replace(r"[KES,\$£€\s]", "", regex=True)
        try:
            numeric = pd.to_numeric(series_str, errors="raise")
            df[col] = numeric
            conversions[col] = f"{original_dtype} → float"
            continue
        except (ValueError, TypeError):
            pass

        # Categorize low-cardinality strings
        if df[col].nunique() / max(len(df), 1) < 0.05:
            df[col] = df[col].astype("category")
            conversions[col] = f"{original_dtype} → category"

    return df, conversions


def _fill_missing(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Fill NaN values: median for numeric, 'Unknown' for categorical/object."""
    total_filled = 0

    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count == 0:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
        else:
            df[col] = df[col].fillna("Unknown")

        total_filled += null_count

    return df, int(total_filled)


def _flag_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    IQR method: flag outliers with a boolean '_outlier_<col>' column.
    Also adds Z-score flag for numeric columns > 3 std deviations.
    """
    flagged_total = 0
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        # IQR
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        # Z-score
        z_scores = np.abs((df[col] - df[col].mean()) / (df[col].std() + 1e-9))

        outlier_mask = (df[col] < lower) | (df[col] > upper) | (z_scores > 3)
        count = int(outlier_mask.sum())

        if count > 0:
            df[f"_outlier_{col}"] = outlier_mask
            flagged_total += count

    return df, flagged_total


def _normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Round all float columns to 2 decimal places (KES standard)."""
    for col in df.select_dtypes(include=[float, np.floating]).columns:
        if col.startswith("_outlier_"):
            continue
        df[col] = df[col].round(2)
    return df


def load_file(file_path: Path) -> pd.DataFrame:
    """Load CSV or Excel file into a DataFrame."""
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def save_cleaned(df: pd.DataFrame, output_path: Path) -> Path:
    """Save cleaned DataFrame to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
