"""
Analytic AI — Automated Insight Generator
Rule-based engine that writes human-readable business insights
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def generate_insights(kpis: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a list of insight items and an executive summary
    from the KPI dictionary produced by the analytics engine.
    """
    insights: list[dict[str, Any]] = []

    _revenue_insights(kpis, insights)
    _profit_insights(kpis, insights)
    _growth_insights(kpis, insights)
    _product_insights(kpis, insights)
    _customer_insights(kpis, insights)
    _inventory_insights(kpis, insights)

    summary = _build_executive_summary(kpis, insights)

    return {
        "insights": insights,
        "executive_summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Rule functions
# ─────────────────────────────────────────────────────────────

def _revenue_insights(kpis: dict, out: list) -> None:
    rev = kpis.get("total_revenue")
    if rev is None:
        return

    if rev == 0:
        out.append(_insight(
            "revenue", "critical",
            "Total revenue is KES 0. Verify the data contains a revenue/sales column.",
            metric="total_revenue", value=0,
        ))
    elif rev < 10_000:
        out.append(_insight(
            "revenue", "warning",
            f"Total revenue is low at KES {rev:,.2f}. "
            "This may reflect a very short time period or limited transactions.",
            metric="total_revenue", value=rev,
        ))
    else:
        out.append(_insight(
            "revenue", "info",
            f"Total revenue stands at KES {rev:,.2f}.",
            metric="total_revenue", value=rev,
        ))


def _profit_insights(kpis: dict, out: list) -> None:
    margin = kpis.get("profit_margin_pct")
    if margin is None:
        return

    if margin < 0:
        out.append(_insight(
            "profitability", "critical",
            f"The business is currently operating at a loss — profit margin is {margin:.1f}%. "
            "Immediate action needed: review COGS and operating expenses.",
            metric="profit_margin_pct", value=margin,
        ))
    elif margin < 10:
        out.append(_insight(
            "profitability", "warning",
            f"Profit margin is tight at {margin:.1f}%. "
            "Consider renegotiating supplier costs or revising pricing strategy.",
            metric="profit_margin_pct", value=margin,
        ))
    elif margin < 20:
        out.append(_insight(
            "profitability", "info",
            f"Profit margin is healthy at {margin:.1f}%. "
            "Room exists to invest in marketing to grow top-line revenue.",
            metric="profit_margin_pct", value=margin,
        ))
    else:
        out.append(_insight(
            "profitability", "info",
            f"Strong profit margin of {margin:.1f}%. "
            "The business is operating efficiently. Consider reinvesting surplus into expansion.",
            metric="profit_margin_pct", value=margin,
        ))


def _growth_insights(kpis: dict, out: list) -> None:
    growth = kpis.get("mom_growth_rate_pct")
    monthly = kpis.get("monthly_revenue", [])
    if growth is None:
        return

    if growth < -15:
        last = monthly[-1]["period"] if monthly else "this month"
        out.append(_insight(
            "growth", "critical",
            f"Revenue dropped sharply by {abs(growth):.1f}% in {last} vs the prior month. "
            "This is a red-flag decline — investigate cause immediately (seasonal drop, lost client, competitor?)",
            metric="mom_growth_rate_pct", value=growth,
        ))
    elif growth < -5:
        out.append(_insight(
            "growth", "warning",
            f"Revenue declined {abs(growth):.1f}% month-over-month. "
            "Consider revising marketing spend or running a promotional campaign.",
            metric="mom_growth_rate_pct", value=growth,
        ))
    elif growth < 0:
        out.append(_insight(
            "growth", "warning",
            f"Slight revenue dip of {abs(growth):.1f}% month-over-month. "
            "Monitor closely over the next 2–3 months before taking action.",
            metric="mom_growth_rate_pct", value=growth,
        ))
    elif growth > 20:
        out.append(_insight(
            "growth", "info",
            f"Excellent growth of {growth:.1f}% month-over-month! "
            "Identify which product/branch is driving this surge and double down on it.",
            metric="mom_growth_rate_pct", value=growth,
        ))
    else:
        out.append(_insight(
            "growth", "info",
            f"Steady growth of {growth:.1f}% month-over-month. "
            "The business is on a positive trajectory.",
            metric="mom_growth_rate_pct", value=growth,
        ))


def _product_insights(kpis: dict, out: list) -> None:
    top = kpis.get("top_product")
    breakdown = kpis.get("product_revenue_breakdown", {})

    if top and breakdown:
        total = sum(breakdown.values())
        top_pct = (breakdown.get(top, 0) / total * 100) if total else 0
        out.append(_insight(
            "products", "info",
            f"Top performing product is «{top}» contributing {top_pct:.1f}% of total revenue.",
            metric="top_product_share_pct", value=round(top_pct, 2),
        ))

        # Revenue concentration risk
        if top_pct > 60:
            out.append(_insight(
                "products", "warning",
                f"High revenue concentration risk — «{top}» accounts for over 60% of sales. "
                "Diversify your product portfolio to reduce dependency.",
                metric="concentration_risk_pct", value=round(top_pct, 2),
            ))

    top_branch = kpis.get("top_branch")
    branch_bd  = kpis.get("branch_revenue_breakdown", {})
    if top_branch and branch_bd:
        total = sum(branch_bd.values())
        branch_pct = (branch_bd.get(top_branch, 0) / total * 100) if total else 0
        out.append(_insight(
            "branches", "info",
            f"Best performing branch: «{top_branch}» with {branch_pct:.1f}% of total revenue.",
            metric="top_branch_share_pct", value=round(branch_pct, 2),
        ))


def _customer_insights(kpis: dict, out: list) -> None:
    clv = kpis.get("estimated_clv_annual")
    unique = kpis.get("unique_clients")

    if clv is not None:
        out.append(_insight(
            "customers", "info",
            f"Estimated annual Customer Lifetime Value (CLV): KES {clv:,.2f}. "
            "Focus retention efforts on high-CLV customers to maximize long-term revenue.",
            metric="estimated_clv_annual", value=clv,
        ))

    if unique is not None and unique < 10:
        out.append(_insight(
            "customers", "warning",
            f"Only {unique} unique customers detected. "
            "A very small customer base creates revenue concentration risk — invest in customer acquisition.",
            metric="unique_clients", value=unique,
        ))


def _inventory_insights(kpis: dict, out: list) -> None:
    turnover = kpis.get("inventory_turnover")
    if turnover is None:
        return

    if turnover < 2:
        out.append(_insight(
            "inventory", "warning",
            f"Inventory turnover rate is low at {turnover:.2f}×. "
            "Stock may be moving slowly — consider discounting slow-moving items.",
            metric="inventory_turnover", value=turnover,
        ))
    elif turnover > 10:
        out.append(_insight(
            "inventory", "info",
            f"High inventory turnover of {turnover:.2f}× — products are selling fast. "
            "Ensure stock replenishment cycles can keep up with demand.",
            metric="inventory_turnover", value=turnover,
        ))
    else:
        out.append(_insight(
            "inventory", "info",
            f"Healthy inventory turnover of {turnover:.2f}×.",
            metric="inventory_turnover", value=turnover,
        ))


# ─────────────────────────────────────────────────────────────
# Executive Summary Builder
# ─────────────────────────────────────────────────────────────

def _build_executive_summary(kpis: dict, insights: list) -> str:
    lines: list[str] = ["📊 **Executive Summary — Analytic AI**\n"]

    rev     = kpis.get("total_revenue")
    margin  = kpis.get("profit_margin_pct")
    growth  = kpis.get("mom_growth_rate_pct")
    top     = kpis.get("top_product")
    records = kpis.get("total_records", 0)

    lines.append(f"Analysis based on **{records:,} transactions**.\n")

    if rev is not None:
        lines.append(f"- **Total Revenue**: KES {rev:,.2f}")
    if margin is not None:
        sentiment = "strong" if margin > 15 else "moderate" if margin > 5 else "low"
        lines.append(f"- **Profit Margin**: {margin:.1f}% ({sentiment})")
    if growth is not None:
        direction = "⬆ up" if growth >= 0 else "⬇ down"
        lines.append(f"- **Month-on-Month Growth**: {direction} {abs(growth):.1f}%")
    if top:
        lines.append(f"- **Top Product**: {top}")

    criticals = [i for i in insights if i["severity"] == "critical"]
    warnings  = [i for i in insights if i["severity"] == "warning"]

    if criticals:
        lines.append(f"\n⚠️ **{len(criticals)} critical issue(s)** require immediate attention.")
    if warnings:
        lines.append(f"🔔 **{len(warnings)} warning(s)** flagged for review.")

    if not criticals and not warnings:
        lines.append("\n✅ Business metrics look healthy. Keep monitoring for sustained growth.")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────

def _insight(category: str, severity: str, text: str,
             metric: str | None = None, value: float | None = None) -> dict:
    return {
        "category": category,
        "severity": severity,
        "text": text,
        "metric": metric,
        "value": value,
    }
