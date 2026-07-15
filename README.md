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
```

---

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
