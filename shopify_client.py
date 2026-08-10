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
import base64
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("shopify_client")


def get_mime_type(file_path: str) -> tuple[str, str]:
    """
    Returns the MIME type and Shopify resource type for a file path.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        return 'image/jpeg', 'IMAGE'
    elif ext == '.png':
        return 'image/png', 'IMAGE'
    elif ext == '.webp':
        return 'image/webp', 'IMAGE'
    elif ext == '.gif':
        return 'image/gif', 'IMAGE'
    elif ext == '.mp4':
        return 'video/mp4', 'VIDEO'
    elif ext == '.mov':
        return 'video/quicktime', 'VIDEO'
    elif ext == '.webm':
        return 'video/webm', 'VIDEO'
    elif ext == '.m4v':
        return 'video/mp4', 'VIDEO'
    else:
        return 'application/octet-stream', 'FILE'



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
    sku: Optional[str] = None,
    inventory_quantity: Optional[int] = None,
    # New Shopify Fields (backwards compatible defaults)
    compare_at_price: Optional[float] = None,
    barcode: Optional[str] = None,
    track_inventory: bool = True,
    sell_out_of_stock: bool = False,
    requires_shipping: bool = True,
    weight: Optional[float] = None,
    weight_unit: Optional[str] = None,
    country_of_origin: Optional[str] = None,
    hs_code: Optional[str] = None,
    cost_per_item: Optional[float] = None,
    options: Optional[List[Dict[str, Any]]] = None,
    variants: Optional[List[Dict[str, Any]]] = None,
    seo_title: Optional[str] = None,
    seo_description: Optional[str] = None,
    handle: Optional[str] = None,
    template_suffix: Optional[str] = None,
    metafields: Optional[List[Dict[str, Any]]] = None,
    published: Optional[bool] = None,
    inventory_locations: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Creates a real product in the configured Shopify store via the Admin REST API
    and returns it in the normalized shape used across the workflow.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/products.json"

    variants_payload = []
    
    if variants:
        for var in variants:
            v_pay = {
                "price": str(var.get("price", price)),
                "requires_shipping": var.get("requires_shipping", requires_shipping),
                "taxable": var.get("taxable", True),
            }
            if var.get("compare_at_price") is not None:
                v_pay["compare_at_price"] = str(var["compare_at_price"])
            elif compare_at_price is not None:
                v_pay["compare_at_price"] = str(compare_at_price)
                
            if var.get("sku") or sku:
                v_pay["sku"] = var.get("sku") or sku
            if var.get("barcode"):
                v_pay["barcode"] = var["barcode"]
            elif barcode:
                v_pay["barcode"] = barcode
                
            if var.get("weight") is not None:
                v_pay["weight"] = var["weight"]
            elif weight is not None:
                v_pay["weight"] = weight
                
            if var.get("weight_unit") or weight_unit:
                v_pay["weight_unit"] = var.get("weight_unit") or weight_unit
            
            track = var.get("track_inventory", track_inventory)
            v_pay["inventory_management"] = "shopify" if track else None
            
            sell = var.get("sell_out_of_stock", sell_out_of_stock)
            v_pay["inventory_policy"] = "continue" if sell else "deny"
            
            for idx in range(1, 4):
                opt_val = var.get(f"option{idx}")
                if opt_val:
                    v_pay[f"option{idx}"] = opt_val
                    
            variants_payload.append(v_pay)
    else:
        variant_payload: Dict[str, Any] = {
            "price": str(price),
            "requires_shipping": requires_shipping,
            "taxable": True,
        }
        if compare_at_price is not None:
            variant_payload["compare_at_price"] = str(compare_at_price)
        if sku:
            variant_payload["sku"] = sku
        if barcode:
            variant_payload["barcode"] = barcode
        if weight is not None:
            variant_payload["weight"] = weight
        if weight_unit:
            variant_payload["weight_unit"] = weight_unit
            
        variant_payload["inventory_management"] = "shopify" if track_inventory else None
        variant_payload["inventory_policy"] = "continue" if sell_out_of_stock else "deny"
        variants_payload.append(variant_payload)

    product_payload: Dict[str, Any] = {
        "title": title,
        "body_html": body_html or "",
        "product_type": product_type or "",
        "status": status.lower(),
        "variants": variants_payload,
    }

    if vendor:
        product_payload["vendor"] = vendor
    if tags:
        product_payload["tags"] = tags
    if handle:
        product_payload["handle"] = handle
    if template_suffix:
        product_payload["template_suffix"] = template_suffix
    if published is not None:
        product_payload["published"] = published
    if options:
        product_payload["options"] = options

    if seo_title:
        product_payload["metafields_global_title_tag"] = seo_title
    if seo_description:
        product_payload["metafields_global_description_tag"] = seo_description
    if metafields:
        product_payload["metafields"] = metafields

    payload = {"product": product_payload}

    logger.info("Creating Shopify product '%s' on store %s", title, store_url)

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Shopify create_product failed (%s): %s", exc.response.status_code, exc.response.text)
        raise ShopifyAPIError(f"Shopify API error ({exc.response.status_code}): {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error("Shopify create_product request failed: %s", exc)
        raise ShopifyAPIError(f"Shopify request failed: {exc}") from exc

    data = response.json()
    product = data.get("product")
    if not product:
        raise ShopifyAPIError(f"Unexpected Shopify response: {data}")

    # Set inventory items details (cost, origin, hs code) and inventory quantity
    for idx, variant in enumerate(product.get("variants", [])):
        inventory_item_id = variant.get("inventory_item_id")
        if inventory_item_id:
            try:
                # Update inventory item fields
                inv_item_payload = {}
                v_cost = variants[idx].get("cost_per_item") if variants else cost_per_item
                v_country = variants[idx].get("country_of_origin") if variants else country_of_origin
                v_hs = variants[idx].get("hs_code") if variants else hs_code
                
                if v_cost is not None:
                    inv_item_payload["cost"] = str(v_cost)
                if v_country:
                    inv_item_payload["country_code_of_origin"] = v_country
                if v_hs:
                    inv_item_payload["harmonized_system_code"] = v_hs
                    
                if inv_item_payload:
                    inv_item_endpoint = f"{base_url}/inventory_items/{inventory_item_id}.json"
                    httpx.put(inv_item_endpoint, json={"inventory_item": inv_item_payload}, headers=headers, timeout=30).raise_for_status()
                
                # Set inventory levels
                v_qty = variants[idx].get("inventory_quantity") if variants else inventory_quantity
                v_locations = variants[idx].get("inventory_locations") if variants else inventory_locations
                
                if v_qty is not None:
                    inv_lvl_endpoint = f"{base_url}/inventory_levels.json?inventory_item_ids={inventory_item_id}"
                    inv_lvl_res = httpx.get(inv_lvl_endpoint, headers=headers, timeout=30)
                    inv_lvl_res.raise_for_status()
                    levels = inv_lvl_res.json().get("inventory_levels", [])
                    if levels:
                        if v_locations and isinstance(v_locations, dict):
                            loc_id_map = {}
                            try:
                                loc_res = httpx.get(f"{base_url}/locations.json", headers=headers, timeout=30)
                                if loc_res.status_code == 200:
                                    for loc in loc_res.json().get("locations", []):
                                        loc_id_map[loc["name"].lower()] = loc["id"]
                            except Exception:
                                pass
                            
                            grouped_qty = {}
                            for loc_name, qty in v_locations.items():
                                loc_id = loc_id_map.get(loc_name.lower())
                                if not loc_id and loc_name.isdigit():
                                    loc_id = int(loc_name)
                                if not loc_id:
                                    loc_id = levels[0]["location_id"]
                                grouped_qty[loc_id] = grouped_qty.get(loc_id, 0) + qty
                                
                            for loc_id, qty in grouped_qty.items():
                                inv_endpoint = f"{base_url}/inventory_levels/set.json"
                                httpx.post(inv_endpoint, json={
                                    "location_id": loc_id,
                                    "inventory_item_id": inventory_item_id,
                                    "available": qty
                                }, headers=headers, timeout=30).raise_for_status()
                        else:
                            location_id = levels[0]["location_id"]
                            inv_endpoint = f"{base_url}/inventory_levels/set.json"
                            httpx.post(inv_endpoint, json={
                                "location_id": location_id,
                                "inventory_item_id": inventory_item_id,
                                "available": v_qty
                            }, headers=headers, timeout=30).raise_for_status()
                            
                        product["variants"][idx]["inventory_quantity"] = v_qty
            except Exception as e:
                logger.error("Failed to configure variant %d inventory levels/item details: %s", idx, e)

    return _normalize_product(product, store_url)


def update_product(
    product_id: Any,
    title: Optional[str] = None,
    body_html: Optional[str] = None,
    price: Optional[float] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    vendor: Optional[str] = None,
    sku: Optional[str] = None,
    inventory_quantity: Optional[int] = None,
    compare_at_price: Optional[float] = None,
    barcode: Optional[str] = None,
    track_inventory: Optional[bool] = None,
    sell_out_of_stock: Optional[bool] = None,
    requires_shipping: Optional[bool] = None,
    weight: Optional[float] = None,
    weight_unit: Optional[str] = None,
    country_of_origin: Optional[str] = None,
    hs_code: Optional[str] = None,
    cost_per_item: Optional[float] = None,
    options: Optional[List[Dict[str, Any]]] = None,
    variants: Optional[List[Dict[str, Any]]] = None,
    seo_title: Optional[str] = None,
    seo_description: Optional[str] = None,
    handle: Optional[str] = None,
    template_suffix: Optional[str] = None,
    metafields: Optional[List[Dict[str, Any]]] = None,
    published: Optional[bool] = None,
    inventory_locations: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Updates an existing product on Shopify via the REST Admin API.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/products/{product_id}.json"

    # Fetch existing to get variant ids
    existing = get_product(product_id)
    existing_variants = existing.get("variants") or []

    product_payload: Dict[str, Any] = {}
    if title is not None: product_payload["title"] = title
    if body_html is not None: product_payload["body_html"] = body_html
    if product_type is not None: product_payload["product_type"] = product_type
    if status is not None: product_payload["status"] = status.lower()
    if vendor is not None: product_payload["vendor"] = vendor
    if tags is not None: product_payload["tags"] = tags
    if handle is not None: product_payload["handle"] = handle
    if template_suffix is not None: product_payload["template_suffix"] = template_suffix
    if published is not None: product_payload["published"] = published
    if options is not None: product_payload["options"] = options

    if seo_title is not None:
        product_payload["metafields_global_title_tag"] = seo_title
    if seo_description is not None:
        product_payload["metafields_global_description_tag"] = seo_description
    if metafields is not None:
        product_payload["metafields"] = metafields

    variants_payload = []
    if variants:
        for idx, var in enumerate(variants):
            var_id = var.get("id")
            if not var_id and var.get("sku"):
                for ev in existing_variants:
                    if ev.get("sku") == var["sku"]:
                        var_id = ev.get("id")
                        break
            
            v_pay = {}
            if var_id: v_pay["id"] = var_id
            if var.get("price") is not None: v_pay["price"] = str(var["price"])
            elif price is not None: v_pay["price"] = str(price)
            
            if var.get("compare_at_price") is not None: v_pay["compare_at_price"] = str(var["compare_at_price"])
            elif compare_at_price is not None: v_pay["compare_at_price"] = str(compare_at_price)
            
            if var.get("sku"): v_pay["sku"] = var["sku"]
            elif sku: v_pay["sku"] = sku
            
            if var.get("barcode"): v_pay["barcode"] = var["barcode"]
            elif barcode: v_pay["barcode"] = barcode
            
            if var.get("weight") is not None: v_pay["weight"] = var["weight"]
            elif weight is not None: v_pay["weight"] = weight
            
            if var.get("weight_unit"): v_pay["weight_unit"] = var["weight_unit"]
            elif weight_unit: v_pay["weight_unit"] = weight_unit
            
            if var.get("requires_shipping") is not None: v_pay["requires_shipping"] = var["requires_shipping"]
            elif requires_shipping is not None: v_pay["requires_shipping"] = requires_shipping
            
            track = var.get("track_inventory", track_inventory)
            if track is not None:
                v_pay["inventory_management"] = "shopify" if track else None
                
            sell = var.get("sell_out_of_stock", sell_out_of_stock)
            if sell is not None:
                v_pay["inventory_policy"] = "continue" if sell else "deny"
                
            for o_idx in range(1, 4):
                opt_val = var.get(f"option{o_idx}")
                if opt_val: v_pay[f"option{o_idx}"] = opt_val
                
            variants_payload.append(v_pay)
    else:
        if existing_variants:
            v_pay = {"id": existing_variants[0]["id"]}
            if price is not None: v_pay["price"] = str(price)
            if compare_at_price is not None: v_pay["compare_at_price"] = str(compare_at_price)
            if sku is not None: v_pay["sku"] = sku
            if barcode is not None: v_pay["barcode"] = barcode
            if weight is not None: v_pay["weight"] = weight
            if weight_unit is not None: v_pay["weight_unit"] = weight_unit
            if requires_shipping is not None: v_pay["requires_shipping"] = requires_shipping
            if track_inventory is not None:
                v_pay["inventory_management"] = "shopify" if track_inventory else None
            if sell_out_of_stock is not None:
                v_pay["inventory_policy"] = "continue" if sell_out_of_stock else "deny"
            variants_payload.append(v_pay)
            
    if variants_payload:
        product_payload["variants"] = variants_payload

    payload = {"product": product_payload}

    logger.info("Updating Shopify product '%s' on store %s", product_id, store_url)

    try:
        response = httpx.put(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Shopify update_product failed (%s): %s", exc.response.status_code, exc.response.text)
        raise ShopifyAPIError(f"Shopify API error ({exc.response.status_code}): {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error("Shopify update_product request failed: %s", exc)
        raise ShopifyAPIError(f"Shopify request failed: {exc}") from exc

    data = response.json()
    product = data.get("product")
    if not product:
        raise ShopifyAPIError(f"Unexpected Shopify response: {data}")

    # Set inventory items details (cost, origin, hs code) and inventory quantity
    for idx, variant in enumerate(product.get("variants", [])):
        inventory_item_id = variant.get("inventory_item_id")
        if inventory_item_id:
            try:
                # Update inventory item fields
                inv_item_payload = {}
                v_cost = variants[idx].get("cost_per_item") if variants else cost_per_item
                v_country = variants[idx].get("country_of_origin") if variants else country_of_origin
                v_hs = variants[idx].get("hs_code") if variants else hs_code
                
                if v_cost is not None:
                    inv_item_payload["cost"] = str(v_cost)
                if v_country is not None:
                    inv_item_payload["country_code_of_origin"] = v_country
                if v_hs is not None:
                    inv_item_payload["harmonized_system_code"] = v_hs
                    
                if inv_item_payload:
                    inv_item_endpoint = f"{base_url}/inventory_items/{inventory_item_id}.json"
                    httpx.put(inv_item_endpoint, json={"inventory_item": inv_item_payload}, headers=headers, timeout=30).raise_for_status()
                
                # Set inventory levels
                v_qty = variants[idx].get("inventory_quantity") if variants else inventory_quantity
                v_locations = variants[idx].get("inventory_locations") if variants else inventory_locations
                
                if v_qty is not None:
                    inv_lvl_endpoint = f"{base_url}/inventory_levels.json?inventory_item_ids={inventory_item_id}"
                    inv_lvl_res = httpx.get(inv_lvl_endpoint, headers=headers, timeout=30)
                    inv_lvl_res.raise_for_status()
                    levels = inv_lvl_res.json().get("inventory_levels", [])
                    if levels:
                        if v_locations and isinstance(v_locations, dict):
                            loc_id_map = {}
                            try:
                                loc_res = httpx.get(f"{base_url}/locations.json", headers=headers, timeout=30)
                                if loc_res.status_code == 200:
                                    for loc in loc_res.json().get("locations", []):
                                        loc_id_map[loc["name"].lower()] = loc["id"]
                            except Exception:
                                pass
                            
                            grouped_qty = {}
                            for loc_name, qty in v_locations.items():
                                loc_id = loc_id_map.get(loc_name.lower())
                                if not loc_id and loc_name.isdigit():
                                    loc_id = int(loc_name)
                                if not loc_id:
                                    loc_id = levels[0]["location_id"]
                                grouped_qty[loc_id] = grouped_qty.get(loc_id, 0) + qty
                                
                            for loc_id, qty in grouped_qty.items():
                                inv_endpoint = f"{base_url}/inventory_levels/set.json"
                                httpx.post(inv_endpoint, json={
                                    "location_id": loc_id,
                                    "inventory_item_id": inventory_item_id,
                                    "available": qty
                                }, headers=headers, timeout=30).raise_for_status()
                        else:
                            location_id = levels[0]["location_id"]
                            inv_endpoint = f"{base_url}/inventory_levels/set.json"
                            httpx.post(inv_endpoint, json={
                                "location_id": location_id,
                                "inventory_item_id": inventory_item_id,
                                "available": v_qty
                            }, headers=headers, timeout=30).raise_for_status()
                            
                        product["variants"][idx]["inventory_quantity"] = v_qty
            except Exception as e:
                logger.error("Failed to configure variant %d inventory levels/item details: %s", idx, e)

    return _normalize_product(product, store_url)


def upload_product_image(
    product_id: Any,
    image_bytes: bytes,
    filename: str = "product.png",
) -> Dict[str, Any]:
    """
    Uploads an image to an existing Shopify product via the Admin
    REST API. Returns the raw Shopify image object on success.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/products/{product_id}/images.json"

    payload = {
        "image": {
            "attachment": base64.b64encode(image_bytes).decode("utf-8"),
            "filename": filename,
        }
    }

    logger.info("Uploading image to Shopify product %s", product_id)

    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Shopify upload_product_image failed (%s): %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise ShopifyAPIError(
            f"Shopify API error ({exc.response.status_code}): {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Shopify upload_product_image request failed: %s", exc)
        raise ShopifyAPIError(f"Shopify request failed: {exc}") from exc

    data = response.json()
    image = data.get("image")
    if not image:
        raise ShopifyAPIError(f"Unexpected Shopify response: {data}")

    return image


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

    # Fetch real-time inventory levels for variants if tracked
    for variant in product.get("variants", []):
        item_id = variant.get("inventory_item_id")
        if item_id:
            try:
                inv_endpoint = f"{base_url}/inventory_levels.json?inventory_item_ids={item_id}"
                inv_res = httpx.get(inv_endpoint, headers=headers, timeout=30)
                inv_res.raise_for_status()
                levels = inv_res.json().get("inventory_levels", [])
                if levels:
                    total_qty = sum(level.get("available") or 0 for level in levels)
                    variant["inventory_quantity"] = total_qty
                else:
                    variant["inventory_quantity"] = 0
            except Exception as e:
                logger.error("Failed to fetch inventory level for item %s: %s", item_id, e)

    return _normalize_product(product, store_url)


def upload_product_images(
    product_id: Any,
    image_paths: List[str],
) -> List[Dict[str, Any]]:
    """
    Uploads a list of local images to an existing Shopify product via the GraphQL Admin API.

    1. Creates a staged upload target for each image.
    2. Uploads the image bytes to the staged target.
    3. Associates the uploaded media with the product.

    Returns a list of created media objects (id, status, mediaContentType).
    """
    base_url, store_url, headers = _get_config()
    graphql_url = f"{base_url}/graphql.json"

    # Helper to run GraphQL queries
    def _run_graphql(query: str, variables: Dict[str, Any], operation_name: str) -> Dict[str, Any]:
        try:
            logger.info("Executing Shopify GraphQL mutation: %s", operation_name)
            response = httpx.post(
                graphql_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Shopify GraphQL mutation '%s' failed (%s): %s",
                operation_name,
                exc.response.status_code,
                exc.response.text,
            )
            raise ShopifyAPIError(
                f"Shopify GraphQL API error ({exc.response.status_code}): {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Shopify GraphQL request failed for '%s': %s", operation_name, exc)
            raise ShopifyAPIError(f"Shopify GraphQL request failed: {exc}") from exc

        data = response.json()
        if "errors" in data:
            logger.error("Shopify GraphQL '%s' returned errors: %s", operation_name, data["errors"])
            raise ShopifyAPIError(f"Shopify GraphQL errors: {data['errors']}")
        return data

    uploaded_media = []

    staged_mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    media_mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          id
          status
          mediaContentType
        }
        mediaUserErrors {
          field
          message
        }
      }
    }
    """

    for image_path in image_paths:
        if not os.path.exists(image_path):
            logger.warning("Image path does not exist: %s", image_path)
            continue

        filename = os.path.basename(image_path)
        logger.info("Starting staged upload for image: %s", filename)

        # Step A: stagedUploadsCreate
        staged_input = {
            "filename": filename,
            "mimeType": "image/png",
            "httpMethod": "POST",
            "resource": "IMAGE"
        }

        staged_data = _run_graphql(
            query=staged_mutation,
            variables={"input": [staged_input]},
            operation_name="stagedUploadsCreate"
        )

        create_result = staged_data.get("data", {}).get("stagedUploadsCreate", {})
        user_errors = create_result.get("userErrors", [])
        if user_errors:
            error_msg = f"stagedUploadsCreate userErrors: {user_errors}"
            logger.error(error_msg)
            raise ShopifyAPIError(error_msg)

        targets = create_result.get("stagedTargets", [])
        if not targets:
            raise ShopifyAPIError("stagedUploadsCreate did not return stagedTargets.")

        target = targets[0]
        target_url = target.get("url")
        resource_url = target.get("resourceUrl")
        parameters = target.get("parameters", [])

        if not target_url or not resource_url:
            raise ShopifyAPIError("Invalid stagedTarget response from Shopify.")

        # Step B: POST actual bytes as multipart form data
        logger.info("Uploading bytes to target URL: %s", target_url)
        try:
            with open(image_path, "rb") as f:
                file_bytes = f.read()

            # Compile parameters in order, placing 'file' at the very end
            multipart_fields = []
            for param in parameters:
                multipart_fields.append((param.get("name"), param.get("value")))

            # The 'file' field MUST be the last field in the request
            multipart_fields.append(("file", (filename, file_bytes, "image/png")))

            # Send request
            upload_response = httpx.post(
                target_url,
                files=multipart_fields,
                timeout=30
            )
            upload_response.raise_for_status()
            logger.info("Successfully uploaded file bytes to Shopify storage.")
        except httpx.HTTPError as exc:
            logger.error("Failed to upload image bytes to staged upload URL: %s", exc)
            raise ShopifyAPIError(f"Staged file upload failed: {exc}") from exc

        # Step C: productCreateMedia
        logger.info("Associating resource URL with product: %s", product_id)
        media_input = {
            "originalSource": resource_url,
            "mediaContentType": "IMAGE"
        }

        # Product ID needs to be shopify GID format: gid://shopify/Product/{product_id}
        gid_product_id = str(product_id)
        if not gid_product_id.startswith("gid://shopify/Product/"):
            gid_product_id = f"gid://shopify/Product/{product_id}"

        media_data = _run_graphql(
            query=media_mutation,
            variables={
                "productId": gid_product_id,
                "media": [media_input]
            },
            operation_name="productCreateMedia"
        )

        media_result = media_data.get("data", {}).get("productCreateMedia", {})
        media_user_errors = media_result.get("mediaUserErrors", [])
        if media_user_errors:
            error_msg = f"productCreateMedia mediaUserErrors: {media_user_errors}"
            logger.error(error_msg)
            raise ShopifyAPIError(error_msg)

        media_objects = media_result.get("media", [])
        if media_objects:
            uploaded_media.extend(media_objects)
            logger.info("Successfully created product media: %s", media_objects[0])

    return uploaded_media


def get_or_create_custom_collection(title: str) -> int:
    """
    Finds a custom collection by title or creates one if it doesn't exist.
    Returns the custom collection ID.
    """
    base_url, store_url, headers = _get_config()
    
    # 1. Query existing collections
    endpoint = f"{base_url}/custom_collections.json"
    logger.info("Searching for custom collection: '%s'", title)
    try:
        response = httpx.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        collections = response.json().get("custom_collections", [])
        for coll in collections:
            if coll.get("title", "").strip().lower() == title.strip().lower():
                logger.info("Found custom collection '%s' with ID: %s", title, coll["id"])
                return coll["id"]
    except Exception as e:
        logger.error("Failed to query custom collections: %s", e)
        # fallback/log, but don't hard crash if it's just a query error
        
    # 2. Create collection if not found
    payload = {
        "custom_collection": {
            "title": title,
            "published": True
        }
    }
    logger.info("Creating new custom collection: '%s'", title)
    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        collection = response.json().get("custom_collection")
        if not collection:
            raise ShopifyAPIError("Unexpected custom collection payload from Shopify")
        logger.info("Created custom collection '%s' with ID: %s", title, collection["id"])
        return collection["id"]
    except Exception as e:
        logger.error("Failed to create custom collection: %s", e)
        raise ShopifyAPIError(f"Create collection failed: {e}")


def add_product_to_collection(product_id: Any, collection_id: int) -> Dict[str, Any]:
    """
    Associates a product with a custom collection by creating a Collect record.
    """
    base_url, store_url, headers = _get_config()
    endpoint = f"{base_url}/collects.json"
    
    payload = {
        "collect": {
            "product_id": int(product_id),
            "collection_id": int(collection_id)
        }
    }
    logger.info("Adding product %s to collection %s", product_id, collection_id)
    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
        if response.status_code == 422 and "already" in response.text:
            logger.info("Product %s is already in collection %s", product_id, collection_id)
            return {"status": "already_added"}
        response.raise_for_status()
        return response.json().get("collect", {})
    except Exception as e:
        logger.error("Failed to add product to collection: %s", e)
        raise ShopifyAPIError(f"Add product to collection failed: {e}")


def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """
    Checks if a product variant with the given SKU already exists in Shopify.
    If yes, returns a dict with product information. Otherwise, returns None.
    """
    if not sku:
        return None
    base_url, store_url, headers = _get_config()
    graphql_url = f"{base_url}/graphql.json"

    query = """
    query getVariantBySku($query: String!) {
      productVariants(first: 1, query: $query) {
        edges {
          node {
            id
            sku
            product {
              id
              title
              handle
            }
          }
        }
      }
    }
    """
    
    logger.info("Checking if SKU '%s' already exists in Shopify...", sku)
    try:
        response = httpx.post(
            graphql_url,
            json={"query": query, "variables": {"query": f"sku:{sku}"}},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            logger.error("SKU duplicate check query returned errors: %s", data["errors"])
            return None
        
        edges = data.get("data", {}).get("productVariants", {}).get("edges", [])
        if edges:
            node = edges[0].get("node", {})
            product_node = node.get("product", {})
            product_id = product_node.get("id")
            raw_id = product_id
            if raw_id and raw_id.startswith("gid://shopify/Product/"):
                raw_id = int(raw_id.split("/")[-1])
            return {
                "variant_id": node.get("id"),
                "sku": node.get("sku"),
                "product_id": raw_id,
                "title": product_node.get("title"),
                "url": f"https://{store_url}/products/{product_node.get('handle')}" if product_node.get('handle') else ""
            }
    except Exception as e:
        logger.exception("Failed to check duplicate product by SKU: %s", e)
    return None


def get_product_by_title(title: str) -> Optional[Dict[str, Any]]:
    """
    Checks if a product with the given title already exists in Shopify.
    If yes, returns a dict with product information. Otherwise, returns None.
    """
    if not title:
        return None
    base_url, store_url, headers = _get_config()
    graphql_url = f"{base_url}/graphql.json"

    query = """
    query getProductByTitle($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            title
            handle
          }
        }
      }
    }
    """
    
    logger.info("Checking if product with title '%s' already exists in Shopify...", title)
    try:
        response = httpx.post(
            graphql_url,
            json={"query": query, "variables": {"query": f"title:'{title}'"}},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            logger.error("Title duplicate check query returned errors: %s", data["errors"])
            return None
        
        edges = data.get("data", {}).get("products", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            if node.get("title", "").strip().lower() == title.strip().lower():
                product_id = node.get("id")
                raw_id = product_id
                if raw_id and raw_id.startswith("gid://shopify/Product/"):
                    raw_id = int(raw_id.split("/")[-1])
                return {
                    "product_id": raw_id,
                    "title": node.get("title"),
                    "url": f"https://{store_url}/products/{node.get('handle')}" if node.get('handle') else ""
                }
    except Exception as e:
        logger.exception("Failed to check duplicate product by title: %s", e)
    return None


def upload_product_media_files(
    product_id: Any,
    file_paths: List[str],
) -> List[Dict[str, Any]]:
    """
    Uploads a list of local images or videos to an existing Shopify product via the GraphQL Admin API.
    1. Creates a staged upload target for each file.
    2. Uploads the file bytes to the staged target.
    3. Associates the uploaded media with the product.
    Returns a list of created media objects (id, status, mediaContentType).
    """
    base_url, store_url, headers = _get_config()
    graphql_url = f"{base_url}/graphql.json"

    def _run_graphql(query: str, variables: Dict[str, Any], operation_name: str) -> Dict[str, Any]:
        try:
            logger.info("Executing Shopify GraphQL mutation: %s", operation_name)
            response = httpx.post(
                graphql_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Shopify GraphQL mutation '%s' failed (%s): %s",
                operation_name,
                exc.response.status_code,
                exc.response.text,
            )
            raise ShopifyAPIError(
                f"Shopify GraphQL API error ({exc.response.status_code}): {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Shopify GraphQL request failed for '%s': %s", operation_name, exc)
            raise ShopifyAPIError(f"Shopify GraphQL request failed: {exc}") from exc

        data = response.json()
        if "errors" in data:
            logger.error("Shopify GraphQL '%s' returned errors: %s", operation_name, data["errors"])
            raise ShopifyAPIError(f"Shopify GraphQL errors: {data['errors']}")
        return data

    uploaded_media = []

    staged_mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    media_mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          id
          status
          mediaContentType
        }
        mediaUserErrors {
          field
          message
        }
      }
    }
    """

    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.warning("Media path does not exist: %s", file_path)
            continue

        filename = os.path.basename(file_path)
        logger.info("Starting staged upload for file: %s", filename)

        # Detect MIME type and Resource type
        mime_type, resource_type = get_mime_type(file_path)

        # Step A: stagedUploadsCreate
        staged_input = {
            "filename": filename,
            "mimeType": mime_type,
            "httpMethod": "POST",
            "resource": resource_type
        }
        
        # File size is mandatory for videos and files
        if resource_type in ("VIDEO", "FILE", "MODEL_3D"):
            staged_input["fileSize"] = str(os.path.getsize(file_path))

        staged_data = _run_graphql(
            query=staged_mutation,
            variables={"input": [staged_input]},
            operation_name="stagedUploadsCreate"
        )

        create_result = staged_data.get("data", {}).get("stagedUploadsCreate", {})
        user_errors = create_result.get("userErrors", [])
        if user_errors:
            error_msg = f"stagedUploadsCreate userErrors: {user_errors}"
            logger.error(error_msg)
            raise ShopifyAPIError(error_msg)

        targets = create_result.get("stagedTargets", [])
        if not targets:
            raise ShopifyAPIError("stagedUploadsCreate did not return stagedTargets.")

        target = targets[0]
        target_url = target.get("url")
        resourceUrl = target.get("resourceUrl")
        parameters = target.get("parameters", [])

        if not target_url or not resourceUrl:
            raise ShopifyAPIError("Invalid stagedTarget response from Shopify.")

        # Step B: POST actual bytes as multipart form data
        logger.info("Uploading bytes to target URL: %s", target_url)
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            # Compile parameters in order, placing 'file' at the very end
            multipart_fields = []
            for param in parameters:
                multipart_fields.append((param.get("name"), param.get("value")))

            # The 'file' field MUST be the last field in the request
            multipart_fields.append(("file", (filename, file_bytes, mime_type)))

            # Send request
            upload_response = httpx.post(
                target_url,
                files=multipart_fields,
                timeout=60 # Videos might take longer
            )
            upload_response.raise_for_status()
            logger.info("Successfully uploaded file bytes to Shopify storage.")
        except httpx.HTTPError as exc:
            logger.error("Failed to upload file bytes to staged upload URL: %s", exc)
            raise ShopifyAPIError(f"Staged file upload failed: {exc}") from exc

        # Step C: productCreateMedia
        logger.info("Associating resource URL with product: %s", product_id)
        media_input = {
            "originalSource": resourceUrl,
            "mediaContentType": resource_type
        }

        # Product ID needs to be shopify GID format: gid://shopify/Product/{product_id}
        gid_product_id = str(product_id)
        if not gid_product_id.startswith("gid://shopify/Product/"):
            gid_product_id = f"gid://shopify/Product/{product_id}"

        media_data = _run_graphql(
            query=media_mutation,
            variables={
                "productId": gid_product_id,
                "media": [media_input]
            },
            operation_name="productCreateMedia"
        )

        media_result = media_data.get("data", {}).get("productCreateMedia", {})
        media_user_errors = media_result.get("mediaUserErrors", [])
        if media_user_errors:
            error_msg = f"productCreateMedia mediaUserErrors: {media_user_errors}"
            logger.error(error_msg)
            raise ShopifyAPIError(error_msg)

        media_objects = media_result.get("media", [])
        if media_objects:
            uploaded_media.extend(media_objects)
            logger.info("Successfully created product media: %s", media_objects[0])

    return uploaded_media