"""
Figure upload to Supabase Storage.
Provides public URLs for figures in the RAG system.
"""

import logging
from pathlib import Path
from typing import Optional

from supabase import Client, create_client

from src.utils.config import settings

logger = logging.getLogger(__name__)


class SupabaseFigureUploader:
    """
    Uploads figures to Supabase Storage.
    """

    def __init__(self):
        """Initialize Supabase Storage client."""
        # Only initialize if credentials are configured
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning("Supabase credentials not configured - uploader disabled")
            self.client = None
            self.enabled = False
            return

        try:
            # Create Supabase client
            self.client: Client = create_client(
                settings.supabase_url, settings.supabase_key
            )

            self.bucket_name = settings.supabase_storage_bucket
            self.enabled = True

            logger.info(
                f"Supabase Storage uploader initialized for bucket: {self.bucket_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
            self.enabled = False

    def upload_figure(self, figure_path: Path, figure_id: str) -> Optional[str]:
        """
        Upload a figure to Supabase Storage and return its public URL.

        Args:
            figure_path: Path to the figure file
            figure_id: Unique identifier for the figure

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug("Supabase uploader not enabled, skipping upload")
            return None

        try:
            # Object path in bucket
            object_path = f"figures/{figure_id}.png"

            # Read file content
            with open(figure_path, "rb") as f:
                file_content = f.read()

            # Upload to Supabase Storage
            response = self.client.storage.from_(self.bucket_name).upload(
                path=object_path,
                file=file_content,
                file_options={"content-type": "image/png", "upsert": "true"},
            )

            # Generate public URL
            # Supabase public URL format: https://<project-ref>.supabase.co/storage/v1/object/public/<bucket>/<path>
            public_url = f"{settings.supabase_url}/storage/v1/object/public/{self.bucket_name}/{object_path}"

            logger.info(f"Uploaded: {figure_id}.png")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload {figure_id}: {e}")
            return None

    def upload_figures_batch(self, figures: list) -> list:
        """
        Upload multiple figures and update their metadata with URLs.

        Args:
            figures: List of figure metadata dicts

        Returns:
            Updated list with supabase_url populated
        """
        if not self.enabled:
            logger.info("Supabase uploader not enabled, using local file paths only")
            return figures

        logger.info(f"Uploading {len(figures)} figures to Supabase Storage")

        for figure in figures:
            try:
                figure_path = Path(figure["local_path"])
                figure_id = figure["figure_id"]

                # Upload and get URL
                url = self.upload_figure(figure_path, figure_id)

                # Update metadata (keeping cloudflare_url key for backwards compatibility)
                figure["cloudflare_url"] = url
                figure["supabase_url"] = url  # Add explicit supabase_url field

            except Exception as e:
                logger.error(f"Failed to upload figure {figure.get('figure_id')}: {e}")
                figure["cloudflare_url"] = None
                figure["supabase_url"] = None
                continue

        return figures


# Backwards compatibility alias
R2Uploader = SupabaseFigureUploader


def upload_figure(figure_path: str, figure_id: str) -> Optional[str]:
    """Convenience function to upload a single figure."""
    uploader = SupabaseFigureUploader()
    return uploader.upload_figure(Path(figure_path), figure_id)
