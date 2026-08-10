import logging
import os
import re
from dotenv import load_dotenv

# Ensure environment variables are loaded before client initialization
load_dotenv()

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context
from tools.image_generator import save_product_image

logger = logging.getLogger("image_generator_agent")


def sanitize_filename(name: str) -> str:
    """
    Sanitize product name for filesystem safety.
    - lowercase
    - spaces to underscores
    - strip special characters (only keep lowercase alphanumeric and underscores)
    """
    name = name.lower()
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def generate_images(tool_context: ToolContext) -> str:
    """
    Pass-through: actual image generation, quality verification, 
    and upload will run dynamically after product creation in the publisher step.
    """
    logger.info("Deferred image generation: images will be generated, quality-checked, and uploaded after product creation.")
    return "Pre-generation skipped. Actual generation, verification, and upload are deferred to the publishing stage."


image_generator_agent = Agent(
    name="ImageGeneratorAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Shopify Image Generator Agent.

Your task is to take the generated image prompts from the workflow state.

To support the post-creation workflow, call the generate_images() tool to indicate that pre-generation is successfully completed/deferred.

Your final action MUST be calling generate_images().
""",
    tools=[
        get_product_context,
        generate_images,
    ],
)
