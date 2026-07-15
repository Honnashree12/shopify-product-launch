from google.adk.tools.tool_context import ToolContext


def get_workflow_context(tool_context: ToolContext) -> dict:
    """
    Returns the complete workflow context.
    """

    return {
        "product_name": tool_context.state.get("product_name"),
        "product_description": tool_context.state.get("product_description"),
        "product_price": tool_context.state.get("product_price"),
        "product_category": tool_context.state.get("product_category"),

        "generated_description": tool_context.state.get("generated_description"),
        "seo_metadata": tool_context.state.get("seo_metadata"),
        "marketing": tool_context.state.get("marketing"),
        "image_prompts": tool_context.state.get("image_prompts"),

        "shopify_product": tool_context.state.get("shopify_product"),
    }