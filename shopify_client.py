"""
Real Shopify Admin API client.

This module replaces the previous `shopify_mock` HTTP service as the
integration point used by the Publisher and Verification agents.
It talks directly to a real Shopify store's Admin REST API using the
credentials supplied via environment variables:

    SHOPIFY_STORE_URL     e.g. "your-store.myshopify.com"
    SHOPIFY_ACCESS_TOKEN  Admin API access token (starts with "shpat_")
    SHOPIFY_API_VERSION   e.g. "2025-07"

No credentials are hardcoded anywhere in this file.
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("shopify_client")


class ShopifyConfigError(Exception):
    """Raised when required Shopify environment variables are missing."""


class ShopifyAPIError(Exception):
    """Raised when the Shopify Admin API returns an error response."""


def _clean_store_url(raw_url: str) -> str:
    return (
        raw_url.strip()
        .replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
    )


def _get_config() -> tuple[str, str, Dict[str, str]]:
    """
    Reads Shopify credentials from environment variables and builds
    the Admin API base URL + request headers.
    """
    store_url = os.getenv("SHOPIFY_STORE_URL")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2025-07")

    if not store_url:
        raise ShopifyConfigError(
            "SHOPIFY_STORE_URL is not set. Add it to your .env file, "
            "e.g. SHOPIFY_STORE_URL=your-store.myshopify.com"
        )
    if not access_token:
        raise ShopifyConfigError(
            "SHOPIFY_ACCESS_TOKEN is not set. Add it to your .env file."
        )

    store_url = _clean_store_url(store_url)
    base_url = f"https://{store_url}/admin/api/{api_version}"

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    return base_url, store_url, headers


def _normalize_product(product: Dict[str, Any], store_url: str) -> Dict[str, Any]:
    """
    Flattens a real Shopify Admin API product payload into the same
    simple shape the workflow already expects (id, title, status,
    price, url, variants, ...), so publisher_agent / verification_agent /
    report_generator_agent do not need to change how they read it.
    """
    variants: List[Dict[str, Any]] = product.get("variants", []) or []
    price = variants[0].get("price") if variants else "0.0"
    handle = product.get("handle", "")

    return {
        "id": product.get("id"),
        "title": product.get("title"),
        "body_html": product.get("body_html"),
        "vendor": product.get("vendor"),
        "product_type": product.get("product_type"),
        "status": product.get("status"),
        "handle": handle,
        "price": float(price) if price not in (None, "") else 0.0,
        "url": f"https://{store_url}/products/{handle}" if store_url and handle else "",
        "tags": product.get("tags", ""),
        "variants": variants,
    }


def create_product(
    title: str,
    body_html: Optional[str],
    price: float,
    product_type: Optional[str],
    status: str = "active",
    tags: Optional[str] = None,
    vendor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a real product in the configured Shopify store via the
    Admin REST API and returns it in the normalized shape used across
    the workflow.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/products.json"

    product_payload: Dict[str, Any] = {
        "title": title,
        "body_html": body_html or "",
        "product_type": product_type or "",
        "status": status,
        "variants": [{"price": str(price)}],
    }

    if vendor:
        product_payload["vendor"] = vendor
    if tags:
        product_payload["tags"] = tags

    payload = {"product": product_payload}

    logger.info("Creating Shopify product '%s' on store %s", title, store_url)

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Shopify create_product failed (%s): %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise ShopifyAPIError(
            f"Shopify API error ({exc.response.status_code}): {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Shopify create_product request failed: %s", exc)
        raise ShopifyAPIError(f"Shopify request failed: {exc}") from exc

    data = response.json()
    product = data.get("product")
    if not product:
        raise ShopifyAPIError(f"Unexpected Shopify response: {data}")

    return _normalize_product(product, store_url)


def get_product(product_id: Any) -> Dict[str, Any]:
    """
    Fetches a real product from Shopify by ID and returns it in the
    normalized shape used across the workflow.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/products/{product_id}.json"

    try:
        response = httpx.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ShopifyAPIError(
                f"Product {product_id} not found on Shopify."
            ) from exc
        logger.error(
            "Shopify get_product failed (%s): %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise ShopifyAPIError(
            f"Shopify API error ({exc.response.status_code}): {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Shopify get_product request failed: %s", exc)
        raise ShopifyAPIError(f"Shopify request failed: {exc}") from exc

    data = response.json()
    product = data.get("product")
    if not product:
        raise ShopifyAPIError(f"Unexpected Shopify response: {data}")

    return _normalize_product(product, store_url)
