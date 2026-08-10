from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ProductLaunchState(BaseModel):

    # ------------------------
    # Input
    # ------------------------

    product_name: str

    raw_description: str

    price: Optional[float] = None

    category: Optional[str] = None

    # ------------------------
    # AI Outputs
    # ------------------------

    generated_description: Optional[str] = None

    seo_metadata: Optional[Dict[str, Any]] = None

    marketing: Optional[Dict[str, Any]] = None

    marketing_assets: Optional[Dict[str, Any]] = None

    # ------------------------
    # Images
    # ------------------------

    image_prompts: Optional[Dict[str, str]] = None

    image_paths: Optional[List[str]] = None

    shopify_media: Optional[List[Dict[str, Any]]] = None

    # ------------------------
    # Shopify
    # ------------------------

    shopify_product: Optional[Dict[str, Any]] = None

    shopify_product_id: Optional[int] = None

    shopify_variant_id: Optional[int] = None

    shopify_url: Optional[str] = None

    # ------------------------
    # Verification
    # ------------------------

    verification_result: Optional[Dict[str, Any]] = None

    # ------------------------
    # Reports
    # ------------------------

    markdown_report_path: Optional[str] = None

    json_report_path: Optional[str] = None

    # ------------------------
    # Workflow
    # ------------------------

    status: str = "pending"

    approved_to_publish: bool = True

    workshop_id: Optional[str] = None

    product_folder_path: Optional[str] = None

    sku: Optional[str] = None

    inventory_quantity: Optional[int] = None

    product_status: Optional[str] = "active"

    detected_images: Optional[List[str]] = None

    detected_videos: Optional[List[str]] = None

    media_upload_results: Optional[List[Dict[str, Any]]] = None

    folder_report: Optional[str] = None

    preview_mode: bool = True

    manifest: Optional[Dict[str, Any]] = None

    conversions: Optional[List[str]] = None

    unsupported_media: Optional[List[Dict[str, Any]]] = None

    missing_fields_list: Optional[List[str]] = None

    conflicts_list: Optional[List[Dict[str, Any]]] = None

    duplicate_detected: bool = False

    existing_product_id: Optional[int] = None

    existing_product_title: Optional[str] = None

    existing_product_url: Optional[str] = None

    duplicate_action: str = "ASK"

    duplicate_action_resolved: Optional[str] = None

    errors: Dict[str, str] = Field(default_factory=dict)