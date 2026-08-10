import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "launch_platform.db"))

def get_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def parse_json_field(val: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not val:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        parsed = json.loads(val)
        if isinstance(parsed, str):
            return json.loads(parsed)
        return parsed
    except Exception:
        return default

def init_db(clear: bool = False):
    """Initialize database schemas for workshops and registrations."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with get_connection() as conn:
        if clear:
            conn.execute("DROP TABLE IF EXISTS workshops")
            conn.execute("DROP TABLE IF EXISTS registrations")
        # Create workshops table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workshops (
                id TEXT PRIMARY KEY,
                shopify_product_id INTEGER,
                shopify_variant_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                date TEXT,
                time TEXT,
                duration TEXT,
                venue TEXT,
                age_group TEXT,
                price REAL,
                topics TEXT,
                poster_path TEXT,
                video_url TEXT,
                sales_team_email TEXT,
                generated_description TEXT,
                seo_metadata TEXT,
                marketing TEXT,
                image_prompts TEXT,
                image_paths TEXT,
                shopify_media TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        # Ensure shopify_variant_id column exists (migration helper)
        try:
            conn.execute("ALTER TABLE workshops ADD COLUMN shopify_variant_id INTEGER")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Create registrations/orders table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                order_id TEXT PRIMARY KEY,
                shopify_order_id INTEGER,
                shopify_order_number TEXT,
                workshop_id TEXT,
                customer_name TEXT,
                customer_email TEXT,
                customer_phone TEXT,
                amount REAL,
                payment_status TEXT,
                child_name TEXT,
                child_age INTEGER,
                parent_name TEXT,
                school TEXT,
                emergency_contact TEXT,
                created_at TEXT
            )
        """)
        
        # Ensure school & emergency_contact columns exist in registrations (migration helper)
        try:
            conn.execute("ALTER TABLE registrations ADD COLUMN school TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE registrations ADD COLUMN emergency_contact TEXT")
        except sqlite3.OperationalError:
            pass
            
        conn.commit()

def create_workshop(workshop_data: Dict[str, Any]) -> str:
    """Create a new workshop draft entry."""
    workshop_id = workshop_data.get("id") or f"workshop_{int(datetime.utcnow().timestamp())}"
    now = datetime.utcnow().isoformat()
    
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO workshops (
                id, name, description, date, time, duration, venue, age_group, price, 
                topics, poster_path, video_url, sales_team_email, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workshop_id,
                workshop_data["name"],
                workshop_data.get("description", ""),
                workshop_data.get("date", ""),
                workshop_data.get("time", ""),
                workshop_data.get("duration", ""),
                workshop_data.get("venue", ""),
                workshop_data.get("age_group", ""),
                workshop_data.get("price", 0.0),
                json.dumps(workshop_data.get("topics", [])),
                workshop_data.get("poster_path", ""),
                workshop_data.get("video_url", ""),
                workshop_data.get("sales_team_email", ""),
                workshop_data.get("status", "draft"),
                now,
                now
            )
        )
        conn.commit()
    return workshop_id

def update_workshop_status(workshop_id: str, status: str):
    """Update status of a workshop in the database."""
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE workshops SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, workshop_id)
        )
        conn.commit()

def update_workshop_ai_content(workshop_id: str, updates: Dict[str, Any]):
    """Update AI-generated content for a workshop."""
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE workshops
            SET generated_description = ?,
                seo_metadata = ?,
                marketing = ?,
                image_prompts = ?,
                image_paths = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                updates.get("generated_description"),
                json.dumps(updates.get("seo_metadata", {})),
                json.dumps(updates.get("marketing", {})),
                json.dumps(updates.get("image_prompts", {})),
                json.dumps(updates.get("image_paths", [])),
                updates.get("status", "generated"),
                now,
                workshop_id
            )
        )
        conn.commit()

def publish_workshop(workshop_id: str, shopify_product_id: int, shopify_url: str,
                      shopify_media: List[Dict[str, Any]] = None, shopify_variant_id: int = None):
    """Mark a workshop as published and bind it to a Shopify product.

    shopify_variant_id is the ID of the product's first variant, required by the
    landing page to build a valid Shopify Cart Permalink checkout URL. Without it,
    the landing page has no way to know the product was actually published and
    will keep showing its "preview draft mode" fallback message.
    """
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE workshops
            SET shopify_product_id = ?,
                shopify_variant_id = ?,
                shopify_media = ?,
                status = 'published',
                updated_at = ?
            WHERE id = ?
            """,
            (
                shopify_product_id,
                shopify_variant_id,
                json.dumps(shopify_media or []),
                now,
                workshop_id
            )
        )
        conn.commit()

def get_workshop(workshop_id: str) -> Optional[Dict[str, Any]]:
    """Fetch details of a single workshop."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        # Decode JSON fields safely
        data["topics"] = parse_json_field(data["topics"], [])
        data["seo_metadata"] = parse_json_field(data["seo_metadata"], {})
        data["marketing"] = parse_json_field(data["marketing"], {})
        data["image_prompts"] = parse_json_field(data["image_prompts"], {})
        data["image_paths"] = parse_json_field(data["image_paths"], [])
        data["shopify_media"] = parse_json_field(data["shopify_media"], [])
        return data

def get_workshop_by_shopify_id(shopify_product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch details of a workshop by Shopify Product ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM workshops WHERE shopify_product_id = ?", (shopify_product_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        # Decode JSON fields safely
        data["topics"] = parse_json_field(data["topics"], [])
        data["seo_metadata"] = parse_json_field(data["seo_metadata"], {})
        data["marketing"] = parse_json_field(data["marketing"], {})
        data["image_prompts"] = parse_json_field(data["image_prompts"], {})
        data["image_paths"] = parse_json_field(data["image_paths"], [])
        data["shopify_media"] = parse_json_field(data["shopify_media"], [])
        return data

def get_all_workshops() -> List[Dict[str, Any]]:
    """Fetch all workshops in the system."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM workshops ORDER BY created_at DESC").fetchall()
        results = []
        for r in rows:
            data = dict(r)
            # Decode JSON fields safely
            data["topics"] = parse_json_field(data["topics"], [])
            data["seo_metadata"] = parse_json_field(data["seo_metadata"], {})
            data["marketing"] = parse_json_field(data["marketing"], {})
            data["image_prompts"] = parse_json_field(data["image_prompts"], {})
            data["image_paths"] = parse_json_field(data["image_paths"], [])
            data["shopify_media"] = parse_json_field(data["shopify_media"], [])
            results.append(data)
        return results

def add_registration(reg_data: Dict[str, Any]):
    """Insert a new order/registration."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO registrations (
                order_id, shopify_order_id, shopify_order_number, workshop_id, customer_name,
                customer_email, customer_phone, amount, payment_status, child_name, child_age, parent_name, 
                school, emergency_contact, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reg_data["order_id"],
                reg_data.get("shopify_order_id"),
                reg_data.get("shopify_order_number"),
                reg_data.get("workshop_id"),
                reg_data["customer_name"],
                reg_data["customer_email"],
                reg_data.get("customer_phone"),
                reg_data.get("amount", 0.0),
                reg_data.get("payment_status", "pending"),
                reg_data.get("child_name"),
                reg_data.get("child_age"),
                reg_data.get("parent_name"),
                reg_data.get("school"),
                reg_data.get("emergency_contact"),
                reg_data.get("created_at") or datetime.utcnow().isoformat()
            )
        )
        conn.commit()

def get_all_registrations() -> List[Dict[str, Any]]:
    """Fetch all registrations."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM registrations ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def get_registration(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch details of a single registration by order_id (registration_id)."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM registrations WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return None
        return dict(row)

def get_dashboard_metrics() -> Dict[str, Any]:
    """Calculate dashboard summary statistics."""
    with get_connection() as conn:
        total_workshops = conn.execute("SELECT COUNT(*) FROM workshops").fetchone()[0]
        published_workshops = conn.execute("SELECT COUNT(*) FROM workshops WHERE status = 'published'").fetchone()[0]
        upcoming_workshops = conn.execute("SELECT COUNT(*) FROM workshops WHERE date >= ?", (datetime.utcnow().strftime("%Y-%m-%d"),)).fetchone()[0]
        
        total_registrations = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
        revenue = conn.execute("SELECT SUM(amount) FROM registrations WHERE payment_status = 'paid' OR payment_status = 'authorized'").fetchone()[0] or 0.0
        
        recent_orders = conn.execute("SELECT * FROM registrations ORDER BY created_at DESC LIMIT 5").fetchall()
        
        return {
            "total_workshops": total_workshops,
            "published_workshops": published_workshops,
            "upcoming_workshops": upcoming_workshops,
            "total_registrations": total_registrations,
            "total_revenue": revenue,
            "recent_orders": [dict(r) for r in recent_orders]
        }