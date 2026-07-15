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

from agents.strategist_agent import strategist_agent


async def main():

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name="shopify-launch",
        user_id="demo-user",
    )

    session.state.update(
        {
            "product_name": "Wireless Earbuds",
            "raw_description": "Bluetooth earbuds with Active Noise Cancellation, Bluetooth 5.3, USB-C Fast Charging and 30-hour battery life.",
            "price": 2999,
            "category": "Electronics",
        }
    )

    runner = Runner(
        agent=strategist_agent,
        app_name="shopify-launch",
        session_service=session_service,
    )

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

Description:
Bluetooth earbuds with Active Noise Cancellation,
Bluetooth 5.3,
USB-C Fast Charging,
30-hour battery life.

Generate a complete marketing campaign.
"""
            )
        ],
    )

    print("\nRunning Strategist Agent...\n")

    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=message,
    ):
        if event.content:
            print(event.content)

    updated = await session_service.get_session(
        app_name="shopify-launch",
        user_id="demo-user",
        session_id=session.id,
    )

    print("\n========================================")
    print("MARKETING OUTPUT")
    print("========================================\n")

    marketing = updated.state.get("marketing")

    if marketing:

        print("Campaign Name:")
        print(marketing["campaign_name"])
        print()

        print("Target Audience:")
        print(marketing["target_audience"])
        print()

        print("Marketing Strategy:")
        print(marketing["marketing_strategy"])
        print()

        print("Social Caption:")
        print(marketing["social_caption"])
        print()

        print("Email Subject:")
        print(marketing["email_subject"])
        print()

        print("Email Body:")
        print(marketing["email_body"])
        print()

        print("Call To Action:")
        print(marketing["call_to_action"])
        print()

    else:
        print("Marketing strategy was not generated.")

    print("\n========================================")
    print("FULL SESSION STATE")
    print("========================================\n")

    for key, value in updated.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())