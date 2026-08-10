import os
from google import genai
from google.genai import types

# Make sure env is loaded
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "intern-bnmit-july-2026"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

client = genai.Client()

models_to_test = [
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
    "imagen-3.0-fast-generate-002",
    "imagegeneration@006",
    "imagegeneration@005"
]

for model in models_to_test:
    print(f"Testing model: {model}...")
    try:
        response = client.models.generate_images(
            model=model,
            prompt="A simple blue square.",
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1"
            )
        )
        if response.generated_images:
            print(f"-> SUCCESS! Model {model} is available and generated images.")
            break
    except Exception as e:
        print(f"-> FAILED for model {model}: {e}")
