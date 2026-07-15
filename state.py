from typing import Dict, Any, Optional
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

    # ------------------------
    # Shopify
    # ------------------------

    shopify_product: Optional[Dict[str, Any]] = None

    shopify_product_id: Optional[int] = None

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

    errors: Dict[str, str] = Field(default_factory=dict)