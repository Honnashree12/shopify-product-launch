import uuid
from typing import Optional, Dict, Any

from workflow.adk_runner import session_service, APP_NAME

USER_ID = "default-user"


async def create_session(initial_state: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None):

    state = {
        "product_name": "",
        "product_description": "",
        "product_price": None,
        "product_category": "",
        "generated_description": "",
        "seo_metadata": {},
        "marketing": {},
        "marketing_assets": {},
        "image_prompts": {},
        "shopify_product": {},
        "shopify_product_id": None,
        "shopify_variant_id": None,
        "shopify_url": None,
        "verification_result": {},
        "markdown_report_path": "",
        "json_report_path": "",
        "workshop_id": None,
        "approved_to_publish": True,
        "product_folder_path": None,
        "sku": None,
        "inventory_quantity": None,
        "product_status": "active",
        "detected_images": [],
        "detected_videos": [],
        "media_upload_results": [],
        "folder_report": "",
    }

    if initial_state:
        state.update(initial_state)

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id or str(uuid.uuid4()),
        state=state,
    )

    return session