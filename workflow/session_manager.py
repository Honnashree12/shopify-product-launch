import uuid
from typing import Optional, Dict, Any

from workflow.adk_runner import session_service, APP_NAME

USER_ID = "default-user"


async def create_session(initial_state: Optional[Dict[str, Any]] = None):

    state = {
        "product_name": "",
        "product_description": "",
        "product_price": None,
        "product_category": "",
        "generated_description": "",
        "seo_metadata": {},
        "marketing": {},
        "image_prompts": {},
        "shopify_product": {},
        "shopify_product_id": None,
        "shopify_url": None,
        "verification_result": {},
        "markdown_report_path": "",
        "json_report_path": "",
    }

    if initial_state:
        state.update(initial_state)

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=str(uuid.uuid4()),
        state=state,
    )

    return session