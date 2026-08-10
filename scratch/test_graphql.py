import os
import httpx
from dotenv import load_dotenv
load_dotenv()
store_url = os.getenv("SHOPIFY_STORE_URL")
access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
api_version = os.getenv("SHOPIFY_API_VERSION", "2025-07")
base_url = f"https://{store_url}/admin/api/{api_version}"
headers = {
    "X-Shopify-Access-Token": access_token,
    "Content-Type": "application/json",
}
graphql_url = f"{base_url}/graphql.json"
query = """
query {
  shop {
    name
  }
}
"""
try:
    print(f"Testing POST to {graphql_url}...")
    res = httpx.post(graphql_url, json={"query": query}, headers=headers, timeout=30)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
except Exception as e:
    print(f"GraphQL failed: {e}")
