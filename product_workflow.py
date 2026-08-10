from google.adk import Workflow

from agents.strategist_agent import strategist_agent
from agents.copywriter_agent import copywriter_agent
from agents.seo_agent import seo_agent
from agents.marketing_agent import marketing_agent
from agents.image_prompt_agent import image_prompt_agent
from agents.image_generator_agent import image_generator_agent
from agents.publisher_agent import publisher_agent
from agents.verification_agent import verification_agent
from agents.report_generator_agent import report_generator_agent

product_launch_workflow = Workflow(
    name="ProductLaunchWorkflow",
    edges=[
        ("START", strategist_agent),
        (strategist_agent, copywriter_agent),
        (copywriter_agent, seo_agent),
        (seo_agent, marketing_agent),
        (marketing_agent, image_prompt_agent),
        (image_prompt_agent, image_generator_agent),
        (image_generator_agent, publisher_agent),
        (publisher_agent, verification_agent),
        (verification_agent, report_generator_agent),
    ],
)


from agents.folder_agents import (
    folder_ingestion_agent,
    folder_validation_agent,
    folder_creation_agent,
    folder_media_agent,
    folder_verification_agent,
    folder_report_agent,
)

folder_product_workflow = Workflow(
    name="FolderProductWorkflow",
    edges=[
        ("START", folder_ingestion_agent),
        (folder_ingestion_agent, folder_validation_agent),
        (folder_validation_agent, folder_creation_agent),
        (folder_creation_agent, folder_media_agent),
        (folder_media_agent, folder_verification_agent),
        (folder_verification_agent, folder_report_agent),
    ],
)