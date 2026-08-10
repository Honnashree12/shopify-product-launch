import sys
import os
import shutil

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tests.test_image_workflow import (
    test_sanitize_filename,
    test_image_config_defaults,
    test_mock_image_generation,
    test_verify_quality_fail_resolution,
    test_verify_quality_fail_aspect_ratio,
    test_shopify_media_service_upload,
    test_shopify_media_service_retry_upload
)

def run_test(name, func, *args, **kwargs):
    print(f"Running {name}...")
    try:
        func(*args, **kwargs)
        print("-> SUCCESS")
    except Exception as e:
        print(f"-> FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise e

def main():
    print("==================================================")
    print("RUNNING IMAGE WORKFLOW INTEGRATION TESTS")
    print("==================================================")
    
    # Inline Setup
    os.makedirs("outputs/images", exist_ok=True)
    
    try:
        run_test("test_sanitize_filename", test_sanitize_filename)
        run_test("test_image_config_defaults", test_image_config_defaults)
        run_test("test_mock_image_generation", test_mock_image_generation)
        run_test("test_verify_quality_fail_resolution", test_verify_quality_fail_resolution)
        run_test("test_verify_quality_fail_aspect_ratio", test_verify_quality_fail_aspect_ratio)
        run_test("test_shopify_media_service_upload", test_shopify_media_service_upload)
        run_test("test_shopify_media_service_retry_upload", test_shopify_media_service_retry_upload)
        
        print("\n==================================================")
        print("TEST RUN RESULTS: ALL TESTS PASSED SUCCESSFULLY! [PASS]")
        print("==================================================")
    finally:
        # Inline Teardown
        if os.path.exists("outputs/images"):
            shutil.rmtree("outputs/images")

if __name__ == "__main__":
    main()
