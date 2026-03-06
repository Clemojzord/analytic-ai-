import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_forecast_missing_dataset_requires_analytics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Request a forecast for a non-existent dataset ID
        response = await ac.get("/forecast/9999?periods=3")
    
    # Since dataset 9999 has no KPI Snapshot computed, we expect a 400 bad request error.
    assert response.status_code == 400
    assert "Analytics must be computed first" in response.json()["detail"]
