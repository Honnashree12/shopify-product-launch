import pytest
from fastapi.testclient import TestClient
import sys
import os

# Adjust path to import main and state
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint returns 200 and ADK is ready."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "adk_ready": True}

def test_initiate_launch():
    """Verify that the product launch endpoint accepts payload and starts session."""
    payload = {
        "product_name": "Eco-friendly Water Bottle",
        "raw_description": "Stainless steel, double-walled insulation, 500ml.",
        "price": 24.99,
        "category": "Home & Kitchen"
    }
    response = client.post("/launch", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["product_name"] == "Eco-friendly Water Bottle"
    assert data["status"] == "pending"
    assert data["raw_description"] == "Stainless steel, double-walled insulation, 500ml."

def test_shopify_mock_endpoints():
    """Verify the mock Shopify creation and retrieval endpoints using SQLite."""
    headers = {"X-Shopify-Access-Token": "test-token"}
    payload = {
        "product": {
            "title": "Test Insulated Flask",
            "body_html": "<p>Vacuum insulated flask</p>",
            "vendor": "Hydrate Co",
            "product_type": "Flask",
            "status": "draft",
            "price": 19.99
        }
    }
    
    # 1. Test POST /products
    post_response = client.post("/products", json=payload, headers=headers)
    assert post_response.status_code == 200
    post_data = post_response.json()
    assert "product" in post_data
    assert post_data["product"]["title"] == "Test Insulated Flask"
    assert post_data["product"]["price"] == 19.99
    assert post_data["product"]["status"] == "draft"
    assert "id" in post_data["product"]
    assert "handle" in post_data["product"]
    assert "url" in post_data["product"]
    
    product_id = post_data["product"]["id"]
    
    # 2. Test GET /products/{id}
    get_response = client.get(f"/products/{product_id}", headers=headers)
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["product"]["id"] == product_id
    assert get_data["product"]["title"] == "Test Insulated Flask"
    assert get_data["product"]["price"] == 19.99
    assert get_data["product"]["url"] == post_data["product"]["url"]
