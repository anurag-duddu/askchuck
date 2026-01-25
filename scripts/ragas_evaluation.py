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


def get_vision_llm_for_ragas():
    """
    Get vision-capable LLM for multimodal RAGAS evaluation.

    Uses Groq's Llama 4 Scout model which supports vision.
    Tries llm_factory first (better structured output), falls back to LangchainLLMWrapper.
    """
    from src.utils.config import settings

    try:
        # Try using llm_factory with Groq for better structured output handling
        from groq import Groq
        from ragas.llms import llm_factory

        client = Groq(api_key=settings.groq_api_key)
        return llm_factory(
            settings.groq_vision_model,
            provider="groq",
            client=client,
        )
    except Exception as e:
        logger.warning(f"llm_factory failed, falling back to LangchainLLMWrapper: {e}")

        # Fallback to LangchainLLMWrapper
        from langchain_groq import ChatGroq
        from ragas.llms import LangchainLLMWrapper

        vision_llm = ChatGroq(
            model=settings.groq_vision_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )
        return LangchainLLMWrapper(vision_llm)


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


def get_multimodal_relevance_metric():
    """
    Get MultiModalRelevance metric for evaluating answers against
    both text and image contexts.

    Uses Groq's vision-capable Llama 4 Scout model.
    """
    from ragas.metrics import MultiModalRelevance

    vision_llm = get_vision_llm_for_ragas()
    return MultiModalRelevance(llm=vision_llm)


def extract_figure_urls(rag_response: Dict) -> List[str]:
    """
    Extract figure URLs from a RAG response.

    Args:
        rag_response: Response from AskChuckRAG.query()

    Returns:
        List of figure URLs (Supabase storage URLs)
    """
    figures = rag_response.get("figures", [])
    urls = []

    for fig in figures:
        # Figures already have URLs from the RAG chain
        if fig.get("url"):
            urls.append(fig["url"])

    return urls


async def evaluate_multimodal_relevance(
    question: str,
    answer: str,
    text_contexts: List[str],
    figure_urls: List[str],
) -> float:
    """
    Evaluate multimodal relevance of an answer against text and image contexts.

    Args:
        question: The user's question
        answer: The generated answer
        text_contexts: List of text context strings
        figure_urls: List of figure image URLs

    Returns:
        Relevance score (0.0 or 1.0)
    """
    from ragas.dataset_schema import SingleTurnSample

    metric = get_multimodal_relevance_metric()

    # Combine text and image contexts
    # RAGAS MultiModalRelevance accepts mixed context types
    combined_contexts = text_contexts + figure_urls

    if not combined_contexts:
        logger.warning("No contexts provided for multimodal evaluation")
        return 0.0

    try:
        # Create SingleTurnSample for the metric
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=combined_contexts,
        )

        # Use single_turn_ascore which accepts SingleTurnSample
        result = await metric.single_turn_ascore(sample)
        return float(result)
    except Exception as e:
        error_msg = str(e)

        # Check if this is the known parsing error with Groq
        if "StringIO" in error_msg or "parse" in error_msg.lower():
            logger.warning(
                "RAGAS parsing error with Groq vision model, using custom fallback evaluation"
            )
            return await _custom_multimodal_relevance(
                question, answer, text_contexts, figure_urls
            )

        logger.error(f"Multimodal relevance evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return 0.0


async def _custom_multimodal_relevance(
    question: str,
    answer: str,
    text_contexts: List[str],
    figure_urls: List[str],
) -> float:
    """
    Custom multimodal relevance evaluation when RAGAS parsing fails.

    Uses Groq's vision model directly with a structured prompt to evaluate
    whether the answer aligns with the provided contexts and images.

    Returns:
        Relevance score (0.0 or 1.0)
    """
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq

    from src.utils.config import settings

    # Build the prompt with contexts
    context_text = "\n\n".join(text_contexts[:3])  # Limit to avoid token overflow

    prompt_content = []

    # Add text instruction
    prompt_content.append(
        {
            "type": "text",
            "text": f"""Evaluate whether the following answer is relevant to the question and aligns with the provided context.

Question: {question}

Answer: {answer}

Text Context:
{context_text}

The following images are also part of the context:
""",
        }
    )

    # Add figure URLs as images (up to 2 to avoid token limits)
    for url in figure_urls[:2]:
        if url.startswith("http"):
            prompt_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": url},
                }
            )

    # Add final instruction
    prompt_content.append(
        {
            "type": "text",
            "text": """
Based on the question, context, and images above, is the answer relevant and aligned with the provided materials?

Respond with ONLY "relevant" or "not_relevant" (nothing else).""",
        }
    )

    try:
        # Use Groq's vision model directly
        llm = ChatGroq(
            model=settings.groq_vision_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )

        message = HumanMessage(content=prompt_content)
        response = await llm.ainvoke([message])

        result_text = response.content.lower().strip()

        if "relevant" in result_text and "not" not in result_text:
            return 1.0
        else:
            return 0.0

    except Exception as e:
        logger.error(f"Custom multimodal evaluation failed: {e}")
        return 0.0


def run_multimodal_evaluation(
    questions: List[str],
    answers: List[str],
    text_contexts: List[List[str]],
    figure_urls_list: List[List[str]],
) -> Dict:
    """
    Run multimodal relevance evaluation on a batch of question-answer pairs.

    Args:
        questions: List of questions
        answers: List of generated answers
        text_contexts: List of text context lists
        figure_urls_list: List of figure URL lists

    Returns:
        Dictionary with multimodal relevance scores
    """
    import asyncio
    import time

    logger.info(
        f"Running MultiModal Relevance evaluation on {len(questions)} questions..."
    )

    async def evaluate_all():
        scores = []
        for i, (q, a, texts, figs) in enumerate(
            zip(questions, answers, text_contexts, figure_urls_list)
        ):
            try:
                score = await evaluate_multimodal_relevance(q, a, texts, figs)
                scores.append(score)
                logger.info(
                    f"Question {i+1}/{len(questions)}: multimodal_relevance = {score}"
                )

                # Add delay between evaluations to avoid Groq rate limits
                # Groq free tier: 12K tokens/min
                if i < len(questions) - 1:
                    await asyncio.sleep(3)  # 3 second delay between requests

            except Exception as e:
                logger.error(f"Error evaluating question {i+1}: {e}")
                scores.append(0.0)
        return scores

    # Run async evaluation
    scores = asyncio.run(evaluate_all())

    avg_score = sum(scores) / len(scores) if scores else 0.0

    logger.info(f"MultiModal Relevance Average: {avg_score:.3f}")

    return {
        "multimodal_relevance": avg_score,
        "individual_scores": scores,
        "questions_with_figures": sum(1 for f in figure_urls_list if f),
    }


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
    from src.retrieval.retrieval_pipeline import get_retrieval_pipeline

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

    # Get raw chunks with full content for RAGAS
    # The RAG response sources are display-formatted and don't include full content
    retrieval = get_retrieval_pipeline()
    raw_chunks = retrieval.retrieve(query=question, top_k=5, include_figures=False)

    # Extract full contexts from raw chunks
    contexts = [
        chunk.get("content", "") for chunk in raw_chunks if chunk.get("content")
    ]

    # Fallback: if no contexts, use highlight_text from sources
    if not contexts:
        contexts = [
            source.get("highlight_text", "")
            for source in response.get("sources", [])
            if source.get("highlight_text")
        ]

    # Extract figure URLs for multimodal evaluation
    figure_urls = extract_figure_urls(response)

    result = {
        "question": question,
        "answer": response["answer"],
        "contexts": contexts,
        "figure_urls": figure_urls,
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


def evaluate_from_dataset(
    sample_size: Optional[int] = None,
    include_multimodal: bool = False,
) -> Dict:
    """
    Run evaluation using questions from the golden dataset.

    Args:
        sample_size: Number of questions to evaluate (None for all)
        include_multimodal: Whether to run multimodal relevance evaluation

    Returns:
        Evaluation results
    """
    from tqdm import tqdm

    from src.generation.rag_chain import AskChuckRAG
    from src.retrieval.retrieval_pipeline import get_retrieval_pipeline

    # Load dataset
    dataset = load_golden_dataset()
    questions = dataset["questions"]

    # Filter out out-of-scope questions
    questions = [q for q in questions if q.get("category") != "out_of_scope"]

    # Sample if requested
    if sample_size:
        questions = questions[:sample_size]

    logger.info(f"Evaluating {len(questions)} questions from golden dataset")

    # Initialize RAG chain and retrieval
    rag = AskChuckRAG()
    retrieval = get_retrieval_pipeline()

    # Collect data
    eval_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
        "figure_urls": [],
    }

    for q in tqdm(questions, desc="Querying RAG system"):
        try:
            response = rag.query(
                question=q["question"],
                conversation_history=[],
                include_figures=True,
                top_k=5,
            )

            # Get raw chunks with full content for RAGAS
            raw_chunks = retrieval.retrieve(
                query=q["question"], top_k=5, include_figures=False
            )

            # Extract full contexts from raw chunks
            contexts = [
                chunk.get("content", "") for chunk in raw_chunks if chunk.get("content")
            ]

            if not contexts:
                contexts = ["No context retrieved"]

            # Extract figure URLs for multimodal
            figure_urls = extract_figure_urls(response)

            eval_data["question"].append(q["question"])
            eval_data["answer"].append(response["answer"])
            eval_data["contexts"].append(contexts)
            eval_data["ground_truth"].append(q["expected_answer"])
            eval_data["figure_urls"].append(figure_urls)

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

    result = {
        "num_questions": len(eval_data["question"]),
        "ragas_scores": scores,
    }

    # Run multimodal evaluation if requested
    if include_multimodal:
        questions_with_figures = sum(1 for f in eval_data["figure_urls"] if f)
        logger.info(
            f"\nRunning MultiModal Relevance on {questions_with_figures} questions with figures..."
        )

        mm_results = run_multimodal_evaluation(
            questions=eval_data["question"],
            answers=eval_data["answer"],
            text_contexts=eval_data["contexts"],
            figure_urls_list=eval_data["figure_urls"],
        )
        result["multimodal_scores"] = mm_results

    return result


def quick_test(include_multimodal: bool = False) -> Dict:
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
    logger.info(f"Figures retrieved: {len(result.get('figure_urls', []))}")

    if result.get("ground_truth"):
        # Run RAGAS on single question
        scores = run_ragas_evaluation(
            questions=[question],
            answers=[result["answer"]],
            contexts=[result["contexts"] or ["No context"]],
            ground_truths=[ground_truth],
        )
        result["ragas_scores"] = scores

    # Run multimodal evaluation if requested
    if include_multimodal:
        logger.info("\nRunning MultiModal Relevance evaluation...")
        mm_results = run_multimodal_evaluation(
            questions=[question],
            answers=[result["answer"]],
            text_contexts=[result["contexts"] or []],
            figure_urls_list=[result.get("figure_urls", [])],
        )
        result["multimodal_scores"] = mm_results

    return result


def quick_multimodal_test() -> Dict:
    """Run a quick test specifically for multimodal evaluation with figures."""
    setup_environment()

    # Use a question that should retrieve figures
    question = "Show me an Action Analysis form and explain how it works"

    logger.info(f"Testing multimodal with: {question}")

    result = evaluate_single_question(question)

    logger.info("\n" + "=" * 60)
    logger.info("MultiModal Quick Test Results")
    logger.info("=" * 60)
    logger.info(f"Question: {question}")
    logger.info(f"Answer: {result['answer'][:200]}...")
    logger.info(f"Text contexts: {len(result['contexts'])}")
    logger.info(f"Figure URLs: {len(result.get('figure_urls', []))}")

    for i, url in enumerate(result.get("figure_urls", [])[:3]):
        logger.info(f"  Figure {i+1}: {url}")

    # Run multimodal evaluation
    if result.get("figure_urls"):
        mm_results = run_multimodal_evaluation(
            questions=[question],
            answers=[result["answer"]],
            text_contexts=[result["contexts"] or []],
            figure_urls_list=[result.get("figure_urls", [])],
        )
        result["multimodal_scores"] = mm_results
    else:
        logger.warning("No figures retrieved - multimodal evaluation skipped")
        result["multimodal_scores"] = {
            "multimodal_relevance": None,
            "note": "No figures retrieved",
        }

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
        "--multimodal",
        action="store_true",
        help="Include MultiModal Relevance evaluation (requires figures)",
    )
    parser.add_argument(
        "--multimodal-test",
        action="store_true",
        help="Run quick test specifically for multimodal evaluation with figures",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    setup_environment()

    results = {}

    if args.multimodal_test:
        results = quick_multimodal_test()

    elif args.quick:
        results = quick_test(include_multimodal=args.multimodal)

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
        results = evaluate_from_dataset(
            sample_size=args.sample,
            include_multimodal=args.multimodal,
        )

    elif args.full:
        results = evaluate_from_dataset(
            sample_size=None,
            include_multimodal=args.multimodal,
        )

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
