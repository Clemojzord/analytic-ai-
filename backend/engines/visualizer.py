"""
Analytic AI — Visualization Engine
Seaborn + Matplotlib chart generation → base64 PNG
"""
from __future__ import annotations

import base64
import io
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (no display required)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# ── Theme ────────────────────────────────────────────────────
PALETTE = ["#38bdf8", "#2dd4bf", "#a78bfa", "#fbbf24", "#34d399",
           "#fb7185", "#818cf8", "#fb923c", "#22d3ee", "#e879f9"]

sns.set_theme(
    style="dark",
    rc={
        "figure.facecolor": "#0d1424",
        "axes.facecolor":   "#111827",
        "axes.edgecolor":   "#1e293b",
        "axes.labelcolor":  "#94a3b8",
        "text.color":       "#f0f9ff",
        "xtick.color":      "#475569",
        "ytick.color":      "#475569",
        "grid.color":       "#1e293b",
        "grid.linestyle":   "--",
        "grid.alpha":       0.5,
    },
)

CHART_TYPES = ["revenue_trend", "product_pie", "branch_bar", "sales_heatmap", "segment_scatter"]


# ─────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────

def generate_chart(df: pd.DataFrame, chart_type: str) -> dict[str, Any]:
    """
    Generate a chart PNG, return as base64 data URL.
    chart_type: one of CHART_TYPES
    """
    handlers = {
        "revenue_trend": _revenue_trend,
        "product_pie":   _product_pie,
        "branch_bar":    _branch_bar,
        "sales_heatmap": _sales_heatmap,
        "segment_scatter": _segment_scatter,
    }

    if chart_type not in handlers:
        raise ValueError(f"Unknown chart_type '{chart_type}'. Choose from: {CHART_TYPES}")

    fig, title = handlers[chart_type](df)
    data_url = _fig_to_base64(fig)
    plt.close(fig)

    return {
        "chart_type": chart_type,
        "format": "png",
        "data_url": data_url,
        "title": title,
    }


# ─────────────────────────────────────────────────────────────
# Chart implementations
# ─────────────────────────────────────────────────────────────

def _revenue_trend(df: pd.DataFrame):
    """Line chart: revenue over time."""
    date_col = _find_col(df, ["date", "created_at", "transaction_date", "period"])
    rev_col  = _find_numeric_col(df, ["revenue", "sales", "amount", "total", "income"])

    fig, ax = plt.subplots(figsize=(10, 5))

    if date_col and rev_col:
        tmp = df[[date_col, rev_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col]).sort_values(date_col)
        tmp["period"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
        monthly = tmp.groupby("period")[rev_col].sum().reset_index()

        ax.fill_between(monthly["period"], monthly[rev_col], alpha=0.15, color=PALETTE[0])
        ax.plot(monthly["period"], monthly[rev_col], color=PALETTE[0], linewidth=2.5, marker="o", markersize=5)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"KES {x:,.0f}"))
        ax.set_xlabel("Month", labelpad=10)
        ax.set_ylabel("Revenue (KES)", labelpad=10)
    else:
        # Fallback: plot first numeric column
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            ax.plot(df[num_cols[0]].values, color=PALETTE[0], linewidth=2)

    title = "Revenue Trend"
    ax.set_title(title, color="#f0f9ff", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout()
    return fig, title


def _product_pie(df: pd.DataFrame):
    """Pie chart: revenue by product."""
    product_col = _find_col(df, ["product", "item", "sku", "name", "description"])
    rev_col     = _find_numeric_col(df, ["revenue", "sales", "amount", "total"])

    fig, ax = plt.subplots(figsize=(8, 8), facecolor="#0d1424")
    ax.set_facecolor("#0d1424")

    if product_col and rev_col:
        data = df.groupby(product_col)[rev_col].sum().sort_values(ascending=False).head(8)
        wedges, texts, autotexts = ax.pie(
            data.values,
            labels=data.index,
            autopct="%1.1f%%",
            colors=PALETTE[:len(data)],
            pctdistance=0.82,
            startangle=140,
            wedgeprops={"edgecolor": "#0d1424", "linewidth": 2},
        )
        for t in texts: t.set_color("#94a3b8")
        for a in autotexts: a.set_color("#f0f9ff"); a.set_fontweight("bold")
    else:
        ax.text(0.5, 0.5, "No product/revenue columns found",
                ha="center", va="center", color="#94a3b8", transform=ax.transAxes)

    title = "Product Revenue Distribution"
    ax.set_title(title, color="#f0f9ff", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout()
    return fig, title


def _branch_bar(df: pd.DataFrame):
    """Horizontal bar chart: revenue by branch."""
    branch_col = _find_col(df, ["branch", "location", "store", "region", "outlet"])
    rev_col    = _find_numeric_col(df, ["revenue", "sales", "amount", "total"])

    fig, ax = plt.subplots(figsize=(10, 6))

    if branch_col and rev_col:
        data = df.groupby(branch_col)[rev_col].sum().sort_values().tail(10)
        bars = ax.barh(data.index, data.values, color=PALETTE[:len(data)], height=0.6)
        ax.bar_label(bars, labels=[f"KES {v:,.0f}" for v in data.values],
                     padding=6, color="#94a3b8", fontsize=9)
        ax.set_xlabel("Revenue (KES)", labelpad=10)
    else:
        ax.text(0.5, 0.5, "No branch/revenue columns found",
                ha="center", va="center", color="#94a3b8", transform=ax.transAxes)

    title = "Branch Performance"
    ax.set_title(title, color="#f0f9ff", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout()
    return fig, title


def _sales_heatmap(df: pd.DataFrame):
    """Heatmap: sales amount by weekday × hour (or pivot of top 2 categorical cols)."""
    date_col = _find_col(df, ["date", "created_at", "transaction_date"])
    rev_col  = _find_numeric_col(df, ["revenue", "sales", "amount", "total"])

    fig, ax = plt.subplots(figsize=(12, 5))

    if date_col and rev_col:
        tmp = df[[date_col, rev_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col])
        tmp["weekday"] = tmp[date_col].dt.day_name()
        tmp["hour"]    = tmp[date_col].dt.hour

        pivot = tmp.pivot_table(
            index="weekday", columns="hour", values=rev_col, aggfunc="sum", fill_value=0
        )
        day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        pivot = pivot.reindex([d for d in day_order if d in pivot.index])

        sns.heatmap(
            pivot, ax=ax,
            cmap=sns.color_palette("Blues", as_cmap=True),
            linewidths=0.3, linecolor="#0d1424",
            fmt=".0f", annot=len(pivot) <= 7,
            cbar_kws={"shrink": 0.8}
        )
        ax.set_xlabel("Hour of Day", labelpad=10)
        ax.set_ylabel("Weekday", labelpad=10)
    else:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if len(num_cols) >= 2:
            corr = df[num_cols].corr()
            sns.heatmap(corr, ax=ax, annot=True, fmt=".2f",
                        cmap="coolwarm", linewidths=0.5)
        else:
            ax.text(0.5, 0.5, "Insufficient time/numeric data for heatmap",
                    ha="center", va="center", color="#94a3b8", transform=ax.transAxes)

    title = "Sales Heatmap (Weekday × Hour)"
    ax.set_title(title, color="#f0f9ff", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout()
    return fig, title


def _segment_scatter(df: pd.DataFrame):
    """Scatter: customer segmentation by purchase value vs frequency."""
    client_col = _find_col(df, ["client", "customer", "customer_id", "client_id"])
    rev_col    = _find_numeric_col(df, ["revenue", "sales", "amount", "total"])

    fig, ax = plt.subplots(figsize=(10, 6))

    if client_col and rev_col:
        stats = df.groupby(client_col)[rev_col].agg(["sum", "count"]).reset_index()
        stats.columns = ["client", "total_spend", "frequency"]

        sc = ax.scatter(
            stats["frequency"], stats["total_spend"],
            c=stats["total_spend"],
            cmap="plasma", alpha=0.7, s=60,
            edgecolors="none"
        )
        plt.colorbar(sc, ax=ax, label="Total Spend (KES)")
        ax.set_xlabel("Purchase Frequency", labelpad=10)
        ax.set_ylabel("Total Spend (KES)", labelpad=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"KES {x:,.0f}"))
    else:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if len(num_cols) >= 2:
            ax.scatter(df[num_cols[0]], df[num_cols[1]], alpha=0.5, color=PALETTE[0], s=40)
            ax.set_xlabel(num_cols[0], labelpad=10)
            ax.set_ylabel(num_cols[1], labelpad=10)
        else:
            ax.text(0.5, 0.5, "No customer/revenue data for segmentation",
                    ha="center", va="center", color="#94a3b8", transform=ax.transAxes)

    title = "Customer Segmentation"
    ax.set_title(title, color="#f0f9ff", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout()
    return fig, title


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{b64}"


def _find_col(df: pd.DataFrame, keywords: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for kw in keywords:
        for lc, orig in cols_lower.items():
            if kw in lc:
                return orig
    return None


def _find_numeric_col(df: pd.DataFrame, keywords: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for kw in keywords:
        for lc, orig in cols_lower.items():
            if kw in lc and pd.api.types.is_numeric_dtype(df[orig]):
                return orig
    return None
