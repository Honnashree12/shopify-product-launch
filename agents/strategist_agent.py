from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context

def save_marketing_strategy(
    campaign_name: str,
    target_audience: str,
    marketing_strategy: str,
    social_caption: str,
    email_subject: str,
    email_body: str,
    call_to_action: str,
    tool_context: ToolContext,
) -> str:
    """
    Save only marketing assets.
    Product details are already present in the workflow state.
    """

    tool_context.state["marketing"] = {
        "campaign_name": campaign_name.strip(),
        "target_audience": target_audience.strip(),
        "marketing_strategy": marketing_strategy.strip(),
        "social_caption": social_caption.strip(),
        "email_subject": email_subject.strip(),
        "email_body": email_body.strip(),
        "call_to_action": call_to_action.strip(),
    }

    print("\n========== STRATEGIST ==========")
    print(tool_context.state["marketing"])
    print("================================\n")

    return "Marketing strategy saved successfully."


strategist_agent = Agent(
    name="StrategistAgent",
    model="gemini-2.5-flash",
    instruction="""
You are a Senior Shopify Marketing Strategist.

The workflow state already contains:

- Product Name
- Product Description
- Product Price
- Product Category
- HTML Description
- SEO Metadata

Your task is ONLY to generate:

1. Campaign Name
2. Target Audience
3. Marketing Strategy
4. Social Media Caption
5. Promotional Email Subject
6. Promotional Email Body
7. Call To Action

IMPORTANT RULES

DO NOT invent any product details.

DO NOT change:
- Product name
- Product description
- Product category
- Product price

Everything must refer to the SAME product already stored in the workflow.

If the product is Wireless Bluetooth Headphones,
every output must also describe Wireless Bluetooth Headphones.

Never create a different product.

After generating the marketing assets call:

save_marketing_strategy(
    campaign_name,
    target_audience,
    marketing_strategy,
    social_caption,
    email_subject,
    email_body,
    call_to_action
)

Your FINAL action MUST be calling save_marketing_strategy().
""",
    tools=[get_product_context,
    save_marketing_strategy]
)