import logging

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context
from shopify_client import create_product, ShopifyConfigError, ShopifyAPIError

logger = logging.getLogger("publisher_agent")


def publish_to_shopify(tool_context: ToolContext) -> str:
    """
    Publish the finalized product to the real Shopify Admin API.
    Uses ONLY the original workflow state.
    """

    state = tool_context.state

    print("\n========== WORKFLOW STATE ==========")
    print(state)
    print("====================================\n")

    product_name = state.get("product_name")
    product_description = state.get("product_description")
    product_price = state.get("product_price")
    product_category = state.get("product_category")

    generated_description = state.get("generated_description")
    seo_metadata = state.get("seo_metadata", {})

    missing = []

    if not product_name:
        missing.append("product_name")

    if not product_description:
        missing.append("product_description")

    if product_price is None:
        missing.append("product_price")

    if not product_category:
        missing.append("product_category")

    if not generated_description:
        missing.append("generated_description")

    if not seo_metadata:
        missing.append("seo_metadata")

    if missing:
        return (
            "Publishing failed.\n"
            "Missing workflow state:\n"
            + "\n".join(f"- {item}" for item in missing)
        )

    # Tags are optional -- reuse SEO keywords as tags when available,
    # without requiring any change to the SEO agent itself.
    tags = seo_metadata.get("keywords") if isinstance(seo_metadata, dict) else None

    try:

        product = create_product(
            title=product_name,
            body_html=generated_description,
            price=float(product_price),  # ensure numeric
            product_type=product_category,
            status="active",
            tags=tags,
        )

        state["shopify_product"] = product
        state["shopify_product_id"] = product["id"]
        state["shopify_url"] = product["url"]

        print("\n========== PRODUCT PUBLISHED ==========")
        print(product)
        print("=======================================\n")

        return (
            f"Product published successfully.\n"
            f"Product ID: {product['id']}\n"
            f"URL: {product['url']}"
        )

    except (ShopifyConfigError, ShopifyAPIError) as e:
        logger.error("Shopify publish failed: %s", e)
        return f"Publishing failed: {e}"
    except Exception as e:
        logger.exception("Unexpected error while publishing to Shopify")
        return f"Publishing failed: {e}"


publisher_agent = Agent(
    name="PublisherAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Shopify Publisher Agent.

You publish products to a real, live Shopify store.

The workflow already contains:

- product_name
- product_description
- product_price
- product_category
- generated_description
- seo_metadata
- marketing
- image_prompts

Do NOT generate content.
Do NOT modify workflow values.
Use ONLY the existing workflow state.

Call:

publish_to_shopify()

Return nothing except the tool call.

Your final action MUST be calling publish_to_shopify().
""",
    tools=[
        get_product_context,
        publish_to_shopify,
    ],
)