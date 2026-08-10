<<<<<<< HEAD
# 🚀 AI Shopify Product Launch Agent

An AI-powered multi-agent system that automates the end-to-end Shopify product launch process using **Google ADK**, **Gemini 2.5 Flash**, and the **Shopify Admin API**.

## 📌 Project Overview

This project uses multiple AI agents that work together to automate publishing a product to Shopify. The workflow generates marketing content, SEO metadata, verifies the product, publishes it to Shopify, and creates launch reports.

---

## ✨ Features

- 📝 AI-generated product copywriting
- 🔍 Automatic SEO metadata generation
- 📢 Marketing campaign generation
- 🛍️ Product publishing to Shopify
- ✅ Product verification
- 📄 Automatic Markdown and JSON launch reports
- 🤖 Multi-agent orchestration using Google ADK

---

## 🏗️ Workflow

```text
Product Input
      │
      ▼
Copywriter Agent
      │
      ▼
SEO Agent
      │
      ▼
Marketing Agent
      │
      ▼
Verification Agent
      │
      ▼
Publish to Shopify
      │
      ▼
Report Generator Agent
```

---

## 🛠️ Tech Stack

- Python
- Google ADK (Agent Development Kit)
- Gemini 2.5 Flash
- FastAPI
- Shopify Admin API
- JSON
- Markdown

---

## 📂 Project Structure

```
shopify-product-launch/
│
├── agents/
│   ├── copywriter_agent.py
│   ├── seo_agent.py
│   ├── strategist_agent.py
│   ├── verification_agent.py
│   ├── publisher_agent.py
│   └── report_generator_agent.py
│
├── tools/
├── workflow/
├── outputs/
├── shopify_client.py
├── main.py
├── product_workflow.py
├── requirements.txt
└── README.md
=======
# Shopify Product Launch & Creation Agent

This project is an advanced agentic assistant built with the Google ADK and FastAPI. It integrates with Shopify to automate the product catalog ingestion and creation workflows.

## Table of Contents
1. [Key Features](#key-features)
2. [Project Structure](#project-structure)
3. [Environment Configuration](#environment-configuration)
4. [Launch campaign vs Folder Upload](#launch-campaign-vs-folder-upload)
5. [Product Folder Layout Schema](#product-folder-layout-schema)
6. [Pipeline Execution Stages](#pipeline-execution-stages)
7. [Installation & Running Locally](#installation--running-locally)
8. [API Endpoints](#api-endpoints)
9. [Running Tests](#running-tests)

---

## Key Features

1. **Campaign Generation Agent**: Takes a raw product name and description, runs copywriters, SEO optimization, strategy, creates digital mockup prompts, generates images via Imagen, publishes to Shopify, and creates reports.
2. **Product Folder Creation Agent**: Ingests local product folders containing title, description, price, variant settings, SKUs, inventory, and supporting media files (MP4 videos, PNG/JPEG images).
3. **Resilient Staged Media Uploads**: Uses Shopify GraphQL staged uploads to upload both image files and video files safely without requiring external video hosts (like YouTube or Vimeo).
4. **Duplicate Safeguards**: Before publishing, checks for duplicates using Title and SKU. If matching records exist, halts execution to protect catalog hygiene.
5. **Detailed Reports**: Generates clean Markdown reports and JSON data logs locally in the `outputs/` directory.

---

## Project Structure

```
shopify-product-launch/
├── agents/                  # ADK Agent definitions
│   ├── folder_agents.py     # Folder creation pipeline agents
│   └── ...
├── tools/                   # ADK Tool definitions
│   ├── folder_tools.py      # Folder creation pipeline tools
│   └── ...
├── services/                # Backend services
│   └── shopify_media_service.py  # Video & image uploader logic
├── tests/                   # Test suite
│   ├── test_folder_workflow.py   # Folder Creation Agent tests
│   └── ...
├── static/                  # Launch Console frontend dashboard
│   ├── index.html           # Web console UI
│   └── ...
├── main.py                  # FastAPI server controller
├── shopify_client.py        # Custom client with GraphQL helpers
└── state.py                 # Pydantic schema for session state variables
>>>>>>> 87f8288 (Add Shopify product creation agent)
```

---

<<<<<<< HEAD
## 🚀 How It Works

1. User submits product information.
2. Copywriter Agent enhances the product description.
3. SEO Agent generates:
   - SEO Title
   - Meta Description
   - Keywords
   - URL Slug
4. Marketing Agent creates:
   - Campaign Name
   - Target Audience
   - Marketing Strategy
   - Social Media Caption
   - Email Subject
   - Call To Action
5. Verification Agent validates product information.
6. Publisher Agent publishes the product to Shopify.
7. Report Generator Agent creates:
   - `launch_report.md`
   - `launch_report.json`

---

## 📥 Sample Input

```json
{
  "product_name": "Wireless Bluetooth Earbuds",
  "raw_description": "Experience premium sound with ENC noise cancellation and 30-hour battery life.",
  "price": 2499,
  "category": "Electronics"
}
```

---

## 📤 Sample Output

- Product published to Shopify
- SEO Metadata generated
- Marketing campaign generated
- Verification completed
- Markdown report generated
- JSON report generated

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/your-username/shopify-product-launch.git
cd shopify-product-launch
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment:

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn main:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

---

## 🔑 Environment Variables

Create a `.env` file and configure your Shopify credentials:

```env
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-access-token
SHOPIFY_API_VERSION=2025-07
GOOGLE_API_KEY=your-google-api-key
```

---

## 📄 Reports Generated

After a successful launch, the project generates:

- `launch_report.md`
- `launch_report.json`

These reports contain:

- Product Details
- Shopify Details
- SEO Metadata
- Marketing Content
- Verification Results

---

## 🎯 Future Enhancements

- Product image generation using AI
- Email automation
- Multi-language SEO
- Analytics dashboard
- Inventory management
- Bulk product publishing

---

## 👩‍💻 Author

**Honnashree**

Final Year AIML Student

---

## ⭐ If you found this project useful, consider giving it a star!
=======
## Environment Configuration

Create a `.env` file in the root directory:
```ini
GEMINI_API_KEY="your-gemini-api-key"
SHOPIFY_SHOP_URL="https://your-store.myshopify.com"
SHOPIFY_ACCESS_TOKEN="shpat_your_token"
```

---

## Launch Campaign vs Folder Upload

* **Launch Campaign**: Input a product name, price, and category. The AI automatically writes copy, does SEO optimization, generates visual mockups, and lists the product.
* **Create from Folder**: Ingests a pre-packaged product folder. Ideal for bulk migrations or when high-fidelity photos/videos are already prepared.

---

## Product Folder Layout Schema

Place files inside a folder structured as follows:
```
my-product-folder/
├── product.json
├── images/
│   ├── hero.png
│   └── side.jpg
└── videos/
    └── intro.mp4
```

### JSON Metadata format (`product.json`)
```json
{
  "title": "Premium Wireless Earbuds",
  "description": "Ergonomic noise-cancelling earbuds with 35h battery life.",
  "price": 2499.00,
  "currency": "INR",
  "category": "Electronics",
  "vendor": "SoundMax",
  "tags": ["audio", "bluetooth", "wireless"],
  "sku": "EARBUDS-MAX-01",
  "inventory_quantity": 25,
  "status": "ACTIVE"
}
```

### Fallback Mode (No `product.json`)
If `product.json` is missing, the agent falls back to parsing text and markdown files in the folder:
* **Title**: `title.txt` or `title.md`
* **Description**: `description.txt` or `description.md`
* **Price**: `price.txt` or `price.md`
* **SKU**: `sku.txt` or `sku.md`
* **Inventory Quantity**: `quantity.txt` or `quantity.md` or `inventory.txt`

---

## Pipeline Execution Stages

1. **Ingest**: Read files, scan folders for images and MP4 videos, and parse fields.
2. **Validate**: Perform strict validations on required parameters (e.g. non-empty title, price > 0).
3. **Create**: Create Shopify product (and manage stock tracking if SKU & inventory are specified).
4. **Media**: Perform asynchronous staged uploads for all detected media and link them to the product.
5. **Verify**: Perform live GraphQL checks to verify listing status and variant visibility.
6. **Report**: Write local Markdown summary and JSON report files in the `outputs/` folder.

---

## Installation & Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
3. Open the web panel at [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) in your browser.

---

## API Endpoints

### 1. Launch Folder Product
* **URL**: `/launch-folder`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Body**: Files list (includes subfolders)
* **Response**:
  ```json
  {
    "session_id": "session-uuid",
    "status": "pending",
    "message": "Folder workflow started successfully."
  }
  ```

### 2. Check Session Status
* **URL**: `/status/{session_id}`
* **Method**: `GET`
* **Response**: Returns the current execution state (e.g. `completed`, `failed`).

---

## Running Tests

### Run Folder Creation Agent Unit Tests
To run isolated tests for folder ingestion and staged uploaders:
```bash
python -c "import pluggy; pluggy.PluginManager.load_setuptools_entrypoints = lambda *a, **k: 0; import pytest, sys; sys.exit(pytest.main(['tests/test_folder_workflow.py']))"
```

### Run Workshop Platform Integration Tests
To run pre-existing integration tests:
```bash
python run_tests.py
```
>>>>>>> 87f8288 (Add Shopify product creation agent)
