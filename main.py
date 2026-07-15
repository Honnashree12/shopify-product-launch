import uuid
import asyncio
import os
from typing import Optional, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from google.genai import types

from state import ProductLaunchState

from workflow.adk_runner import runner, session_service, APP_NAME
from workflow.session_manager import create_session, USER_ID

load_dotenv()

app = FastAPI(
    title="AI Shopify Product Launch Agent API",
    description="Google ADK Multi-Agent Shopify Workflow",
    version="1.0.0",
)

# NOTE: The mock Shopify API router has been removed from this app.
# Publisher/Verification agents now call the real Shopify Admin API
# directly via shopify_client.py using SHOPIFY_STORE_URL /
# SHOPIFY_ACCESS_TOKEN / SHOPIFY_API_VERSION from the environment.
# The shopify_mock/ module itself is left in place (unused) and can
# still be run standalone for local testing if ever needed.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/", include_in_schema=False)
def serve_launch_console():
    """Serves the Launch Console frontend."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ProductLaunchInput(BaseModel):
    product_name: str
    raw_description: str
    price: Optional[float] = None
    category: Optional[str] = None


active_sessions: Dict[str, ProductLaunchState] = {}


def run_adk_workflow_background(session_id: str):

    print("\n===================================")
    print("SHOPIFY PRODUCT LAUNCH STARTED")
    print("===================================")

    state = active_sessions.get(session_id)

    if state is None:
        return

    try:

        state.status = "running"

        session = asyncio.run(
            create_session(
                {
                    "product_name": state.product_name,
                    "product_description": state.raw_description,
                    "product_price": state.price,
                    "product_category": state.category,
                }
            )
        )

        print(f"ADK Session Created: {session.id}")

        print("\n===== INITIAL SESSION STATE =====")
        print(dict(session.state))
        print("=================================\n")

        prompt = """
You are launching ONE Shopify product.

The product details are already stored in the workflow state.

Use ONLY the values returned by get_product_context().

Never invent another product.

Begin the workflow.
"""

        message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        events = runner.run(
            user_id=USER_ID,
            session_id=session.id,
            new_message=message,
        )

        for event in events:
            print(event)

        # IMPORTANT: `session` above is a snapshot captured BEFORE the
        # workflow ran. runner.run() updates the session inside
        # session_service's internal store, not this local object, so
        # reading session.state here would return stale/empty values.
        # Re-fetch the session to get the final, merged state.
        final_session = asyncio.run(
            session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session.id,
            )
        )

        final_state = final_session.state

        print("\n===== FINAL SESSION STATE =====")
        print(dict(final_state))
        print("===============================\n")

        state.generated_description = final_state.get(
            "generated_description"
        )

        state.seo_metadata = final_state.get(
            "seo_metadata"
        )

        state.marketing = final_state.get(
            "marketing"
        )

        state.shopify_product = final_state.get(
            "shopify_product"
        )

        state.shopify_product_id = final_state.get(
            "shopify_product_id"
        )

        state.shopify_url = final_state.get(
            "shopify_url"
        )

        state.verification_result = final_state.get(
            "verification_result"
        )

        state.markdown_report_path = final_state.get(
            "markdown_report_path"
        )

        state.json_report_path = final_state.get(
            "json_report_path"
        )

        state.status = "completed"

        print("\n===================================")
        print("WORKFLOW COMPLETED")
        print("===================================")

    except Exception as e:

        print(e)

        state.status = "failed"
        state.errors["workflow_error"] = str(e)


@app.post("/launch", status_code=202)
def initiate_product_launch(
    raw_input: ProductLaunchInput,
    background_tasks: BackgroundTasks,
):

    session_id = str(uuid.uuid4())

    active_sessions[session_id] = ProductLaunchState(
        product_name=raw_input.product_name,
        raw_description=raw_input.raw_description,
        price=raw_input.price,
        category=raw_input.category,
        status="pending",
    )

    background_tasks.add_task(
        run_adk_workflow_background,
        session_id,
    )

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Workflow started successfully.",
        "status_endpoint": f"/status/{session_id}",
    }


@app.get("/status/{session_id}", response_model=ProductLaunchState)
def get_status(session_id: str):

    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return active_sessions[session_id]


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "runner": True,
    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )