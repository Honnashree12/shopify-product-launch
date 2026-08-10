from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context

def save_marketing_assets(
    campaign_headline: str,
    short_description: str,
    long_copy: str,
    social_caption: str,
    instagram_caption: str,
    whatsapp_message: str,
    email_subject: str,
    email_body: str,
    call_to_action: str,
    taglines: str,
    tool_context: ToolContext,
) -> str:
    """Save the detailed AI-generated marketing copy assets into the shared workflow state."""
    tool_context.state["marketing_assets"] = {
        "campaign_headline": campaign_headline.strip(),
        "short_description": short_description.strip(),
        "long_copy": long_copy.strip(),
        "social_caption": social_caption.strip(),
        "instagram_caption": instagram_caption.strip(),
        "whatsapp_message": whatsapp_message.strip(),
        "email_subject": email_subject.strip(),
        "email_body": email_body.strip(),
        "call_to_action": call_to_action.strip(),
        "taglines": taglines.strip()
    }
    
    print("\n========== MARKETING AGENT ==========")
    print(repr(tool_context.state["marketing_assets"]))
    print("=====================================\n")
    return "Marketing assets saved successfully."

marketing_agent = Agent(
    name="MarketingAgent",
    model="gemini-2.5-flash",
    instruction="""
You are an expert E-commerce Copywriter and Growth Marketer.

Your task is to take the product details and the high-level strategy (stored in the workflow state under 'marketing') and generate detailed promotional copy assets for the campaign.

Use only the actual workshop or product information. Do not invent details like custom partnerships or government/ISRO affiliations unless explicitly in the product context.

Generate the following:
1. Campaign Headline: A catchy, high-conversion headline (e.g., "This Independence Day, Look Beyond The Sky").
2. Short Campaign Description: A concise 2-sentence description for quick reads.
3. Long Marketing Copy: A structured, emotionally engaging narrative connecting child curiosity, STEM education, India's space achievements, and satellite communication.
4. Social Media Caption: Clean caption with relevant hashtags.
5. Instagram Caption: Visually appealing, emoji-friendly caption.
6. WhatsApp Promotional Message: Short, persuasive, formatted with bold text and emojis, suitable for direct sharing.
7. Email Subject: Exciting subject line.
8. Email Body: Engaging email template text.
9. Call to Action: Punchy, actionable text.
10. Promotional Taglines: 3 bullet points / taglines summarizing the benefits.

After generating these assets, call:
save_marketing_assets(
    campaign_headline,
    short_description,
    long_copy,
    social_caption,
    instagram_caption,
    whatsapp_message,
    email_subject,
    email_body,
    call_to_action,
    taglines
)

Your final action MUST be calling save_marketing_assets().
""",
    tools=[
        get_product_context,
        save_marketing_assets
    ]
)
