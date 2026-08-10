from google.adk import Agent
from tools.folder_tools import (
    ingest_and_extract_folder_tool,
    validate_folder_data_tool,
    create_shopify_product_tool,
    upload_folder_media_tool,
    verify_folder_product_tool,
    generate_folder_reports_tool,
)

folder_ingestion_agent = Agent(
    name="FolderIngestionAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Ingestion Agent.
Your job is to read the product folder and extract all product information.

Call the tool:
ingest_and_extract_folder_tool()

Return only the tool call.
""",
    tools=[ingest_and_extract_folder_tool],
)

folder_validation_agent = Agent(
    name="FolderValidationAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Validation Agent.
Your job is to validate the extracted product information.

Call the tool:
validate_folder_data_tool()

Return only the tool call.
""",
    tools=[validate_folder_data_tool],
)

folder_creation_agent = Agent(
    name="FolderCreationAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Creation Agent.
Your job is to create the Shopify product using the validated product data.

Call the tool:
create_shopify_product_tool()

Return only the tool call.
""",
    tools=[create_shopify_product_tool],
)

folder_media_agent = Agent(
    name="FolderMediaAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Media Agent.
Your job is to upload and attach all images and videos found in the product folder to the created Shopify product.

Call the tool:
upload_folder_media_tool()

Return only the tool call.
""",
    tools=[upload_folder_media_tool],
)

folder_verification_agent = Agent(
    name="FolderVerificationAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Verification Agent.
Your job is to verify that the Shopify product was created successfully with all details.

Call the tool:
verify_folder_product_tool()

Return only the tool call.
""",
    tools=[verify_folder_product_tool],
)

folder_report_agent = Agent(
    name="FolderReportAgent",
    model="gemini-2.5-flash",
    instruction="""
You are the Folder Report Agent.
Your job is to compile the final product launch report and save it.

Call the tool:
generate_folder_reports_tool()

Return only the tool call.
""",
    tools=[generate_folder_reports_tool],
)
