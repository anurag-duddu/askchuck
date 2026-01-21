#!/usr/bin/env python3
"""
CLI script for testing retrieval pipeline.
Tests with sample queries and displays results.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.retrieval_pipeline import RetrievalPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# Sample test queries from PRD
SAMPLE_QUERIES = {
    "exact_terminology": [
        "What is VTCON?",
        "Design Factor Observation Extension",
        "Means/Ends Analysis",
    ],
    "semantic_paraphrasing": [
        "How to categorize things from specific to general",
        "Documenting insights about problems",
        "Organizing functions by shared solutions",
    ],
    "mixed": [
        "What is the Abstraction Ladder and how does it work?",
        "Examples of Design Factors in housing projects",
    ],
    "figures": [
        "Show me a diagram of an Information Structure",
        "Housing system Abstraction Structure figure",
    ],
    "broad_conceptual": [
        "Explain Structured Planning methodology",
        "What are Owen's core principles for design research",
    ],
}


def display_results(query: str, results: list, show_content: bool = False) -> None:
    """Display retrieval results in a formatted way."""
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    if not results:
        print("  No results found.")
        return

    print(f"\nFound {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        chunk_id = result.get("chunk_id", "unknown")
        doc_title = result.get("document_title", "Unknown")
        section = result.get("section", "")
        chunk_type = result.get("chunk_type", "text")
        chunk_level = result.get("chunk_level", "child")

        # Get score (rerank score if available, otherwise retrieval score)
        score = result.get("rerank_score", result.get("score", 0.0))
        score_type = "rerank" if "rerank_score" in result else "retrieval"

        print(f"{i}. {doc_title}")
        print(f"   Chunk ID: {chunk_id}")
        print(f"   Section: {section}" if section else "")
        print(f"   Type: {chunk_type} | Level: {chunk_level}")
        print(f"   Score ({score_type}): {score:.4f}")

        # Show Owen terms if available
        owen_terms = result.get("owen_terms", [])
        if owen_terms:
            print(f"   Owen Terms: {', '.join(owen_terms[:5])}")

        # Show content preview if requested
        if show_content:
            content = result.get("content", "")
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   Content: {preview}")

        print()


def test_single_query(
    query: str,
    alpha: float = 0.5,
    top_k: int = 5,
    expand_query: bool = False,
    expand_parents: bool = True,
    show_content: bool = False,
) -> None:
    """Test retrieval with a single query."""
    # Initialize pipeline with custom alpha
    from src.retrieval.pinecone_retriever import PineconeHybridRetriever

    retriever = PineconeHybridRetriever(
        alpha=alpha, expand_to_parents=expand_parents
    )
    pipeline = RetrievalPipeline(retriever=retriever)

    logger.info(f"\nTesting query with alpha={alpha}, top_k={top_k}")

    # Run retrieval
    results = pipeline.retrieve(
        query, top_k=top_k, expand_query=expand_query, expand_parents=expand_parents
    )

    # Display results
    display_results(query, results, show_content)


def test_all_queries(alpha: float = 0.5, top_k: int = 3) -> None:
    """Test all sample queries from the PRD."""
    print("\n" + "#" * 80)
    print("TESTING ALL SAMPLE QUERIES")
    print("#" * 80)

    # Initialize pipeline
    from src.retrieval.pinecone_retriever import PineconeHybridRetriever

    retriever = PineconeHybridRetriever(alpha=alpha)
    pipeline = RetrievalPipeline(retriever=retriever)

    for category, queries in SAMPLE_QUERIES.items():
        print(f"\n{'=' * 80}")
        print(f"Category: {category.upper().replace('_', ' ')}")
        print(f"{'=' * 80}")

        for query in queries:
            results = pipeline.retrieve(query, top_k=top_k)
            print(f"\nQuery: {query}")
            print(f"Results: {len(results)}")

            if results:
                top_result = results[0]
                score = top_result.get("rerank_score", top_result.get("score", 0.0))
                print(f"  Top: {top_result.get('document_title')} (score={score:.4f})")


def test_alpha_comparison(query: str, top_k: int = 5) -> None:
    """Compare retrieval at different alpha values."""
    print("\n" + "#" * 80)
    print("ALPHA PARAMETER COMPARISON")
    print("#" * 80)

    alphas = [0.0, 0.5, 1.0]

    for alpha in alphas:
        print(f"\n{'=' * 80}")
        print(f"Alpha = {alpha} ({'pure BM25' if alpha == 0.0 else 'pure semantic' if alpha == 1.0 else 'balanced hybrid'})")
        print(f"{'=' * 80}")

        from src.retrieval.pinecone_retriever import PineconeHybridRetriever

        retriever = PineconeHybridRetriever(alpha=alpha)
        pipeline = RetrievalPipeline(retriever=retriever)

        results = pipeline.retrieve(query, top_k=top_k)

        if results:
            print(f"\nTop {min(3, len(results))} results:")
            for i, r in enumerate(results[:3], 1):
                score = r.get("rerank_score", r.get("score", 0.0))
                print(f"  {i}. {r.get('chunk_id')} (score={score:.4f})")


def main():
    parser = argparse.ArgumentParser(
        description="Test retrieval pipeline with sample queries"
    )

    parser.add_argument("--query", type=str, help="Custom query to test")

    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Dense/sparse weighting (0.0=pure BM25, 1.0=pure semantic)",
    )

    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results to return"
    )

    parser.add_argument(
        "--expand-query",
        action="store_true",
        help="Expand query with Owen terminology",
    )

    parser.add_argument(
        "--no-expand-parents",
        action="store_true",
        help="Disable parent-child expansion",
    )

    parser.add_argument(
        "--show-content",
        action="store_true",
        help="Show content preview in results",
    )

    parser.add_argument(
        "--test-all", action="store_true", help="Test all sample queries"
    )

    parser.add_argument(
        "--compare-alpha",
        action="store_true",
        help="Compare results at different alpha values",
    )

    args = parser.parse_args()

    try:
        if args.test_all:
            # Test all sample queries
            test_all_queries(alpha=args.alpha, top_k=args.top_k)

        elif args.compare_alpha:
            # Compare alpha values
            query = args.query or "What is structured planning?"
            test_alpha_comparison(query, top_k=args.top_k)

        elif args.query:
            # Test single custom query
            test_single_query(
                args.query,
                alpha=args.alpha,
                top_k=args.top_k,
                expand_query=args.expand_query,
                expand_parents=not args.no_expand_parents,
                show_content=args.show_content,
            )

        else:
            # Default: test with a sample query
            default_query = "What is the Abstraction Ladder?"
            logger.info(f"No query specified, using default: '{default_query}'")
            test_single_query(
                default_query,
                alpha=args.alpha,
                top_k=args.top_k,
                show_content=args.show_content,
            )

        print("\n✓ Retrieval testing complete!\n")

    except Exception as e:
        logger.error(f"\n✗ Retrieval testing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
