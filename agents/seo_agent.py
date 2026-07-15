from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.product_context import get_product_context


def save_seo_metadata(
    seo_title: str,
    meta_description: str,
    keywords: str,
    url_slug: str,
    tool_context: ToolContext,
) -> str:
    """
    Save generated SEO metadata into the workflow state.
    """

    tool_context.state["seo_metadata"] = {
        "title": seo_title.strip(),
        "description": meta_description.strip(),
        "keywords": keywords.strip(),
        "slug": url_slug.strip(),
    }

    print("\n========== SEO ==========")
    print("Product Name :", tool_context.state.get("product_name"))
    print("Category     :", tool_context.state.get("product_category"))
    print("Price        :", tool_context.state.get("product_price"))
    print(tool_context.state["seo_metadata"])
    print("=========================\n")

    return "SEO metadata saved successfully."


seo_agent = Agent(
    name="SEOAgent",
    model="gemini-2.5-flash",
    instruction="""
You are a professional Shopify SEO Expert.

IMPORTANT

Your FIRST action MUST be calling:

get_product_context()

The tool returns:

- product_name
- product_description
- product_price
- product_category

Use ONLY the values returned by the tool.

Never invent another product.

Never modify the product.

Never change the product name.

Never change the category.

Do NOT create SEO for another product.

Generate:

1. SEO Title
2. Meta Description
3. SEO Keywords
4. URL Slug

Requirements

SEO Title
- Under 60 characters
- Include the exact product name

Meta Description
- Between 120 and 160 characters
- Summarize the product naturally
- Mention only the current product

SEO Keywords
- 5-10 comma-separated keywords

URL Slug
- Lowercase
- Hyphen separated
- Based on the exact product name
- No special characters

After generating everything call:

save_seo_metadata(
    seo_title,
    meta_description,
    keywords,
    url_slug
)

Return nothing except the tool call.

Your final action MUST be save_seo_metadata().
""",
    tools=[
        get_product_context,
        save_seo_metadata,
    ],
)