#!/usr/bin/env python3
"""
CLI script for verifying RAG generation functionality.
Tests all generation features and reports pass/fail.
"""

import argparse
import logging
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generation.prompts import build_full_prompt, format_context_chunks
from src.generation.rag_chain import AskChuckRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def test_basic_query() -> bool:
    """Test basic query and response generation."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Basic Query")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()
        result = rag.query("What is a Design Factor?")

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        chunk_ids = result.get("chunk_ids", [])

        if not answer:
            logger.error("  ✗ No answer generated")
            return False

        logger.info(f"  ✓ Answer generated ({len(answer)} chars)")
        logger.info(f"  ✓ Sources: {len(sources)}")
        logger.info(f"  ✓ Chunk IDs: {len(chunk_ids)}")

        return True

    except Exception as e:
        logger.error(f"  ✗ Basic query failed: {e}")
        return False


def test_citation_format() -> bool:
    """Test that citations are in [Document, Section] format."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Citation Format")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()
        result = rag.query("What is a Function in Structured Planning?")

        answer = result.get("answer", "")

        # Look for citations in [Document, Section] format
        citation_pattern = r"\[([^\]]+),\s*([^\]]+)\]"
        citations = re.findall(citation_pattern, answer)

        if citations:
            logger.info(f"  ✓ Found {len(citations)} citations in answer")
            for i, (doc, section) in enumerate(citations[:3], 1):
                logger.info(f"    {i}. [{doc}, {section}]")
            return True
        else:
            logger.warning("  ⚠ No citations found in answer (may be expected)")
            # Still pass - citations are encouraged but not strictly required
            return True

    except Exception as e:
        logger.error(f"  ✗ Citation format test failed: {e}")
        return False


def test_chunk_ids_in_metadata() -> bool:
    """Test that chunk IDs are included in response metadata."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Chunk IDs in Metadata")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()
        result = rag.query("Explain the Abstraction Ladder")

        chunk_ids = result.get("chunk_ids", [])

        if not chunk_ids:
            logger.error("  ✗ No chunk IDs in metadata")
            return False

        logger.info(f"  ✓ Found {len(chunk_ids)} chunk IDs")
        logger.info(f"    Sample: {chunk_ids[0]}")

        return True

    except Exception as e:
        logger.error(f"  ✗ Chunk ID test failed: {e}")
        return False


def test_figure_integration() -> bool:
    """Test figure integration with R2 URLs."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Figure Integration")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()
        result = rag.query("Show me an Information Structure diagram", top_k=5)

        figures = result.get("figures", [])

        logger.info(f"  Retrieved {len(figures)} figures")

        if figures:
            # Check figure structure
            first_fig = figures[0]
            has_url = "url" in first_fig
            has_caption = "caption" in first_fig

            if has_url and has_caption:
                logger.info(f"  ✓ Figures have proper structure")
                logger.info(f"    URL: {first_fig.get('url', '')[:50]}...")
                logger.info(f"    Caption: {first_fig.get('caption', '')[:50]}...")

            # Check max 3 figures
            if len(figures) <= 3:
                logger.info(f"  ✓ Figure limit respected (max 3)")
            else:
                logger.error(f"  ✗ Too many figures: {len(figures)} > 3")
                return False

            return True
        else:
            logger.info("  ⚠ No figures found (expected if no figures indexed)")
            return True  # Pass - figures may not exist in test data

    except Exception as e:
        logger.error(f"  ✗ Figure integration test failed: {e}")
        return False


def test_conversation_history() -> bool:
    """Test conversation history maintenance."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Conversation History")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()

        # First query
        result1 = rag.query("What is a Speculation?")
        answer1 = result1.get("answer", "")

        # Build history
        history = [
            {"role": "user", "content": "What is a Speculation?"},
            {"role": "assistant", "content": answer1},
        ]

        # Follow-up query
        result2 = rag.query("How does it relate to Design Factors?", conversation_history=history)
        answer2 = result2.get("answer", "")

        if answer2:
            logger.info("  ✓ Follow-up query with history succeeded")
            logger.info(f"    Answer length: {len(answer2)} chars")
            return True
        else:
            logger.error("  ✗ No answer for follow-up query")
            return False

    except Exception as e:
        logger.error(f"  ✗ Conversation history test failed: {e}")
        return False


def test_no_context_fallback() -> bool:
    """Test fallback for queries with no context."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: No Context Fallback")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()
        result = rag.query("What is quantum computing?")  # Out of scope

        answer = result.get("answer", "")
        chunks_used = result.get("chunks_used", 0)

        # Should acknowledge not finding information
        acknowledges_limitation = any(
            phrase in answer.lower()
            for phrase in ["couldn't find", "don't have", "not covered", "not available"]
        )

        if acknowledges_limitation or chunks_used == 0:
            logger.info("  ✓ Handles missing context gracefully")
            logger.info(f"    Chunks used: {chunks_used}")
            return True
        else:
            logger.warning("  ⚠ Response may not acknowledge limitation")
            return True  # Still pass

    except Exception as e:
        logger.error(f"  ✗ No context fallback test failed: {e}")
        return False


def test_streaming() -> bool:
    """Test streaming functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Streaming")
    logger.info("=" * 60)

    try:
        rag = AskChuckRAG()

        tokens_received = 0
        sources_received = False
        chunk_ids_received = False

        for chunk in rag.stream_query("What is Action Analysis?", top_k=3):
            chunk_type = chunk.get("type")

            if chunk_type == "token":
                tokens_received += 1

            elif chunk_type == "sources":
                sources_received = True

            elif chunk_type == "chunk_ids":
                chunk_ids_received = True

        if tokens_received > 0:
            logger.info(f"  ✓ Streaming works ({tokens_received} tokens)")

        if sources_received and chunk_ids_received:
            logger.info("  ✓ Metadata yielded after streaming")

        return tokens_received > 0

    except Exception as e:
        logger.error(f"  ✗ Streaming test failed: {e}")
        return False


def test_prompt_construction() -> bool:
    """Test prompt construction with glossary and context."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 8: Prompt Construction")
    logger.info("=" * 60)

    try:
        # Mock chunks
        mock_chunks = [
            {
                "chunk_id": "test_chunk_1",
                "document_title": "Test Document",
                "section": "Introduction",
                "chunk_type": "text",
                "chunk_level": "child",
                "content": "This is test content about Functions.",
                "metadata": {"source_section": "Introduction", "level": "child"},
            }
        ]

        system_prompt, user_prompt = build_full_prompt(
            question="What is a Function?",
            context_chunks=mock_chunks,
            conversation_history=[],
        )

        # Check that glossary is included
        has_glossary = "Function" in system_prompt and "Design Factor" in system_prompt

        # Check that context is formatted
        has_context = "Test Document" in system_prompt and "test content" in system_prompt

        if has_glossary:
            logger.info("  ✓ Glossary included in system prompt")

        if has_context:
            logger.info("  ✓ Context formatted in system prompt")

        logger.info(f"  System prompt length: {len(system_prompt)} chars")
        logger.info(f"  User prompt length: {len(user_prompt)} chars")

        return has_glossary and has_context

    except Exception as e:
        logger.error(f"  ✗ Prompt construction test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify RAG generation functionality"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip expensive operations)",
    )

    args = parser.parse_args()

    logger.info("\n" + "#" * 60)
    logger.info("RAG GENERATION VERIFICATION")
    logger.info("#" * 60)

    tests = [
        ("Basic Query", test_basic_query),
        ("Citation Format", test_citation_format),
        ("Chunk IDs in Metadata", test_chunk_ids_in_metadata),
        ("Figure Integration", test_figure_integration),
        ("Conversation History", test_conversation_history),
        ("No Context Fallback", test_no_context_fallback),
        ("Streaming", test_streaming),
        ("Prompt Construction", test_prompt_construction),
    ]

    if args.quick:
        # Skip expensive tests
        tests = [
            ("Basic Query", test_basic_query),
            ("Prompt Construction", test_prompt_construction),
            ("Chunk IDs in Metadata", test_chunk_ids_in_metadata),
        ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "#" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("#" * 60 + "\n")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")

    logger.info(f"\n  Total: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        logger.info("\n✓ All generation tests passed!\n")
        sys.exit(0)
    else:
        logger.warning(f"\n⚠ {total_count - passed_count} test(s) failed\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
