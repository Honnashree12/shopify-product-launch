import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import cv2

from google.adk.tools.tool_context import ToolContext
from shopify_client import (
    create_product,
    update_product,
    get_product,
    get_product_by_sku,
    get_product_by_title,
    ShopifyAPIError,
)
from services.shopify_media_service import ShopifyMediaService
from google import genai
from google.genai import types
import tools.file_extractor as file_extractor

logger = logging.getLogger("folder_tools")


def find_product_root(folder_path: str) -> str:
    """
    Finds the root directory containing product assets (or product.json).
    Recursively descends single-subdirectory paths to handle arbitrary nesting.
    """
    if not os.path.exists(folder_path):
        return folder_path

    # If product.json exists directly, this is the root
    if any(f.lower() == "product.json" for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))):
        return folder_path

    # Check for single subdirectory
    subdirs = [
        os.path.join(folder_path, d)
        for d in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, d)) and not d.startswith(".")
    ]
    if len(subdirs) == 1:
        return find_product_root(subdirs[0])

    return folder_path


def get_genai_client():
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True" or "GOOGLE_API_KEY" not in os.environ:
        return genai.Client()
    return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def ingest_and_extract_folder_tool(tool_context: ToolContext) -> str:
    """
    Recursively scans folder, extracts content from multiple formats (PDF, DOCX, XLSX, CSV, JSON, TXT/MD),
    performs safe image/video conversion, and maps fields using Gemini.
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."

    raw_path = state.get("product_folder_path")
    if not raw_path:
        state["workflow_error"] = "product_folder_path not found in session state."
        return "Failed: product_folder_path not found."

    product_dir = find_product_root(raw_path)
    logger.info("Ingesting product folder from root: %s", product_dir)

    if not os.path.exists(product_dir):
        state["workflow_error"] = f"Product directory does not exist: {product_dir}"
        return f"Failed: directory {product_dir} does not exist."

    all_files = file_extractor.scan_directory(product_dir)
    conversions = []
    document_contents = []
    media_metadata = []
    
    detected_images = []
    detected_videos = []
    unsupported_media = []

    for file_path in all_files:
        basename = os.path.basename(file_path)
        if basename.startswith(".") or "_converted" in basename:
            continue
        ext = os.path.splitext(file_path)[1].lower()

        # Handle Document/Structured files
        if ext == ".json":
            is_malformed = False
            try:
                with open(file_path, "r", encoding="utf-8") as jf:
                    json.load(jf)
            except Exception:
                is_malformed = True
            
            if is_malformed:
                content = file_extractor.extract_csv(file_path)
                document_contents.append(f"=== File (Malformed JSON as Text): {basename} ===\n{content}\n")
                conversions.append(f"Fallback: Read malformed JSON {basename} as plain text.")
            else:
                content = file_extractor.extract_json(file_path)
                document_contents.append(f"=== File: {basename} ===\n{content}\n")
        elif ext == ".pdf":
            content = file_extractor.extract_pdf(file_path)
            document_contents.append(f"=== File: {basename} ===\n{content}\n")
        elif ext == ".docx":
            content = file_extractor.extract_docx(file_path)
            document_contents.append(f"=== File: {basename} ===\n{content}\n")
        elif ext in (".xlsx", ".xls"):
            content = file_extractor.extract_xlsx(file_path)
            document_contents.append(f"=== File: {basename} ===\n{content}\n")
        elif ext == ".csv":
            content = file_extractor.extract_csv(file_path)
            document_contents.append(f"=== File: {basename} ===\n{content}\n")
        elif ext in (".txt", ".md") or "readme" in basename.lower():
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as tf:
                    content = tf.read()
            except Exception:
                content = ""
            if content:
                document_contents.append(f"=== File: {basename} ===\n{content}\n")

        # Handle Images
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".tiff", ".bmp"):
            conv_path, converted = file_extractor.convert_image_if_needed(file_path)
            if converted:
                conversions.append(f"Converted unsupported image {basename} to PNG format.")
                metadata = file_extractor.get_image_metadata(conv_path)
                detected_images.append(conv_path)
            elif ext in (".tiff", ".bmp"):
                unsupported_media.append({"filename": basename, "reason": "Shopify upload compatibility"})
                continue
            else:
                metadata = file_extractor.get_image_metadata(file_path)
                detected_images.append(file_path)
            
            media_metadata.append(metadata)

        # Handle Videos
        elif ext in (".mp4", ".mov", ".webm", ".avi", ".mkv", ".wmv"):
            try:
                cap = cv2.VideoCapture(file_path)
                is_valid = cap.isOpened()
                cap.release()
            except Exception:
                is_valid = False
            
            if not is_valid:
                unsupported_media.append({"filename": basename, "reason": "Corrupted or unreadable video file"})
                continue
                
            conv_path, converted = file_extractor.convert_video_if_needed(file_path)
            if converted:
                conversions.append(f"Converted unsupported video {basename} to MP4 format (audio track omitted).")
                metadata = file_extractor.get_video_metadata(conv_path)
                detected_videos.append(conv_path)
            elif ext in (".webm", ".avi", ".mkv", ".wmv"):
                unsupported_media.append({"filename": basename, "reason": "Shopify upload compatibility"})
                continue
            else:
                metadata = file_extractor.get_video_metadata(file_path)
                detected_videos.append(file_path)
                
            media_metadata.append(metadata)

    # Call Gemini to perform intelligent field mapping, category inference, conflict checks
    extracted_text_blocks = "\n".join(document_contents)
    media_metadata_json = json.dumps(media_metadata, indent=2)

    prompt = f"""
You are the Ingestion and AI Field Mapping Agent.
Your job is to read the extracted file contents from a product folder and map them to Shopify product fields.

Here are the extracted file contents:
{extracted_text_blocks}

Also, here is the list of media files found in the directory and their metadata:
{media_metadata_json}

Your task is to analyze these inputs and output a valid JSON matching the following structure:
{{
  "title": str or null,
  "description": str,
  "price": float or null,
  "compare_at_price": float or null,
  "cost_per_item": float or null,
  "category": str or null,
  "product_type": str or null,
  "vendor": str or null,
  "sku": str or null,
  "barcode": str or null,
  "track_inventory": bool,
  "inventory_quantity": int or null,
  "inventory_locations": dict of str to int,
  "sell_out_of_stock": bool,
  "requires_shipping": bool,
  "weight": float or null,
  "weight_unit": str,
  "country_of_origin": str or null,
  "hs_code": str or null,
  "status": "DRAFT" or "ACTIVE",
  "tags": list of str,
  "seo_title": str or null,
  "seo_description": str or null,
  "handle": str or null,
  "variants": list of dicts,
  "confidence": dict of str to str,
  "conflicts": list of dicts,
  "missing_fields": list of str,
  "media_ranking": list of dicts
}}

Rules for extraction:
1. Price synonyms: "MRP" or "List Price" -> compare_at_price; "Selling Price" or "Sale Price" -> price; "Stock" or "Qty" -> inventory_quantity; "Brand" or "Manufacturer" -> vendor.
2. In description: combine primary details, specifications, instructions, marketing content intelligently.
3. In confidence: mark field extraction confidence based on data clarity (HIGH, MEDIUM, LOW).
4. In conflicts: if price, SKU, title, or barcode differ between files, add them to conflicts (with keys "field" and "message") and set confidence of that field to "LOW".
5. In missing_fields: add required fields ("title", "description", "price") if completely missing from the inputs.
6. In media_ranking: classify and rank all images/videos from the metadata. Mark logos/unrelated screenshots/duplicate images as is_product_media = false. Priority: hero/main first, then product, secondary, and video.
7. If the product represents a digital item, workshop, or course, set requires_shipping to false.

Return ONLY the raw JSON output.
"""

    try:
        client = get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        manifest = json.loads(response.text.strip())
        logger.info("AI field mapping completed successfully.")
    except Exception as e:
        logger.error("Gemini field mapping failed: %s", e)
        # Fallback empty manifest
        manifest = {
            "title": None,
            "description": "",
            "price": None,
            "confidence": {},
            "conflicts": [],
            "missing_fields": ["title", "description", "price"],
            "media_ranking": []
        }

    # Rank and order the detected images and videos based on AI classification
    final_images = []
    final_videos = []
    rankings = manifest.get("media_ranking") or []
    
    def get_rank_val(x):
        r = x.get("rank")
        if isinstance(r, (int, float)):
            return int(r)
        if isinstance(r, str) and r.isdigit():
            return int(r)
        return 99
    rankings = sorted(rankings, key=get_rank_val)
    
    for r in rankings:
        if r.get("is_product_media", True):
            path = r.get("file_path")
            if path and os.path.exists(path):
                if r.get("type") == "IMAGE":
                    final_images.append(path)
                elif r.get("type") == "VIDEO":
                    final_videos.append(path)

    # Fallback if AI didn't return list
    if not final_images:
        final_images = detected_images
    if not final_videos:
        final_videos = detected_videos

    # Save to state
    state["manifest"] = manifest
    state["conversions"] = conversions
    state["unsupported_media"] = unsupported_media
    
    state["product_name"] = manifest.get("title")
    state["product_description"] = manifest.get("description")
    state["product_price"] = manifest.get("price")
    state["product_category"] = manifest.get("product_type") or manifest.get("category")
    state["vendor"] = manifest.get("vendor")
    state["tags"] = manifest.get("tags") or []
    state["sku"] = manifest.get("sku")
    state["inventory_quantity"] = manifest.get("inventory_quantity")
    state["product_status"] = manifest.get("status") or "DRAFT"
    
    state["detected_images"] = final_images
    state["detected_videos"] = final_videos

    return (
        f"Folder Ingestion complete.\n"
        f"Extracted Title: {manifest.get('title')}\n"
        f"Extracted Price: {manifest.get('price')}\n"
        f"Detected Images: {len(final_images)}\n"
        f"Detected Videos: {len(final_videos)}\n"
        f"Conversions: {len(conversions)}"
    )


def validate_folder_data_tool(tool_context: ToolContext) -> str:
    """
    Validates extracted folder data, checks conflicts and missing required information,
    and pauses for preview.
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."

    manifest = state.get("manifest") or {}
    missing = manifest.get("missing_fields") or []
    conflicts = manifest.get("conflicts") or []

    # Pause for preview if not approved and in preview mode
    if not state.get("approved_to_publish", False) and state.get("preview_mode", True):
        state["status"] = "awaiting_approval"
        state["missing_fields_list"] = missing
        state["conflicts_list"] = conflicts
        
        msg = "Validation paused: Product creation preview generated."
        if missing:
            msg += f" Missing required fields: {', '.join(missing)}."
        if conflicts:
            msg += f" Mapped conflicts detected: {len(conflicts)}."
        return msg

    title = state.get("product_name")
    description = state.get("product_description")
    price = state.get("product_price")

    missing_fields = []
    if not title:
        missing_fields.append("title")
    if not description:
        missing_fields.append("description")
    if price is None:
        missing_fields.append("price")

    if missing_fields:
        err_msg = (
            f"PRODUCT CREATION STOPPED\n\n"
            f"Missing required information:\n" + "\n".join(f"- {f}" for f in missing_fields) + "\n\n"
            f"Please resolve these fields and try again."
        )
        state["workflow_error"] = err_msg
        return err_msg

    try:
        price_val = float(price)
        if price_val < 0:
            err_msg = "PRODUCT CREATION STOPPED\n\nPrice cannot be negative."
            state["workflow_error"] = err_msg
            return err_msg
    except (ValueError, TypeError) as e:
        err_msg = f"PRODUCT CREATION STOPPED\n\nInvalid price value: {price}. Reason: {e}"
        state["workflow_error"] = err_msg
        return err_msg

    return "Product folder validation passed. Ready for creation."


def create_shopify_product_tool(tool_context: ToolContext) -> str:
    """
    Creates or updates the Shopify product after validation.
    Handles duplicate checking and duplicate actions (CREATE, UPDATE, CANCEL).
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."

    # Preview review pause check
    if not state.get("approved_to_publish", False) and state.get("preview_mode", True):
        state["status"] = "awaiting_approval"
        return "Awaiting user approval before creation."

    manifest = state.get("manifest") or {}
    title = state.get("product_name")
    description = state.get("product_description")
    price = state.get("product_price")
    sku = state.get("sku")
    
    duplicate_action = state.get("duplicate_action") or "ASK"

    # Duplicate Detection
    existing_product = None
    if sku:
        existing_product = get_product_by_sku(sku)
    if not existing_product and title:
        existing_product = get_product_by_title(title)

    if existing_product:
        if duplicate_action == "ASK":
            state["status"] = "awaiting_approval"
            state["duplicate_detected"] = True
            state["existing_product_id"] = existing_product["product_id"]
            state["existing_product_title"] = existing_product["title"]
            state["existing_product_url"] = existing_product["url"]
            return f"Product duplicate detected. Action required: Create, Update, or Cancel."
        elif duplicate_action == "CANCEL":
            err_msg = f"PRODUCT CREATION CANCELLED\n\nDuplicate product detected with Title '{existing_product['title']}'."
            state["workflow_error"] = err_msg
            return err_msg

    # Create or Update Product on Shopify
    try:
        compare_at = manifest.get("compare_at_price")
        cost = manifest.get("cost_per_item")
        barcode = manifest.get("barcode")
        track_inv = manifest.get("track_inventory", True)
        sell_out = manifest.get("sell_out_of_stock", False)
        req_ship = manifest.get("requires_shipping", True)
        weight = manifest.get("weight")
        weight_unit = manifest.get("weight_unit", "kg")
        origin = manifest.get("country_of_origin")
        hs_code = manifest.get("hs_code")
        status = str(state.get("product_status") or "DRAFT").lower()
        
        seo_title = manifest.get("seo_title") or title
        seo_desc = manifest.get("seo_description") or description[:155] if description else ""
        handle = manifest.get("handle")
        
        options = manifest.get("options")
        variants = manifest.get("variants")
        inv_locations = manifest.get("inventory_locations")

        tags_list = state.get("tags") or []
        tags = ", ".join(tags_list) if tags_list else None

        if existing_product and duplicate_action == "UPDATE":
            product_id = existing_product["product_id"]
            logger.info("Updating existing Shopify product ID %s...", product_id)
            product = update_product(
                product_id=product_id,
                title=title,
                body_html=description,
                price=float(price),
                product_type=state.get("product_category"),
                status=status,
                tags=tags,
                vendor=state.get("vendor"),
                sku=sku,
                inventory_quantity=state.get("inventory_quantity"),
                compare_at_price=compare_at,
                barcode=barcode,
                track_inventory=track_inv,
                sell_out_of_stock=sell_out,
                requires_shipping=req_ship,
                weight=weight,
                weight_unit=weight_unit,
                country_of_origin=origin,
                hs_code=hs_code,
                cost_per_item=cost,
                options=options,
                variants=variants,
                seo_title=seo_title,
                seo_description=seo_desc,
                handle=handle,
                inventory_locations=inv_locations,
            )
            state["shopify_product"] = product
            state["shopify_product_id"] = product["id"]
            state["shopify_url"] = product["url"]
            state["duplicate_action_resolved"] = "UPDATED"
            
            variant_id = None
            if product.get("variants"):
                variant_id = product["variants"][0].get("id")
            state["shopify_variant_id"] = variant_id
            
            return f"Shopify product ID {product_id} updated successfully."
        else:
            logger.info("Creating new Shopify product...")
            product = create_product(
                title=title,
                body_html=description,
                price=float(price),
                product_type=state.get("product_category"),
                status=status,
                tags=tags,
                vendor=state.get("vendor"),
                sku=sku,
                inventory_quantity=state.get("inventory_quantity"),
                compare_at_price=compare_at,
                barcode=barcode,
                track_inventory=track_inv,
                sell_out_of_stock=sell_out,
                requires_shipping=req_ship,
                weight=weight,
                weight_unit=weight_unit,
                country_of_origin=origin,
                hs_code=hs_code,
                cost_per_item=cost,
                options=options,
                variants=variants,
                seo_title=seo_title,
                seo_description=seo_desc,
                handle=handle,
                inventory_locations=inv_locations,
            )
            state["shopify_product"] = product
            state["shopify_product_id"] = product["id"]
            state["shopify_url"] = product["url"]
            
            variant_id = None
            if product.get("variants"):
                variant_id = product["variants"][0].get("id")
            state["shopify_variant_id"] = variant_id
            
            return f"Shopify product created successfully. ID: {product['id']}"
            
    except ShopifyAPIError as e:
        err_msg = f"Shopify API error during creation/update: {e}"
        state["workflow_error"] = err_msg
        return err_msg
    except Exception as e:
        err_msg = f"Unexpected error during product creation/update: {e}"
        state["workflow_error"] = err_msg
        return err_msg


def upload_folder_media_tool(tool_context: ToolContext) -> str:
    """
    Uploads and attaches images and videos to the Shopify product.
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."

    product_id = state.get("shopify_product_id")
    if not product_id:
        state["workflow_error"] = "Shopify product ID is missing in state."
        return "Failed: product ID missing."

    detected_images = state.get("detected_images") or []
    detected_videos = state.get("detected_videos") or []

    upload_results = []

    # Upload Images
    logger.info("Uploading images for product %s...", product_id)
    image_results = ShopifyMediaService.upload_and_attach_all_media(product_id, detected_images)
    upload_results.extend(image_results)

    # Upload Videos
    logger.info("Uploading videos for product %s...", product_id)
    video_results = ShopifyMediaService.upload_and_attach_all_media(product_id, detected_videos)
    upload_results.extend(video_results)

    state["media_upload_results"] = upload_results

    # Verify and retrieve active media list
    verified_media = ShopifyMediaService.verify_media(product_id)
    state["shopify_media"] = verified_media

    # Check for failures
    failed_media = [item.get("file_path") or item.get("image_path") or "unknown" for item in upload_results if not item.get("success")]
    success_count = len(upload_results) - len(failed_media)

    if failed_media:
        failed_list = ", ".join(failed_media)
        logger.warning("Some media files failed to upload: %s", failed_list)
        return f"Media upload completed with partial failures. Uploaded {success_count}/{len(upload_results)} files. Failed files: {failed_list}"

    return f"Media upload completed successfully. Uploaded {success_count} files."


def verify_folder_product_tool(tool_context: ToolContext) -> str:
    """
    Verify the created product on Shopify.
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."
    product_id = state.get("shopify_product_id")
    expected_price = state.get("product_price")
    expected_title = state.get("product_name")

    result = {
        "product_exists": False,
        "status_active": False,
        "price_matched": False,
        "purchasable": False,
        "errors": [],
    }

    if product_id is None:
        result["errors"].append("shopify_product_id missing")
        state["verification_result"] = result
        return "Verification check complete. Result: Failed (shopify_product_id missing)."

    try:
        product = get_product(product_id)
        result["product_exists"] = True

        # Check status
        expected_status = str(state.get("product_status") or "ACTIVE").lower()
        actual_status = str(product.get("status") or "").lower()
        if actual_status == expected_status:
            result["status_active"] = True
        else:
            result["errors"].append(f"Expected status '{expected_status}', got '{actual_status}'")

        # Check price
        actual_price = float(product.get("price", 0))
        expected_price_val = float(expected_price)
        if abs(actual_price - expected_price_val) < 0.01:
            result["price_matched"] = True
        else:
            result["errors"].append(f"Expected price {expected_price_val}, got {actual_price}")

        # Check SKU
        expected_sku = state.get("sku")
        if expected_sku and product.get("variants"):
            actual_sku = product["variants"][0].get("sku")
            if actual_sku != expected_sku:
                result["errors"].append(f"Expected SKU '{expected_sku}', got '{actual_sku}'")

        # Check Inventory Level
        expected_qty = state.get("inventory_quantity")
        if expected_qty is not None and product.get("variants"):
            actual_qty = product["variants"][0].get("inventory_quantity")
            if actual_qty is not None and actual_qty != expected_qty:
                result["errors"].append(f"Expected Inventory {expected_qty}, got {actual_qty}")

        has_variant = bool(product.get("variants"))
        if not has_variant:
            result["errors"].append("Product has no variants")

        result["purchasable"] = (
            result["product_exists"]
            and (expected_status != "active" or result["status_active"])
            and result["price_matched"]
            and has_variant
            and len(result["errors"]) == 0
        )

        state["verification_result"] = result

        if result["purchasable"] or (expected_status == "draft" and result["product_exists"] and len(result["errors"]) == 0):
            return "Verification check complete. Result: PASSED."

        errors_summary = "; ".join(result["errors"])
        return f"Verification check complete. Result: FAILED ({errors_summary})."

    except Exception as e:
        logger.error("Shopify verification failed: %s", e)
        result["errors"].append(str(e))
        state["verification_result"] = result
        return f"Verification check complete. Result: Failed ({e})"


def generate_folder_reports_tool(tool_context: ToolContext) -> str:
    """
    Generate and save Markdown and JSON launch reports for the folder flow.
    """
    state = tool_context.state
    if state.get("workflow_error"):
        return "Skipping due to previous errors."

    outputs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
    os.makedirs(outputs_dir, exist_ok=True)

    markdown_path = os.path.join(outputs_dir, "launch_report.md")
    json_path = os.path.join(outputs_dir, "launch_report.json")

    product = state.get("shopify_product") or {}
    verification = state.get("verification_result") or {}
    upload_results = state.get("media_upload_results") or []
    
    total_imgs = len(state.get("detected_images") or [])
    total_vids = len(state.get("detected_videos") or [])
    
    failed_uploads = [item for item in upload_results if not item.get("success")]
    success_imgs = sum(1 for item in upload_results if item.get("success") and item.get("media_content_type") == "IMAGE")
    success_vids = sum(1 for item in upload_results if item.get("success") and item.get("media_content_type") == "VIDEO")

    # Construct frontend friendly SEO metadata
    keywords = ", ".join(state.get("tags") or [])
    seo_metadata = {
        "title": state.get("product_name"),
        "description": state.get("product_description"),
        "keywords": keywords,
        "slug": str(state.get("product_name") or "").lower().replace(" ", "-")
    }
    state["seo_metadata"] = seo_metadata
    state["generated_description"] = state.get("product_description")

    action_word = "UPDATED" if state.get("duplicate_action_resolved") == "UPDATED" else "CREATED"

    # Generate output text report representation
    if not verification.get("errors"):
        report_status = "SUCCESS"
        status_line = f"========================================\nSHOPIFY PRODUCT {action_word} SUCCESSFULLY\n========================================"
    else:
        report_status = "FAILED"
        status_line = f"========================================\nPRODUCT {action_word} FAILED\n========================================"

    report_text = f"""{status_line}

Product:
{state.get("product_name")}

Shopify Product ID:
{product.get("id")}

Action:
{action_word}

Status:
{str(state.get("product_status")).upper()}

Price:
{state.get("currency") or "₹"}{state.get("product_price")}

SKU:
{state.get("sku") or "N/A"}

Images:
{success_imgs}/{total_imgs} uploaded successfully

Videos:
{success_vids}/{total_vids} uploaded successfully
"""
    # Conversions
    conversions = state.get("conversions") or []
    if conversions:
        report_text += "\nMedia Conversions:\n"
        for c in conversions:
            report_text += f"- {c}\n"

    # Unsupported Media
    unsupported = state.get("unsupported_media") or []
    if unsupported:
        report_text += "\nUnsupported / Ignored Media:\n"
        for u in unsupported:
            report_text += f"- {u.get('filename')}: {u.get('reason')}\n"

    if failed_uploads:
        report_text += "\nFailed Uploads:\n"
        for item in failed_uploads:
            path = item.get("file_path") or item.get("image_path") or "unknown"
            reason = item.get("error") or "staged upload failed"
            report_text += f"- {os.path.basename(path)}: {reason}\n"

    report_text += f"\nProduct URL:\n{state.get('shopify_url')}\n========================================"

    state["folder_report"] = report_text

    # Generate Markdown Report File
    markdown_report = f"""# Shopify Product Ingestion Report

## Launch Status: {report_status}

{report_text}

---

## Detailed Data
* **Title:** {state.get("product_name")}
* **Category:** {state.get("product_category")}
* **Vendor:** {state.get("vendor")}
* **Inventory Quantity:** {state.get("inventory_quantity")}

## Verification Errors
{json.dumps(verification.get("errors") or [], indent=2)}
"""

    # Generate JSON Report File
    try:
        json_report = json.dumps(dict(state), indent=4, default=str)
    except Exception:
        json_report = json.dumps({
            "product_name": state.get("product_name"),
            "shopify_product_id": product.get("id"),
            "shopify_url": state.get("shopify_url"),
            "verification": verification,
            "media_results": upload_results
        }, indent=4)

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_report)

    state["markdown_report_path"] = markdown_path
    state["json_report_path"] = json_path

    try:
        print("\n" + report_text + "\n")
    except UnicodeEncodeError:
        print("\n" + report_text.encode("ascii", "replace").decode("ascii") + "\n")

    return "Launch reports and text representation generated successfully."
