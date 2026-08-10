from agents.copywriter_agent import copywriter_agent
from agents.seo_agent import seo_agent
from agents.strategist_agent import strategist_agent
from agents.image_prompt_agent import image_prompt_agent
from agents.publisher_agent import publisher_agent
from agents.verification_agent import verification_agent
from agents.report_generator_agent import report_generator_agent

from agents.folder_agents import (
    folder_ingestion_agent,
    folder_validation_agent,
    folder_creation_agent,
    folder_media_agent,
    folder_verification_agent,
    folder_report_agent,
)

print("✅ Copywriter loaded:", copywriter_agent.name)
print("✅ SEO loaded:", seo_agent.name)
print("✅ Strategist loaded:", strategist_agent.name)
print("✅ Image Prompt loaded:", image_prompt_agent.name)
print("✅ Publisher loaded:", publisher_agent.name)
print("✅ Verification loaded:", verification_agent.name)
print("✅ Report Generator loaded:", report_generator_agent.name)

print("✅ Folder Ingestion loaded:", folder_ingestion_agent.name)
print("✅ Folder Validation loaded:", folder_validation_agent.name)
print("✅ Folder Creation loaded:", folder_creation_agent.name)
print("✅ Folder Media loaded:", folder_media_agent.name)
print("✅ Folder Verification loaded:", folder_verification_agent.name)
print("✅ Folder Report loaded:", folder_report_agent.name)