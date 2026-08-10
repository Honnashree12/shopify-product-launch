import time
import logging
from typing import Any, List, Dict
import httpx

from shopify_client import (
    _get_config,
    ShopifyAPIError,
    upload_product_images,
    upload_product_media_files
)
import image_config

logger = logging.getLogger("shopify_media_service")

class ShopifyMediaService:
    @staticmethod
    def upload_image(product_id: Any, image_path: str) -> Dict[str, Any]:
        """
        Uploads a single image to Shopify using the GraphQL-based media uploader.
        """
        logger.info("Uploading media image %s for product %s", image_path, product_id)
        results = upload_product_images(product_id, [image_path])
        if not results:
            raise ShopifyAPIError(f"Staged upload returned empty results for file: {image_path}")
        return results[0]

    @classmethod
    def retry_upload(cls, product_id: Any, image_path: str, retries: int = None) -> Dict[str, Any]:
        """
        Resilient wrapper for upload_image that retries up to retry_count times on failure.
        """
        max_retries = retries if retries is not None else image_config.RETRY_COUNT
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            logger.info("Uploading image '%s' (Attempt %d/%d)...", image_path, attempt, max_retries)
            try:
                result = cls.upload_image(product_id, image_path)
                logger.info("Successfully uploaded media image '%s'. Media ID: %s", image_path, result.get("id"))
                return {
                    "success": True,
                    "image_path": image_path,
                    "media_id": result.get("id"),
                    "attempts": attempt,
                    "status": result.get("status"),
                    "media_content_type": result.get("mediaContentType")
                }
            except Exception as e:
                logger.warning("Upload failed for image '%s' on attempt %d: %s", image_path, attempt, e)
                if attempt < max_retries:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.info("Sleeping for %d seconds before retrying...", sleep_time)
                    time.sleep(sleep_time)
                else:
                    return {
                        "success": False,
                        "image_path": image_path,
                        "error": str(e),
                        "attempts": attempt
                    }
        
        return {
            "success": False,
            "image_path": image_path,
            "error": "Max retries exceeded",
            "attempts": max_retries
        }

    @staticmethod
    def verify_media(product_id: Any) -> List[Dict[str, Any]]:
        """
        Queries Shopify GraphQL API to fetch the active media list for verification.
        """
        base_url, store_url, headers = _get_config()
        graphql_url = f"{base_url}/graphql.json"
        
        # Format product GID
        gid = str(product_id)
        if not gid.startswith("gid://shopify/Product/"):
            gid = f"gid://shopify/Product/{product_id}"

        query = """
        query getProductMedia($id: ID!) {
          product(id: $id) {
            media(first: 50) {
              nodes {
                id
                status
                mediaContentType
              }
            }
          }
        }
        """
        
        logger.info("Verifying product media exists on Shopify for GID %s", gid)
        try:
            response = httpx.post(
                graphql_url,
                json={"query": query, "variables": {"id": gid}},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                logger.error("Verify media GraphQL query returned errors: %s", data["errors"])
                raise ShopifyAPIError(f"Verify media failed: {data['errors']}")
            
            product_data = data.get("data", {}).get("product")
            if not product_data:
                logger.warning("Verify media: product with ID %s not found on Shopify", gid)
                return []
            
            media_nodes = product_data.get("media", {}).get("nodes", [])
            logger.info("Found %d media items on Shopify for product %s", len(media_nodes), product_id)
            return media_nodes
        except Exception as e:
            logger.exception("Failed to query media status on Shopify")
            return []

    @classmethod
    def upload_and_attach_all(cls, product_id: Any, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Uploads a list of images one-by-one with retry resilience.
        Returns details for logging and reporting.
        """
        results = []
        for path in image_paths:
            res = cls.retry_upload(product_id, path)
            results.append(res)
        return results

    @classmethod
    def retry_upload_media(cls, product_id: Any, file_path: str, retries: int = None) -> Dict[str, Any]:
        """
        Resilient wrapper for upload_product_media_files that retries up to retry_count times on failure.
        Supports both image and video uploads.
        """
        max_retries = retries if retries is not None else image_config.RETRY_COUNT
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            logger.info("Uploading media file '%s' (Attempt %d/%d)...", file_path, attempt, max_retries)
            try:
                results = upload_product_media_files(product_id, [file_path])
                if not results:
                    raise ShopifyAPIError(f"Staged upload returned empty results for file: {file_path}")
                result = results[0]
                logger.info("Successfully uploaded media file '%s'. Media ID: %s", file_path, result.get("id"))
                return {
                    "success": True,
                    "file_path": file_path,
                    "media_id": result.get("id"),
                    "attempts": attempt,
                    "status": result.get("status"),
                    "media_content_type": result.get("mediaContentType")
                }
            except Exception as e:
                logger.warning("Upload failed for media file '%s' on attempt %d: %s", file_path, attempt, e)
                if attempt < max_retries:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.info("Sleeping for %d seconds before retrying...", sleep_time)
                    time.sleep(sleep_time)
                else:
                    return {
                        "success": False,
                        "file_path": file_path,
                        "error": str(e),
                        "attempts": attempt
                    }
        
        return {
            "success": False,
            "file_path": file_path,
            "error": "Max retries exceeded",
            "attempts": max_retries
        }

    @classmethod
    def upload_and_attach_all_media(cls, product_id: Any, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Uploads a list of media files (images or videos) one-by-one with retry resilience.
        Returns details for logging and reporting.
        """
        results = []
        for path in file_paths:
            res = cls.retry_upload_media(product_id, path)
            results.append(res)
        return results
