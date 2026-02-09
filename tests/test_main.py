import pytest
from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Firmable AI" in response.text

def test_analyze_unauthorized():
    response = client.post("/analyze", json={"url": "https://example.com"})
    assert response.status_code == 401

def test_analyze_authorized():
    # This will fail without a valid Gemini key and internet connection, 
    # but we can test the auth check.
    headers = {"Authorization": "Bearer your_super_secret_key_here"}
    response = client.post("/analyze", headers=headers, json={"url": "https://example.com"})
    # It might return 500 if the scraper/AI fails due to missing key, which is fine for the auth test.
    assert response.status_code in [200, 500] 

def test_chat_unauthorized():
    response = client.post("/chat", json={"url": "https://example.com", "query": "hello"})
    assert response.status_code == 401
