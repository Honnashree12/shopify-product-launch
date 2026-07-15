import asyncio
import os

from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.report_generator_agent import report_generator_agent

load_dotenv()


async def main():

    print("Vertex:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
    print("Project:", os.getenv("GOOGLE_CLOUD_PROJECT"))
    print("Location:", os.getenv("GOOGLE_CLOUD_LOCATION"))

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name="report-test",
        user_id="demo-user",
        session_id="report-session",
    )

    session.state.update(
        {
            "product_name": "Wireless Earbuds",

            "category": "Electronics",

            "price": 2999,

            "generated_description": """
<h2>Immersive Audio</h2>

<p>
Bluetooth 5.3 earbuds with ANC,
USB-C Fast Charging,
30-hour battery life.
</p>
""",

            "seo_metadata": {
                "title": "Wireless Earbuds with ANC",
                "description": "Premium Bluetooth earbuds",
                "keywords": "wireless earbuds, anc",
                "slug": "wireless-earbuds",
            },

            "image_prompts": {
                "hero": "Hero image prompt",
                "lifestyle": "Lifestyle prompt",
                "banner": "Banner prompt",
            },

            "shopify_url":
                "https://mock-shopify-store.myshopify.com/products/wireless-earbuds-with-anc-6",

            "verification_result": "PASS",

            "errors": "None",

            "status": "SUCCESS",
        }
    )

    runner = Runner(
        agent=report_generator_agent,
        app_name="report-test",
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"""
Generate the final launch reports.

Product Name:
{session.state["product_name"]}

Category:
{session.state["category"]}

Price:
{session.state["price"]}

Generated Description:
{session.state["generated_description"]}

SEO Metadata:
{session.state["seo_metadata"]}

Image Prompts:
{session.state["image_prompts"]}

Shopify URL:
{session.state["shopify_url"]}

Verification Result:
{session.state["verification_result"]}

Errors:
{session.state["errors"]}

Status:
{session.state["status"]}

Generate:

1. Markdown Report

2. JSON Report

Then call save_launch_reports().
"""
            )
        ],
    )

    print("\n==============================")
    print("RUNNING REPORT GENERATOR")
    print("==============================\n")

    async for event in runner.run_async(
        user_id="demo-user",
        session_id="report-session",
        new_message=message,
    ):
        if event.content:
            print(event.content)

    session = await session_service.get_session(
        app_name="report-test",
        user_id="demo-user",
        session_id="report-session",
    )

    print("\n==============================")
    print("REPORT FILES")
    print("==============================\n")

    print(session.state.get("markdown_report_path"))
    print(session.state.get("json_report_path"))

    print("\n==============================")
    print("SESSION STATE")
    print("==============================\n")

    for key, value in session.state.items():
        print(f"{key}:")
        print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())