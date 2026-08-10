from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from product_workflow import product_launch_workflow, folder_product_workflow

APP_NAME = "shopify-product-launch"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=product_launch_workflow,
    session_service=session_service,
)

folder_runner = Runner(
    app_name=APP_NAME,
    agent=folder_product_workflow,
    session_service=session_service,
)