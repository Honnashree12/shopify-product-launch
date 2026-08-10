import pytest
import os
import sys
import json
import sqlite3
from fastapi.testclient import TestClient

# Adjust path to import files correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from data.database import init_db, create_workshop, get_workshop, add_registration, get_dashboard_metrics

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Force DB re-init with clean slate
    init_db(clear=True)
    yield
    # We can clean up DB file after tests if needed, but keeping it is fine for dev

def test_database_crud():
    """Verify workshop and registration insert/read operations."""
    w_data = {
        "id": "test-mission-tiranga",
        "name": "Mission Tiranga Space Workshop",
        "description": "Satellite assembly and wave physics.",
        "date": "15 August 2026",
        "time": "11:00 AM - 1:00 PM",
        "duration": "2 Hours",
        "venue": "Jayanagar",
        "age_group": "8-14",
        "price": 499.0,
        "topics": ["Space", "Satellite"],
        "poster_path": "http://example.com/poster.png",
        "video_url": "http://example.com/video.mp4",
        "sales_team_email": "sales@example.com",
        "status": "draft"
    }
    
    # 1. Create
    workshop_id = create_workshop(w_data)
    assert workshop_id == "test-mission-tiranga"
    
    # 2. Get
    workshop = get_workshop(workshop_id)
    assert workshop is not None
    assert workshop["name"] == "Mission Tiranga Space Workshop"
    assert workshop["price"] == 499.0
    assert "topics" in workshop and len(workshop["topics"]) == 2
    
    # 3. Add registration
    reg_data = {
        "order_id": "shopify_order_112233",
        "shopify_order_id": 112233,
        "shopify_order_number": "1001",
        "workshop_id": "test-mission-tiranga",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "customer_phone": "9876543210",
        "amount": 499.0,
        "payment_status": "paid",
        "child_name": "Alice Doe",
        "child_age": 11,
        "parent_name": "John Doe",
        "created_at": "2026-07-29T10:00:00Z"
    }
    add_registration(reg_data)
    
    # 4. Metrics
    metrics = get_dashboard_metrics()
    assert metrics["total_workshops"] >= 1
    assert metrics["total_registrations"] >= 1
    assert metrics["total_revenue"] >= 499.0
    assert len(metrics["recent_orders"]) >= 1
    assert metrics["recent_orders"][0]["child_name"] == "Alice Doe"

def test_webhook_endpoint():
    """Verify that Shopify orders webhook successfully parses note_attributes and records signups."""
    # 1. Create a dummy workshop with shopify product ID inside the DB
    w_data = {
        "id": "test-workshop-webhook",
        "name": "Webhook Workshop Test",
        "description": "Testing Shopify Webhook integrations.",
        "date": "15 August 2026",
        "time": "11:00 AM - 1:00 PM",
        "duration": "2 Hours",
        "venue": "Jayanagar",
        "age_group": "8-14",
        "price": 499.0,
        "topics": ["Space"],
        "poster_path": "http://example.com/poster.png",
        "video_url": "http://example.com/video.mp4",
        "sales_team_email": "sales@example.com",
        "status": "draft"
    }
    create_workshop(w_data)
    
    # Manually update product ID inside DB
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "launch_platform.db"))
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE workshops SET shopify_product_id = 998877 WHERE id = 'test-workshop-webhook'")
        conn.commit()
        
    # 2. Simulate webhook POST payload
    webhook_payload = {
        "id": 987654321,
        "order_number": 1002,
        "name": "#1002",
        "total_price": "499.00",
        "financial_status": "paid",
        "email": "parent-webhook@example.com",
        "customer": {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "parent-webhook@example.com",
            "phone": "9123456789"
        },
        "note_attributes": [
            {"name": "Child Name", "value": "Bobby Smith"},
            {"name": "Child Age", "value": "9"},
            {"name": "Parent Name", "value": "Jane Smith"}
        ],
        "line_items": [
            {
                "product_id": 998877,
                "title": "Webhook Workshop Ticket",
                "quantity": 1,
                "price": "499.00"
            }
        ]
    }
    
    response = client.post("/api/webhooks/orders/create", json=webhook_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "processed"
    assert res_data["registrations_added"] == 1
    
    # Verify DB contains the new registration
    metrics = get_dashboard_metrics()
    recent = metrics["recent_orders"]
    matching = [o for o in recent if o["child_name"] == "Bobby Smith"]
    assert len(matching) == 1
    assert matching[0]["child_age"] == 9
    assert matching[0]["customer_email"] == "parent-webhook@example.com"
