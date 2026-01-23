#!/usr/bin/env python3
"""
CLI script for testing RAG generation.
Tests with sample queries and displays formatted responses.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generation.rag_chain import AskChuckRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# Sample test queries from PRD
SAMPLE_QUERIES = {
    "basic_factual": [
        "What is a Design Factor?",
        "Explain the Abstraction Ladder concept",
        "What is a Speculation in Structured Planning?",
    ],
    "visual": [
        "Show me an example of an Information Structure",
        "What does a Function Structure look like?",
        "Diagram of an Abstraction Ladder",
    ],
    "multi_turn": [
        "What is a Speculation?",
        "How does it relate to Design Factors?",
        "Give me an example from Owen's work",
    ],
    "out_of_scope": [
        "What is Owen's opinion on Agile methodology?",
        "Compare Structured Planning to Design Sprints",
    ],
    "hierarchical": [
        "Explain the relationship between Structured Planning phases",
        "What are the specific steps in Action Analysis?",
    ],
}


def display_response(question: str, result: dict, show_full: bool = False) -> None:
    """Display RAG response in a formatted way."""
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)

    # Answer
    answer = result.get("answer", "")
    print(f"\nANSWER:\n{answer}\n")

    # Sources
    sources = result.get("sources", [])
    if sources:
        print(f"\nSOURCES ({len(sources)}):")
        for i, source in enumerate(sources, 1):
            display = source.get("display", "")
            chunk_id = source.get("chunk_id", "")
            chunk_level = source.get("chunk_level", "")
            print(f"  {i}. {display}")
            if show_full:
                print(f"     Chunk ID: {chunk_id} (Level: {chunk_level})")

    # Chunk IDs
    if show_full:
        chunk_ids = result.get("chunk_ids", [])
        if chunk_ids:
            print(f"\nCHUNK IDS ({len(chunk_ids)}):")
            for cid in chunk_ids:
                print(f"  - {cid}")

    # Figures
    figures = result.get("figures", [])
    if figures:
        print(f"\nFIGURES ({len(figures)}):")
        for i, fig in enumerate(figures, 1):
            caption = fig.get("caption", "")
            url = fig.get("url", "")
            doc = fig.get("document", "")
            fig_num = fig.get("figure_number", "?")
            print(f"  {i}. Figure {fig_num}: {caption}")
            print(f"     Document: {doc}")
            print(f"     URL: {url}")

    # Stats
    chunks_used = result.get("chunks_used", 0)
    print(f"\nSTATS: {chunks_used} chunks used")


def test_single_query(
    query: str,
    stream: bool = False,
    include_figures: bool = True,
    top_k: int = 5,
    show_full: bool = False,
) -> None:
    """Test generation with a single query."""
    rag = AskChuckRAG()

    logger.info(f"\nTesting query (stream={stream}, top_k={top_k})")

    if stream:
        # Stream the response
        print("\n" + "=" * 80)
        print(f"QUESTION: {query}")
        print("=" * 80)
        print("\nANSWER:")

        full_answer = ""
        sources = []
        chunk_ids = []
        figures = []

        for chunk in rag.stream_query(
            query, include_figures=include_figures, top_k=top_k
        ):
            chunk_type = chunk.get("type")

            if chunk_type == "token":
                content = chunk.get("content", "")
                print(content, end="", flush=True)
                full_answer += content

            elif chunk_type == "sources":
                sources = chunk.get("sources", [])

            elif chunk_type == "chunk_ids":
                chunk_ids = chunk.get("chunk_ids", [])

            elif chunk_type == "figures":
                figures = chunk.get("figures", [])

        # Display metadata after streaming
        print("\n")

        if sources:
            print(f"\nSOURCES ({len(sources)}):")
            for i, source in enumerate(sources, 1):
                print(f"  {i}. {source.get('display', '')}")

        if figures:
            print(f"\nFIGURES ({len(figures)}):")
            for i, fig in enumerate(figures, 1):
                print(f"  {i}. {fig.get('caption', '')}")
                print(f"     URL: {fig.get('url', '')}")

        print(f"\nSTATS: {len(chunk_ids)} chunks used")

    else:
        # Non-streaming response
        result = rag.query(query, include_figures=include_figures, top_k=top_k)
        display_response(query, result, show_full)


def test_multi_turn() -> None:
    """Test multi-turn conversation."""
    print("\n" + "#" * 80)
    print("MULTI-TURN CONVERSATION TEST")
    print("#" * 80)

    rag = AskChuckRAG()
    conversation = []

    queries = SAMPLE_QUERIES["multi_turn"]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TURN {i}: {query}")
        print(f"{'=' * 80}")

        result = rag.query(query, conversation_history=conversation)

        # Display answer
        print(f"\nANSWER:\n{result['answer']}\n")

        # Update conversation
        conversation.append({"role": "user", "content": query})
        conversation.append({"role": "assistant", "content": result["answer"]})

        # Show source count
        print(f"Sources: {len(result['sources'])}, Chunks: {result['chunks_used']}")


def test_all_queries() -> None:
    """Test all sample queries."""
    print("\n" + "#" * 80)
    print("TESTING ALL SAMPLE QUERIES")
    print("#" * 80)

    rag = AskChuckRAG()

    for category, queries in SAMPLE_QUERIES.items():
        if category == "multi_turn":
            continue  # Skip multi-turn for batch test

        print(f"\n{'=' * 80}")
        print(f"Category: {category.upper().replace('_', ' ')}")
        print(f"{'=' * 80}")

        for query in queries:
            result = rag.query(query, top_k=3)

            print(f"\nQuery: {query}")
            answer_preview = (
                result["answer"][:150] + "..."
                if len(result["answer"]) > 150
                else result["answer"]
            )
            print(f"Answer: {answer_preview}")
            print(
                f"Sources: {len(result['sources'])}, Figures: {len(result['figures'])}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Test RAG generation with sample queries"
    )

    parser.add_argument("--query", type=str, help="Custom query to test")

    parser.add_argument(
        "--stream", action="store_true", help="Stream the response token by token"
    )

    parser.add_argument(
        "--no-figures", action="store_true", help="Disable figure retrieval"
    )

    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of chunks to retrieve"
    )

    parser.add_argument(
        "--show-full", action="store_true", help="Show full details (chunk IDs, etc.)"
    )

    parser.add_argument(
        "--test-all", action="store_true", help="Test all sample queries"
    )

    parser.add_argument(
        "--test-multi-turn", action="store_true", help="Test multi-turn conversation"
    )

    args = parser.parse_args()

    try:
        if args.test_all:
            # Test all sample queries
            test_all_queries()

        elif args.test_multi_turn:
            # Test multi-turn conversation
            test_multi_turn()

        elif args.query:
            # Test single custom query
            test_single_query(
                args.query,
                stream=args.stream,
                include_figures=not args.no_figures,
                top_k=args.top_k,
                show_full=args.show_full,
            )

        else:
            # Default: test with a sample query
            default_query = "What is a Design Factor?"
            logger.info(f"No query specified, using default: '{default_query}'")
            test_single_query(
                default_query,
                stream=args.stream,
                include_figures=not args.no_figures,
                top_k=args.top_k,
                show_full=args.show_full,
            )

        print("\n✓ Generation testing complete!\n")

    except Exception as e:
        logger.error(f"\n✗ Generation testing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
