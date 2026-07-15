from google.adk.tools.tool_context import ToolContext


def get_product_context(tool_context: ToolContext) -> dict:
    """
    Returns the original product information stored in the workflow state.
    """

    print("\n========== TOOL CONTEXT ==========")

    try:
        print(dict(tool_context.state))
    except Exception:
        print(tool_context.state)

    print("==================================")

    product = {
        "product_name": tool_context.state.get("product_name"),
        "product_description": tool_context.state.get("product_description"),
        "product_price": tool_context.state.get("product_price"),
        "product_category": tool_context.state.get("product_category"),
    }

    print(product)

    return product