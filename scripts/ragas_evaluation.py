"""
Standalone RAGAS Evaluation for AskChuck.

This file provides a clean, modular interface for running RAGAS evaluations
independently from the full evaluation suite.

Usage:
    # Quick test with single question
    python scripts/ragas_evaluation.py --quick

    # Evaluate with custom questions
    python scripts/ragas_evaluation.py --questions "What is a Design Factor?" "What is VTCON?"

    # Evaluate sample from golden dataset
    python scripts/ragas_evaluation.py --sample 5

    # Full evaluation
    python scripts/ragas_evaluation.py --full
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Set up environment variables for LangSmith tracing."""
    from src.utils.config import settings

    if settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        logger.info(
            f"LangSmith tracing enabled for project: {settings.langchain_project}"
        )
    else:
        logger.warning("LangSmith API key not configured - tracing disabled")


def get_llm_for_ragas():
    """
    Get LLM instance for RAGAS evaluation.

    Uses Groq (configured in settings) as the evaluation LLM.
    """
    from langchain_groq import ChatGroq

    from src.utils.config import settings

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key,
        temperature=0,
    )


def get_embeddings_for_ragas():
    """
    Get embeddings for RAGAS evaluation.

    Uses Voyage AI (configured in settings) for embeddings.
    """
    from langchain_voyageai import VoyageAIEmbeddings

    from src.utils.config import settings

    return VoyageAIEmbeddings(
        model="voyage-3",
        voyage_api_key=settings.voyage_api_key,
    )


def get_ragas_metrics():
    """
    Get RAGAS metric instances configured with our LLM.

    Returns:
        List of RAGAS metric objects
    """
    from ragas.metrics import (AnswerRelevancy, ContextPrecision,
                               ContextRecall, Faithfulness)

    # Get our LLM and embeddings
    llm = get_llm_for_ragas()
    embeddings = get_embeddings_for_ragas()

    # Create metrics with our LLM
    return [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
    ]


def evaluate_single_question(
    question: str,
    ground_truth: Optional[str] = None,
) -> Dict:
    """
    Evaluate a single question using the RAG system and RAGAS metrics.

    Args:
        question: The question to evaluate
        ground_truth: Optional expected answer for evaluation

    Returns:
        Dictionary with answer, contexts, and optional RAGAS scores
    """
    from src.generation.rag_chain import AskChuckRAG

    logger.info(f"Evaluating: {question[:50]}...")

    # Initialize RAG chain
    rag = AskChuckRAG()

    # Get response
    response = rag.query(
        question=question,
        conversation_history=[],
        include_figures=True,
        top_k=5,
    )

    # Extract contexts
    contexts = [
        source.get("content", source.get("text", ""))
        for source in response.get("sources", [])
    ]

    result = {
        "question": question,
        "answer": response["answer"],
        "contexts": contexts,
        "sources": response.get("sources", []),
        "chunks_used": response.get("chunks_used", 0),
    }

    if ground_truth:
        result["ground_truth"] = ground_truth

    return result


def run_ragas_evaluation(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: Optional[List[str]] = None,
) -> Dict:
    """
    Run RAGAS evaluation on a set of question-answer pairs.

    Args:
        questions: List of questions
        answers: List of generated answers
        contexts: List of context lists (one per question)
        ground_truths: Optional list of expected answers

    Returns:
        Dictionary with RAGAS scores
    """
    from datasets import Dataset
    from ragas import evaluate

    logger.info(f"Running RAGAS evaluation on {len(questions)} questions...")

    # Prepare dataset
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
    }

    if ground_truths:
        data["ground_truth"] = ground_truths

    dataset = Dataset.from_dict(data)

    # Get metrics
    metrics = get_ragas_metrics()

    # Run evaluation
    try:
        result = evaluate(dataset, metrics=metrics)

        # Access scores via to_pandas() and compute mean
        df = result.to_pandas()

        # Get mean scores for each metric (excluding non-numeric columns)
        numeric_cols = df.select_dtypes(include=["float64", "float32", "int64"]).columns
        mean_scores = df[numeric_cols].mean()

        scores = {}
        for metric_name in [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]:
            if metric_name in mean_scores:
                scores[metric_name] = float(mean_scores[metric_name])
            else:
                scores[metric_name] = 0.0

        logger.info("RAGAS Evaluation Results:")
        for metric, score in scores.items():
            if score > 0:
                logger.info(f"  {metric}: {score:.3f}")
            else:
                logger.info(f"  {metric}: N/A (metric may have failed)")

        return scores

    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def load_golden_dataset() -> Dict:
    """Load the golden dataset."""
    golden_path = Path(__file__).parent.parent / "tests" / "golden_dataset.json"

    if not golden_path.exists():
        raise FileNotFoundError(f"Golden dataset not found at {golden_path}")

    with open(golden_path) as f:
        return json.load(f)


def evaluate_from_dataset(sample_size: Optional[int] = None) -> Dict:
    """
    Run evaluation using questions from the golden dataset.

    Args:
        sample_size: Number of questions to evaluate (None for all)

    Returns:
        Evaluation results
    """
    from tqdm import tqdm

    from src.generation.rag_chain import AskChuckRAG

    # Load dataset
    dataset = load_golden_dataset()
    questions = dataset["questions"]

    # Filter out out-of-scope questions
    questions = [q for q in questions if q.get("category") != "out_of_scope"]

    # Sample if requested
    if sample_size:
        questions = questions[:sample_size]

    logger.info(f"Evaluating {len(questions)} questions from golden dataset")

    # Initialize RAG chain
    rag = AskChuckRAG()

    # Collect data
    eval_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    for q in tqdm(questions, desc="Querying RAG system"):
        try:
            response = rag.query(
                question=q["question"],
                conversation_history=[],
                include_figures=True,
                top_k=5,
            )

            contexts = [
                source.get("content", source.get("text", ""))
                for source in response.get("sources", [])
            ]

            if not contexts:
                contexts = ["No context retrieved"]

            eval_data["question"].append(q["question"])
            eval_data["answer"].append(response["answer"])
            eval_data["contexts"].append(contexts)
            eval_data["ground_truth"].append(q["expected_answer"])

        except Exception as e:
            logger.error(f"Error evaluating '{q['question'][:30]}...': {e}")
            continue

    if not eval_data["question"]:
        return {"error": "No questions successfully evaluated"}

    # Run RAGAS
    scores = run_ragas_evaluation(
        questions=eval_data["question"],
        answers=eval_data["answer"],
        contexts=eval_data["contexts"],
        ground_truths=eval_data["ground_truth"],
    )

    return {
        "num_questions": len(eval_data["question"]),
        "ragas_scores": scores,
    }


def quick_test() -> Dict:
    """Run a quick test with a single question."""
    setup_environment()

    question = "What is a Design Factor?"
    ground_truth = (
        "A Design Factor is a document that captures insight about a Function. "
        "It contains four components: Observation (essence), Extension (exploration), "
        "Design Implications (strategies), and Speculations (ideas for solutions)."
    )

    result = evaluate_single_question(question, ground_truth)

    logger.info("\n" + "=" * 60)
    logger.info("Quick Test Results")
    logger.info("=" * 60)
    logger.info(f"Question: {question}")
    logger.info(f"Answer: {result['answer'][:200]}...")
    logger.info(f"Contexts retrieved: {len(result['contexts'])}")

    if result.get("ground_truth"):
        # Run RAGAS on single question
        scores = run_ragas_evaluation(
            questions=[question],
            answers=[result["answer"]],
            contexts=[result["contexts"] or ["No context"]],
            ground_truths=[ground_truth],
        )
        result["ragas_scores"] = scores

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Standalone RAGAS Evaluation for AskChuck"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with single question",
    )
    parser.add_argument(
        "--questions",
        nargs="+",
        help="Custom questions to evaluate",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Sample N questions from golden dataset",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full evaluation on entire golden dataset",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    setup_environment()

    results = {}

    if args.quick:
        results = quick_test()

    elif args.questions:
        # Evaluate custom questions
        all_results = []
        for q in args.questions:
            result = evaluate_single_question(q)
            all_results.append(result)

        # Run RAGAS
        if all_results:
            scores = run_ragas_evaluation(
                questions=[r["question"] for r in all_results],
                answers=[r["answer"] for r in all_results],
                contexts=[r["contexts"] or ["No context"] for r in all_results],
            )
            results = {
                "questions": all_results,
                "ragas_scores": scores,
            }

    elif args.sample:
        results = evaluate_from_dataset(sample_size=args.sample)

    elif args.full:
        results = evaluate_from_dataset(sample_size=None)

    else:
        # Default: quick test
        results = quick_test()

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
