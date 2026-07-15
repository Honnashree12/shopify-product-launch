import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents.image_prompt_agent import image_prompt_agent


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
            "marketing": {
                "campaign_name": "Sound Sanctuary",
                "target_audience": "Music lovers, professionals, commuters",
                "marketing_strategy": "Premium immersive listening experience.",
                "social_caption": "Escape into your music.",
                "email_subject": "Experience Premium Sound",
                "email_body": "Discover immersive listening today.",
                "call_to_action": "Shop Now",
            },
        }
    )

    print("\nCurrent Session State\n")
    print(session.state)

    runner = Runner(
        agent=image_prompt_agent,
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

Description:
Bluetooth earbuds with Active Noise Cancellation,
Bluetooth 5.3,
USB-C Fast Charging,
30-hour battery.

Category:
Electronics

Marketing Campaign:
Premium immersive listening experience.

Generate:

1 Hero Image Prompt

1 Lifestyle Image Prompt

1 Promotional Banner Prompt
"""
            )
        ],
    )

    print("\n===================================")
    print("Running Image Prompt Agent...")
    print("===================================\n")

    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=message,
    ):
        if event.content:
            print(event.content)

    updated_session = await session_service.get_session(
        app_name="shopify-launch",
        user_id="demo-user",
        session_id=session.id,
    )

    prompts = updated_session.state.get("image_prompts", {})

    print("\n===================================")
    print("IMAGE PROMPTS")
    print("===================================\n")

    print("Hero Prompt:\n")
    print(prompts.get("hero", ""))

    print("\nLifestyle Prompt:\n")
    print(prompts.get("lifestyle", ""))

    print("\nBanner Prompt:\n")
    print(prompts.get("banner", ""))

    print("\n===================================")
    print("FULL SESSION STATE")
    print("===================================\n")

    for key, value in updated_session.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())