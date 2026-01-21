# PRD-08: Evaluation

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-08 |
| Version | v2.0 |
| Phase | 7 |
| Estimated Duration | 2-3 hours |
| Dependencies | PRD-06 (Generation) |
| Owner | Developer |

**Key Changes from v1.0:**
- Updated to v2.0 for consistency with finalized PRD set
- LangSmith tracing already implemented in PRD-06 (no code changes needed)
- Maintained comprehensive 50+ question golden dataset requirement
- Focused exclusively on RAG evaluation (retrieval + generation quality)
- Frontend integration testing deferred to manual QA phase

---

## Objective

Establish a rigorous evaluation framework for measuring and improving AskChuck's quality. This phase creates a golden dataset of question-answer pairs, implements RAGAS metrics for automated evaluation, sets up LangSmith tracing for observability, and defines testing strategies for both retrieval and generation components. The evaluation framework enables data-driven iteration on system quality.

---

## Background

Evaluating RAG systems is notoriously difficult because quality is multi-dimensional. A response might retrieve the right documents but synthesize them poorly, or it might generate fluent prose that misrepresents the sources. Traditional metrics like BLEU or ROUGE fail to capture these nuances because they compare surface-level text similarity rather than semantic accuracy.

RAGAS (Retrieval Augmented Generation Assessment) provides a framework specifically designed for RAG evaluation. It measures multiple dimensions: faithfulness (is the response grounded in context?), answer relevancy (does it address the question?), context precision (are retrieved chunks relevant?), and context recall (does context contain needed information?). Together, these metrics provide a holistic view of system quality.

Beyond automated metrics, human evaluation remains essential for subjective dimensions like helpfulness, clarity, and appropriate use of Owen's terminology. A golden dataset with expert-curated answers enables both automated comparison and manual review of system outputs.

For AskChuck specifically, evaluation must consider domain-specific criteria. Does the system use Owen's terminology correctly? Does it surface relevant figures for visual concepts? Does it appropriately acknowledge when questions fall outside the corpus? These Owen-specific quality dimensions require custom evaluation approaches.

---

## Functional Requirements

### FR-01: Golden Dataset Creation

The system shall have a curated dataset of question-answer pairs for evaluation.

**Acceptance Criteria:**
- Minimum 50 QA pairs covering diverse query types
- Questions span definition, procedural, example, and relationship queries
- Each pair includes expected answer and relevant source documents
- Dataset is versioned and stored in JSON format
- Includes difficulty ratings (easy, medium, hard)

### FR-02: RAGAS Metrics Implementation

The system shall compute standard RAGAS metrics for response quality.

**Acceptance Criteria:**
- Computes faithfulness score (grounding in context)
- Computes answer relevancy score (addresses question)
- Computes context precision score (relevant chunks ranked higher)
- Computes context recall score (context contains needed info)
- Produces aggregate scores across dataset

### FR-03: Retrieval Evaluation

The system shall evaluate retrieval quality independently.

**Acceptance Criteria:**
- Computes Hit Rate@k (correct doc in top k)
- Computes MRR (mean reciprocal rank)
- Computes NDCG@k (normalized discounted cumulative gain)
- Evaluates both dense and sparse retrieval separately
- Evaluates hybrid retrieval performance

### FR-04: LangSmith Integration

The system shall log all operations to LangSmith for observability.

**Acceptance Criteria:**
- All RAG queries create traces
- Traces include retrieval, reranking, and generation steps
- Latency is recorded at each step
- Token counts are tracked
- Errors are logged with context

### FR-05: Regression Testing

The system shall support automated regression testing.

**Acceptance Criteria:**
- Test suite runs against golden dataset
- Compares current metrics to baseline
- Flags significant quality degradation
- Can be run in CI/CD pipeline

### FR-06: Owen-Specific Quality Checks

The system shall evaluate domain-specific quality criteria.

**Acceptance Criteria:**
- Checks correct usage of Owen terminology
- Verifies figures are retrieved for visual queries
- Confirms sources are cited in responses
- Tests handling of out-of-scope questions

---

## Golden Dataset Structure

### Dataset Schema

```json
{
  "version": "1.0",
  "created_at": "2025-01-18",
  "description": "AskChuck evaluation dataset for Owen's Structured Planning",
  "questions": [
    {
      "id": "q001",
      "question": "What is a Design Factor?",
      "category": "definition",
      "difficulty": "easy",
      "expected_answer": "A Design Factor is a document that captures insight about a Function. It contains four parts: Observation (the essence of the insight), Extension (exploration of causes and effects), Design Implications (strategic directions), and Speculations (concrete ideas formatted as adjective-noun phrases).",
      "expected_sources": [
        {"document": "Context for Creativity", "section": "Design Factors"}
      ],
      "expected_terms": ["Design Factor", "Observation", "Extension", "Design Implication", "Speculation"],
      "requires_figure": false,
      "notes": "Core concept, should be answered definitively"
    }
  ]
}
```

### Question Categories

The golden dataset should include questions across these categories with the following distribution:

**Definition Queries (30%)** ask what a specific term or concept means. These test whether the system can retrieve and synthesize definitional content from Owen's papers. Examples include "What is a Function in Structured Planning?" and "Define the term Speculation as Owen uses it."

**Procedural Queries (25%)** ask how to do something within the methodology. These test whether the system can retrieve and explain multi-step processes. Examples include "How do you conduct Action Analysis?" and "What are the steps in creating an Information Structure?"

**Example Queries (20%)** ask for concrete instances or applications of concepts. These test whether the system can retrieve case studies and project examples. Examples include "Give me an example of an Abstraction Ladder" and "What was the Hydrospace project?"

**Relationship Queries (15%)** ask how concepts connect to each other. These test whether the system can synthesize information across multiple sources. Examples include "How do Functions relate to Speculations?" and "What's the difference between Function Structure and Information Structure?"

**Visual Queries (10%)** specifically request diagrams or ask about visually-represented concepts. These test figure retrieval and description capabilities. Examples include "Show me a diagram of an Information Structure" and "What does the Means/Ends worksheet look like?"

---

## Implementation Details

### File: tests/golden_dataset.json

```json
{
  "version": "1.0",
  "created_at": "2025-01-18",
  "questions": [
    {
      "id": "def_001",
      "question": "What is a Design Factor?",
      "category": "definition",
      "difficulty": "easy",
      "expected_answer": "A Design Factor is a document that captures insight about a Function in Structured Planning. It has four main parts: an Observation that states the essence of the insight, an Extension that explores causes and effects, Design Implications that suggest strategic directions, and Speculations that propose concrete ideas as evocative adjective-noun phrases.",
      "expected_sources": ["Context for Creativity"],
      "expected_terms": ["Design Factor", "Observation", "Extension", "Speculation"],
      "requires_figure": false
    },
    {
      "id": "def_002",
      "question": "What is an Abstraction Ladder?",
      "category": "definition",
      "difficulty": "easy",
      "expected_answer": "An Abstraction Ladder is a tool for categorizing items from specific to general. Moving up the ladder reveals increasingly abstract categories; moving down reveals more specific instances. It was conceptualized by semanticists Korzybski and Hayakawa and is used in Structured Planning to find fresh perspectives for innovation.",
      "expected_sources": ["The Power of Abstraction"],
      "expected_terms": ["Abstraction Ladder", "categorization", "abstraction"],
      "requires_figure": true
    },
    {
      "id": "def_003",
      "question": "What is a Function in Owen's methodology?",
      "category": "definition",
      "difficulty": "easy",
      "expected_answer": "In Owen's Structured Planning, a Function is an action performed by a system or user, written as a verb phrase. Functions are the atomic units of analysis and represent what the system must do. They can be System Functions (performed by the system) or User Functions (performed by the user operating the system).",
      "expected_sources": ["Context for Creativity"],
      "expected_terms": ["Function", "System Function", "User Function"],
      "requires_figure": false
    },
    {
      "id": "def_004",
      "question": "What is an Information Structure?",
      "category": "definition",
      "difficulty": "medium",
      "expected_answer": "An Information Structure is a hierarchical organization of Functions based on their likelihood of sharing solutions. It is created by the VTCON computer program, which groups Functions that should be considered together for design regardless of their conventional classification. The structure supports inventive design by clustering Functions with potential solutions in common.",
      "expected_sources": ["Context for Creativity", "The Power of Abstraction"],
      "expected_terms": ["Information Structure", "VTCON", "Function", "cluster"],
      "requires_figure": true
    },
    {
      "id": "def_005",
      "question": "What is a Speculation in Structured Planning?",
      "category": "definition",
      "difficulty": "easy",
      "expected_answer": "A Speculation is a tactical, concrete idea for fulfilling a Function, formatted as an evocative adjective-noun phrase. Speculations are generated from Design Implications and represent specific concepts that could be used in the final design. Examples include 'Feedback-Controlled Heating' and 'Micro Sampler'.",
      "expected_sources": ["Context for Creativity"],
      "expected_terms": ["Speculation", "Design Factor", "adjective-noun"],
      "requires_figure": false
    },
    {
      "id": "proc_001",
      "question": "How do you conduct Action Analysis?",
      "category": "procedural",
      "difficulty": "medium",
      "expected_answer": "Action Analysis is conducted by creating a three-level top-down hierarchy. First, identify Modes of operation (distinct states like Use, Maintenance, Transport). Then, for each Mode, describe Activities (purposeful performances like theatrical scenes). Finally, identify Functions (specific actions) for each Activity. Throughout, capture Design Factors documenting insights about what goes wrong or right.",
      "expected_sources": ["Context for Creativity"],
      "expected_terms": ["Action Analysis", "Mode", "Activity", "Function", "Design Factor"],
      "requires_figure": false
    },
    {
      "id": "proc_002",
      "question": "What are the steps in Means/Ends Analysis?",
      "category": "procedural",
      "difficulty": "hard",
      "expected_answer": "Means/Ends Analysis is the process of naming unnamed nodes in an Information Structure. For each cluster, you establish what end the elements below are means to. You move up the structure finding insightful category names that capture the functionality of grouped elements. The goal is to establish fresh perspectives from which to generate solutions.",
      "expected_sources": ["The Power of Abstraction"],
      "expected_terms": ["Means/Ends Analysis", "Information Structure", "abstraction"],
      "requires_figure": true
    },
    {
      "id": "exam_001",
      "question": "Give me an example of an Abstraction Ladder",
      "category": "example",
      "difficulty": "medium",
      "expected_answer": "Owen provides a chair example: At the bottom are specific designs like Eames Lounge Chair and Barcelona Chair. These group into 'Modern Classic Seating', which joins other styles to form 'Living Room Chairs'. This combines with Dining Room Chairs and others to form 'Chairs'. At the top, Chairs joins Tables, Beds, and Counters under 'Horizontal Surfaces'.",
      "expected_sources": ["The Power of Abstraction"],
      "expected_terms": ["Abstraction Ladder", "Horizontal Surfaces", "Chairs"],
      "requires_figure": true
    },
    {
      "id": "exam_002",
      "question": "What was the Hydrospace project?",
      "category": "example",
      "difficulty": "medium",
      "expected_answer": "The Hydrospace project was an IIT Institute of Design project for ARMCO Steel Company exploring future ocean industries. It examined deep-sea oil production, mineral harvesting from the sea bottom, and high-value fish farming. It exemplifies bottom-up innovation, where over 100 Problem Elements were organized into an Information Structure and progressively synthesized into an integrated system solution.",
      "expected_sources": ["Bottom-up, Top-down"],
      "expected_terms": ["Hydrospace", "bottom-up", "Problem Element", "Information Structure"],
      "requires_figure": true
    },
    {
      "id": "rel_001",
      "question": "How do Functions relate to Speculations?",
      "category": "relationship",
      "difficulty": "medium",
      "expected_answer": "Functions and Speculations are linked through Design Factors. When a Function is identified during Action Analysis, insights about it are captured in Design Factors. Each Design Factor generates Speculations—concrete ideas for how to fulfill the Function. In the Information Structure, Functions are grouped based on which Speculations they share, indicating they might have common solutions.",
      "expected_sources": ["Context for Creativity"],
      "expected_terms": ["Function", "Speculation", "Design Factor"],
      "requires_figure": false
    },
    {
      "id": "rel_002",
      "question": "What's the difference between top-down and bottom-up innovation?",
      "category": "relationship",
      "difficulty": "medium",
      "expected_answer": "Top-down innovation discovers a master concept first, then derives details. It offers clarity and simplicity but may force aspects into a mold. Bottom-up innovation gathers insights about parts first, then integrates toward a concept. It enables thorough exploration and creative freedom but has uncertain vision. Owen's Structured Planning uses both: bottom-up to create the Information Structure, then top-down to innovate system elements.",
      "expected_sources": ["Bottom-up, Top-down"],
      "expected_terms": ["top-down", "bottom-up", "Information Structure"],
      "requires_figure": false
    },
    {
      "id": "vis_001",
      "question": "Show me a diagram of an Information Structure",
      "category": "visual",
      "difficulty": "easy",
      "expected_answer": "The Information Structure diagram shows a hierarchical tree with Functions at the bottom and the project name at the top. Nodes in between represent clusters formed by VTCON based on interaction between Functions. The International Design Institute example shows Functions like 'Define mission of school' grouped into clusters like 'Instruction and Learning' at progressively higher levels.",
      "expected_sources": ["The Power of Abstraction", "Context for Creativity"],
      "expected_terms": ["Information Structure", "Function", "cluster", "VTCON"],
      "requires_figure": true
    },
    {
      "id": "out_001",
      "question": "What does Owen say about Agile methodology?",
      "category": "out_of_scope",
      "difficulty": "easy",
      "expected_answer": "Owen's literature does not discuss Agile methodology. His work focuses on Structured Planning, which predates Agile and has different goals. You might be interested in how Structured Planning approaches iterative development through its synthesis phases.",
      "expected_sources": [],
      "expected_terms": [],
      "requires_figure": false,
      "notes": "Tests appropriate handling of out-of-scope queries"
    }
  ]
}
```

### File: scripts/run_evaluation.py

```python
"""
Evaluation script for AskChuck.
Runs RAGAS metrics and retrieval evaluation against golden dataset.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset

from src.generation.rag_chain import get_rag_chain
from src.retrieval.retrieval_pipeline import get_retrieval_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "tests" / "golden_dataset.json"


def load_golden_dataset() -> list:
    """Load the golden dataset from JSON."""
    with open(GOLDEN_DATASET_PATH, 'r') as f:
        data = json.load(f)
    return data["questions"]


def run_rag_evaluation(questions: list, sample_size: Optional[int] = None) -> dict:
    """
    Run full RAG evaluation using RAGAS metrics.

    Args:
        questions: List of question dictionaries from golden dataset
        sample_size: Optional limit on number of questions to evaluate

    Returns:
        Dictionary with evaluation results
    """
    logger.info("Running RAG evaluation...")

    rag_chain = get_rag_chain()

    # Prepare data for RAGAS
    eval_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    # Select questions (optionally sample)
    eval_questions = questions[:sample_size] if sample_size else questions

    for q in eval_questions:
        # Skip out-of-scope questions for RAGAS eval
        if q.get("category") == "out_of_scope":
            continue

        logger.info(f"Evaluating: {q['question'][:50]}...")

        # Get RAG response
        response = rag_chain.query(q["question"])

        # Extract contexts from retrieval
        contexts = [
            chunk.get("content", "")
            for chunk in response.get("sources", [])
        ]

        eval_data["question"].append(q["question"])
        eval_data["answer"].append(response["answer"])
        eval_data["contexts"].append(contexts)
        eval_data["ground_truth"].append(q["expected_answer"])

    # Create dataset
    dataset = Dataset.from_dict(eval_data)

    # Run RAGAS evaluation
    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
    )

    return {
        "ragas_scores": result,
        "num_questions": len(eval_data["question"]),
        "timestamp": datetime.now().isoformat()
    }


def run_retrieval_evaluation(questions: list) -> dict:
    """
    Evaluate retrieval quality independently.

    Computes Hit Rate, MRR, and checks if expected sources are retrieved.
    """
    logger.info("Running retrieval evaluation...")

    pipeline = get_retrieval_pipeline()

    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    figure_hits = 0
    figure_expected = 0

    for q in questions:
        if q.get("category") == "out_of_scope":
            continue

        expected_sources = q.get("expected_sources", [])
        if not expected_sources:
            continue

        # Retrieve without reranking for pure retrieval eval
        results = pipeline.retrieval.retrieve(q["question"], top_k=10)

        # Check for hits
        retrieved_docs = [
            r.get("document_title", "").lower()
            for r in results
        ]

        expected_doc_names = [
            s.lower() if isinstance(s, str) else s.get("document", "").lower()
            for s in expected_sources
        ]

        # Find first hit
        first_hit_rank = None
        for rank, doc in enumerate(retrieved_docs, 1):
            if any(exp in doc for exp in expected_doc_names):
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

    total = len([q for q in questions if q.get("category") != "out_of_scope" and q.get("expected_sources")])

    return {
        "hit_rate_at_1": hits_at_1 / total if total > 0 else 0,
        "hit_rate_at_5": hits_at_5 / total if total > 0 else 0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0,
        "figure_retrieval_rate": figure_hits / figure_expected if figure_expected > 0 else 0,
        "total_questions": total
    }


def run_terminology_check(questions: list) -> dict:
    """
    Check if responses use Owen's terminology correctly.
    """
    logger.info("Running terminology check...")

    rag_chain = get_rag_chain()

    correct_term_usage = 0
    total_term_checks = 0

    for q in questions:
        expected_terms = q.get("expected_terms", [])
        if not expected_terms:
            continue

        response = rag_chain.query(q["question"])
        answer = response["answer"].lower()

        # Check if expected terms appear in response
        terms_found = sum(1 for term in expected_terms if term.lower() in answer)

        total_term_checks += len(expected_terms)
        correct_term_usage += terms_found

    return {
        "terminology_accuracy": correct_term_usage / total_term_checks if total_term_checks > 0 else 0,
        "terms_checked": total_term_checks
    }


def main():
    """Run complete evaluation suite."""
    logger.info("=" * 60)
    logger.info("AskChuck Evaluation Suite")
    logger.info("=" * 60)

    # Load dataset
    questions = load_golden_dataset()
    logger.info(f"Loaded {len(questions)} questions from golden dataset")

    # Run evaluations
    results = {}

    # Retrieval evaluation
    logger.info("\n--- Retrieval Evaluation ---")
    results["retrieval"] = run_retrieval_evaluation(questions)
    logger.info(f"Hit Rate@1: {results['retrieval']['hit_rate_at_1']:.2%}")
    logger.info(f"Hit Rate@5: {results['retrieval']['hit_rate_at_5']:.2%}")
    logger.info(f"MRR: {results['retrieval']['mrr']:.3f}")
    logger.info(f"Figure Retrieval: {results['retrieval']['figure_retrieval_rate']:.2%}")

    # Terminology check
    logger.info("\n--- Terminology Check ---")
    results["terminology"] = run_terminology_check(questions)
    logger.info(f"Terminology Accuracy: {results['terminology']['terminology_accuracy']:.2%}")

    # RAGAS evaluation (on sample for speed)
    logger.info("\n--- RAGAS Evaluation (sample) ---")
    results["ragas"] = run_rag_evaluation(questions, sample_size=10)
    logger.info(f"Faithfulness: {results['ragas']['ragas_scores'].get('faithfulness', 'N/A')}")
    logger.info(f"Answer Relevancy: {results['ragas']['ragas_scores'].get('answer_relevancy', 'N/A')}")

    # Save results
    output_path = Path(__file__).parent.parent / "tests" / "evaluation_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {output_path}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Evaluation Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| Golden dataset has 50+ questions | Count questions in JSON |
| Questions cover all categories | Verify distribution |
| RAGAS metrics compute successfully | Run evaluation script |
| Retrieval metrics compute correctly | Verify against manual check |
| LangSmith traces appear | Check LangSmith dashboard |
| Terminology check works | Verify expected terms detected |
| Results are saved to JSON | Check output file |

---

## Target Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| RAGAS Faithfulness | > 0.80 | > 0.70 |
| RAGAS Answer Relevancy | > 0.75 | > 0.65 |
| RAGAS Context Precision | > 0.70 | > 0.60 |
| Hit Rate@5 | > 0.85 | > 0.75 |
| MRR | > 0.60 | > 0.50 |
| Terminology Accuracy | > 0.80 | > 0.70 |

---

## Next Steps

Once evaluation is set up and baseline metrics are established, proceed to **PRD-09: Deployment** to deploy the application to production.
