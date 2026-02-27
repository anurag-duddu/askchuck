"""Firebase Admin SDK initialization using Application Default Credentials."""

import logging
import threading
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)
_init_lock = threading.Lock()


def get_firebase_app() -> Optional[firebase_admin.App]:
    """Get or initialize Firebase Admin app (thread-safe singleton)."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        with _init_lock:
            try:
                return firebase_admin.get_app()
            except ValueError:
                try:
                    # ADC works automatically on Cloud Run
                    cred = credentials.ApplicationDefault()
                    app = firebase_admin.initialize_app(
                        cred,
                        {"projectId": "askchuck"},
                    )
                    logger.info("Firebase Admin SDK initialized via ADC")
                    return app
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase Admin: {e}")
                    return None


def verify_id_token(token: str) -> Optional[dict]:
    """Verify a Firebase ID token. Returns decoded claims or None."""
    app = get_firebase_app()
    if not app:
        return None
    try:
        decoded = auth.verify_id_token(token, app=app)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def get_firestore_client():
    """Get Firestore client using ADC."""
    from google.cloud import firestore

    return firestore.Client(project="askchuck")
