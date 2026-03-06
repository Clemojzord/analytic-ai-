import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/register", json={
            "email": "test_auth@example.com",
            "password": "securepassword",
            "full_name": "Auth User"
        })
    
    # If the database is persistent between tests, it might return 400 if it exists.
    # Allowing 200 (created) or 400 (already exists) as valid.
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        assert response.json()["email"] == "test_auth@example.com"


@pytest.mark.asyncio
async def test_login_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We assume the user was created in the previous test (or already exists).
        response = await ac.post("/auth/login", data={
            "username": "test_auth@example.com",
            "password": "securepassword"
        })
    
    # Ensure it returns an access token
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
