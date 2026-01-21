"""
Figure upload to Cloudflare R2 storage.
Provides public URLs for figures in the RAG system.
"""

import logging
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.config import settings

logger = logging.getLogger(__name__)


class R2Uploader:
    """
    Uploads figures to Cloudflare R2 (S3-compatible) storage.
    """

    def __init__(self):
        """Initialize R2 uploader with boto3 S3 client."""
        # Only initialize if credentials are configured
        if not settings.cloudflare_account_id or not settings.cloudflare_r2_access_key_id:
            logger.warning(
                "Cloudflare R2 credentials not configured - uploader disabled"
            )
            self.client = None
            self.enabled = False
            return

        # Create S3 client configured for Cloudflare R2
        endpoint_url = f"https://{settings.cloudflare_account_id}.r2.cloudflarestorage.com"

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.cloudflare_r2_access_key_id,
            aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
            region_name="auto",  # R2 uses 'auto' region
        )

        self.bucket_name = settings.cloudflare_r2_bucket_name
        self.enabled = True

        logger.info(f"R2 uploader initialized for bucket: {self.bucket_name}")

    def upload_figure(self, figure_path: Path, figure_id: str) -> Optional[str]:
        """
        Upload a figure to R2 and return its public URL.

        Args:
            figure_path: Path to the figure file
            figure_id: Unique identifier for the figure

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug("R2 uploader not enabled, skipping upload")
            return None

        try:
            # Object key (path in bucket)
            object_key = f"figures/{figure_id}.png"

            # Upload file
            self.client.upload_file(
                str(figure_path),
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": "image/png"},
            )

            # Generate public URL
            # R2 public URL format: https://pub-<account-id>.r2.dev/<object-key>
            # Note: Requires public access configuration in R2 dashboard
            public_url = (
                f"https://pub-{settings.cloudflare_account_id}.r2.dev/{object_key}"
            )

            logger.info(f"Uploaded: {figure_id}.png")
            return public_url

        except ClientError as e:
            logger.error(f"Failed to upload {figure_id}: {e}")
            return None

    def upload_figures_batch(self, figures: list) -> list:
        """
        Upload multiple figures and update their metadata with URLs.

        Args:
            figures: List of figure metadata dicts

        Returns:
            Updated list with cloudflare_url populated
        """
        if not self.enabled:
            logger.info("R2 uploader not enabled, using local file paths only")
            return figures

        logger.info(f"Uploading {len(figures)} figures to R2")

        for figure in figures:
            try:
                figure_path = Path(figure["local_path"])
                figure_id = figure["figure_id"]

                # Upload and get URL
                url = self.upload_figure(figure_path, figure_id)

                # Update metadata
                figure["cloudflare_url"] = url

            except Exception as e:
                logger.error(f"Failed to upload figure {figure.get('figure_id')}: {e}")
                figure["cloudflare_url"] = None
                continue

        return figures


def upload_figure(figure_path: str, figure_id: str) -> Optional[str]:
    """Convenience function to upload a single figure."""
    uploader = R2Uploader()
    return uploader.upload_figure(Path(figure_path), figure_id)
