from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.product_context import get_product_context


def save_description(
    description: str,
    tool_context: ToolContext,
) -> str:
    """
    Save the generated Shopify HTML description into workflow state.
    """

    tool_context.state["generated_description"] = description

    print("\n========== COPYWRITER ==========")
    print("Product Name :", tool_context.state.get("product_name"))
    print("Category     :", tool_context.state.get("product_category"))
    print("Price        :", tool_context.state.get("product_price"))
    print("Description Saved Successfully")
    print("================================\n")

    return "Product description saved successfully."


copywriter_agent = Agent(
    name="CopywriterAgent",
    model="gemini-2.5-flash",
    instruction="""
You are an expert Shopify Copywriter.

IMPORTANT

Your FIRST action MUST be calling:

get_product_context()

The tool returns:

- product_name
- product_description
- product_price
- product_category

Use ONLY those returned values.

Never invent another product.

Never replace the product.

Never change the product name.

Never change the category.

Never write "Product Name Missing".

If information is unavailable, politely omit it instead of inventing it.

Generate a professional Shopify HTML description.

Use exactly this structure:

<h2>Product Name</h2>

<p>
Short engaging introduction.
</p>

<h3>Key Benefits</h3>

<ul>
<li>Benefit 1</li>
<li>Benefit 2</li>
<li>Benefit 3</li>
</ul>

<h3>Features</h3>

<ul>
<li>Feature 1</li>
<li>Feature 2</li>
<li>Feature 3</li>
</ul>

<h3>Specifications</h3>

<p>
Mention only the specifications provided in the product description.
</p>

<h3>Why Choose This Product?</h3>

<p>
Write a persuasive paragraph encouraging purchase.
</p>

<p>
<strong>Order yours today!</strong>
</p>

Do NOT output the HTML as your response text.
Do NOT wrap it in markdown or code fences (no ```).
Do NOT show the HTML to the user at all.

The ONLY correct output for this turn is a single function call:

save_description(description=<the HTML you generated>)

If your response does not contain a function call, you have done
this task incorrectly. Never produce a final text answer containing
the description -- always pass it as the `description` argument to
save_description() instead.
""",
    tools=[
        get_product_context,
        save_description,
    ],
)