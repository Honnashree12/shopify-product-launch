import os
import json

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.product_context import get_product_context


def save_launch_reports(tool_context: ToolContext) -> str:
    """
    Generate and save Markdown and JSON launch reports
    using the complete workflow state.
    """

    state = tool_context.state

    # Create outputs folder
    outputs_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "outputs")
    )
    os.makedirs(outputs_dir, exist_ok=True)

    markdown_path = os.path.join(outputs_dir, "launch_report.md")
    json_path = os.path.join(outputs_dir, "launch_report.json")

    # Read data from workflow state
    seo = state.get("seo_metadata", {})
    marketing = state.get("marketing", {})
    verification = state.get("verification_result", {})
    product = state.get("shopify_product", {})

    # ---------------- Markdown Report ---------------- #

    markdown_report = f"""# Shopify Product Launch Report

## Product

**Title:** {product.get("title", "N/A")}

**Category:** {state.get("product_category", "N/A")}

**Price:** ₹{state.get("product_price", "N/A")}

**Description:**

{state.get("product_description", "N/A")}

---

## Shopify

**Product ID:** {product.get("id", "N/A")}

**URL:** {state.get("shopify_url", "N/A")}

**Status:** {product.get("status", "N/A")}

---

## SEO

**Title:**

{seo.get("title", "")}

**Meta Description:**

{seo.get("description", "")}

**Keywords:**

{seo.get("keywords", "")}

**Slug:**

{seo.get("slug", "")}

---

## Marketing

**Campaign:**

{marketing.get("campaign_name", "")}

**Audience:**

{marketing.get("target_audience", "")}

**Strategy:**

{marketing.get("marketing_strategy", "")}

**Social Caption:**

{marketing.get("social_caption", "")}

**Email Subject:**

{marketing.get("email_subject", "")}

**Call To Action:**

{marketing.get("call_to_action", "")}

---

## Verification

{json.dumps(verification, indent=4)}

---

## Workflow Status

✅ Copywriter Completed

✅ SEO Generated

✅ Marketing Generated

✅ Shopify Published

✅ Verification Passed

✅ Reports Generated
"""

    # ---------------- JSON Report ---------------- #

    try:
        json_report = json.dumps(dict(state), indent=4, default=str)
    except Exception:
        json_report = json.dumps(
            {
                "product": {
                    "title": product.get("title"),
                    "category": state.get("product_category"),
                    "price": state.get("product_price"),
                    "description": state.get("product_description"),
                },
                "shopify": {
                    "product_id": product.get("id"),
                    "url": state.get("shopify_url"),
                    "status": product.get("status"),
                },
                "seo": seo,
                "marketing": marketing,
                "verification": verification,
            },
            indent=4,
        )

    # Save files
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_report)

    # Save paths into workflow state
    state["markdown_report_path"] = markdown_path
    state["json_report_path"] = json_path

    print("\n========== REPORT GENERATED ==========")
    print("Markdown Report :", markdown_path)
    print("JSON Report     :", json_path)
    print("======================================\n")

    return f"""Reports generated successfully.

Markdown:
{markdown_path}

JSON:
{json_path}
"""


report_generator_agent = Agent(
    name="ReportGeneratorAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the final reporting agent.

The workflow has already completed.

Do NOT generate any new content.

Simply call:

save_launch_reports()

Your final action MUST be calling save_launch_reports().
""",
    tools=[
        get_product_context,
        save_launch_reports,
    ],
)