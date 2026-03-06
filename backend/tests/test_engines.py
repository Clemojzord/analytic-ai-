"""
Analytic AI — Test Suite

Run:  cd backend && pytest tests/ -v
"""
import io
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add backend root to import path
sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_CSV = Path(__file__).parent / "sample_sales.csv"


# ─────────────────────────────────────────────────────────────
# Engine: Cleaner
# ─────────────────────────────────────────────────────────────

class TestCleaner:
    def _load(self) -> pd.DataFrame:
        return pd.read_csv(SAMPLE_CSV)

    def test_normalize_columns(self):
        from engines.cleaner import clean_dataframe
        df = self._load()
        df.columns = ["Date", "Product Name", "Branch/Store", "Revenue KES", "Cost KES", "Qty", "Customer ID"]
        cleaned, report = clean_dataframe(df)
        for col in cleaned.columns:
            assert " " not in col, f"Column '{col}' still has spaces"
            assert col == col.lower(), f"Column '{col}' is not lowercase"

    def test_removes_duplicates(self):
        from engines.cleaner import clean_dataframe
        df = self._load()
        df = pd.concat([df, df.iloc[:3]], ignore_index=True)
        cleaned, report = clean_dataframe(df)
        assert report["duplicates_removed"] >= 3

    def test_fills_nulls(self):
        from engines.cleaner import clean_dataframe
        df = self._load()
        df.loc[0, "revenue"] = None
        df.loc[1, "product"] = None
        cleaned, report = clean_dataframe(df)
        assert report["nulls_filled"] >= 2
        assert cleaned["product"].isna().sum() == 0

    def test_outlier_flagging(self):
        from engines.cleaner import clean_dataframe
        df = self._load()
        df.loc[0, "revenue"] = 999_999.99  # obvious outlier
        cleaned, report = clean_dataframe(df)
        assert report["outliers_flagged"] >= 1

    def test_rows_preserved(self):
        from engines.cleaner import clean_dataframe
        df = self._load()
        cleaned, report = clean_dataframe(df)
        assert report["rows_after"] <= report["rows_before"]
        assert report["rows_after"] > 0


# ─────────────────────────────────────────────────────────────
# Engine: Analytics
# ─────────────────────────────────────────────────────────────

class TestAnalytics:
    def _load(self) -> pd.DataFrame:
        from engines.cleaner import clean_dataframe
        df = pd.read_csv(SAMPLE_CSV)
        cleaned, _ = clean_dataframe(df)
        return cleaned

    def test_total_revenue_positive(self):
        from engines.analytics import compute_kpis
        df = self._load()
        kpis = compute_kpis(df)
        assert "total_revenue" in kpis
        assert kpis["total_revenue"] > 0

    def test_profit_margin_in_range(self):
        from engines.analytics import compute_kpis
        df = self._load()
        kpis = compute_kpis(df)
        if "profit_margin_pct" in kpis:
            assert -100 <= kpis["profit_margin_pct"] <= 100

    def test_monthly_revenue_sorted(self):
        from engines.analytics import compute_kpis
        df = self._load()
        kpis = compute_kpis(df)
        periods = [m["period"] for m in kpis.get("monthly_revenue", [])]
        assert periods == sorted(periods)

    def test_top_product_is_string(self):
        from engines.analytics import compute_kpis
        df = self._load()
        kpis = compute_kpis(df)
        if "top_product" in kpis:
            assert isinstance(kpis["top_product"], str)
            assert len(kpis["top_product"]) > 0

    def test_clv_positive(self):
        from engines.analytics import compute_kpis
        df = self._load()
        kpis = compute_kpis(df)
        if "estimated_clv_annual" in kpis:
            assert kpis["estimated_clv_annual"] > 0


# ─────────────────────────────────────────────────────────────
# Engine: Insights
# ─────────────────────────────────────────────────────────────

class TestInsights:
    def _get_insights(self) -> dict:
        from engines.analytics import compute_kpis
        from engines.cleaner import clean_dataframe
        from engines.insight_gen import generate_insights
        df = pd.read_csv(SAMPLE_CSV)
        cleaned, _ = clean_dataframe(df)
        kpis = compute_kpis(cleaned)
        return generate_insights(kpis)

    def test_insights_list_not_empty(self):
        result = self._get_insights()
        assert len(result["insights"]) > 0

    def test_executive_summary_not_empty(self):
        result = self._get_insights()
        assert len(result["executive_summary"]) > 50

    def test_severity_values_valid(self):
        result = self._get_insights()
        valid = {"info", "warning", "critical"}
        for i in result["insights"]:
            assert i["severity"] in valid, f"Invalid severity: {i['severity']}"

    def test_zero_revenue_triggers_critical(self):
        from engines.insight_gen import generate_insights
        kpis = {"total_revenue": 0, "total_records": 10}
        result = generate_insights(kpis)
        sevs = [i["severity"] for i in result["insights"]]
        assert "critical" in sevs


# ─────────────────────────────────────────────────────────────
# Smoke: Visualization
# ─────────────────────────────────────────────────────────────

class TestVisualizer:
    def _load(self) -> pd.DataFrame:
        from engines.cleaner import clean_dataframe
        df = pd.read_csv(SAMPLE_CSV)
        cleaned, _ = clean_dataframe(df)
        return cleaned

    def test_revenue_trend_returns_base64(self):
        from engines.visualizer import generate_chart
        df = self._load()
        result = generate_chart(df, "revenue_trend")
        assert result["data_url"].startswith("data:image/png;base64,")
        assert len(result["data_url"]) > 1000

    def test_product_pie_returns_base64(self):
        from engines.visualizer import generate_chart
        df = self._load()
        result = generate_chart(df, "product_pie")
        assert "data_url" in result

    def test_invalid_chart_type_raises(self):
        from engines.visualizer import generate_chart
        df = self._load()
        with pytest.raises(ValueError, match="Unknown chart_type"):
            generate_chart(df, "nonexistent_chart")
