import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()

def test_register(client):
    response = client.post("/api/auth/register", json={
        "name": "Test",
        "email": "test@test.com",
        "password": "123456",
        "role": "student"
    })
    assert response.status_code in [201, 400]

def test_invalid_login(client):
    response = client.post("/api/auth/login", json={
        "email": "wrong@test.com",
        "password": "123"
    })
    assert response.status_code == 404

def test_unauthorized_class_create(client):
    response = client.post("/api/class/create", json={"name": "Test"})
    assert response.status_code == 401