"""
Analytic AI — Data Cleaning Engine
Pandas-powered modular cleaning pipeline
"""
from __future__ import annotations

import re
from typing import Any, Tuple

import numpy as np
import pandas as pd


class CleaningPipeline:
    """
    A modular data cleaning pipeline that applies multiple steps to a DataFrame.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.rows_before = len(df)
        self.rows_after = 0
        self.duplicates_removed = 0
        self.nulls_filled = 0
        self.outliers_flagged = 0
        self.columns_renamed = {}
        self.type_conversions = {}
        self.warnings = []

    def run(self) -> Tuple[pd.DataFrame, dict]:
        """Execute all cleaning steps in sequence."""
        steps = [
            ("normalize_columns", self._normalize_columns),
            ("remove_duplicates", self._remove_duplicates),
            ("infer_types", self._infer_types),
            ("fill_missing", self._fill_missing),
            ("flag_outliers", self._flag_outliers),
            ("normalize_currency", self._normalize_currency),
        ]

        for step_name, step_func in steps:
            try:
                step_func()
            except Exception as e:
                self.warnings.append(f"Step {step_name} failed: {str(e)}")

        self.rows_after = len(self.df)
        
        report = {
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "rows_removed": self.rows_before - self.rows_after,
            "duplicates_removed": self.duplicates_removed,
            "nulls_filled": self.nulls_filled,
            "outliers_flagged": self.outliers_flagged,
            "columns_renamed": self.columns_renamed,
            "type_conversions": self.type_conversions,
            "warnings": self.warnings,
        }
        return self.df, report

    def _normalize_columns(self):
        """Standardize column names: lowercase, snake_case, alphanumeric."""
        original_cols = self.df.columns.tolist()
        new_cols = []
        for col in original_cols:
            clean = str(col).lower().strip()
            clean = re.sub(r'[^a-z0-9]+', '_', clean)
            clean = re.sub(r'_+', '_', clean).strip('_')
            
            if not clean or clean.isdigit():
                clean = f"column_{original_cols.index(col)}"
            
            base_clean = clean
            counter = 1
            while clean in new_cols:
                clean = f"{base_clean}_{counter}"
                counter += 1
            
            new_cols.append(clean)
            if str(col) != clean:
                self.columns_renamed[str(col)] = clean

        self.df.columns = new_cols

    def _remove_duplicates(self):
        """Remove exact duplicate rows."""
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        self.duplicates_removed = before - len(self.df)

    def _infer_types(self):
        """Attempt to convert object/string columns to more specific types."""
        for col in self.df.columns:
            # Check for object or string types using pandas utility
            if pd.api.types.is_object_dtype(self.df[col]) or pd.api.types.is_string_dtype(self.df[col]):
                # Try datetime (More aggressive)
                if any(kw in col for kw in ("date", "time", "created", "updated", "period")):
                    try:
                        # Try parsing with format='mixed' which is very robust for multi-format columns
                        converted = pd.to_datetime(self.df[col], errors='coerce', format='mixed')
                        
                        non_null_count = int(converted.notnull().sum())
                        if non_null_count >= len(self.df) * 0.4:
                            self.df[col] = converted
                            self.type_conversions[col] = "datetime"
                            continue
                    except Exception:
                        pass

                # Try numeric (Improved Multi-stage)
                try:
                    # Stage 1: Direct numeric conversion
                    converted = pd.to_numeric(self.df[col], errors='coerce')
                    non_null_count = int(converted.notnull().sum())
                    
                    # Stage 2: Clean currency/punctuation
                    if non_null_count < len(self.df) * 0.5:
                        cleaned_series = self.df[col].astype(str).str.replace(r'[^-0-9.]', '', regex=True)
                        cleaned_series = cleaned_series.replace('', np.nan)
                        converted_clean = pd.to_numeric(cleaned_series, errors='coerce')
                        if int(converted_clean.notnull().sum()) > non_null_count:
                            converted = converted_clean
                            non_null_count = int(converted.notnull().sum())

                    if non_null_count > 0 and non_null_count >= len(self.df) * 0.4:
                        self.df[col] = converted
                        self.type_conversions[col] = "float"
                        continue
                except Exception:
                    pass

                # Fallback to category
                unique_count = self.df[col].nunique()
                if unique_count > 0:
                    # Categorical if:
                    # 1. It has repeating values (ratio < 0.8)
                    # 2. AND it's not a high-cardinality text column (like names/IDs)
                    # For small datasets, we must be careful.
                    is_low_cardinality = (unique_count / len(self.df) < 0.8)
                    is_small_set_category = (unique_count < 10 and len(self.df) > unique_count)
                    
                    if is_low_cardinality or is_small_set_category:
                        self.df[col] = self.df[col].astype('category')
                        self.type_conversions[col] = "category"

    def _fill_missing(self):
        """Fill NaN values based on column type."""
        for col in self.df.columns:
            try:
                null_count = int(self.df[col].isnull().sum())
                if null_count == 0:
                    continue
                
                # Explicit type-based filling
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    self.df[col] = self.df[col].fillna(self.df[col].median() if not self.df[col].empty else 0)
                elif pd.api.types.is_datetime64_any_dtype(self.df[col]):
                    # Leave NaT for datetime as it's the standard null for this type
                    pass
                elif isinstance(self.df[col].dtype, pd.CategoricalDtype):
                    if "Unknown" not in self.df[col].cat.categories:
                        self.df[col] = self.df[col].cat.add_categories("Unknown")
                    self.df[col] = self.df[col].fillna("Unknown")
                else:
                    # Catch-all for object/string columns
                    self.df[col] = self.df[col].fillna("Unknown")
                
                self.nulls_filled += null_count
            except Exception as e:
                self.warnings.append(f"Failed to fill NaNs in {col}: {e}")

    def _flag_outliers(self):
        """Identify statistical outliers using IQR & Z-score."""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col.startswith('_'): continue
            try:
                q1 = self.df[col].quantile(0.25)
                q3 = self.df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                
                std = self.df[col].std()
                if std > 0:
                    z_scores = np.abs((self.df[col] - self.df[col].mean()) / std)
                    outlier_mask = (self.df[col] < lower) | (self.df[col] > upper) | (z_scores > 3)
                else:
                    outlier_mask = (self.df[col] < lower) | (self.df[col] > upper)
                
                count = int(outlier_mask.sum())
                if count > 0:
                    self.df[f"_outlier_{col}"] = outlier_mask
                    self.outliers_flagged += count
            except Exception:
                continue

    def _normalize_currency(self):
        """Round numeric columns to 2 decimal places."""
        float_cols = self.df.select_dtypes(include=[float, np.floating]).columns
        for col in float_cols:
            if not col.startswith("_"):
                self.df[col] = self.df[col].round(2)


def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Function interface for the CleaningPipeline."""
    pipeline = CleaningPipeline(df)
    return pipeline.run()
