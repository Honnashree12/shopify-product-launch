from fastapi import FastAPI
import uvicorn

from shopify_mock.service import router

app = FastAPI(title="Mock Shopify API")

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Mock Shopify API is running"}

if __name__ == "__main__":
    uvicorn.run(
        "shopify_mock.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )