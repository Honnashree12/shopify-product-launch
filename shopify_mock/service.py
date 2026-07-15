import os
import sqlite3
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel, Field

# SQLite Database Location
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shopify_mock.db")

# Initialize SQLite database and tables
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body_html TEXT,
            vendor TEXT,
            product_type TEXT,
            status TEXT DEFAULT 'draft',
            handle TEXT,
            price REAL DEFAULT 0.0,
            url TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run database setup on module load
init_db()

router = APIRouter(tags=["Shopify Mock Service"])

class ShopifyProductInput(BaseModel):
    title: str = Field(..., description="The title of the product.")
    body_html: Optional[str] = Field(None, description="The HTML description of the product.")
    vendor: Optional[str] = Field("Mock Vendor", description="The vendor name.")
    product_type: Optional[str] = Field("Mock Type", description="The product category/type.")
    status: Optional[str] = Field("draft", description="Listing status (draft, active, archived).")
    price: Optional[float] = Field(0.0, description="Product variant price.")

class ProductPayload(BaseModel):
    product: ShopifyProductInput

@router.post("/products")
def create_product(
    payload: ProductPayload,
    x_shopify_access_token: Optional[str] = Header(None, alias="X-Shopify-Access-Token")
):
    """
    Creates a mock Shopify product and stores it in the SQLite database.
    Returns a Shopify-like JSON response.
    """
    if not x_shopify_access_token:
         # Standard Shopify request validation (mock version)
         pass

    prod = payload.product
    handle = prod.title.lower().replace(" ", "-").replace("/", "-")
    
    # Insert product into SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO mock_products (title, body_html, vendor, product_type, status, handle, price, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prod.title,
                prod.body_html,
                prod.vendor,
                prod.product_type,
                prod.status,
                handle,
                prod.price,
                ""  # placeholder, we update it with id shortly
            )
        )
        product_id = cursor.lastrowid
        
        # Build the final Shopify store URL using the ID
        store_url = f"https://mock-shopify-store.myshopify.com/products/{handle}-{product_id}"
        cursor.execute("UPDATE mock_products SET url = ? WHERE id = ?", (store_url, product_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

    # Formulate Shopify-like response structure
    return {
        "product": {
            "id": product_id,
            "title": prod.title,
            "body_html": prod.body_html,
            "vendor": prod.vendor,
            "product_type": prod.product_type,
            "status": prod.status,
            "handle": handle,
            "price": prod.price,
            "url": store_url,
            "variants": [
                {
                    "id": product_id * 10,
                    "price": str(prod.price),
                    "title": "Default Title"
                }
            ]
        }
    }

@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    x_shopify_access_token: Optional[str] = Header(None, alias="X-Shopify-Access-Token")
):
    """
    Retrieves a mock Shopify product by its ID from the SQLite database.
    """
    if not x_shopify_access_token:
         pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM mock_products WHERE id = ?", (product_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product": {
            "id": row["id"],
            "title": row["title"],
            "body_html": row["body_html"],
            "vendor": row["vendor"],
            "product_type": row["product_type"],
            "status": row["status"],
            "handle": row["handle"],
            "price": row["price"],
            "url": row["url"],
            "variants": [
                {
                    "id": row["id"] * 10,
                    "price": str(row["price"]),
                    "title": "Default Title"
                }
            ]
        }
    }
