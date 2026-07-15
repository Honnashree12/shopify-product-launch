import logging

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context
from shopify_client import get_product, ShopifyConfigError, ShopifyAPIError

logger = logging.getLogger("verification_agent")


def verify_product_listing(tool_context: ToolContext) -> str:
    """
    Verify that the published Shopify product exists and matches
    the expected workflow values.
    """

    state = tool_context.state

    product_id = state.get("shopify_product_id")
    expected_price = state.get("product_price")   # <-- FIXED

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
        return "Verification failed: Product ID missing."

    if expected_price is None:
        result["errors"].append("product_price missing")
        state["verification_result"] = result
        return "Verification failed: product_price missing."

    try:

        product = get_product(product_id)

        result["product_exists"] = True

        if str(product.get("status", "")).lower() == "active":
            result["status_active"] = True
        else:
            result["errors"].append(
                f"Product status is {product.get('status')}"
            )

        actual_price = float(product.get("price", 0))
        expected_price = float(expected_price)

        if abs(actual_price - expected_price) < 0.01:
            result["price_matched"] = True
        else:
            result["errors"].append(
                f"Expected {expected_price}, got {actual_price}"
            )

        # A real Shopify product is purchasable once it is active,
        # priced correctly, and has at least one variant to sell.
        has_variant = bool(product.get("variants"))
        if not has_variant:
            result["errors"].append("Product has no variants")

        result["purchasable"] = (
            result["product_exists"]
            and result["status_active"]
            and result["price_matched"]
            and has_variant
        )

        state["verification_result"] = result

        print("\n========== VERIFICATION ==========")
        print(result)
        print("==================================\n")

        if result["purchasable"]:
            return "Verification PASSED."

        return "Verification FAILED."

    except (ShopifyConfigError, ShopifyAPIError) as e:
        logger.error("Shopify verification failed: %s", e)
        result["errors"].append(str(e))
        state["verification_result"] = result
        return f"Verification failed: {e}"
    except Exception as e:
        logger.exception("Unexpected error during Shopify verification")
        result["errors"].append(str(e))
        state["verification_result"] = result
        return f"Verification failed: {e}"


verification_agent = Agent(
    name="VerificationAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Shopify Verification Agent.

You verify products against a real, live Shopify store.

The workflow already contains:

- shopify_product_id
- product_price

Never invent values.

Simply call:

verify_product_listing()

Return nothing except the tool call.

Your final action MUST be calling verify_product_listing().
""",
    tools=[
        get_product_context,
        verify_product_listing,
    ],
)