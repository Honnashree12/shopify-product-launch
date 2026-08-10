import os

# Image Generation Configuration
PROVIDER = os.getenv("IMAGE_PROVIDER", "Google Imagen")  # Configurable: Google Imagen, OpenAI Images, Flux, Stable Diffusion XL, Ideogram, Nano Banana
RESOLUTION = os.getenv("IMAGE_RESOLUTION", "1024x1024")
ASPECT_RATIO = os.getenv("IMAGE_ASPECT_RATIO", "1:1")
NUMBER_OF_IMAGES = int(os.getenv("IMAGE_NUMBER_OF_IMAGES", "8"))
RETRY_COUNT = int(os.getenv("IMAGE_RETRY_COUNT", "3"))

# Commercial product photography negative prompts to optimize realistic output
NEGATIVE_PROMPTS = (
    "plastic look, blurry, low resolution, watermark, text artifacts, oversaturated colors, "
    "distorted structures, distorted hands, fake lighting, fake reflections, unrealistic shadows, "
    "hallucinated branding, cropped products, incorrect proportions, illustration, drawing, painting"
)

# AI Vision verification quality thresholds (for LLM verification)
QUALITY_THRESHOLD = 0.8
