from state import ProductLaunchState

from agents.copywriter_agent import CopywriterAgent
from agents.seo_agent import SEOAgent
from agents.strategist_agent import StrategistAgent
from agents.image_prompt_agent import ImagePromptAgent

state = ProductLaunchState(
    product_name="Wireless Earbuds",
    raw_description="Bluetooth earbuds with active noise cancellation",
    price=2999,
    category="Electronics"
)

print("Testing Copywriter Agent...")
copywriter = CopywriterAgent()
state = copywriter.run(state)
print("✓ Copywriter Agent passed")

print("Testing SEO Agent...")
seo = SEOAgent()
state = seo.run(state)
print("✓ SEO Agent passed")

print("Testing Strategist Agent...")
strategist = StrategistAgent()
state = strategist.run(state)
print("✓ Strategist Agent passed")

print("Testing Image Prompt Agent...")
image_agent = ImagePromptAgent()
state = image_agent.run(state)
print("✓ Image Prompt Agent passed")

print("\nAll agents executed successfully!")
print(state)