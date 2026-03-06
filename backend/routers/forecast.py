from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
from sklearn.linear_model import LinearRegression

from core.database import get_db
from models.dataset import KPISnapshot

router = APIRouter(prefix="/forecast", tags=["Forecasting"])

@router.get("/{dataset_id}")
async def get_forecast(dataset_id: int, periods: int = 3, db: AsyncSession = Depends(get_db)):
    """
    Generates a generic Time-Series Forecast (e.g. next N periods of revenue)
    using simple Machine Learning (Linear Regression over historical metrics) 
    based on the computed analytics engine KPIs.
    """
    result = await db.execute(select(KPISnapshot).where(KPISnapshot.dataset_id == dataset_id))
    snap = result.scalar_one_or_none()
    
    if not snap or not snap.monthly_data:
        raise HTTPException(
            status_code=400, 
            detail="Analytics must be computed first to generate a forecast."
        )
        
    # Extract historical revenue data for the forecast
    revenues = [item["revenue"] for item in snap.monthly_data if "revenue" in item]
    if len(revenues) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Not enough historical monthly data (requires at least 3 periods) to forecast reliably."
        )
        
    # Fit Linear Regression Model
    X = np.arange(len(revenues)).reshape(-1, 1)
    y = np.array(revenues)
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict over the requested future periods
    future_X = np.arange(len(revenues), len(revenues) + periods).reshape(-1, 1)
    predictions = model.predict(future_X)
    
    forecasts = []
    # If original periods exist, we could try parsing dates. For simplicity, we just return stepwise prediction.
    last_period_name = snap.monthly_data[-1].get("period", f"Period {len(revenues)}")
    
    for i, pred in enumerate(predictions):
        forecasts.append({
            "step": i + 1,
            "period_label": f"Future +{i+1} after {last_period_name}",
            "forecasted_revenue": max(0, float(pred))  # floor at 0
        })
        
    return {
        "dataset_id": dataset_id,
        "historical_periods": len(revenues),
        "forecast_periods": periods,
        "forecast": forecasts
    }
