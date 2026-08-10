"""
Generates product images from text prompts using Google's Gemini
2.5 Flash Image (Nano Banana) model via the google-genai SDK.
"""

import os
import logging
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)

IMAGE_MODEL = "gemini-2.5-flash-image-preview"

_client = None


def _get_client() -> genai.Client:
    """
    Lazily creates the genai.Client on first use, instead of at
    import time. main.py only calls load_dotenv() AFTER importing
    the agents (which import this module), so building the client
    at module level would run before the .env variables are loaded
    into os.environ and raise a missing API key error.
    """
    global _client
    if _client is None:
        if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True" or "GOOGLE_API_KEY" not in os.environ:
            _client = genai.Client()
        else:
            _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


def _extract_image_bytes(response) -> bytes | None:
    if not response.candidates:
        return None

    content = response.candidates[0].content
    if not content or not content.parts:
        return None

    for part in content.parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data

    return None


def generate_product_image(prompt: str) -> bytes:
    """
    Generates a single product image and returns the raw image bytes.
    Tries Vertex AI Imagen, Gemini Multimodal Modality, and Developer API Imagen fallback.
    """
    client = _get_client()
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True"
    
    if use_vertex:
        try:
            logger.info("Attempting image generation via Vertex AI Imagen 3 (imagen-3.0-generate-002)...")
            response = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="1:1"
                )
            )
            if response.generated_images:
                logger.info("Successfully generated image via Vertex AI Imagen 3.")
                return response.generated_images[0].image.image_bytes
        except Exception as e:
            logger.warning("Vertex AI Imagen 3 failed: %s. Falling back to multimodal content generation.", e)

    # 2. Try multimodal Gemini 2.5 Flash image modality
    try:
        logger.info("Attempting multimodal image generation (gemini-2.5-flash-image-preview)...")
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
        image_bytes = _extract_image_bytes(response)
        if image_bytes:
            logger.info("Successfully generated image via Multimodal Gemini 2.5 Flash.")
            return image_bytes
    except Exception as e:
        logger.warning("Multimodal content generation failed: %s. Trying Imagen Developer API.", e)

    # 3. Try Imagen Developer API (imagen-3.0-generate-002) as final model fallback
    try:
        logger.info("Attempting image generation via Developer API Imagen 3 (imagen-3.0-generate-002)...")
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1"
            )
        )
        if response.generated_images:
            logger.info("Successfully generated image via Developer API Imagen 3.")
            return response.generated_images[0].image.image_bytes
    except Exception as e:
        logger.warning("Imagen 3 Developer API fallback failed: %s.", e)

    raise RuntimeError("All Gemini/Imagen image generation methods failed.")


def save_product_image(prompt: str, output_path: str) -> None:
    """
    Generates a product image from a prompt and saves it to output_path.
    """
    image_bytes = generate_product_image(prompt)
    image = Image.open(BytesIO(image_bytes))
    image.save(output_path)
