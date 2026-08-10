import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from data.database import init_db, create_workshop, get_connection

client = TestClient(app)
init_db(clear=True)
create_workshop({
    'id': 'mission-tiranga',
    'name': 'Test',
    'description': 'Test',
    'date': '2026-08-15',
    'time': '11',
    'duration': '2',
    'venue': 'V',
    'age_group': '8-14',
    'price': 499,
    'topics': [],
    'poster_path': '',
    'video_url': '',
    'sales_team_email': '',
    'status': 'draft'
})

with get_connection() as conn:
    conn.execute('UPDATE workshops SET shopify_variant_id="44556677" WHERE id="mission-tiranga"')
    conn.commit()

r = client.post('/api/workshops/mission-tiranga/register', json={
    'child_name': 'Rohan Doe',
    'child_age': 11,
    'school': 'S',
    'parent_name': 'P',
    'customer_email': 'david@example.com',
    'customer_phone': '1',
    'emergency_contact': '2'
})
print("RESPONSE STATUS:", r.status_code)
print("RESPONSE JSON:", r.json())
