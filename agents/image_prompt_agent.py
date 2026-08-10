from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from tools.product_context import get_product_context

def save_image_prompts(
    hero_prompt: str,
    lifestyle_prompt: str,
    banner_prompt: str,
    classroom_prompt: str,
    thumbnail_prompt: str,
    certificate_prompt: str,
    gallery1_prompt: str,
    gallery2_prompt: str,
    tool_context: ToolContext,
) -> str:
    """
    Save generated AI image prompts into the shared workflow state.
    Supports Hero, Lifestyle, Banner, Classroom, Thumbnail, Certificate, and 2 Gallery images.
    """

    tool_context.state["image_prompts"] = {
        "hero": hero_prompt.strip(),
        "lifestyle": lifestyle_prompt.strip(),
        "banner": banner_prompt.strip(),
        "classroom": classroom_prompt.strip(),
        "thumbnail": thumbnail_prompt.strip(),
        "certificate": certificate_prompt.strip(),
        "gallery1": gallery1_prompt.strip(),
        "gallery2": gallery2_prompt.strip(),
        # Map backward compatible keys for safety
        "feature": gallery1_prompt.strip(),
        "packaging": certificate_prompt.strip(),
    }

    return "Image prompts saved successfully."


image_prompt_agent = Agent(
    name="ImagePromptAgent",
    model="gemini-2.5-flash",
    instruction="""
You are a professional AI Creative Director specializing in commercial product photography.

Your FIRST action MUST be calling:

get_product_context()

Use only actual product/workshop information.

Your task is to generate EIGHT professional AI image prompts suitable for generating highly realistic, commercial-catalog quality product images. The images must look like real DSLR photography with studio lighting and natural colors, avoiding any plastic appearance, oversaturation, text artifacts, or watermarks.

Generate the following:

1. Hero Image Prompt
- Clean white studio background, product/kit centered.
- Professional catalog style, sharp focus, soft shadows, realistic materials.

2. Lifestyle Image Prompt
- Real environment showing the product/kit in use or context.
- Natural lighting, realistic people/setting, premium commercial photography style.

3. Workshop Banner Prompt
- Wide composition (landscape ratio) suited for website banners/heros.
- Beautiful, high-conversion visual background with space left elegantly for marketing text overlays.

4. Classroom Scene Prompt
- Depict children/students actively learning, collaborating and building models in a bright, modern classroom.
- Natural lighting, authentic reactions, professional documentary photography style.

5. Product Thumbnail Prompt
- Square close-up of a key element of the kit or logo, clean, simple layout, optimized for tiny viewports.

6. Certificate Preview Prompt
- A professional workshop certificate template, elegantly styled with minimal text placeholder, clean layout.

7. Gallery Image 1 Prompt
- Creative composition showing the tools, components, and workbook spread on a desk.

8. Gallery Image 2 Prompt
- Dynamic close-up highlighting textures, metallic/plastic pieces, or model assembly details.

After generating all eight prompts, call:

save_image_prompts(
    hero_prompt,
    lifestyle_prompt,
    banner_prompt,
    classroom_prompt,
    thumbnail_prompt,
    certificate_prompt,
    gallery1_prompt,
    gallery2_prompt
)

Do not explain anything.
Only generate the image prompts.
""",
    tools=[
        save_image_prompts,
        get_product_context
    ]
)