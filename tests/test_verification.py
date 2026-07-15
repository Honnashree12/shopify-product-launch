import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.verification_agent import verification_agent


async def main():

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name="verification-test",
        user_id="demo-user",
    )

    session.state.update(
        {
            "shopify_product_id": 7,
            "price": 2999,
        }
    )

    print("\n==============================")
    print("CURRENT SESSION STATE")
    print("==============================\n")

    print(session.state)

    runner = Runner(
        agent=verification_agent,
        app_name="verification-test",
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
Verify this Shopify product.

Product ID:
{session.state["shopify_product_id"]}

Expected Price:
{session.state["price"]}

Call verify_product_listing().
"""
            )
        ],
    )

    print("\n==============================")
    print("RUNNING VERIFICATION AGENT")
    print("==============================\n")

    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=message,
    ):
        if event.content:
            print(event.content)

    updated_session = await session_service.get_session(
        app_name="verification-test",
        user_id="demo-user",
        session_id=session.id,
    )

    print("\n==============================")
    print("VERIFICATION RESULT")
    print("==============================\n")

    print(updated_session.state.get("verification_result"))

    print("\n==============================")
    print("FULL SESSION STATE")
    print("==============================\n")

    for key, value in updated_session.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())