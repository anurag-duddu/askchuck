"""
Owen's Structured Planning Terminology Glossary.

This glossary defines the specialized vocabulary used in Charles Owen's
methodology. It is used for:
1. Contextual enrichment - helping LLM understand Owen's terms
2. Terminology tagging - identifying which concepts each chunk contains
3. System prompts - grounding the RAG generation model
4. Query expansion - adding related terms to search queries
"""

from typing import List, Set

# Owen's Structured Planning terminology
OWEN_GLOSSARY = {
    # Core Structured Planning Concepts
    "Function": {
        "definition": "An action performed by a system or user, written as a verb phrase. Functions are the atomic units of Structured Planning and represent what the system must do.",
        "examples": ["Set up controls", "Check progress", "Prepare sauces"],
        "related": ["System Function", "User Function", "Function Structure"],
    },
    "Design Factor": {
        "definition": "A document capturing insight about a Function. Contains: Observation (essence), Extension (exploration), Design Implications (strategies), and Speculations (concrete ideas).",
        "examples": ["Initialization Uncertainty"],
        "related": ["Observation", "Extension", "Design Implication", "Speculation"],
    },
    "Speculation": {
        "definition": "A tactical, concrete idea for fulfilling a Function, formatted as an evocative adjective-noun phrase.",
        "examples": ["Feedback-Controlled Heating", "Micro Sampler"],
        "related": ["Design Factor", "Design Implication"],
    },
    "Design Implication": {
        "definition": "A topical strategy for using an insight, derived from general strategies. Suggests directions without specifying concrete form.",
        "examples": ["Sense heat in cooking containers"],
        "related": ["Design Factor", "Speculation"],
    },
    "Information Structure": {
        "definition": "A hierarchical organization of Functions based on likelihood of sharing solutions. Created by VTCON program.",
        "examples": ["International Design Institute Information Structure"],
        "related": ["VTCON", "Function", "Cluster"],
    },
    "Function Structure": {
        "definition": "A top-down hierarchical breakdown of system requirements into Modes, Activities, and Functions. Created during Action Analysis.",
        "examples": ["Housing System Function Structure"],
        "related": ["Mode", "Activity", "Function", "Action Analysis"],
    },
    "Abstraction Ladder": {
        "definition": "A tool for categorizing items from specific to general. Used to find fresh perspectives for innovation.",
        "examples": ["Chairs → Living Room Chairs → Modern Classic Seating"],
        "related": ["Abstraction Structure", "Categorization"],
    },
    "Abstraction Structure": {
        "definition": "A two-dimensional hierarchical structure combining multiple Abstraction Ladders.",
        "examples": ["Housing System Abstraction Structure"],
        "related": ["Abstraction Ladder", "Hierarchy"],
    },
    # Process Terms
    "Action Analysis": {
        "definition": "The Structured Planning phase that exhaustively identifies Functions through systematic examination of Modes and Activities.",
        "examples": ["Action Analysis of Housing System Use Mode"],
        "related": ["Function Structure", "Mode", "Activity"],
    },
    "Means/Ends Analysis": {
        "definition": "Process of naming unnamed nodes in an Information Structure by establishing what end the elements below are means to.",
        "examples": [
            "Advise students and Network alumni are means to Building Professional Networks"
        ],
        "related": ["Information Structure", "Abstraction Ladder"],
    },
    "Structured Planning": {
        "definition": "Owen's complete methodology for human-centered innovation combining systematic analysis with creative synthesis.",
        "examples": ["Structured Planning process for International Design Institute"],
        "related": ["Action Analysis", "RELATN", "VTCON"],
    },
    # Structural Elements
    "Mode": {
        "definition": "Highest level in Function Structure hierarchy. Distinct states a system goes through from production to retirement.",
        "examples": ["Use Mode", "Production Mode", "Maintenance Mode"],
        "related": ["Activity", "Function", "Function Structure"],
    },
    "Activity": {
        "definition": "Middle level in Function Structure. Purposeful performances within a Mode, described like theatrical scenes.",
        "examples": ["Cooking Activity", "Loading Activity"],
        "related": ["Mode", "Function", "Function Structure"],
    },
    "Cluster": {
        "definition": "A grouping of Functions in an Information Structure based on shared potential solutions.",
        "examples": ["Cluster 201: Functions related to instruction"],
        "related": ["Information Structure", "VTCON", "Function"],
    },
    "Node": {
        "definition": "A point in an Information Structure representing either a Function or a cluster of Functions.",
        "examples": ["Node 213: Instruction and Learning"],
        "related": ["Information Structure", "Cluster"],
    },
    # Tools and Programs
    "RELATN": {
        "definition": "Computer program that produces a graph of Functions based on how Speculations support or obstruct them.",
        "examples": ["RELATN analysis showing Function interactions"],
        "related": ["VTCON", "Function", "Speculation"],
    },
    "VTCON": {
        "definition": "Computer program that decomposes the RELATN graph to find clusters of highly interrelated Functions.",
        "examples": ["VTCON output showing hierarchical clustering"],
        "related": ["RELATN", "Information Structure", "Cluster"],
    },
}

# All term variations for matching (case-insensitive)
TERM_VARIATIONS = {
    "Function": ["function", "functions"],
    "Design Factor": ["design factor", "design factors"],
    "Speculation": ["speculation", "speculations"],
    "Design Implication": ["design implication", "design implications"],
    "Information Structure": ["information structure", "information structures"],
    "Function Structure": ["function structure", "function structures"],
    "Abstraction Ladder": ["abstraction ladder", "abstraction ladders"],
    "Abstraction Structure": ["abstraction structure", "abstraction structures"],
    "Action Analysis": ["action analysis"],
    "Means/Ends Analysis": ["means/ends analysis", "means-ends analysis"],
    "Structured Planning": ["structured planning"],
    "Mode": ["mode", "modes"],
    "Activity": ["activity", "activities"],
    "Cluster": ["cluster", "clusters"],
    "Node": ["node", "nodes"],
    "RELATN": ["relatn"],
    "VTCON": ["vtcon"],
}


def extract_owen_terms(text: str) -> List[str]:
    """
    Extract Owen terminology present in text.

    Args:
        text: Text to analyze

    Returns:
        List of Owen terms found in text
    """
    text_lower = text.lower()
    found_terms = []

    for canonical_term, variations in TERM_VARIATIONS.items():
        for variation in variations:
            if variation in text_lower:
                found_terms.append(canonical_term)
                break  # Don't count same term multiple times

    return found_terms


def tag_chunk_with_terms(chunk_text: str) -> List[str]:
    """
    Tag a chunk with Owen terminology.

    Args:
        chunk_text: Text of the chunk

    Returns:
        List of Owen terms present in chunk
    """
    return extract_owen_terms(chunk_text)


def get_term_definition(term: str) -> str:
    """
    Get the definition of an Owen term.

    Args:
        term: Owen terminology term

    Returns:
        Definition string, or empty if term not found
    """
    if term in OWEN_GLOSSARY:
        return OWEN_GLOSSARY[term]["definition"]
    return ""


def get_related_terms(term: str) -> List[str]:
    """
    Get related terms for an Owen term.

    Args:
        term: Owen terminology term

    Returns:
        List of related terms
    """
    if term in OWEN_GLOSSARY:
        return OWEN_GLOSSARY[term]["related"]
    return []


def get_all_terms() -> List[str]:
    """Get list of all Owen terms in the glossary."""
    return list(OWEN_GLOSSARY.keys())


def format_glossary_for_prompt(max_terms: int = 16) -> str:
    """
    Format glossary for inclusion in system prompt.

    Formats the most important Owen terms with definitions and examples
    in a compact format suitable for LLM prompts.

    Args:
        max_terms: Maximum number of terms to include (default: 16)

    Returns:
        Formatted glossary string
    """
    # Priority ordering - most fundamental concepts first
    priority_terms = [
        "Function",
        "Design Factor",
        "Speculation",
        "Design Implication",
        "Information Structure",
        "Function Structure",
        "Abstraction Ladder",
        "Action Analysis",
        "Structured Planning",
        "Mode",
        "Activity",
        "Cluster",
        "VTCON",
        "RELATN",
        "Means/Ends Analysis",
        "Abstraction Structure",
    ]

    formatted_parts = []

    for term in priority_terms[:max_terms]:
        if term in OWEN_GLOSSARY:
            info = OWEN_GLOSSARY[term]
            definition = info["definition"]

            # Format examples if available
            examples_str = ""
            if info.get("examples"):
                examples_list = info["examples"][:2]  # Max 2 examples
                examples_str = f" (e.g., {', '.join(examples_list)})"

            formatted_parts.append(f"- **{term}**: {definition}{examples_str}")

    return "\n".join(formatted_parts)
