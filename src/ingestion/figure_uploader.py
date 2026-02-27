"""
Figure upload to Firebase Storage.
Provides public URLs for figures in the RAG system.
"""

import logging
from pathlib import Path
from typing import Optional

from google.cloud import storage as gcs

from src.utils.config import settings

logger = logging.getLogger(__name__)


class FirebaseStorageFigureUploader:
    """
    Uploads figures to Firebase Storage using Application Default Credentials (ADC).
    Works automatically on Cloud Run without a service account key file.
    """

    def __init__(self):
        """Initialize Firebase Storage client using ADC."""
        if not settings.firebase_storage_bucket:
            logger.warning(
                "FIREBASE_STORAGE_BUCKET not configured - figure uploader disabled"
            )
            self.gcs_client = None
            self.bucket = None
            self.enabled = False
            return

        try:
            # Uses Application Default Credentials automatically
            self.gcs_client = gcs.Client()
            self.bucket_name = settings.firebase_storage_bucket
            self.bucket = self.gcs_client.bucket(self.bucket_name)
            self.enabled = True

            logger.info(
                f"Firebase Storage figure uploader initialized for bucket: {self.bucket_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Firebase Storage client: {e}")
            self.gcs_client = None
            self.bucket = None
            self.enabled = False

    def get_figure_url(self, filename: str) -> str:
        """
        Construct the public URL for a figure by filename.

        Args:
            filename: The figure filename (e.g., "fig_001.png")

        Returns:
            Public URL string
        """
        return f"https://storage.googleapis.com/{self.bucket_name}/figures/{filename}"

    def upload_figure(self, figure_path: Path, figure_id: str) -> Optional[str]:
        """
        Upload a figure to Firebase Storage and return its public URL.

        Args:
            figure_path: Path to the figure file
            figure_id: Unique identifier for the figure

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug("Firebase Storage uploader not enabled, skipping upload")
            return None

        try:
            filename = f"{figure_id}.png"
            object_path = f"figures/{filename}"

            blob = self.bucket.blob(object_path)
            blob.upload_from_filename(str(figure_path), content_type="image/png")

            # Make the object publicly readable
            blob.make_public()

            public_url = self.get_figure_url(filename)
            logger.info(f"Uploaded: {filename}")
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
            Updated list with firebase_url populated
        """
        if not self.enabled:
            logger.info(
                "Firebase Storage uploader not enabled, using local file paths only"
            )
            return figures

        logger.info(f"Uploading {len(figures)} figures to Firebase Storage")

        for figure in figures:
            try:
                figure_path = Path(figure["local_path"])
                figure_id = figure["figure_id"]

                url = self.upload_figure(figure_path, figure_id)

                figure["firebase_url"] = url

            except Exception as e:
                logger.error(f"Failed to upload figure {figure.get('figure_id')}: {e}")
                figure["firebase_url"] = None
                continue

        return figures


def upload_figure(figure_path: str, figure_id: str) -> Optional[str]:
    """Convenience function to upload a single figure."""
    uploader = FirebaseStorageFigureUploader()
    return uploader.upload_figure(Path(figure_path), figure_id)
