"""
PDF upload to Firebase Storage.
Provides public URLs for source PDFs to enable citation navigation.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote

from google.cloud import storage as gcs

from src.utils.config import RAW_DIR, settings

logger = logging.getLogger(__name__)

# Thread-safe singleton lock
_pdf_uploader_lock = threading.Lock()
_pdf_uploader: Optional["FirebaseStoragePDFUploader"] = None

# Maximum file size for upload (100MB)
MAX_PDF_SIZE_MB = 100


class FirebaseStoragePDFUploader:
    """
    Uploads PDF documents to Firebase Storage for web access.
    Uses Application Default Credentials (ADC) — works automatically on Cloud Run.
    Thread-safe singleton with retry logic and proper error handling.
    """

    def __init__(self):
        """Initialize Firebase Storage client for PDFs."""
        if not settings.firebase_storage_bucket:
            logger.warning(
                "FIREBASE_STORAGE_BUCKET not configured - PDF uploader disabled"
            )
            self.gcs_client = None
            self.bucket = None
            self.enabled = False
            self.bucket_name = ""
            return

        try:
            # Uses Application Default Credentials automatically
            self.gcs_client = gcs.Client()
            self.bucket_name = settings.firebase_storage_bucket
            self.bucket = self.gcs_client.bucket(self.bucket_name)
            self.enabled = True
            logger.info(
                f"Firebase Storage PDF uploader initialized for bucket: {self.bucket_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Firebase Storage client: {type(e).__name__}: {e}",
                exc_info=True,
            )
            self.gcs_client = None
            self.bucket = None
            self.enabled = False
            self.bucket_name = ""

    def _build_public_url(self, object_path: str) -> str:
        """Build a properly encoded public URL for an object in Firebase Storage."""
        return f"https://storage.googleapis.com/{self.bucket_name}/{object_path}"

    def get_pdf_url(self, filename: str) -> Optional[str]:
        """
        Get the public URL for a PDF by filename.

        Args:
            filename: PDF filename (e.g., "document.pdf")

        Returns:
            Public URL for the PDF, or None if uploader is not properly configured
        """
        if not self.enabled:
            logger.debug(
                f"PDF uploader not enabled, cannot generate URL for {filename}"
            )
            return None

        if not self.bucket_name:
            logger.error(
                f"Missing Firebase Storage configuration: bucket={self.bucket_name}"
            )
            return None

        if not filename or not filename.strip():
            logger.warning("Empty filename provided to get_pdf_url")
            return None

        # URL-encode the filename for safe path construction
        encoded_filename = quote(filename.strip(), safe="")
        object_path = f"pdfs/{encoded_filename}"
        return self._build_public_url(object_path)

    def upload_pdf(self, pdf_path: Path, max_retries: int = 3) -> Optional[str]:
        """
        Upload a PDF to Firebase Storage and return its public URL.

        Args:
            pdf_path: Path to the PDF file
            max_retries: Number of retry attempts for transient failures

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug(
                f"Firebase Storage PDF uploader not enabled, skipping {pdf_path.name}"
            )
            return None

        # Validate file exists
        if not pdf_path.exists():
            logger.error(f"PDF file does not exist: {pdf_path}")
            return None

        # Validate file extension
        if pdf_path.suffix.lower() != ".pdf":
            logger.error(f"File is not a PDF: {pdf_path}")
            return None

        # Validate file size
        try:
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_PDF_SIZE_MB:
                logger.error(
                    f"PDF {pdf_path.name} exceeds size limit: {file_size_mb:.2f}MB > {MAX_PDF_SIZE_MB}MB"
                )
                return None
        except OSError as e:
            logger.error(f"Failed to get file size for {pdf_path}: {e}")
            return None

        # URL-encode the filename for safe path construction
        encoded_filename = quote(pdf_path.name, safe="")
        object_path = f"pdfs/{encoded_filename}"

        logger.debug(f"Starting upload of {pdf_path.name} ({file_size_mb:.2f}MB)")
        start_time = time.time()

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                blob = self.bucket.blob(object_path)
                blob.upload_from_filename(str(pdf_path), content_type="application/pdf")
                # Make the object publicly readable
                blob.make_public()

                elapsed = time.time() - start_time
                public_url = self._build_public_url(object_path)
                logger.info(
                    f"Uploaded PDF: {pdf_path.name} ({file_size_mb:.2f}MB) in {elapsed:.2f}s"
                )
                return public_url

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    backoff = 2**attempt  # exponential: 1s, 2s, 4s
                    logger.warning(
                        f"Upload attempt {attempt + 1}/{max_retries} failed for {pdf_path.name}: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)

        elapsed = time.time() - start_time
        logger.error(
            f"Failed to upload {pdf_path.name} after {max_retries} retries ({elapsed:.2f}s): {last_error}",
            exc_info=True,
        )
        return None

    def upload_all_pdfs(self) -> Dict[str, str]:
        """
        Upload all PDFs from RAW_DIR and return mapping of filename to URL.

        Returns:
            Dict mapping PDF filename to public URL
        """
        if not self.enabled:
            logger.warning("PDF uploader not enabled")
            return {}

        try:
            pdf_files = list(RAW_DIR.glob("*.pdf"))
        except OSError as e:
            logger.error(f"Failed to list PDFs in {RAW_DIR}: {e}")
            return {}

        logger.info(f"Starting batch upload of {len(pdf_files)} PDFs from {RAW_DIR}")

        url_mapping = {}
        failed_files = []

        for idx, pdf_path in enumerate(pdf_files, 1):
            logger.debug(f"Uploading PDF {idx}/{len(pdf_files)}: {pdf_path.name}")
            url = self.upload_pdf(pdf_path)
            if url:
                # Use original filename as key for lookup consistency
                url_mapping[pdf_path.name] = url
            else:
                failed_files.append(pdf_path.name)

        logger.info(
            f"Batch upload complete: {len(url_mapping)}/{len(pdf_files)} successful. "
            f"Failed: {failed_files if failed_files else 'none'}"
        )
        return url_mapping


def get_pdf_uploader() -> FirebaseStoragePDFUploader:
    """
    Get or create the global PDF uploader instance (thread-safe).

    Uses double-checked locking pattern for thread safety.
    """
    global _pdf_uploader
    if _pdf_uploader is None:
        with _pdf_uploader_lock:
            if _pdf_uploader is None:
                _pdf_uploader = FirebaseStoragePDFUploader()
    return _pdf_uploader


def upload_all_pdfs() -> Dict[str, str]:
    """Convenience function to upload all PDFs."""
    return get_pdf_uploader().upload_all_pdfs()
