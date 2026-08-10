import pytest
import os
import sys
import json
from fastapi.testclient import TestClient

# Adjust path to import files correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from data.database import init_db, create_workshop, get_workshop, add_registration, get_registration, get_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database state before each test."""
    init_db(clear=True)
    yield

def test_database_school_emergency_contact():
    """Verify that school and emergency_contact fields are successfully saved and queried."""
    init_db(clear=True)
    w_data = {
        "id": "test-curriculum",
        "name": "Astronomy Workshop",
        "description": "Intro to space telemetry.",
        "date": "2026-08-15",
        "time": "11:00 AM - 1:00 PM",
        "duration": "2 Hours",
        "venue": "Science Center",
        "age_group": "8-14",
        "price": 250.0,
        "topics": ["Astronomy"],
        "poster_path": "http://example.com/poster.png",
        "video_url": "http://example.com/video.mp4",
        "sales_team_email": "sales@example.com",
        "status": "draft"
    }
    create_workshop(w_data)

    reg_data = {
        "order_id": "REG-TEST-12345",
        "shopify_order_id": None,
        "shopify_order_number": None,
        "workshop_id": "test-curriculum",
        "customer_name": "Jane Parent / Joey Student",
        "customer_email": "jane@example.com",
        "customer_phone": "9998887777",
        "amount": 250.0,
        "payment_status": "pending",
        "child_name": "Joey Student",
        "child_age": 10,
        "parent_name": "Jane Parent",
        "school": "Space Academy High",
        "emergency_contact": "9112223333",
        "created_at": "2026-07-31T20:00:00Z"
    }
    add_registration(reg_data)

    retrieved = get_registration("REG-TEST-12345")
    assert retrieved is not None
    assert retrieved["school"] == "Space Academy High"
    assert retrieved["emergency_contact"] == "9112223333"
    assert retrieved["payment_status"] == "pending"

def test_registration_endpoint():
    """Verify that the pre-registration endpoint registers student and returns cart redirect URL."""
    init_db(clear=True)
    # 1. Create a dummy workshop with shopify variant ID inside the DB
    w_data = {
        "id": "mission-tiranga",
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
    create_workshop(w_data)

    # Manually update variant ID inside DB for testing
    with get_connection() as conn:
        conn.execute(
            "UPDATE workshops SET shopify_variant_id = ? WHERE id = ?",
            ("44556677", "mission-tiranga")
        )
        conn.commit()

    payload = {
        "child_name": "Rohan Doe",
        "child_age": 11,
        "school": "Vikas High School",
        "parent_name": "David Doe",
        "customer_email": "david@example.com",
        "customer_phone": "9876543210",
        "emergency_contact": "1234567890"
    }

    response = client.post("/api/workshops/mission-tiranga/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "registration_id" in data
    assert "redirect_url" in data

    # Verify redirection checkout parameters
    redirect_url = data["redirect_url"]
    print("\n[DEBUG] redirect_url:", redirect_url)
    try:
        assert "44556677" in redirect_url, f"Expected 44556677 in {redirect_url}"
        assert "registration_id" in redirect_url, f"Expected registration_id in {redirect_url}"
        assert "student_name" in redirect_url, f"Expected student_name in {redirect_url}"
        assert "checkout" in redirect_url, f"Expected checkout in {redirect_url}"
    except AssertionError as e:
        print("[FAIL_INFO]", str(e))
        raise e

    # Check local SQLite db holds the pending registration
    saved = get_registration(data["registration_id"])
    assert saved is not None
    assert saved["payment_status"] == "pending"
    assert saved["school"] == "Vikas High School"
    assert saved["emergency_contact"] == "1234567890"

def test_webhook_order_webhook_payment_update():
    """Verify webhook binds a Shopify payment order to a pending registration."""
    init_db(clear=True)
    # 1. Create a dummy workshop with shopify product ID inside the DB
    w_data = {
        "id": "mission-tiranga",
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
    create_workshop(w_data)

    # Manually update product ID inside DB for testing
    with get_connection() as conn:
        conn.execute(
            "UPDATE workshops SET shopify_product_id = ? WHERE id = ?",
            ("88990011", "mission-tiranga")
        )
        conn.commit()

    # 2. Insert a pending registration
    pending_reg = {
        "order_id": "REG-ABC-123",
        "shopify_order_id": None,
        "shopify_order_number": None,
        "workshop_id": "mission-tiranga",
        "customer_name": "David Doe / Rohan Doe",
        "customer_email": "david@example.com",
        "customer_phone": "9876543210",
        "amount": 499.0,
        "payment_status": "pending",
        "child_name": "Rohan Doe",
        "child_age": 11,
        "parent_name": "David Doe",
        "school": "Vikas High School",
        "emergency_contact": "1234567890",
        "created_at": "2026-07-31T21:00:00Z"
    }
    add_registration(pending_reg)

    # 3. Simulate order created webhook payload carrying registration_id in note attributes
    webhook_payload = {
        "id": 99887766,
        "order_number": "1005",
        "name": "#1005",
        "financial_status": "paid",
        "total_price": "499.00",
        "email": "david@example.com",
        "line_items": [
            {
                "product_id": 88990011,
                "price": "499.00",
                "quantity": 1,
                "name": "Mission Tiranga Space Workshop Ticket"
            }
        ],
        "note_attributes": [
            {
                "name": "registration_id",
                "value": "REG-ABC-123"
            }
        ],
        "customer": {
            "first_name": "David",
            "last_name": "Doe",
            "email": "david@example.com"
        }
    }

    response = client.post("/api/webhooks/orders/create", json=webhook_payload)
    assert response.status_code == 200
    assert response.json()["registrations_added"] == 1

    # Verify SQLite updated database columns
    updated = get_registration("REG-ABC-123")
    assert updated is not None
    assert updated["shopify_order_id"] == 99887766
    assert updated["shopify_order_number"] == "1005"
    assert updated["payment_status"] == "paid"
    assert updated["school"] == "Vikas High School"
    assert updated["emergency_contact"] == "1234567890"

    # Verify that a customer confirmation email file was logged to outputs/emails
    emails_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "emails"))
    customer_email_file = os.path.join(emails_dir, "customer_REG-ABC-123.html")
    assert os.path.exists(customer_email_file)

    with open(customer_email_file, "r", encoding="utf-8") as f:
        email_content = f.read()
        assert "Rohan Doe" in email_content
        # Verify ticket ID is present in the email content
        assert "Ticket ID: REG-ABC-123" in email_content
        # Verify QR code image source is present in the email content
        assert "api.qrserver.com" in email_content
