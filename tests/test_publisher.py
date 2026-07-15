import asyncio
import os

from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.publisher_agent import publisher_agent

load_dotenv()


async def main():

    print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
    print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
    print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name="publisher-test",
        user_id="demo-user",
        session_id="publisher-session",
    )

    # -------------------------------------------------
    # Populate session state
    # -------------------------------------------------

    session.state.update(
        {
            "product_name": "Wireless Earbuds",

            "generated_description": """
<h2>Immersive Audio</h2>

<p>
Bluetooth 5.3 earbuds with Active Noise Cancellation,
USB-C Fast Charging,
30-hour battery life.
</p>
""",

            "price": 2999,

            "category": "Electronics",

            "seo_metadata": {
                "title": "Wireless Earbuds with ANC",
                "description": "Premium Bluetooth earbuds with Active Noise Cancellation.",
                "keywords": "wireless earbuds, anc, bluetooth earbuds",
                "slug": "wireless-earbuds",
            },
        }
    )

    print("\n==============================")
    print("CURRENT SESSION STATE")
    print("==============================\n")

    print(session.state)

    runner = Runner(
        agent=publisher_agent,
        app_name="publisher-test",
        session_service=session_service,
    )

    # -------------------------------------------------
    # Pass the product details to the agent
    # -------------------------------------------------

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
Publish this product to Shopify.

Product Name:
{session.state["product_name"]}

Generated Description:
{session.state["generated_description"]}

Price:
{session.state["price"]}

Category:
{session.state["category"]}

SEO Metadata:
{session.state["seo_metadata"]}

Rules:

- Use the SEO title if available.
- Otherwise use the Product Name.
- Use the Generated Description as body_html.
- Use the Price.
- Use the Category.
- Call publish_to_shopify().
- Do not invent any values.
"""
            )
        ],
    )

    print("\n==============================")
    print("RUNNING PUBLISHER AGENT")
    print("==============================\n")

    async for event in runner.run_async(
        user_id="demo-user",
        session_id="publisher-session",
        new_message=message,
    ):
        if event.content:
            print(event.content)

    session = await session_service.get_session(
        app_name="publisher-test",
        user_id="demo-user",
        session_id="publisher-session",
    )

    print("\n==============================")
    print("PUBLISH RESULT")
    print("==============================\n")

    print("Product ID:")
    print(session.state.get("shopify_product_id"))

    print("\nProduct URL:")
    print(session.state.get("shopify_url"))

    print("\n==============================")
    print("FULL SESSION STATE")
    print("==============================\n")

    for key, value in session.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())