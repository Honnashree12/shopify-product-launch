import asyncio
from dotenv import load_dotenv

load_dotenv()

import os

print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents.seo_agent import seo_agent


async def main():

    # -------------------------------------------------------
    # Create in-memory session storage
    # -------------------------------------------------------

    session_service = InMemorySessionService()

    # -------------------------------------------------------
    # Create session
    # -------------------------------------------------------

    session = await session_service.create_session(
        app_name="shopify-launch",
        user_id="demo-user"
    )

    # -------------------------------------------------------
    # Populate shared state
    # -------------------------------------------------------

    session.state.update({
        "product_name": "Wireless Earbuds",
        "raw_description": (
            "Bluetooth earbuds with Active Noise Cancellation, "
            "Bluetooth 5.3, USB-C Fast Charging, "
            "30-hour battery life."
        ),
        "price": 2999,
        "category": "Electronics",
        "generated_description": """
<h2>Immersive Audio, Uninterrupted Freedom</h2>

<p>
Experience crystal-clear sound with Bluetooth 5.3 Wireless Earbuds.
Featuring Active Noise Cancellation, USB-C Fast Charging,
and an impressive 30-hour battery life,
these earbuds are perfect for music lovers,
professionals, and travelers.
</p>
"""
    })

    print("\nCurrent Session State\n")
    print(session.state)

    # -------------------------------------------------------
    # Create Runner
    # -------------------------------------------------------

    runner = Runner(
        agent=seo_agent,
        app_name="shopify-launch",
        session_service=session_service
    )

    # -------------------------------------------------------
    # User Prompt
    # -------------------------------------------------------

    message = Content(
        role="user",
        parts=[
            Part.from_text(
                text="""
Product Name:
Wireless Earbuds

Category:
Electronics

Price:
2999

Raw Description:
Bluetooth earbuds with Active Noise Cancellation,
Bluetooth 5.3,
USB-C Fast Charging,
30-hour battery.

Generated Shopify HTML Description:

<h2>Immersive Audio, Uninterrupted Freedom</h2>

<p>
Experience crystal-clear sound with Bluetooth 5.3 Wireless Earbuds.
Featuring Active Noise Cancellation,
USB-C Fast Charging,
and a 30-hour battery life.
</p>

Generate SEO metadata for this Shopify product.
"""
            )
        ]
    )

    print("\n===================================")
    print("Running SEO Agent...")
    print("===================================\n")

    # -------------------------------------------------------
    # Execute Agent
    # -------------------------------------------------------

    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=message
    ):

        if event.content:
            print(event.content)

    # -------------------------------------------------------
    # Retrieve Updated Session
    # -------------------------------------------------------

    updated_session = await session_service.get_session(
        app_name="shopify-launch",
        user_id="demo-user",
        session_id=session.id
    )

    # -------------------------------------------------------
    # Print Final Output
    # -------------------------------------------------------

    print("\n===================================")
    print("FINAL SEO METADATA")
    print("===================================\n")

    seo = updated_session.state.get("seo_metadata")

    if seo:

        print(f"SEO Title:\n{seo['title']}\n")

        print(f"Meta Description:\n{seo['description']}\n")

        print(f"Keywords:\n{seo['keywords']}\n")

        print(f"URL Slug:\n{seo['slug']}\n")

    else:

        print("SEO metadata was not generated.")

    print("\n===================================")
    print("FULL SESSION STATE")
    print("===================================\n")

    for key, value in updated_session.state.items():

        print(f"{key}:")

        print(value)

        print()


if __name__ == "__main__":
    asyncio.run(main())