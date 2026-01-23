"""
Evaluation script for AskChuck RAG system.

Runs RAGAS metrics, retrieval evaluation, and Owen-specific quality checks
against the golden dataset.

Usage:
    python scripts/run_evaluation.py              # Full evaluation
    python scripts/run_evaluation.py --sample 10  # Sample evaluation
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (AnswerRelevancy, ContextPrecision, ContextRecall,
                           Faithfulness)
from tqdm import tqdm

# Create metric instances
faithfulness = Faithfulness()
answer_relevancy = AnswerRelevancy()
context_precision = ContextPrecision()
context_recall = ContextRecall()

from src.generation.rag_chain import AskChuckRAG
from src.retrieval.retrieval_pipeline import RetrievalPipeline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "tests" / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent.parent / "tests" / "evaluation_results.json"


def load_golden_dataset() -> Dict:
    """Load the golden dataset from JSON."""
    logger.info(f"Loading golden dataset from {GOLDEN_DATASET_PATH}")
    with open(GOLDEN_DATASET_PATH, "r") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data['questions'])} questions")
    return data


def run_rag_evaluation(
    questions: List[Dict], rag_chain: AskChuckRAG, sample_size: Optional[int] = None
) -> Dict:
    """
    Run full RAG evaluation using RAGAS metrics.

    Args:
        questions: List of question dictionaries from golden dataset
        rag_chain: Initialized RAG chain
        sample_size: Optional limit on number of questions to evaluate

    Returns:
        Dictionary with evaluation results
    """
    logger.info("=" * 60)
    logger.info("Running RAGAS Evaluation")
    logger.info("=" * 60)

    # Prepare data for RAGAS
    eval_data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}

    # Select questions (optionally sample)
    eval_questions = questions[:sample_size] if sample_size else questions

    # Filter out out-of-scope questions for RAGAS
    eval_questions = [q for q in eval_questions if q.get("category") != "out_of_scope"]

    logger.info(f"Evaluating {len(eval_questions)} questions with RAGAS...")

    # Get retrieval pipeline for raw chunk content
    from src.retrieval.retrieval_pipeline import get_retrieval_pipeline

    retrieval = get_retrieval_pipeline()

    for q in tqdm(eval_questions, desc="Querying RAG system"):
        try:
            # Get RAG response
            response = rag_chain.query(
                question=q["question"],
                conversation_history=[],
                include_figures=True,
                top_k=5,
            )

            # Get raw chunks with full content for RAGAS
            # The RAG response sources are display-formatted without full content
            raw_chunks = retrieval.retrieve(
                query=q["question"], top_k=5, include_figures=False
            )

            # Extract full contexts from raw chunks
            contexts = [
                chunk.get("content", "") for chunk in raw_chunks if chunk.get("content")
            ]

            if not contexts:
                logger.warning(f"No contexts retrieved for: {q['question'][:50]}...")
                contexts = ["No context retrieved"]

            eval_data["question"].append(q["question"])
            eval_data["answer"].append(response["answer"])
            eval_data["contexts"].append(contexts)
            eval_data["ground_truth"].append(q["expected_answer"])

        except Exception as e:
            logger.error(f"Error querying '{q['question'][:50]}...': {e}")
            continue

    if not eval_data["question"]:
        logger.error("No questions successfully evaluated!")
        return {"error": "No questions evaluated", "ragas_scores": {}}

    # Create dataset
    logger.info("Creating RAGAS dataset...")
    dataset = Dataset.from_dict(eval_data)

    # Run RAGAS evaluation
    logger.info("Running RAGAS metrics (this may take a few minutes)...")
    try:
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        logger.info("RAGAS evaluation complete!")

        # Access scores via to_pandas() and compute mean
        df = result.to_pandas()
        numeric_cols = df.select_dtypes(include=["float64", "float32", "int64"]).columns
        mean_scores = df[numeric_cols].mean()

        ragas_scores = {}
        for metric_name in [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]:
            if metric_name in mean_scores:
                ragas_scores[metric_name] = float(mean_scores[metric_name])
            else:
                ragas_scores[metric_name] = 0.0

        return {
            "ragas_scores": ragas_scores,
            "num_questions": len(eval_data["question"]),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        return {
            "error": str(e),
            "ragas_scores": {},
            "num_questions": len(eval_data["question"]),
        }


def run_retrieval_evaluation(
    questions: List[Dict], pipeline: RetrievalPipeline
) -> Dict:
    """
    Evaluate retrieval quality independently.

    Computes Hit Rate@1, Hit Rate@5, MRR, and figure retrieval accuracy.
    """
    logger.info("=" * 60)
    logger.info("Running Retrieval Evaluation")
    logger.info("=" * 60)

    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    figure_hits = 0
    figure_expected = 0
    total_evaluated = 0

    for q in tqdm(questions, desc="Evaluating retrieval"):
        if q.get("category") == "out_of_scope":
            continue

        expected_sources = q.get("expected_sources", [])
        if not expected_sources:
            continue

        total_evaluated += 1

        try:
            # Retrieve without reranking for pure retrieval eval
            results = pipeline.retrieve(q["question"], top_k=10)

            # Check for hits
            retrieved_docs = [r.get("document_title", "").lower() for r in results]

            expected_doc_names = [
                s.lower() if isinstance(s, str) else s.get("document", "").lower()
                for s in expected_sources
            ]

            # Find first hit
            first_hit_rank = None
            for rank, doc in enumerate(retrieved_docs, 1):
                if any(exp in doc or doc in exp for exp in expected_doc_names):
                    first_hit_rank = rank
                    break

            if first_hit_rank:
                if first_hit_rank == 1:
                    hits_at_1 += 1
                if first_hit_rank <= 5:
                    hits_at_5 += 1
                reciprocal_ranks.append(1.0 / first_hit_rank)
            else:
                reciprocal_ranks.append(0.0)

            # Check figure retrieval
            if q.get("requires_figure"):
                figure_expected += 1
                figure_chunks = [r for r in results if r.get("chunk_type") == "figure"]
                if figure_chunks:
                    figure_hits += 1

        except Exception as e:
            logger.error(
                f"Error evaluating retrieval for '{q['question'][:50]}...': {e}"
            )
            reciprocal_ranks.append(0.0)
            continue

    results = {
        "hit_rate_at_1": hits_at_1 / total_evaluated if total_evaluated > 0 else 0,
        "hit_rate_at_5": hits_at_5 / total_evaluated if total_evaluated > 0 else 0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0,
        "figure_retrieval_rate": (
            figure_hits / figure_expected if figure_expected > 0 else 0
        ),
        "total_questions": total_evaluated,
        "figure_questions": figure_expected,
    }

    logger.info(f"Hit Rate@1: {results['hit_rate_at_1']:.2%}")
    logger.info(f"Hit Rate@5: {results['hit_rate_at_5']:.2%}")
    logger.info(f"MRR: {results['mrr']:.3f}")
    logger.info(
        f"Figure Retrieval: {results['figure_retrieval_rate']:.2%} ({figure_hits}/{figure_expected})"
    )

    return results


def run_terminology_check(questions: List[Dict], rag_chain: AskChuckRAG) -> Dict:
    """
    Check if responses use Owen's terminology correctly.
    """
    logger.info("=" * 60)
    logger.info("Running Owen Terminology Check")
    logger.info("=" * 60)

    correct_term_usage = 0
    total_term_checks = 0
    questions_with_terms = 0

    for q in tqdm(questions, desc="Checking terminology"):
        expected_terms = q.get("expected_terms", [])
        if not expected_terms:
            continue

        questions_with_terms += 1

        try:
            response = rag_chain.query(
                question=q["question"],
                conversation_history=[],
                include_figures=False,
                top_k=5,
            )
            answer = response["answer"].lower()

            # Check if expected terms appear in response
            terms_found = sum(1 for term in expected_terms if term.lower() in answer)

            total_term_checks += len(expected_terms)
            correct_term_usage += terms_found

        except Exception as e:
            logger.error(
                f"Error checking terminology for '{q['question'][:50]}...': {e}"
            )
            continue

    results = {
        "terminology_accuracy": (
            correct_term_usage / total_term_checks if total_term_checks > 0 else 0
        ),
        "terms_found": correct_term_usage,
        "terms_checked": total_term_checks,
        "questions_evaluated": questions_with_terms,
    }

    logger.info(
        f"Terminology Accuracy: {results['terminology_accuracy']:.2%} ({correct_term_usage}/{total_term_checks})"
    )

    return results


def run_citation_check(questions: List[Dict], rag_chain: AskChuckRAG) -> Dict:
    """
    Check if responses include proper source citations.
    """
    logger.info("=" * 60)
    logger.info("Running Citation Check")
    logger.info("=" * 60)

    questions_with_citations = 0
    total_questions = 0

    for q in tqdm(questions, desc="Checking citations"):
        if q.get("category") == "out_of_scope":
            continue

        total_questions += 1

        try:
            response = rag_chain.query(
                question=q["question"],
                conversation_history=[],
                include_figures=False,
                top_k=5,
            )

            sources = response.get("sources", [])
            if sources:
                questions_with_citations += 1

        except Exception as e:
            logger.error(f"Error checking citations for '{q['question'][:50]}...': {e}")
            continue

    results = {
        "citation_rate": (
            questions_with_citations / total_questions if total_questions > 0 else 0
        ),
        "questions_with_citations": questions_with_citations,
        "total_questions": total_questions,
    }

    logger.info(
        f"Citation Rate: {results['citation_rate']:.2%} ({questions_with_citations}/{total_questions})"
    )

    return results


def main():
    """Run complete evaluation suite."""
    parser = argparse.ArgumentParser(description="Run AskChuck evaluation")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Sample size for RAGAS evaluation (default: all questions)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("AskChuck Evaluation Suite")
    logger.info("=" * 60)

    # Load dataset
    dataset = load_golden_dataset()
    questions = dataset["questions"]

    # Initialize systems
    logger.info("Initializing RAG chain and retrieval pipeline...")
    rag_chain = AskChuckRAG()
    pipeline = RetrievalPipeline()

    # Run evaluations
    results = {
        "dataset_version": dataset.get("version", "1.0"),
        "total_questions": len(questions),
        "category_distribution": dataset.get("category_distribution", {}),
        "timestamp": datetime.now().isoformat(),
    }

    # Retrieval evaluation
    logger.info("\n")
    results["retrieval"] = run_retrieval_evaluation(questions, pipeline)

    # Terminology check
    logger.info("\n")
    results["terminology"] = run_terminology_check(questions, rag_chain)

    # Citation check
    logger.info("\n")
    results["citation"] = run_citation_check(questions, rag_chain)

    # RAGAS evaluation
    logger.info("\n")
    sample_size = args.sample
    if sample_size:
        logger.info(f"Running RAGAS on sample of {sample_size} questions")
    else:
        logger.info("Running RAGAS on full dataset (this may take 10-15 minutes)")

    results["ragas"] = run_rag_evaluation(questions, rag_chain, sample_size)

    # Save results
    logger.info(f"\nSaving results to {RESULTS_PATH}...")
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Evaluation Complete!")
    logger.info("=" * 60)

    logger.info("\nRetrieval Metrics:")
    logger.info(f"  Hit Rate@1:        {results['retrieval']['hit_rate_at_1']:.2%}")
    logger.info(f"  Hit Rate@5:        {results['retrieval']['hit_rate_at_5']:.2%}")
    logger.info(f"  MRR:               {results['retrieval']['mrr']:.3f}")
    logger.info(
        f"  Figure Retrieval:  {results['retrieval']['figure_retrieval_rate']:.2%}"
    )

    logger.info("\nOwen-Specific Checks:")
    logger.info(
        f"  Terminology:       {results['terminology']['terminology_accuracy']:.2%}"
    )
    logger.info(f"  Citation Rate:     {results['citation']['citation_rate']:.2%}")

    if "ragas_scores" in results["ragas"] and results["ragas"]["ragas_scores"]:
        logger.info("\nRAGAS Metrics:")
        logger.info(
            f"  Faithfulness:      {results['ragas']['ragas_scores'].get('faithfulness', 'N/A'):.3f}"
        )
        logger.info(
            f"  Answer Relevancy:  {results['ragas']['ragas_scores'].get('answer_relevancy', 'N/A'):.3f}"
        )
        logger.info(
            f"  Context Precision: {results['ragas']['ragas_scores'].get('context_precision', 'N/A'):.3f}"
        )
        logger.info(
            f"  Context Recall:    {results['ragas']['ragas_scores'].get('context_recall', 'N/A'):.3f}"
        )

    logger.info(f"\nResults saved to: {RESULTS_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
