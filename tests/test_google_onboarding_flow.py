import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.db import SessionLocal
from app import models

client = TestClient(app)

def test_google_onboarding_new_user_flow():
    db = SessionLocal()
    test_email = "new_google_tester_123@example.com"
    
    # Cleanup any existing test user
    u = db.query(models.User).filter(models.User.email == test_email).first()
    if u:
        db.delete(u)
        db.commit()

    # 1. Mock Google ID Token verification for a brand new user
    mock_payload = {
        "email": test_email,
        "name": "New Google Tester",
        "sub": "mock_google_id_123456",
        "picture": "https://example.com/avatar.jpg"
    }

    with patch("app.main.verify_google_id_token", new=AsyncMock(return_value=mock_payload)):
        res = client.post("/api/auth/google", json={"id_token": "valid_mock_token"})
        assert res.status_code == 200
        data = res.json()
        
        # Must flag as new user requiring onboarding
        assert data["is_new_user"] is True
        assert data["user"]["is_onboarded"] is False
        assert data["user"]["email"] == test_email
        token = data["access_token"]

        # 2. Complete onboarding with custom preferences
        onboarding_payload = {
            "name": "New Google Tester",
            "email": test_email,
            "age": 28,
            "gender": "female",
            "height": 165.0,
            "weight": 60.0,
            "activity_level": "moderately_active",
            "goal": "fat loss",
            "water_target_ml": 2200.0,
            "preferences": [
                {"preference_type": "diet_type", "value": "Vegan"},
                {"preference_type": "allergy", "value": "peanuts"},
                {"preference_type": "like", "value": "tofu"},
                {"preference_type": "dislike", "value": "mushrooms"}
            ]
        }

        res_onboard = client.post(
            "/calculate-profile",
            json=onboarding_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_onboard.status_code == 201
        onboard_data = res_onboard.json()
        assert onboard_data["is_onboarded"] is True
        assert onboard_data["diet_type"] == "Vegan"
        assert "peanuts" in onboard_data["allergies"]
        assert "tofu" in onboard_data["likes"]
        assert "mushrooms" in onboard_data["dislikes"]
        assert onboard_data["age"] == 28
        assert onboard_data["weight"] == 60.0

        # 3. Subsequent login for the existing user
        res_subsequent = client.post("/api/auth/google", json={"id_token": "valid_mock_token"})
        assert res_subsequent.status_code == 200
        sub_data = res_subsequent.json()
        assert sub_data["is_new_user"] is False
        assert sub_data["user"]["is_onboarded"] is True
        assert sub_data["user"]["diet_type"] == "Vegan"

    # Cleanup test user
    u_after = db.query(models.User).filter(models.User.email == test_email).first()
    if u_after:
        db.delete(u_after)
        db.commit()
    db.close()
