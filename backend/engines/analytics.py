"""
Analytic AI — Analytical Engine
NumPy-powered KPI calculations for retail & service businesses
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute all KPIs automatically from a cleaned DataFrame.
    Returns a dictionary of KPI values.
    """
    kpis: dict[str, Any] = {}

    revenue_col = _detect_column(df, ["revenue", "sales", "amount", "total", "income"])
    cost_col    = _detect_column(df, ["cost", "cogs", "expense", "expenditure"])
    profit_col  = _detect_column(df, ["profit", "net_profit", "gross_profit"])
    product_col = _detect_column(df, ["product", "item", "sku", "name", "description"])
    branch_col  = _detect_column(df, ["branch", "location", "store", "region", "outlet"])
    date_col    = _detect_column(df, ["date", "created_at", "transaction_date", "period"])
    qty_col     = _detect_column(df, ["quantity", "qty", "units", "volume"])
    client_col  = _detect_column(df, ["client", "customer", "customer_id", "client_id"])

    # ── Revenue KPIs ─────────────────────────────────────────
    if revenue_col:
        rev_arr = df[revenue_col].dropna().to_numpy(dtype=float)
        kpis["total_revenue"] = round(float(np.sum(rev_arr)), 2)
        kpis["avg_transaction_value"] = round(float(np.mean(rev_arr)), 2)
        kpis["median_transaction_value"] = round(float(np.median(rev_arr)), 2)
        kpis["revenue_std"] = round(float(np.std(rev_arr)), 2)

    # ── Profit Margin ────────────────────────────────────────
    if revenue_col and cost_col:
        total_rev  = float(np.sum(df[revenue_col].dropna().to_numpy(dtype=float)))
        total_cost = float(np.sum(df[cost_col].dropna().to_numpy(dtype=float)))
        net_profit = total_rev - total_cost
        kpis["total_cost"] = round(total_cost, 2)
        kpis["net_profit"] = round(net_profit, 2)
        kpis["profit_margin_pct"] = round((net_profit / total_rev * 100) if total_rev else 0, 2)
    elif profit_col and revenue_col:
        total_rev    = float(np.sum(df[revenue_col].dropna().to_numpy(dtype=float)))
        total_profit = float(np.sum(df[profit_col].dropna().to_numpy(dtype=float)))
        kpis["net_profit"] = round(total_profit, 2)
        kpis["profit_margin_pct"] = round((total_profit / total_rev * 100) if total_rev else 0, 2)

    # ── Monthly Revenue + Growth Rate ────────────────────────
    if revenue_col and date_col:
        monthly = _monthly_revenue(df, date_col, revenue_col)
        kpis["monthly_revenue"] = monthly

        if len(monthly) >= 2:
            vals   = [m["revenue"] for m in monthly]
            curr, prev = vals[-1], vals[-2]
            growth = ((curr - prev) / prev * 100) if prev else 0
            kpis["mom_growth_rate_pct"] = round(growth, 2)

            # Overall CAGR-style if enough months
            if len(vals) >= 3:
                n = len(vals) - 1
                kpis["avg_monthly_growth_pct"] = round(
                    float(np.mean(np.diff(vals) / np.maximum(vals[:-1], 1) * 100)), 2
                )

    # ── Best Selling Product ─────────────────────────────────
    if product_col and revenue_col:
        top = df.groupby(product_col)[revenue_col].sum().idxmax()
        top_rev = df.groupby(product_col)[revenue_col].sum().max()
        kpis["top_product"] = str(top)
        kpis["top_product_revenue"] = round(float(top_rev), 2)
        kpis["product_revenue_breakdown"] = (
            df.groupby(product_col)[revenue_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .round(2)
            .to_dict()
        )

    # ── Top Branch ───────────────────────────────────────────
    if branch_col and revenue_col:
        top_b = df.groupby(branch_col)[revenue_col].sum().idxmax()
        kpis["top_branch"] = str(top_b)
        kpis["branch_revenue_breakdown"] = (
            df.groupby(branch_col)[revenue_col]
            .sum()
            .sort_values(ascending=False)
            .round(2)
            .to_dict()
        )

    # ── Inventory Turnover ───────────────────────────────────
    if qty_col and cost_col:
        total_qty  = float(np.sum(df[qty_col].dropna().to_numpy(dtype=float)))
        avg_cost   = float(np.mean(df[cost_col].dropna().to_numpy(dtype=float)))
        kpis["inventory_turnover"] = round(total_qty / avg_cost if avg_cost else 0, 2)

    # ── CLV Estimate ─────────────────────────────────────────
    if client_col and revenue_col:
        client_stats = df.groupby(client_col)[revenue_col].agg(["sum", "count"])
        avg_purchase = float(client_stats["sum"].mean())
        avg_freq     = float(client_stats["count"].mean())
        # Assume 12-month retention window
        clv = avg_purchase * avg_freq * 12
        kpis["avg_purchase_value"] = round(avg_purchase, 2)
        kpis["avg_purchase_frequency"] = round(avg_freq, 2)
        kpis["estimated_clv_annual"] = round(clv, 2)
        kpis["unique_clients"] = int(df[client_col].nunique())

    # ── General Stats ────────────────────────────────────────
    kpis["total_records"] = len(df)
    kpis["detected_columns"] = {
        "revenue": revenue_col,
        "cost": cost_col,
        "profit": profit_col,
        "product": product_col,
        "branch": branch_col,
        "date": date_col,
        "quantity": qty_col,
        "client": client_col,
    }

    return kpis


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _detect_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    """Find the first column whose name contains any of the keywords."""
    cols_lower = {c.lower(): c for c in df.columns}
    for kw in keywords:
        for col_lower, col_orig in cols_lower.items():
            if kw in col_lower and pd.api.types.is_numeric_dtype(df[col_orig]):
                return col_orig
            if kw in col_lower and not pd.api.types.is_numeric_dtype(df[col_orig]):
                # For non-numeric key columns (product, branch, client)
                if kw in ("product", "item", "sku", "branch", "location", "store",
                          "region", "outlet", "client", "customer"):
                    return col_orig
    return None


def _monthly_revenue(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
) -> list[dict[str, Any]]:
    """Aggregate revenue by calendar month."""
    df2 = df[[date_col, revenue_col]].copy()
    df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
    df2 = df2.dropna(subset=[date_col])
    df2["period"] = df2[date_col].dt.to_period("M").astype(str)
    monthly = (
        df2.groupby("period")[revenue_col]
        .sum()
        .reset_index()
        .rename(columns={revenue_col: "revenue"})
        .sort_values("period")
    )
    monthly["revenue"] = monthly["revenue"].round(2)

    result: list[dict[str, Any]] = []
    prev_rev: float | None = None
    for _, row in monthly.iterrows():
        growth = round((row.revenue - prev_rev) / prev_rev * 100, 2) if prev_rev else None
        result.append({
            "period": row.period,
            "revenue": float(row.revenue),
            "growth_rate": growth,
        })
        prev_rev = row.revenue

    return result
