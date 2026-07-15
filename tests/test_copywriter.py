import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from google.genai.types import Content, Part

from agents.copywriter_agent import copywriter_agent
from dotenv import load_dotenv
import os

load_dotenv()

print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))


async def main():

    # Create in-memory session storage
    session_service = InMemorySessionService()

    # Create session
    session = await session_service.create_session(
        app_name="shopify-launch",
        user_id="demo-user"
    )
    session.state.update({
    "product_name": "Wireless Earbuds",
    "raw_description": "Bluetooth earbuds with active noise cancellation and 30 hour battery life.",
    "price": 2999,
    "category": "Electronics"
})

    print(session.state)

    # -------------------------------------------------------
    # Populate session state required by agent instructions
    # -------------------------------------------------------



    # -------------------------------------------------------
    # Create runner
    # -------------------------------------------------------

    runner = Runner(
        agent=copywriter_agent,
        app_name="shopify-launch",
        session_service=session_service
    )

    # -------------------------------------------------------
    # Send user request
    # -------------------------------------------------------

    message = Content(
        role="user",
        parts=[
            Part.from_text(
                text="""
Product Name: Wireless Earbuds

Description:
Bluetooth earbuds with Active Noise Cancellation,
30 hour battery,
Bluetooth 5.3,
USB-C Fast Charging.

Price:
2999

Category:
Electronics

Generate a Shopify HTML product description.
"""
            )
        ]
    )

    print("\nRunning Copywriter Agent...\n")

    # Execute agent
    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=message
    ):
        if event.content:
            print(event.content)

    # -------------------------------------------------------
    # Retrieve updated session state
    # -------------------------------------------------------

    updated_session = await session_service.get_session(
        app_name="shopify-launch",
        user_id="demo-user",
        session_id=session.id
    )

    print("\n============================")
    print("FINAL SESSION STATE")
    print("============================")

    for key, value in updated_session.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())