import ssl_config  # noqa: F401 - must run before google/requests imports

import sys
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
import asyncio
import os
import logging
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from google.genai import types

from state import ProductLaunchState

from workflow.adk_runner import runner, folder_runner, session_service, APP_NAME
from workflow.session_manager import create_session, USER_ID
from fastapi import UploadFile, File, Form

load_dotenv()

logger = logging.getLogger(__name__)

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

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


class ProductLaunchInput(BaseModel):
    product_name: str
    raw_description: str
    price: Optional[float] = None
    category: Optional[str] = None


class RegistrationInput(BaseModel):
    child_name: str
    child_age: int
    school: str
    parent_name: str
    customer_email: str
    customer_phone: str
    emergency_contact: str


active_sessions: Dict[str, ProductLaunchState] = {}


def _workflow_completion_error(final_state: Dict) -> Optional[str]:
    """Return a user-facing error when an agent workflow stopped partway through.

    ADK can finish a run without raising an exception when an agent returns a
    normal response instead of its required tool call.  A completed runner is
    therefore not sufficient evidence that a product was published.
    """
    approved = final_state.get("approved_to_publish", False)
    
    required_values = {
        "generated_description": "copywriting",
        "seo_metadata": "SEO generation",
        "marketing": "marketing generation",
        "marketing_assets": "marketing details generation"
    }
    
    if approved:
        required_values.update({
            "shopify_product_id": "Shopify publishing",
            "shopify_url": "Shopify publishing",
            "verification_result": "Shopify verification",
            "markdown_report_path": "report generation",
            "json_report_path": "report generation",
        })
        
    missing_steps = sorted(
        {step for key, step in required_values.items() if not final_state.get(key)}
    )

    if approved:
        verification = final_state.get("verification_result")
        if verification and not verification.get("purchasable"):
            details = "; ".join(verification.get("errors") or [])
            return "Shopify verification failed" + (f": {details}" if details else ".")

    if missing_steps:
        return (
            "The launch pipeline ended before it finished: "
            + ", ".join(missing_steps)
            + "."
        )

    return None


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
                    "approved_to_publish": state.approved_to_publish,
                    "workshop_id": state.workshop_id,
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

        state.marketing_assets = final_state.get(
            "marketing_assets"
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

        state.shopify_variant_id = final_state.get(
            "shopify_variant_id"
        )

        state.verification_result = final_state.get(
            "verification_result"
        )

        state.image_prompts = final_state.get(
            "image_prompts"
        )

        state.image_paths = final_state.get(
            "image_paths"
        )

        state.shopify_media = final_state.get(
            "shopify_media"
        )

        state.markdown_report_path = final_state.get(
            "markdown_report_path"
        )

        state.json_report_path = final_state.get(
            "json_report_path"
        )

        state.workshop_id = final_state.get(
            "workshop_id"
        )
        state.approved_to_publish = final_state.get(
            "approved_to_publish", True
        )

        completion_error = _workflow_completion_error(final_state)

        # Save to database if this was a workshop generation
        if state.workshop_id:
            try:
                from data.database import update_workshop_ai_content, publish_workshop
                
                db_status = "generated"
                if completion_error:
                    db_status = "failed"
                elif state.approved_to_publish:
                    db_status = "published"
                    
                updates = {
                    "generated_description": state.generated_description,
                    "seo_metadata": state.seo_metadata,
                    "marketing": state.marketing_assets or state.marketing,
                    "image_prompts": state.image_prompts,
                    "image_paths": state.image_paths,
                    "status": db_status
                }
                update_workshop_ai_content(state.workshop_id, updates)
                
                if db_status == "published" and state.shopify_product_id:
                    variant_id = state.shopify_variant_id
                    if not variant_id and state.shopify_product and state.shopify_product.get("variants"):
                        variant_id = state.shopify_product["variants"][0].get("id")
                    publish_workshop(
                        state.workshop_id, 
                        state.shopify_product_id, 
                        state.shopify_url or "", 
                        state.shopify_media,
                        shopify_variant_id=variant_id,
                    )
                logger.info("Successfully updated workshop DB status to '%s' for ID %s", db_status, state.workshop_id)
            except Exception as e:
                logger.exception("Failed to update workshop database status (non-fatal)")

        if completion_error:
            logger.error("Launch workflow %s was incomplete: %s", session_id, completion_error)
            state.status = "failed"
            state.errors["workflow_error"] = completion_error
            return

        state.status = "completed"

        print("\n===================================")
        print("WORKFLOW COMPLETED")
        print("===================================")

    except Exception as e:

        print(e)

        state.status = "failed"
        state.errors["workflow_error"] = str(e)


def run_folder_workflow_background(session_id: str):

    print("\n===================================")
    print("SHOPIFY FOLDER PRODUCT LAUNCH STARTED")
    print("===================================")

    state = active_sessions.get(session_id)

    if state is None:
        return

    try:

        state.status = "running"

        # Check if the ADK session already exists
        session_exists = False
        try:
            session = asyncio.run(
                session_service.get_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id,
                )
            )
            session_exists = True
        except Exception:
            pass

        if session_exists:
            # Update the existing session state with latest user resolutions/overrides
            session.state.update({
                "approved_to_publish": state.approved_to_publish,
                "duplicate_action": state.duplicate_action,
                "product_name": state.product_name,
                "product_description": state.raw_description,
                "product_price": state.price,
                "sku": state.sku,
                "inventory_quantity": state.inventory_quantity,
            })
            asyncio.run(session_service.save_session(session))
            print(f"ADK Folder Session Updated/Loaded: {session.id}")
        else:
            # First run: create a new session
            session = asyncio.run(
                create_session(
                    {
                        "product_folder_path": state.product_folder_path,
                        "approved_to_publish": state.approved_to_publish,
                        "duplicate_action": state.duplicate_action,
                        "preview_mode": state.preview_mode,
                    },
                    session_id=session_id
                )
            )
            print(f"ADK Folder Session Created: {session.id}")

        prompt = """
You are launching ONE Shopify product from a product folder.
The product folder path is stored in the workflow state as product_folder_path.
Begin the workflow to ingest, extract, validate, upload media, create, and verify.
"""

        message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        events = folder_runner.run(
            user_id=USER_ID,
            session_id=session.id,
            new_message=message,
        )

        for event in events:
            print(event)

        final_session = asyncio.run(
            session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session.id,
            )
        )

        final_state = final_session.state

        print("\n===== FINAL FOLDER SESSION STATE =====")
        print(dict(final_state))
        print("======================================\n")

        state.product_name = final_state.get("product_name", "")
        state.raw_description = final_state.get("product_description", "")
        state.price = final_state.get("product_price")
        state.category = final_state.get("product_category")
        state.vendor = final_state.get("vendor")
        state.tags = final_state.get("tags") or []
        state.sku = final_state.get("sku")
        state.inventory_quantity = final_state.get("inventory_quantity")
        state.product_status = final_state.get("product_status") or "DRAFT"
        
        state.shopify_product = final_state.get("shopify_product")
        state.shopify_product_id = final_state.get("shopify_product_id")
        state.shopify_url = final_state.get("shopify_url")
        state.shopify_variant_id = final_state.get("shopify_variant_id")
        state.shopify_media = final_state.get("shopify_media")
        
        state.verification_result = final_state.get("verification_result")
        state.markdown_report_path = final_state.get("markdown_report_path")
        state.json_report_path = final_state.get("json_report_path")
        
        state.seo_metadata = final_state.get("seo_metadata")
        state.generated_description = final_state.get("generated_description")
        state.folder_report = final_state.get("folder_report")

        # Copy manifest & preview fields
        state.status = final_state.get("status") or "completed"
        state.manifest = final_state.get("manifest")
        state.conversions = final_state.get("conversions")
        state.unsupported_media = final_state.get("unsupported_media")
        state.missing_fields_list = final_state.get("missing_fields_list")
        state.conflicts_list = final_state.get("conflicts_list")
        state.duplicate_detected = final_state.get("duplicate_detected", False)
        state.existing_product_id = final_state.get("existing_product_id")
        state.existing_product_title = final_state.get("existing_product_title")
        state.existing_product_url = final_state.get("existing_product_url")
        state.duplicate_action = final_state.get("duplicate_action", "ASK")
        state.duplicate_action_resolved = final_state.get("duplicate_action_resolved")

        # Cleanup temporary uploaded files if finished (not paused for approval)
        if state.status != "awaiting_approval":
            try:
                import shutil
                if state.product_folder_path and os.path.exists(state.product_folder_path):
                    shutil.rmtree(state.product_folder_path)
                    logger.info("Cleaned up temporary upload directory: %s", state.product_folder_path)
            except Exception as e:
                logger.error("Failed to cleanup temp upload directory: %s", e)

        # Check if the product was successfully created or if there were workflow errors
        workflow_err = final_state.get("workflow_error")
        if workflow_err:
            state.status = "failed"
            state.errors["workflow_error"] = workflow_err
            return

        if state.status == "awaiting_approval":
            print("\n===================================")
            print("FOLDER WORKFLOW PAUSED FOR APPROVAL")
            print("===================================")
            return

        if not final_state.get("shopify_product_id"):
            missing_fields = []
            if not final_state.get("product_name"):
                missing_fields.append("title")
            if not final_state.get("product_description"):
                missing_fields.append("description")
            if not final_state.get("product_price"):
                missing_fields.append("price")
            
            if missing_fields:
                error_msg = f"PRODUCT CREATION STOPPED\n\nMissing required information:\n" + "\n".join(f"- {f}" for f in missing_fields) + "\n\nPlease update the product folder and try again."
            else:
                error_msg = "Workflow failed to create the product on Shopify. Please check your shop credentials, duplicate settings, or network status."
            
            state.status = "failed"
            state.errors["workflow_error"] = error_msg
            return

        verification = state.verification_result
        if verification and not verification.get("purchasable"):
            status_expected = str(final_state.get("product_status") or "ACTIVE").lower()
            if status_expected == "draft" and verification.get("product_exists") and not verification.get("errors"):
                pass
            else:
                details = "; ".join(verification.get("errors") or [])
                state.status = "failed"
                state.errors["workflow_error"] = "Shopify verification failed" + (f": {details}" if details else ".")
                return

        state.status = "completed"

        print("\n===================================")
        print("FOLDER WORKFLOW COMPLETED")
        print("===================================")

    except Exception as e:

        print(e)
        # Clean up directory on error
        try:
            import shutil
            if state.product_folder_path and os.path.exists(state.product_folder_path):
                shutil.rmtree(state.product_folder_path)
        except Exception:
            pass

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
        "product_name": raw_input.product_name,
        "raw_description": raw_input.raw_description,
    }


class FolderLaunchApprovalInput(BaseModel):
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_price: Optional[float] = None
    sku: Optional[str] = None
    inventory_quantity: Optional[int] = None
    duplicate_action: Optional[str] = "CREATE"
    approved_to_publish: bool = True


@app.post("/launch-folder", status_code=202)
async def initiate_folder_launch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    preview: bool = Form(True),
):

    session_id = str(uuid.uuid4())
    temp_dir = os.path.abspath(os.path.join(OUTPUTS_DIR, "temp_uploads", session_id))
    os.makedirs(temp_dir, exist_ok=True)

    # Reconstruct folder structure
    for file in files:
        rel_path = file.filename.replace("\\", "/")
        while rel_path.startswith("/"):
            rel_path = rel_path[1:]
        if ".." in rel_path:
            continue
        
        file_dest = os.path.join(temp_dir, rel_path)
        os.makedirs(os.path.dirname(file_dest), exist_ok=True)
        
        with open(file_dest, "wb") as f:
            content = await file.read()
            f.write(content)

    # Initialize active session
    active_sessions[session_id] = ProductLaunchState(
        product_name="Folder Ingestion",
        raw_description="Ingesting product from folder...",
        product_folder_path=temp_dir,
        status="pending",
        preview_mode=preview,
        approved_to_publish=not preview,
    )

    background_tasks.add_task(
        run_folder_workflow_background,
        session_id,
    )

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Folder workflow started successfully.",
        "status_endpoint": f"/status/{session_id}",
    }


@app.post("/api/folder-launch/{session_id}/approve", status_code=202)
async def approve_folder_launch(
    session_id: str,
    approval_in: FolderLaunchApprovalInput,
    background_tasks: BackgroundTasks,
):
    state = active_sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    state.status = "running"
    state.approved_to_publish = approval_in.approved_to_publish
    state.duplicate_action = approval_in.duplicate_action or "CREATE"

    if approval_in.product_name:
        state.product_name = approval_in.product_name
    if approval_in.product_description:
        state.raw_description = approval_in.product_description
    if approval_in.product_price is not None:
        state.price = approval_in.product_price
    if approval_in.sku:
        state.sku = approval_in.sku
    if approval_in.inventory_quantity is not None:
        state.inventory_quantity = approval_in.inventory_quantity

    background_tasks.add_task(
        run_folder_workflow_background,
        session_id,
    )

    return {
        "session_id": session_id,
        "status": "running",
        "message": "Workflow approved and resuming in the background.",
    }


@app.get("/status/{session_id}", response_model=ProductLaunchState)
def get_status(session_id: str):

    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return active_sessions[session_id]


# =====================================================================
# Workshop Launch Platform REST API and Webhook Implementation
# =====================================================================
import hmac
import hashlib
import base64
from fastapi import Request
from pydantic import Field

class WorkshopCreateInput(BaseModel):
    name: str
    description: str
    date: str
    time: str
    duration: str
    venue: str
    age_group: str
    price: float
    topics: List[str] = []
    poster_path: Optional[str] = None
    video_url: Optional[str] = None
    sales_team_email: str

def slugify(text: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

@app.on_event("startup")
def on_startup():
    try:
        from data.database import init_db
        init_db()
        logger.info("SQLite database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)

@app.get("/api/dashboard/metrics")
def api_dashboard_metrics():
    from data.database import get_dashboard_metrics
    return get_dashboard_metrics()

@app.get("/api/workshops")
def api_get_workshops():
    from data.database import get_all_workshops
    return get_all_workshops()

@app.get("/api/workshops/{workshop_id}")
def api_get_workshop(workshop_id: str):
    from data.database import get_workshop
    w = get_workshop(workshop_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return w

@app.post("/api/workshops")
def api_create_workshop(input_data: WorkshopCreateInput):
    from data.database import create_workshop
    w_id = slugify(input_data.name)
    
    # Check if exists, append timestamp if duplicate
    from data.database import get_workshop
    if get_workshop(w_id):
        w_id = f"{w_id}-{int(datetime.utcnow().timestamp())}"
        
    workshop_data = input_data.dict()
    workshop_data["id"] = w_id
    workshop_data["status"] = "draft"
    
    create_workshop(workshop_data)
    return {"workshop_id": w_id, "status": "draft"}

@app.post("/api/workshops/{workshop_id}/generate", status_code=202)
def api_generate_workshop_campaign(workshop_id: str, background_tasks: BackgroundTasks):
    from data.database import get_workshop
    w = get_workshop(workshop_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
        
    session_id = str(uuid.uuid4())
    
    active_sessions[session_id] = ProductLaunchState(
        product_name=w["name"],
        raw_description=w["description"],
        price=w["price"],
        category="Workshop",
        status="pending",
        approved_to_publish=False, # Draft mode
        workshop_id=workshop_id,
    )
    
    # Update workshop status in DB
    try:
        from data.database import update_workshop_status
        update_workshop_status(workshop_id, 'generating')
    except Exception as e:
        logger.error("Failed to update status in DB: %s", e)
        
    background_tasks.add_task(
        run_adk_workflow_background,
        session_id,
    )
    
    return {
        "session_id": session_id,
        "status_endpoint": f"/status/{session_id}",
    }

@app.post("/api/workshops/{workshop_id}/publish", status_code=202)
def api_publish_workshop_campaign(workshop_id: str, background_tasks: BackgroundTasks):
    from data.database import get_workshop
    w = get_workshop(workshop_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
        
    if w["status"] not in ("generated", "failed", "published"):
        raise HTTPException(status_code=400, detail=f"Workshop cannot be published in its current state: {w['status']}")
        
    session_id = str(uuid.uuid4())
    
    # We load pre-generated AI content in the active session state
    # This prevents the agents from regenerating content and goes straight to publishing!
    active_sessions[session_id] = ProductLaunchState(
        product_name=w["name"],
        raw_description=w["description"],
        price=w["price"],
        category="Workshop",
        generated_description=w["generated_description"],
        seo_metadata=w["seo_metadata"],
        marketing=w["marketing"],
        marketing_assets=w["marketing"],
        image_prompts=w["image_prompts"],
        image_paths=w["image_paths"],
        status="pending",
        approved_to_publish=True, # Approve for Shopify publishing!
        workshop_id=workshop_id,
    )
    
    # Update workshop status in DB to publishing
    try:
        from data.database import update_workshop_status
        update_workshop_status(workshop_id, 'publishing')
    except Exception as e:
        logger.error("Failed to update status in DB: %s", e)
        
    background_tasks.add_task(
        run_adk_workflow_background,
        session_id,
    )
    
    return {
        "session_id": session_id,
        "status_endpoint": f"/status/{session_id}",
    }

@app.post("/api/workshops/{workshop_id}/register")
def register_student(workshop_id: str, reg_in: RegistrationInput):
    """Accept student pre-registration, save in SQLite as pending, and return checkout redirect."""
    import urllib.parse
    from data.database import get_workshop, add_registration
    
    w = get_workshop(workshop_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
        
    variant_id = str(w.get("shopify_variant_id") or "")
    if not variant_id:
        raise HTTPException(
            status_code=400,
            detail="This workshop has not been published to Shopify yet."
        )
        
    reg_id = f"REG-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    reg_data = {
        "order_id": reg_id,
        "shopify_order_id": None,
        "shopify_order_number": None,
        "workshop_id": workshop_id,
        "customer_name": f"{reg_in.parent_name} / {reg_in.child_name}",
        "customer_email": reg_in.customer_email,
        "customer_phone": reg_in.customer_phone,
        "amount": float(w["price"]),
        "payment_status": "pending",
        "child_name": reg_in.child_name,
        "child_age": reg_in.child_age,
        "parent_name": reg_in.parent_name,
        "school": reg_in.school,
        "emergency_contact": reg_in.emergency_contact,
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        add_registration(reg_data)
    except Exception as e:
        logger.exception("Failed to insert pending registration.")
        raise HTTPException(status_code=500, detail=f"Database write failure: {e}")
        
    store_url = os.getenv("SHOPIFY_STORE_URL", "product-launch-agent.myshopify.com")
    checkout_url = (
        f"https://{store_url}/cart/{variant_id}:1?"
        f"attributes[registration_id]={reg_id}&"
        f"attributes[student_name]={urllib.parse.quote(reg_in.child_name)}&"
        f"attributes[parent_name]={urllib.parse.quote(reg_in.parent_name)}&"
        f"checkout[email]={urllib.parse.quote(reg_in.customer_email)}"
    )
    
    return {
        "status": "success",
        "registration_id": reg_id,
        "redirect_url": checkout_url
    }


@app.post("/api/webhooks/orders/create")
async def shopify_order_webhook(request: Request):
    """Handle Shopify order created webhook to process workshop registrations and send emails."""
    body = await request.body()
    headers = request.headers
    hmac_header = headers.get("X-Shopify-Hmac-Sha256")
    
    # Verify HMAC signature
    shopify_secret = os.getenv("SHOPIFY_API_SECRET")
    if shopify_secret and hmac_header:
        digest = hmac.new(shopify_secret.encode("utf-8"), body, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest).decode("utf-8")
        if not hmac.compare_digest(computed_hmac, hmac_header):
            logger.warning("Invalid Shopify Webhook Signature.")
            raise HTTPException(status_code=401, detail="Unauthorized webhook source")
            
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    line_items = payload.get("line_items", [])
    if not line_items:
        return {"status": "ignored", "message": "No line items found"}
        
    # Process registrations for workshop products
    registrations_added = 0
    from data.database import get_workshop_by_shopify_id, add_registration
    from email_service import send_email, generate_customer_email_html, generate_sales_email_html
    
    for item in line_items:
        shopify_product_id = item.get("product_id")
        if not shopify_product_id:
            continue
            
        workshop = get_workshop_by_shopify_id(shopify_product_id)
        if not workshop:
            # Not a workshop product, skip
            logger.info("Order item product ID %s does not map to a database workshop.", shopify_product_id)
            continue
            
        # Parse cart attributes
        note_attrs = payload.get("note_attributes", [])
        child_name = "N/A"
        child_age = 0
        parent_name = "N/A"
        registration_id = None
        
        for attr in note_attrs:
            name = str(attr.get("name", "")).strip().lower()
            val = str(attr.get("value", "")).strip()
            if name in ("child name", "child_name"):
                child_name = val
            elif name in ("child age", "child_age"):
                try:
                    child_age = int(val)
                except ValueError:
                    pass
            elif name in ("parent name", "parent_name"):
                parent_name = val
            elif name in ("registration_id", "registrationid"):
                registration_id = val
                
        customer = payload.get("customer", {})
        customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or parent_name or "Parent"
        customer_email = customer.get("email") or payload.get("email") or "customer@example.com"
        customer_phone = customer.get("phone") or payload.get("phone") or ""
        
        # Lookup registration in DB if registration_id was supplied
        from data.database import get_registration
        existing_reg = None
        if registration_id:
            try:
                existing_reg = get_registration(registration_id)
            except Exception as e:
                logger.error("Error looking up registration_id %s: %s", registration_id, e)
                
        if existing_reg:
            reg_id = existing_reg["order_id"]
            child_name = existing_reg.get("child_name") or child_name
            child_age = existing_reg.get("child_age") or child_age
            parent_name = existing_reg.get("parent_name") or parent_name
            
            reg_data = existing_reg.copy()
            reg_data.update({
                "shopify_order_id": payload.get("id"),
                "shopify_order_number": str(payload.get("order_number") or payload.get("name", "")),
                "payment_status": payload.get("financial_status", "paid"),
                "amount": float(payload.get("total_price", existing_reg.get("amount", workshop["price"]))),
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone or existing_reg.get("customer_phone")
            })
        else:
            reg_id = registration_id or f"REG-{str(payload.get('id'))}"
            reg_data = {
                "order_id": reg_id,
                "shopify_order_id": payload.get("id"),
                "shopify_order_number": str(payload.get("order_number") or payload.get("name", "")),
                "workshop_id": workshop["id"],
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "amount": float(payload.get("total_price", workshop["price"])),
                "payment_status": payload.get("financial_status", "paid"),
                "child_name": child_name,
                "child_age": child_age,
                "parent_name": parent_name,
                "school": "N/A",
                "emergency_contact": "N/A",
                "created_at": payload.get("created_at") or datetime.utcnow().isoformat()
            }
            
        try:
            add_registration(reg_data)
            registrations_added += 1
            
            # 1. Send Customer Email
            cust_html = generate_customer_email_html(
                customer_name=customer_name,
                workshop_name=workshop["name"],
                date=workshop["date"],
                time=workshop["time"],
                venue=workshop["venue"],
                order_id=reg_data["shopify_order_number"],
                amount=reg_data["amount"],
                child_name=child_name,
                child_age=child_age,
                registration_id=reg_id
            )
            send_email(
                to_email=customer_email,
                subject="Mission Tiranga Registration Confirmed 🚀",
                html_content=cust_html,
                filename_prefix="customer",
                order_id=reg_id
            )
            
            # 2. Send Sales Notification Email
            sales_email = os.getenv("SALES_TEAM_EMAIL") or workshop.get("sales_team_email") or "sales@example.com"
            sales_html = generate_sales_email_html(reg_data, workshop)
            send_email(
                to_email=sales_email,
                subject=f"New Mission Tiranga Registration - Order #{reg_data['shopify_order_number']}",
                html_content=sales_html,
                filename_prefix="salesteam",
                order_id=reg_id
            )
        except Exception as e:
            logger.exception("Failed to process registration webhook for item %s", shopify_product_id)
        
    return {"status": "processed", "registrations_added": registrations_added}

@app.get("/workshops/{handle}")
def serve_workshop_landing_page(handle: str):
    """Dynamic routing to serve the landing page for a specific workshop handle."""
    from data.database import get_workshop
    w = get_workshop(handle)
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
        
    # Read the template html file
    template_path = os.path.join(STATIC_DIR, "landing_page.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=500, detail="Landing page template missing")
        
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    # Get variant ID for shopify checkout link.
    # This is read directly from the workshops table's shopify_variant_id column,
    # populated by publish_workshop() once the ADK pipeline actually publishes the
    # product. Previously this looked for a "shopify_product" key that the database
    # never stores, so variant_id was always empty and the page always showed its
    # "preview draft mode" fallback message, even for successfully published workshops.
    variant_id = str(w.get("shopify_variant_id") or "")
        
    store_url = os.getenv("SHOPIFY_STORE_URL", "product-launch-agent.myshopify.com")
    
    # Check if generated images exist
    images = {}
    image_paths = w.get("image_paths") or []
    def get_static_image_url(path):
        if not path:
            return ""
        rel = os.path.basename(path)
        return f"/outputs/images/{rel}"
        
    for path in image_paths:
        for cat in ["hero", "lifestyle", "banner", "classroom", "thumbnail", "certificate", "gallery1", "gallery2"]:
            if f"_{cat}." in os.path.basename(path) or path.endswith(f"_{cat}.png"):
                images[cat] = get_static_image_url(path)
                
    # Fallback to visual placeholders if not generated yet
    if not images.get("hero"):
        images["hero"] = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1000"
    if not images.get("lifestyle"):
        images["lifestyle"] = "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?q=80&w=1000"
    if not images.get("banner"):
        images["banner"] = "https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=1000"
    if not images.get("classroom"):
        images["classroom"] = "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?q=80&w=1000"
    if not images.get("thumbnail"):
        images["thumbnail"] = "https://images.unsplash.com/photo-1506318137071-a8e063b4bec0?q=80&w=300"
    if not images.get("certificate"):
        images["certificate"] = "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=1000"
    if not images.get("gallery1"):
        images["gallery1"] = "https://images.unsplash.com/photo-1581092921461-eab62e97a780?q=80&w=1000"
    if not images.get("gallery2"):
        images["gallery2"] = "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=1000"
        
    # Perform string replacements in the template html
    html = html.replace("{{WORKSHOP_ID}}", w["id"])
    html = html.replace("{{WORKSHOP_NAME}}", w["name"])
    html = html.replace("{{WORKSHOP_DESCRIPTION}}", w["description"])
    html = html.replace("{{WORKSHOP_DATE}}", w["date"])
    html = html.replace("{{WORKSHOP_TIME}}", w["time"])
    html = html.replace("{{WORKSHOP_DURATION}}", w["duration"])
    html = html.replace("{{WORKSHOP_VENUE}}", w["venue"])
    html = html.replace("{{WORKSHOP_PRICE}}", str(int(w["price"])))
    html = html.replace("{{WORKSHOP_AGE}}", w["age_group"])
    html = html.replace("{{SHOPIFY_STORE_URL}}", store_url)
    html = html.replace("{{VARIANT_ID}}", variant_id)
    
    # AI Copy assets replacements
    marketing = w.get("marketing") or {}
    html = html.replace("{{CAMPAIGN_HEADLINE}}", marketing.get("campaign_headline", "THIS INDEPENDENCE DAY, LOOK BEYOND THE SKY."))
    html = html.replace("{{SHORT_DESCRIPTION}}", marketing.get("short_description", w["description"]))
    html = html.replace("{{LONG_COPY}}", marketing.get("long_copy", w["description"]))
    html = html.replace("{{TAGLINES}}", marketing.get("taglines", "- Build satellite models<br>- Explore Space Comms<br>- Code with AI"))
    
    # Visual replacements
    html = html.replace("{{HERO_IMAGE}}", images["hero"])
    html = html.replace("{{LIFESTYLE_IMAGE}}", images["lifestyle"])
    html = html.replace("{{BANNER_IMAGE}}", images["banner"])
    html = html.replace("{{CLASSROOM_IMAGE}}", images["classroom"])
    html = html.replace("{{THUMBNAIL_IMAGE}}", images["thumbnail"])
    html = html.replace("{{CERTIFICATE_IMAGE}}", images["certificate"])
    html = html.replace("{{GALLERY_IMAGE_1}}", images["gallery1"])
    html = html.replace("{{GALLERY_IMAGE_2}}", images["gallery2"])
    html = html.replace("{{POSTER_IMAGE}}", w.get("poster_path") or "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1000")
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "adk_ready": True,
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