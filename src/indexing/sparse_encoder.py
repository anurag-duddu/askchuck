"""
Sparse vector generation for BM25-style lexical matching.
Uses Pinecone's sparse encoding for hybrid search.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List

from src.utils.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Try to import pinecone-text for BM25 encoding
try:
    from pinecone_text.sparse import BM25Encoder as PineconeBM25

    PINECONE_TEXT_AVAILABLE = True
except ImportError:
    logger.warning("pinecone-text not available, using simple sparse encoding fallback")
    PINECONE_TEXT_AVAILABLE = False


class SparseEncoder:
    """
    Generates BM25-style sparse vectors for hybrid search.
    Uses pinecone-text if available, otherwise simple tokenization.
    """

    def __init__(self):
        """Initialize sparse encoder."""
        self.encoder = None
        self.fitted = False
        self.encoder_path = PROJECT_ROOT / "data" / "sparse_encoder.pkl"

    def fit(self, texts: List[str]) -> None:
        """
        Fit the sparse encoder on a corpus.

        Args:
            texts: List of text strings to fit on
        """
        logger.info(f"Fitting sparse encoder on {len(texts)} texts...")

        if PINECONE_TEXT_AVAILABLE:
            # Use Pinecone's BM25 encoder
            self.encoder = PineconeBM25()
            self.encoder.fit(texts)
        else:
            # Fallback: Simple token frequency encoder
            from collections import Counter

            # Build vocabulary
            all_tokens = []
            for text in texts:
                tokens = self._simple_tokenize(text)
                all_tokens.extend(tokens)

            # Create token to ID mapping
            token_counts = Counter(all_tokens)
            vocab = {
                token: idx
                for idx, (token, _) in enumerate(token_counts.most_common(10000))
            }

            self.encoder = {"vocab": vocab, "type": "simple"}

        self.fitted = True
        logger.info("✓ Sparse encoder fitted")

    def encode(self, text: str) -> Dict[str, List]:
        """
        Encode text into sparse vector format.

        Args:
            text: Text to encode

        Returns:
            Dict with 'indices' and 'values' lists
        """
        if not self.fitted:
            raise ValueError("Encoder not fitted. Call fit() first.")

        if PINECONE_TEXT_AVAILABLE and hasattr(self.encoder, "encode_documents"):
            # Pinecone encoder
            result = self.encoder.encode_documents([text])[0]
            return {"indices": result["indices"], "values": result["values"]}
        else:
            # Simple fallback
            return self._simple_encode(text)

    def encode_batch(self, texts: List[str]) -> List[Dict[str, List]]:
        """
        Encode multiple texts into sparse vectors.

        Args:
            texts: List of texts to encode

        Returns:
            List of sparse vector dicts
        """
        if not self.fitted:
            raise ValueError("Encoder not fitted. Call fit() first.")

        logger.info(f"Encoding {len(texts)} texts to sparse vectors...")

        if PINECONE_TEXT_AVAILABLE and hasattr(self.encoder, "encode_documents"):
            # Batch encode with Pinecone
            results = self.encoder.encode_documents(texts)
            sparse_vectors = [
                {"indices": r["indices"], "values": r["values"]} for r in results
            ]
        else:
            # Encode individually with fallback
            sparse_vectors = [self._simple_encode(text) for text in texts]

        logger.info(f"✓ Generated {len(sparse_vectors)} sparse vectors")
        return sparse_vectors

    def save(self) -> None:
        """Save fitted encoder to disk."""
        if not self.fitted:
            logger.warning("Encoder not fitted, nothing to save")
            return

        self.encoder_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.encoder_path, "wb") as f:
            pickle.dump(self.encoder, f)

        logger.info(f"Saved sparse encoder to {self.encoder_path}")

    def load(self) -> None:
        """Load fitted encoder from disk."""
        if not self.encoder_path.exists():
            raise FileNotFoundError(f"Encoder not found at {self.encoder_path}")

        with open(self.encoder_path, "rb") as f:
            self.encoder = pickle.load(f)

        self.fitted = True
        logger.info(f"Loaded sparse encoder from {self.encoder_path}")

    def _simple_tokenize(self, text: str) -> List[str]:
        """Simple tokenization for fallback."""
        # Lowercase and split on whitespace/punctuation
        import re

        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        return tokens

    def _simple_encode(self, text: str) -> Dict[str, List]:
        """Simple sparse encoding fallback."""
        tokens = self._simple_tokenize(text)
        vocab = self.encoder["vocab"]

        # Count token frequencies
        from collections import Counter

        token_counts = Counter(tokens)

        # Build sparse vector
        indices = []
        values = []

        for token, count in token_counts.items():
            if token in vocab:
                indices.append(vocab[token])
                values.append(float(count))

        # Sort by index
        if indices:
            sorted_pairs = sorted(zip(indices, values))
            indices, values = zip(*sorted_pairs)
            indices = list(indices)
            values = list(values)

        return {"indices": indices, "values": values}


def fit_and_save_encoder(texts: List[str]) -> SparseEncoder:
    """Convenience function to fit and save encoder."""
    encoder = SparseEncoder()
    encoder.fit(texts)
    encoder.save()
    return encoder


def load_encoder() -> SparseEncoder:
    """Convenience function to load saved encoder."""
    encoder = SparseEncoder()
    encoder.load()
    return encoder
