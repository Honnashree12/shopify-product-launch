from google.adk import Workflow

from agents.copywriter_agent import copywriter_agent
from agents.seo_agent import seo_agent
from agents.strategist_agent import strategist_agent
from agents.image_prompt_agent import image_prompt_agent
from agents.publisher_agent import publisher_agent
from agents.verification_agent import verification_agent
from agents.report_generator_agent import report_generator_agent

product_launch_workflow = Workflow(
    name="ProductLaunchWorkflow",
    edges=[
        ("START", copywriter_agent),
        (copywriter_agent, seo_agent),
        (seo_agent, strategist_agent),
        (strategist_agent, image_prompt_agent),
        (image_prompt_agent, publisher_agent),
        (publisher_agent, verification_agent),
        (verification_agent, report_generator_agent),
    ],
)