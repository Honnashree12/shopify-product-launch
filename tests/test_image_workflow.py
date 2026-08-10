import os
import json
import shutil
from unittest import mock
from PIL import Image

import image_config
from services.image_generation_service import ImageGenerationService, sanitize_filename
from services.shopify_media_service import ShopifyMediaService
from shopify_client import ShopifyAPIError

def test_sanitize_filename():
    assert sanitize_filename("Mission Tiranga Workshop!") == "mission_tiranga_workshop"
    assert sanitize_filename("AI Space Code & Assembly 123") == "ai_space_code_assembly_123"

def test_image_config_defaults():
    assert image_config.NUMBER_OF_IMAGES in (5, 8)
    assert image_config.RESOLUTION == "1024x1024"
    assert image_config.ASPECT_RATIO == "1:1"
    assert image_config.RETRY_COUNT == 3
    assert len(image_config.NEGATIVE_PROMPTS) > 0

def test_mock_image_generation():
    # Set provider to mock
    with mock.patch("image_config.PROVIDER", "Mock"):
        prompts = {
            "hero": "A realistic satellite model, white studio background",
            "lifestyle": "Kids assembling a satellite model in classroom",
            "banner": "Wide banner showing satellite in space",
            "packaging": "Satellite model cardboard retail box",
            "closeup": "Close-up of solar panel materials"
        }
        res = ImageGenerationService.generate_and_verify_all("Test Product", prompts)
        
        # Verify result contains the correct number of paths
        assert res["success_count"] == 8
        assert len(res["image_paths"]) == 8
        
        for path in res["image_paths"]:
            assert os.path.exists(path)
            # Verify resolution & aspect ratio
            img = Image.open(path)
            assert img.size == (1024, 1024)

def test_verify_quality_fail_resolution():
    # Create an image that is too small
    small_path = "outputs/images/small.png"
    img = Image.new("RGB", (200, 200), color="blue")
    img.save(small_path)
    
    res = ImageGenerationService.verify_quality(small_path)
    assert res["overall_quality_pass"] is False
    assert res["resolution_ok"] is False

def test_verify_quality_fail_aspect_ratio():
    # Create an image with incorrect aspect ratio
    bad_ratio_path = "outputs/images/bad_ratio.png"
    img = Image.new("RGB", (1024, 800), color="green")
    img.save(bad_ratio_path)
    
    res = ImageGenerationService.verify_quality(bad_ratio_path)
    assert res["overall_quality_pass"] is False
    assert res["aspect_ratio_ok"] is False

@mock.patch("services.shopify_media_service.upload_product_images")
def test_shopify_media_service_upload(mock_upload):
    mock_upload.return_value = [{"id": "gid://shopify/ProductImage/123", "status": "ready", "mediaContentType": "IMAGE"}]
    
    res = ShopifyMediaService.upload_image("gid://shopify/Product/999", "dummy_path.png")
    assert res["id"] == "gid://shopify/ProductImage/123"
    mock_upload.assert_called_once_with("gid://shopify/Product/999", ["dummy_path.png"])

@mock.patch("services.shopify_media_service.upload_product_images")
def test_shopify_media_service_retry_upload(mock_upload):
    # Simulate failures then success
    mock_upload.side_effect = [
        Exception("Network glitch"),
        [{"id": "gid://shopify/ProductImage/123", "status": "ready", "mediaContentType": "IMAGE"}]
    ]
    
    with mock.patch("time.sleep") as mock_sleep:
        res = ShopifyMediaService.retry_upload("gid://shopify/Product/999", "dummy_path.png", retries=3)
        assert res["success"] is True
        assert res["attempts"] == 2
        assert res["media_id"] == "gid://shopify/ProductImage/123"
        mock_sleep.assert_called_once_with(2)
