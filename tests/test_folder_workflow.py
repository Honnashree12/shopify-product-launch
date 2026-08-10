import collections
import collections.abc
collections.Mapping = collections.abc.Mapping
collections.MutableMapping = collections.abc.MutableMapping
collections.Sequence = collections.abc.Sequence
collections.MutableSequence = collections.abc.MutableSequence
collections.Iterable = collections.abc.Iterable

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from state import ProductLaunchState
from tools.folder_tools import (
    ingest_and_extract_folder_tool,
    validate_folder_data_tool,
    create_shopify_product_tool,
    generate_folder_reports_tool,
)

class MockToolContext:
    def __init__(self, state):
        self.state = state


@pytest.fixture
def temp_product_folder(tmp_path):
    folder = tmp_path / "test-product-folder"
    folder.mkdir()
    return folder


# =====================================================================
# SCENARIO 1: Valid folder with product.json
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario1_valid_folder_with_json(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "STEM Explorer Kit",
        "description": "Educational kit for kids",
        "price": 1499.0,
        "compare_at_price": 1999.0,
        "category": "Educational Toys",
        "sku": "STEM-KIT-01",
        "inventory_quantity": 25,
        "status": "ACTIVE",
        "tags": ["STEM", "Kids", "Toys"],
        "confidence": {"title": "HIGH", "price": "HIGH"},
        "conflicts": [],
        "missing_fields": [],
        "media_ranking": [{"file_path": str(temp_product_folder / "hero.png"), "rank": 1, "type": "IMAGE", "is_product_media": True}]
    })
    mock_client.models.generate_content.return_value = mock_response

    # Setup files
    (temp_product_folder / "product.json").write_text('{"title": "STEM Explorer Kit"}', encoding="utf-8")
    (temp_product_folder / "hero.png").write_text("fake image content", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    res = ingest_and_extract_folder_tool(context)

    assert "STEM Explorer Kit" in res
    assert state["product_name"] == "STEM Explorer Kit"
    assert state["product_price"] == 1499.0
    assert state["sku"] == "STEM-KIT-01"
    assert len(state["detected_images"]) == 1


# =====================================================================
# SCENARIO 2: Folder fallback to DOCX, PDF, CSV, XLSX, TXT, MD
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
@patch("tools.file_extractor.extract_pdf")
@patch("tools.file_extractor.extract_docx")
@patch("tools.file_extractor.extract_xlsx")
def test_scenario2_fallbacks(mock_xlsx, mock_docx, mock_pdf, mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Fallbacks Product",
        "description": "Description from DOCX",
        "price": 299.0,
        "sku": "FALLBACK-01",
        "inventory_quantity": 5,
        "confidence": {},
        "conflicts": [],
        "missing_fields": []
    })
    mock_client.models.generate_content.return_value = mock_response

    mock_pdf.return_value = "Content from PDF"
    mock_docx.return_value = "Description from DOCX"
    mock_xlsx.return_value = "Price: 299"

    (temp_product_folder / "details.pdf").write_text("dummy", encoding="utf-8")
    (temp_product_folder / "specs.docx").write_text("dummy", encoding="utf-8")
    (temp_product_folder / "pricing.xlsx").write_text("dummy", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert state["product_name"] == "Fallbacks Product"
    assert state["product_description"] == "Description from DOCX"
    assert state["product_price"] == 299.0


# =====================================================================
# SCENARIO 3: Conflict detection
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario3_conflicts(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Conflict Product",
        "description": "Some description",
        "price": 1299.0,
        "confidence": {"price": "LOW"},
        "conflicts": [{"field": "price", "message": "pricing.xlsx has 1299, but price.txt has 1499"}],
        "missing_fields": []
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "price.txt").write_text("1499", encoding="utf-8")
    (temp_product_folder / "pricing.xlsx").write_text("1299", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert len(state["manifest"]["conflicts"]) == 1
    assert state["manifest"]["confidence"]["price"] == "LOW"


# =====================================================================
# SCENARIO 4: Confidence levels
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario4_confidence_levels(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Confidence Product",
        "description": "Desc",
        "price": 99.0,
        "confidence": {"title": "HIGH", "price": "LOW", "sku": "MEDIUM"},
        "conflicts": [],
        "missing_fields": []
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "info.txt").write_text("Confidence Product", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert state["manifest"]["confidence"]["title"] == "HIGH"
    assert state["manifest"]["confidence"]["price"] == "LOW"


# =====================================================================
# SCENARIO 5: Missing required fields
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario5_missing_fields(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": None,
        "description": "Only description here",
        "price": None,
        "confidence": {},
        "conflicts": [],
        "missing_fields": ["title", "price"]
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "desc.txt").write_text("Only description here", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    # Validate tool should halt/pause
    val_res = validate_folder_data_tool(context)
    assert "Validation paused" in val_res
    assert "title" in state["missing_fields_list"]


# =====================================================================
# SCENARIO 6: Category/Product type taxonomy inference
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario6_category_inference(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Wireless Earbuds",
        "description": "Listen to music",
        "price": 2999.0,
        "category": "Electronics > Audio > Headphones",
        "product_type": "Wireless Earbuds",
        "confidence": {"category": "HIGH"},
        "conflicts": [],
        "missing_fields": []
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "product.json").write_text("{}", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert state["product_category"] == "Wireless Earbuds"
    assert state["manifest"]["category"] == "Electronics > Audio > Headphones"


# =====================================================================
# SCENARIO 7: Digital item / Workshop (no shipping)
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario7_digital_item(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Python Workshop Session",
        "description": "Coding classes",
        "price": 499.0,
        "requires_shipping": False,
        "confidence": {},
        "conflicts": [],
        "missing_fields": []
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "workshop.txt").write_text("Learn Python programming", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert state["manifest"]["requires_shipping"] is False


# =====================================================================
# SCENARIO 8: Safe Image Conversion (TIFF -> PNG)
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
@patch("tools.file_extractor.convert_image_if_needed")
@patch("tools.file_extractor.get_image_metadata")
def test_scenario8_image_conversion(mock_meta, mock_convert, mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "TIFF Product",
        "description": "Desc",
        "price": 10.0,
        "confidence": {},
        "conflicts": [],
        "missing_fields": [],
        "media_ranking": [{"file_path": str(temp_product_folder / "photo_converted.png"), "rank": 1, "type": "IMAGE", "is_product_media": True}]
    })
    mock_client.models.generate_content.return_value = mock_response

    mock_convert.return_value = (str(temp_product_folder / "photo_converted.png"), True)
    mock_meta.return_value = {"file_path": str(temp_product_folder / "photo_converted.png"), "type": "IMAGE", "width": 800, "height": 600}

    (temp_product_folder / "photo.tiff").write_text("fake tiff", encoding="utf-8")
    # Actually create the converted file so exists check passes
    (temp_product_folder / "photo_converted.png").write_text("fake png", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert "Converted unsupported image photo.tiff to PNG format." in state["conversions"]
    assert str(temp_product_folder / "photo_converted.png") in state["detected_images"]


# =====================================================================
# SCENARIO 9: Safe Video Conversion (AVI -> MP4)
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
@patch("tools.file_extractor.convert_video_if_needed")
@patch("tools.file_extractor.get_video_metadata")
@patch("cv2.VideoCapture")
def test_scenario9_video_conversion(mock_video_cap, mock_meta, mock_convert, mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "AVI Product",
        "description": "Desc",
        "price": 10.0,
        "confidence": {},
        "conflicts": [],
        "missing_fields": [],
        "media_ranking": [{"file_path": str(temp_product_folder / "promo_converted.mp4"), "rank": 1, "type": "VIDEO", "is_product_media": True}]
    })
    mock_client.models.generate_content.return_value = mock_response

    # Mock OpenCV Cap check
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_video_cap.return_value = mock_cap

    mock_convert.return_value = (str(temp_product_folder / "promo_converted.mp4"), True)
    mock_meta.return_value = {"file_path": str(temp_product_folder / "promo_converted.mp4"), "type": "VIDEO", "duration": 15.0}

    (temp_product_folder / "promo.avi").write_text("fake avi", encoding="utf-8")
    (temp_product_folder / "promo_converted.mp4").write_text("fake mp4", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    assert "Converted unsupported video promo.avi to MP4 format (audio track omitted)." in state["conversions"]
    assert str(temp_product_folder / "promo_converted.mp4") in state["detected_videos"]


# =====================================================================
# SCENARIO 10: Ranked primary image detection
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario10_ranked_images(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # We pass two images, AI ranks "hero.jpg" as 1, and "side.png" as 2
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Ranked Product",
        "description": "Desc",
        "price": 10.0,
        "confidence": {},
        "conflicts": [],
        "missing_fields": [],
        "media_ranking": [
            {"file_path": str(temp_product_folder / "side.png"), "rank": 2, "type": "IMAGE", "is_product_media": True},
            {"file_path": str(temp_product_folder / "hero.jpg"), "rank": 1, "type": "IMAGE", "is_product_media": True}
        ]
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "side.png").write_text("side", encoding="utf-8")
    (temp_product_folder / "hero.jpg").write_text("hero", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    # hero.jpg should be FIRST in detected_images due to ranking sorting
    assert state["detected_images"][0] == str(temp_product_folder / "hero.jpg")
    assert state["detected_images"][1] == str(temp_product_folder / "side.png")


# =====================================================================
# SCENARIO 11: Safe filtering of logos / screenshots
# =====================================================================
@patch("tools.folder_tools.get_genai_client")
def test_scenario11_filter_logos(mock_get_client, temp_product_folder):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Product with Logo",
        "description": "Desc",
        "price": 10.0,
        "confidence": {},
        "conflicts": [],
        "missing_fields": [],
        "media_ranking": [
            {"file_path": str(temp_product_folder / "product.jpg"), "rank": 1, "type": "IMAGE", "is_product_media": True},
            {"file_path": str(temp_product_folder / "logo.png"), "rank": 2, "type": "IMAGE", "is_product_media": False}
        ]
    })
    mock_client.models.generate_content.return_value = mock_response

    (temp_product_folder / "product.jpg").write_text("product", encoding="utf-8")
    (temp_product_folder / "logo.png").write_text("logo", encoding="utf-8")

    state = {
        "product_folder_path": str(temp_product_folder),
        "preview_mode": True,
        "approved_to_publish": False,
    }
    context = MockToolContext(state)
    ingest_and_extract_folder_tool(context)

    # logo.png should NOT be present in detected_images
    assert str(temp_product_folder / "product.jpg") in state["detected_images"]
    assert str(temp_product_folder / "logo.png") not in state["detected_images"]


# =====================================================================
# SCENARIO 12: Duplicate listing check
# =====================================================================
@patch("tools.folder_tools.get_product_by_sku")
def test_scenario12_duplicate_check(mock_get_sku):
    # Mock that duplicate SKU exists
    mock_get_sku.return_value = {
        "product_id": 98765,
        "title": "Duplicate STEM Kit",
        "url": "https://store.myshopify.com/products/duplicate",
    }

    state = {
        "product_name": "STEM Kit",
        "sku": "STEM-01",
        "approved_to_publish": True,
        "preview_mode": True,
        "duplicate_action": "ASK"
    }
    context = MockToolContext(state)
    res = create_shopify_product_tool(context)

    assert "Product duplicate detected" in res
    assert state["status"] == "awaiting_approval"
    assert state["duplicate_detected"] is True
    assert state["existing_product_id"] == 98765


# =====================================================================
# SCENARIO 13: Duplicate Update Action
# =====================================================================
@patch("tools.folder_tools.get_product_by_sku")
@patch("tools.folder_tools.update_product")
def test_scenario13_duplicate_update(mock_update, mock_get_sku):
    mock_get_sku.return_value = {
        "product_id": 98765,
        "title": "Duplicate STEM Kit",
        "url": "https://store.myshopify.com/products/duplicate",
    }
    
    mock_update.return_value = {
        "id": 98765,
        "title": "Updated STEM Kit",
        "url": "https://store.myshopify.com/products/duplicate",
        "variants": [{"id": 1234, "inventory_item_id": 5678}]
    }

    state = {
        "product_name": "Updated STEM Kit",
        "product_description": "New description",
        "product_price": 1499.0,
        "sku": "STEM-01",
        "approved_to_publish": True,
        "preview_mode": True,
        "duplicate_action": "UPDATE"
    }
    context = MockToolContext(state)
    res = create_shopify_product_tool(context)

    assert "updated successfully" in res
    assert state["shopify_product_id"] == 98765
    assert state["duplicate_action_resolved"] == "UPDATED"


# =====================================================================
# SCENARIO 14: Duplicate Create Action
# =====================================================================
@patch("tools.folder_tools.get_product_by_sku")
@patch("tools.folder_tools.create_product")
def test_scenario14_duplicate_create(mock_create, mock_get_sku):
    mock_get_sku.return_value = {
        "product_id": 98765,
        "title": "Duplicate STEM Kit",
        "url": "https://store.myshopify.com/products/duplicate",
    }
    
    mock_create.return_value = {
        "id": 11111,
        "title": "STEM Kit (Duplicate)",
        "url": "https://store.myshopify.com/products/duplicate-2",
        "variants": [{"id": 1234, "inventory_item_id": 5678}]
    }

    state = {
        "product_name": "STEM Kit",
        "product_description": "Description",
        "product_price": 1499.0,
        "sku": "STEM-01",
        "approved_to_publish": True,
        "preview_mode": True,
        "duplicate_action": "CREATE"
    }
    context = MockToolContext(state)
    res = create_shopify_product_tool(context)

    assert "created successfully" in res
    assert state["shopify_product_id"] == 11111


# =====================================================================
# SCENARIO 15: Duplicate Cancel Action
# =====================================================================
@patch("tools.folder_tools.get_product_by_sku")
def test_scenario15_duplicate_cancel(mock_get_sku):
    mock_get_sku.return_value = {
        "product_id": 98765,
        "title": "Duplicate STEM Kit",
        "url": "https://store.myshopify.com/products/duplicate",
    }

    state = {
        "product_name": "STEM Kit",
        "sku": "STEM-01",
        "approved_to_publish": True,
        "preview_mode": True,
        "duplicate_action": "CANCEL"
    }
    context = MockToolContext(state)
    res = create_shopify_product_tool(context)

    assert "PRODUCT CREATION CANCELLED" in res
    assert "workflow_error" in state
