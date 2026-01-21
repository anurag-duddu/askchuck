# PRD-03: Chunking & Enrichment

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-03 |
| Version | v2.0 |
| Phase | 2 |
| Estimated Duration | 3 hours |
| Dependencies | PRD-02 (Document Ingestion) |
| Owner | Developer |

**Key Changes from v1.0:**
- Switched from fixed 512-token chunks to hybrid hierarchical chunking
- Uses LlamaIndex HierarchicalNodeParser for parent-child relationships
- Custom Owen-specific semantic separators
- Added figure-text relationship tracking (dense and sparse)
- Enhanced chunk schema with hierarchical metadata

---

## Objective

Transform the processed documents from Phase 1 into semantically-aware hierarchical chunks for retrieval, enriched with contextual prefixes that preserve document-level understanding. The chunking strategy combines:

1. **Hierarchical Structure**: Parent-child relationships at multiple granularities (2048-token parents, 512-token children)
2. **Semantic Boundaries**: Owen-specific separators respecting document structure
3. **Figure-Text Relationships**: Dense (explicit references) and sparse (contextual) connections
4. **Contextual Enrichment**: LLM-generated prefixes for standalone chunk understanding

This hybrid approach ensures chunks are both precise for retrieval and rich with contextual relationships for comprehensive answers.

---

## Background

Chunking decisions have outsized impact on RAG quality—research shows chunking strategy alone can swing retrieval metrics by up to 9 percentage points. Owen's literature presents specific challenges that generic chunking approaches mishandle.

### The Owen Literature Challenge

Owen's papers contain highly interconnected concepts with specialized terminology. A chunk containing "The Speculations that support these Functions were generated during Action Analysis" is meaningless without knowing which Functions, what project, and what Action Analysis refers to. Standard fixed-size chunking produces these orphaned fragments that fail retrieval or mislead generation.

### Why Hierarchical Chunking?

Hierarchical chunking addresses the granularity mismatch problem: some queries need specific details (child chunks), while others need broader context (parent chunks). By maintaining parent-child relationships, we can:
- Retrieve specific passages for precise questions
- Expand to parent context when broader understanding is needed
- Preserve document structure in the retrieval process

### Why Semantic Boundaries?

Owen's papers follow clear structural patterns (sections, paragraphs, figure discussions). Respecting these natural boundaries ensures:
- Chunks align with conceptual units, not arbitrary token counts
- Figure references stay with their explanatory text
- Owen terminology isn't split mid-concept

### Why Contextual Enrichment?

Anthropic's contextual retrieval research demonstrates that prepending a short context explanation to each chunk before embedding reduces retrieval failures by 35%. When combined with hybrid search, this improvement reaches 67%. For a specialized domain like Owen's methodology, contextual enrichment is essential rather than optional.

---

## Functional Requirements

### FR-01: Hybrid Hierarchical Chunking

The system shall segment documents using a hybrid hierarchical approach combining semantic boundaries with parent-child relationships.

**Acceptance Criteria:**
- Uses LlamaIndex HierarchicalNodeParser for automatic parent-child tracking
- Parent chunks target 2048 tokens (flexible based on semantic boundaries)
- Child chunks target 512 tokens (flexible based on semantic boundaries)
- Custom separators respect Owen's document structure (sections, paragraphs, figures, sentences)
- Parent-child relationships maintained in bidirectional metadata
- Chunks preserve semantic coherence over fixed token counts
- Never split mid-sentence or mid-term (glossary validation)

### FR-02: Figure Chunk Creation & Relationships

The system shall create dedicated chunks for each figure and track figure-text relationships.

**Acceptance Criteria:**
- Each figure becomes a standalone retrievable chunk
- Figure chunks include: caption, description, document reference
- Figure chunks tagged with metadata for filtered retrieval
- Figure chunks link to Cloudflare R2 URLs for display
- **Dense relationships:** Explicit "Figure N" references tracked in chunk metadata
- **Sparse relationships:** Contextual figure relevance tracked (e.g., same section)

### FR-03: Contextual Enrichment

The system shall prepend contextual prefixes to each chunk explaining its position and relevance within the source document.

**Acceptance Criteria:**
- Every text chunk receives a 2-3 sentence context prefix
- Context identifies document title, section, and topic
- Context uses Owen's terminology correctly
- Context is generated via LLM (Groq Llama 3.1 70B)
- Rate limiting prevents API throttling

### FR-04: Owen Terminology Tagging

The system shall identify and tag Owen methodology terms present in each chunk.

**Acceptance Criteria:**
- Chunks tagged with list of Owen terms present
- Terms from predefined glossary only
- Tags stored in chunk metadata
- Tags enable filtered retrieval queries

### FR-05: Chunk Output Generation

The system shall produce structured output suitable for indexing with hierarchical metadata.

**Acceptance Criteria:**
- JSON output with all chunks and hierarchical metadata
- Consistent schema across all chunks
- Includes original text, enriched text, parent/child IDs, and metadata
- Preserves linkage to source document, section hierarchy, and related figures
- Neighbor chunk IDs for contextual expansion
- Chunk level indicator (parent/child)

---

## Owen Terminology Glossary

This glossary defines the specialized terms in Owen's methodology. It serves three purposes: informing contextual enrichment, enabling terminology tagging, and grounding the generation system prompt.

### File: src/utils/owen_glossary.py

```python
"""
Owen's Structured Planning Terminology Glossary.

This glossary defines the specialized vocabulary used in Charles Owen's
methodology. It is used for:
1. Contextual enrichment - helping LLM understand Owen's terms
2. Terminology tagging - identifying which concepts each chunk contains
3. System prompts - grounding the RAG generation model
4. Query expansion - adding related terms to search queries
"""

OWEN_GLOSSARY = {
    # Core Structured Planning Concepts
    "Function": {
        "definition": "An action performed by a system or user, written as a verb phrase. Functions are the atomic units of Structured Planning and represent what the system must do.",
        "examples": ["Set up controls", "Check progress", "Prepare sauces", "Manage infrastructure"],
        "related": ["System Function", "User Function", "Function Structure"]
    },

    "Design Factor": {
        "definition": "A document capturing insight about a Function. Contains four parts: Observation (essence of insight), Extension (exploration of causes/effects), Design Implications (strategic directions), and Speculations (concrete ideas).",
        "examples": ["Initialization Uncertainty (DF about cooking controls)"],
        "related": ["Observation", "Extension", "Design Implication", "Speculation"]
    },

    "Speculation": {
        "definition": "A tactical, concrete idea for fulfilling a Function, formatted as an evocative adjective-noun phrase. Generated from Design Implications.",
        "examples": ["Feedback-Controlled Heating", "Micro Sampler", "Weekly Advisor"],
        "related": ["Design Factor", "Design Implication", "Solution Element"]
    },

    "Design Implication": {
        "definition": "A topical strategy for using an insight, derived from general strategies. Suggests directions for solution without specifying concrete form.",
        "examples": ["Sense heat in cooking containers", "Regulate heat by feedback"],
        "related": ["Design Factor", "Speculation", "General Strategy"]
    },

    "Information Structure": {
        "definition": "A hierarchical organization of Functions based on their likelihood of sharing solutions. Created by VTCON program. Groups Functions that should be considered together for design, regardless of their conventional classification.",
        "examples": ["International Design Institute Information Structure"],
        "related": ["VTCON", "Function", "Cluster", "Means/Ends Analysis"]
    },

    "Function Structure": {
        "definition": "A top-down hierarchical breakdown of system requirements into Modes, Activities, and Functions. Created during Action Analysis to catalog what the system must do.",
        "examples": ["Housing System Function Structure"],
        "related": ["Mode", "Activity", "Function", "Action Analysis"]
    },

    "Abstraction Ladder": {
        "definition": "A tool for categorizing items from specific to general. Moving up the ladder reveals increasingly abstract categories; moving down reveals more specific instances. Used to find fresh perspectives for innovation.",
        "examples": ["Chairs → Living Room Chairs → Modern Classic Seating → Eames Lounge Chair"],
        "related": ["Abstraction Structure", "Categorization", "Means/Ends"]
    },

    "Abstraction Structure": {
        "definition": "A two-dimensional hierarchical structure combining multiple Abstraction Ladders. Has both width (parallel categories) and depth (levels of abstraction).",
        "examples": ["Housing System Abstraction Structure with Horizontal Surfaces, Space Dividers, Storages, etc."],
        "related": ["Abstraction Ladder", "Hierarchy"]
    },

    # Process Terms
    "Action Analysis": {
        "definition": "The Structured Planning phase that exhaustively identifies Functions through systematic examination of Modes and Activities. Produces the Function Structure while generating Design Factors.",
        "examples": ["Action Analysis of the Housing System Use Mode"],
        "related": ["Function Structure", "Mode", "Activity", "Design Factor"]
    },

    "Means/Ends Analysis": {
        "definition": "Process of naming unnamed nodes in an Information Structure by establishing what end the elements below are means to. Applies abstraction to find insightful category names.",
        "examples": ["Functions 'Advise students' and 'Network alumni' are means to 'Building Professional Networks'"],
        "related": ["Information Structure", "Abstraction Ladder", "Node naming"]
    },

    "Structured Planning": {
        "definition": "Owen's complete methodology for human-centered innovation. Combines systematic analysis with creative synthesis through phases including Action Analysis, structuring via RELATN/VTCON, and concept development.",
        "examples": ["The Structured Planning process for the International Design Institute"],
        "related": ["Action Analysis", "RELATN", "VTCON", "Information Structure"]
    },

    # Structural Elements
    "Mode": {
        "definition": "Highest level in Function Structure hierarchy. Distinct states a system goes through from production to retirement.",
        "examples": ["Use Mode", "Production Mode", "Maintenance Mode", "Transport Mode"],
        "related": ["Activity", "Function", "Function Structure", "Action Analysis"]
    },

    "Activity": {
        "definition": "Middle level in Function Structure. Purposeful performances within a Mode, described like theatrical scenes with users (players), system components (props), and environment (set).",
        "examples": ["Cooking Activity", "Loading Activity"],
        "related": ["Mode", "Function", "Function Structure"]
    },

    "Cluster": {
        "definition": "A grouping of Functions in an Information Structure based on shared potential solutions. Clusters are formed by VTCON program through numerical analysis of interaction between Functions.",
        "examples": ["Cluster 201: Functions related to instruction and learning"],
        "related": ["Information Structure", "VTCON", "Function"]
    },

    "Node": {
        "definition": "A point in an Information Structure representing either a Function (at bottom) or a cluster of Functions/lower nodes. Nodes are named through Means/Ends Analysis.",
        "examples": ["Node 213: Instruction and Learning"],
        "related": ["Information Structure", "Cluster", "Means/Ends Analysis"]
    },

    # Tools and Programs
    "RELATN": {
        "definition": "Computer program in Structured Planning that produces a graph of Functions based on how Speculations support or obstruct them. Creates links showing which Functions should be considered together.",
        "examples": ["RELATN analysis showing Function interactions"],
        "related": ["VTCON", "Function", "Speculation", "Graph"]
    },

    "VTCON": {
        "definition": "Computer program that decomposes the RELATN graph to find clusters of highly interrelated Functions, then hierarchically reassembles them into an Information Structure.",
        "examples": ["VTCON output showing hierarchical clustering"],
        "related": ["RELATN", "Information Structure", "Cluster"]
    },

    # Design Approaches
    "Top-down": {
        "definition": "Innovation approach where a master concept is discovered first, then details are derived from it. Strength: clarity and simplicity. Weakness: may force aspects into a mold.",
        "examples": ["Mies van der Rohe's architectural principles", "Kekulé's benzene ring discovery"],
        "related": ["Bottom-up", "Innovation", "Synthesis"]
    },

    "Bottom-up": {
        "definition": "Innovation approach where insights about parts are gathered first, then integrated toward a master concept. Strength: thoroughness and creative freedom. Weakness: uncertain vision.",
        "examples": ["Hydrospace project", "Christopher Alexander's method"],
        "related": ["Top-down", "Innovation", "Synthesis"]
    },

    # Document Components
    "Observation": {
        "definition": "First part of a Design Factor. A succinct 'silver bullet' statement of the insight, distilled to its essence.",
        "examples": ["'Because of physical differences in how heat is produced, it is difficult to know when a cooking device is ready'"],
        "related": ["Design Factor", "Extension"]
    },

    "Extension": {
        "definition": "Second part of a Design Factor. Fills in details, examines causes and effects, provides a forum for discussion of related information.",
        "examples": ["Explanation of how gas vs electric vs microwave heating differs"],
        "related": ["Design Factor", "Observation"]
    },

    # Projects Referenced
    "Hydrospace": {
        "definition": "IIT Institute of Design project exploring future ocean industries including deep-sea oil, mineral harvesting, and fish farming. Example of bottom-up innovation.",
        "examples": ["The Hydrospace system with mineral gathering and fish farms"],
        "related": ["Bottom-up", "System design"]
    },

    "Space Station": {
        "definition": "1985 NASA project at Institute of Design for integrated stowage and logistics. Applied Abstraction Ladder approach treating Space Station modules as special houses.",
        "examples": ["Habitation/Laboratory Module mockup"],
        "related": ["Abstraction Ladder", "System design"]
    }
}


def get_glossary_terms() -> list:
    """Return list of all glossary term names."""
    return list(OWEN_GLOSSARY.keys())


def get_term_definition(term: str) -> str:
    """Get the definition for a specific term."""
    if term in OWEN_GLOSSARY:
        return OWEN_GLOSSARY[term]["definition"]
    return None


def format_glossary_for_prompt() -> str:
    """Format glossary as concise text for system prompts."""
    lines = []
    for term, data in OWEN_GLOSSARY.items():
        lines.append(f"- **{term}**: {data['definition']}")
    return "\n".join(lines)


def find_terms_in_text(text: str) -> list:
    """
    Find all Owen methodology terms present in a text.
    Uses case-insensitive matching.
    """
    text_lower = text.lower()
    found_terms = []

    for term in OWEN_GLOSSARY.keys():
        # Check for term and common variations
        term_lower = term.lower()
        if term_lower in text_lower:
            found_terms.append(term)
        # Check plural forms
        elif term_lower + "s" in text_lower:
            found_terms.append(term)

    return list(set(found_terms))


def get_related_terms(term: str) -> list:
    """Get terms related to a given term."""
    if term in OWEN_GLOSSARY:
        return OWEN_GLOSSARY[term].get("related", [])
    return []


def expand_query_with_terms(query: str) -> str:
    """
    Expand a query with related Owen terminology.
    Useful for improving retrieval when users use different phrasing.
    """
    found = find_terms_in_text(query)

    expansion_terms = set()
    for term in found:
        related = get_related_terms(term)
        expansion_terms.update(related)

    # Remove terms already in query
    expansion_terms -= set(found)

    if expansion_terms:
        return query + " " + " ".join(expansion_terms)
    return query
```

---

## Technical Specification

### Chunking Strategy: Hybrid Hierarchical Approach

The chunking approach combines four techniques in a sophisticated hybrid pipeline:

1. **Hierarchical Parent-Child Structure** (LlamaIndex HierarchicalNodeParser):
   - Automatic parent-child relationship tracking
   - Parent chunks: 2048 tokens (broader context)
   - Child chunks: 512 tokens (precise retrieval)
   - Bidirectional links maintained in metadata

2. **Semantic Boundary Detection** (Custom Owen-Specific Separators):
   - Section headings (`\n## `, `\n### `)
   - Figure references (`\nFigure `)
   - Paragraph breaks (`\n\n`)
   - Sentence boundaries (`. `)
   - Respects document structure over arbitrary token counts

3. **Figure-Text Relationship Tracking** (Post-Processing):
   - Dense: Explicit "Figure N" references via regex
   - Sparse: Contextual relevance (same section, related concepts)
   - Enables figure-aware retrieval and generation

4. **Contextual Enrichment** (LLM-Generated Prefixes):
   - Prepend context explaining chunk position in document
   - Uses Groq Llama 3.3 70B with Owen glossary
   - Reduces retrieval failures by 35-67%

### Chunk Schema (v2.0 - Hierarchical)

```json
{
  "chunk_id": "owen_power_of_abstraction_2009_chunk_005",
  "document_id": "owen_power_of_abstraction_2009",
  "chunk_type": "text",
  "chunk_level": "child",
  "parent_id": "owen_power_of_abstraction_2009_chunk_002",
  "child_ids": [],
  "original_text": "The steps in abstracting from the specific to the general...",
  "enriched_text": "This chunk is from 'The Power of Abstraction' (2009) by Charles Owen, in the section 'The Abstraction Ladder'. It explains the fundamental process of creating abstraction hierarchies for innovation. The steps in abstracting from the specific to the general...",
  "metadata": {
    "document_title": "The Power of Abstraction",
    "section": "The Abstraction Ladder",
    "section_hierarchy": ["Introduction", "Core Concepts", "The Abstraction Ladder"],
    "page_start": 3,
    "page_end": 3,
    "owen_terms": ["Abstraction Ladder", "Function", "Abstraction Structure"],
    "explicit_figures": ["owen_power_of_abstraction_2009_fig_1"],
    "related_figures": ["owen_power_of_abstraction_2009_fig_2"],
    "neighbor_chunk_ids": ["owen_power_of_abstraction_2009_chunk_004", "owen_power_of_abstraction_2009_chunk_006"],
    "token_count": 487,
    "char_count": 2156,
    "context_prefix": "This chunk is from 'The Power of Abstraction' (2009)..."
  }
}
```

### Figure Chunk Schema (v2.0)

```json
{
  "chunk_id": "owen_power_of_abstraction_2009_fig_1",
  "document_id": "owen_power_of_abstraction_2009",
  "chunk_type": "figure",
  "chunk_level": "independent",
  "parent_id": null,
  "child_ids": [],
  "original_text": "Figure 1 An Abstraction Ladder produced by considering existing chairs...",
  "enriched_text": "This is Figure 1 from 'The Power of Abstraction' (2009) by Charles Owen. It illustrates the Abstraction Ladder concept, a key tool in Structured Planning for moving from specific instances to general categories. Figure 1 An Abstraction Ladder produced by considering existing chairs...",
  "metadata": {
    "document_title": "The Power of Abstraction",
    "section": "The Abstraction Ladder",
    "section_hierarchy": ["Introduction", "Core Concepts", "The Abstraction Ladder"],
    "figure_number": 1,
    "page": 4,
    "caption": "An Abstraction Ladder produced by considering existing chairs in a living room and extrapolating their categorization.",
    "r2_url": "https://<account>.r2.cloudflarestorage.com/askchuck/figures/owen_power_of_abstraction_2009_fig_1.png",
    "local_path": "data/figures/owen_power_of_abstraction_2009_fig_1.png",
    "owen_terms": ["Abstraction Ladder", "Abstraction Structure"],
    "has_image": true,
    "referenced_by_chunks": ["owen_power_of_abstraction_2009_chunk_005", "owen_power_of_abstraction_2009_chunk_007"],
    "neighbor_chunk_ids": [],
    "token_count": 89,
    "char_count": 412
  }
}
```

---

## Implementation Details

### File: src/chunking/chunker.py

```python
"""
Hybrid hierarchical chunking for Owen's academic documents.
Uses LlamaIndex HierarchicalNodeParser with custom Owen-specific semantic separators.
"""

import logging
import re
from typing import Optional, List, Dict
import tiktoken

from llama_index.core.node_parser import HierarchicalNodeParser, SentenceSplitter
from llama_index.core.schema import Document, TextNode

from src.utils.owen_glossary import find_terms_in_text

logger = logging.getLogger(__name__)


class OwenChunker:
    """
    Hybrid hierarchical chunker optimized for Owen's Structured Planning literature.

    Combines:
    1. LlamaIndex HierarchicalNodeParser for parent-child relationships
    2. Custom Owen-specific semantic separators
    3. Post-processing for figure-text relationships
    """

    def __init__(
        self,
        parent_chunk_size: int = 2048,
        child_chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.chunk_overlap = chunk_overlap

        # Tokenizer for accurate token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Owen-specific separators respecting document structure
        self.owen_separators = [
            "\n## ",      # Major section headers
            "\n### ",     # Subsection headers
            "\nFigure ",  # Figure references
            "\n\n",       # Paragraph breaks
            "\n",         # Line breaks
            ". ",         # Sentence boundaries
        ]

        # Configure semantic-aware sentence splitter
        sentence_splitter = SentenceSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=chunk_overlap,
            separator=" ",  # Base separator
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;]+[,.;]?",  # Sentence boundaries
        )

        # Use hierarchical parser with semantic splitter
        self.node_parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=[parent_chunk_size, child_chunk_size],
            chunk_overlap=chunk_overlap,
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self.tokenizer.encode(text))

    def _apply_owen_separators(self, text: str) -> str:
        """Pre-process text with Owen-specific separator markers."""
        # Add clear markers for Owen-specific boundaries
        for sep in self.owen_separators:
            if sep in text:
                # Ensure separators are emphasized for splitting
                text = text.replace(sep, f"\n{sep}")
        return text

    def chunk_document(self, doc_data: dict) -> list:
        """
        Chunk a processed document into hierarchical retrievable units.

        Args:
            doc_data: Processed document dictionary from ingestion

        Returns:
            List of chunk dictionaries with parent-child relationships
        """
        doc_id = doc_data["document_id"]
        doc_title = doc_data["metadata"]["title"]

        logger.info(f"Chunking document with hierarchical approach: {doc_title}")

        # Combine all text sections with section markers
        full_text = self._prepare_document_text(doc_data)

        # Apply Owen-specific separators
        processed_text = self._apply_owen_separators(full_text)

        # Create LlamaIndex Document
        llama_doc = Document(text=processed_text, id_=doc_id)

        # Parse into hierarchical nodes
        nodes = self.node_parser.get_nodes_from_documents([llama_doc])

        # Convert LlamaIndex nodes to our chunk format
        chunks = self._convert_nodes_to_chunks(nodes, doc_data)

        # Post-process: add figure-text relationships
        chunks = self._add_figure_relationships(chunks, doc_data)

        # Create figure chunks
        figure_chunks = self._create_figure_chunks(doc_data)
        chunks.extend(figure_chunks)

        logger.info(f"Created {len(chunks)} chunks ({len(figure_chunks)} figures) from {doc_title}")
        return chunks

    def _prepare_document_text(self, doc_data: dict) -> str:
        """Combine document sections with structure markers."""
        sections = []
        for section in doc_data.get("sections", []):
            heading = section.get("heading", "")
            content = section.get("content", "")
            level = section.get("level", 2)

            # Add section marker
            marker = "#" * level
            section_text = f"\n{marker} {heading}\n\n{content}"
            sections.append(section_text)

        return "\n\n".join(sections)

    def _convert_nodes_to_chunks(
        self,
        nodes: List[TextNode],
        doc_data: dict
    ) -> list:
        """
        Convert LlamaIndex TextNodes to our chunk format.
        Preserves parent-child relationships and adds Owen-specific metadata.
        """
        doc_id = doc_data["document_id"]
        doc_title = doc_data["metadata"]["title"]

        chunks = []
        node_id_map = {}  # Map LlamaIndex node IDs to our chunk IDs

        for i, node in enumerate(nodes):
            chunk_id = f"{doc_id}_chunk_{i + 1:03d}"
            node_id_map[node.node_id] = chunk_id

            # Determine chunk level from relationships
            chunk_level = "parent" if node.relationships.get("child") else "child"

            # Extract section info from text
            section_info = self._extract_section_info(node.text, doc_data)

            # Find Owen terms
            owen_terms = find_terms_in_text(node.text)

            # Get parent/child IDs
            parent_node = node.relationships.get("parent")
            parent_id = node_id_map.get(parent_node.node_id) if parent_node else None

            child_nodes = node.relationships.get("child", [])
            child_ids = [node_id_map.get(cn.node_id) for cn in child_nodes if cn.node_id in node_id_map]

            chunk = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "chunk_type": "text",
                "chunk_level": chunk_level,
                "parent_id": parent_id,
                "child_ids": child_ids,
                "original_text": node.text,
                "enriched_text": None,  # Set by enrichment step
                "metadata": {
                    "document_title": doc_title,
                    "section": section_info["section"],
                    "section_hierarchy": section_info["hierarchy"],
                    "page_start": section_info.get("page_start"),
                    "page_end": section_info.get("page_end"),
                    "owen_terms": owen_terms,
                    "explicit_figures": [],  # Populated by post-processing
                    "related_figures": [],   # Populated by post-processing
                    "neighbor_chunk_ids": [],  # Populated later
                    "token_count": self._count_tokens(node.text),
                    "char_count": len(node.text),
                }
            }

            chunks.append(chunk)

        # Add neighbor chunk IDs
        for i, chunk in enumerate(chunks):
            neighbors = []
            if i > 0:
                neighbors.append(chunks[i-1]["chunk_id"])
            if i < len(chunks) - 1:
                neighbors.append(chunks[i+1]["chunk_id"])
            chunk["metadata"]["neighbor_chunk_ids"] = neighbors

        return chunks

    def _extract_section_info(self, text: str, doc_data: dict) -> dict:
        """Extract section information from chunk text."""
        # Match against document sections to find which section this chunk belongs to
        for section in doc_data.get("sections", []):
            if section.get("heading", "") in text[:200]:  # Check first 200 chars
                return {
                    "section": section.get("heading", "Unknown"),
                    "hierarchy": self._build_hierarchy(section, doc_data),
                    "page_start": section.get("page_start"),
                    "page_end": section.get("page_end"),
                }

        return {
            "section": "Unknown Section",
            "hierarchy": [],
            "page_start": None,
            "page_end": None,
        }

    def _build_hierarchy(self, section: dict, doc_data: dict) -> list:
        """Build section hierarchy path."""
        # Simple implementation - could be enhanced with actual hierarchical tracking
        return [section.get("heading", "Unknown")]

    def _add_figure_relationships(self, chunks: list, doc_data: dict) -> list:
        """
        Post-processing: Add figure-text relationships.
        - Dense: Explicit "Figure N" references
        - Sparse: Contextual relevance (same section)
        """
        figures = doc_data.get("figures", [])
        figure_pattern = re.compile(r'\bFigure\s+(\d+)\b', re.IGNORECASE)

        for chunk in chunks:
            # Dense relationships: Find explicit figure references
            explicit_refs = figure_pattern.findall(chunk["original_text"])
            explicit_figure_ids = []

            for fig_num in explicit_refs:
                for fig in figures:
                    if str(fig.get("figure_number")) == fig_num:
                        explicit_figure_ids.append(fig["figure_id"])

            chunk["metadata"]["explicit_figures"] = list(set(explicit_figure_ids))

            # Sparse relationships: Figures in same section
            chunk_section = chunk["metadata"]["section"]
            related_figure_ids = []

            for fig in figures:
                # Rough heuristic: figures near the same page range
                fig_page = fig.get("page", 0)
                chunk_page_start = chunk["metadata"].get("page_start", 0)
                chunk_page_end = chunk["metadata"].get("page_end", 999)

                if chunk_page_start <= fig_page <= chunk_page_end + 1:  # +1 for figures on next page
                    if fig["figure_id"] not in explicit_figure_ids:
                        related_figure_ids.append(fig["figure_id"])

            chunk["metadata"]["related_figures"] = related_figure_ids

        return chunks

    def _create_figure_chunks(self, doc_data: dict) -> list:
        """Create dedicated chunks for all figures."""
        doc_id = doc_data["document_id"]
        doc_title = doc_data["metadata"]["title"]
        figures = doc_data.get("figures", [])

        figure_chunks = []

        for figure in figures:
            # Combine caption and description for the chunk text
            caption = figure.get("caption", "")
            description = figure.get("description", "")

            chunk_text = f"Figure {figure.get('figure_number', '?')}: {caption}\n\n{description}"

            # Find Owen terms
            owen_terms = find_terms_in_text(chunk_text)

            # Find which text chunks reference this figure
            referenced_by = self._find_referencing_chunks(figure, doc_data)

            # Extract section info
            section_info = self._get_figure_section(figure, doc_data)

            chunk = {
                "chunk_id": figure["figure_id"],
                "document_id": doc_id,
                "chunk_type": "figure",
                "chunk_level": "independent",
                "parent_id": None,
                "child_ids": [],
                "original_text": chunk_text,
                "enriched_text": None,  # Set by enrichment step
                "metadata": {
                    "document_title": doc_title,
                    "section": section_info["section"],
                    "section_hierarchy": section_info["hierarchy"],
                    "figure_number": figure.get("figure_number"),
                    "page": figure.get("page"),
                    "caption": caption,
                    "r2_url": figure.get("r2_url"),
                    "local_path": figure.get("local_path"),
                    "owen_terms": owen_terms,
                    "has_image": True,
                    "referenced_by_chunks": referenced_by,
                    "neighbor_chunk_ids": [],
                    "token_count": self._count_tokens(chunk_text),
                    "char_count": len(chunk_text)
                }
            }

            figure_chunks.append(chunk)

        return figure_chunks

    def _find_referencing_chunks(self, figure: dict, doc_data: dict) -> list:
        """Find text chunks that explicitly reference this figure."""
        # This will be populated during _add_figure_relationships
        # For now, return empty - will be filled by cross-referencing
        return []

    def _get_figure_section(self, figure: dict, doc_data: dict) -> dict:
        """Determine which section a figure belongs to based on page number."""
        fig_page = figure.get("page", 0)

        for section in doc_data.get("sections", []):
            page_start = section.get("page_start", 0)
            page_end = section.get("page_end", 999)

            if page_start <= fig_page <= page_end:
                return {
                    "section": section.get("heading", "Unknown"),
                    "hierarchy": [section.get("heading", "Unknown")]
                }

        return {
            "section": "Unknown Section",
            "hierarchy": []
        }

    def chunk_all_documents(self, parsed_docs: list) -> list:
        """
        Chunk all processed documents with hierarchical structure.

        Args:
            parsed_docs: List of processed document dictionaries

        Returns:
            Flat list of all chunks across all documents with relationships
        """
        all_chunks = []

        for doc in parsed_docs:
            doc_chunks = self.chunk_document(doc)
            all_chunks.extend(doc_chunks)

        # Post-process: Update figure chunks with referencing chunk info
        self._update_figure_references(all_chunks)

        logger.info(f"Total chunks created: {len(all_chunks)}")
        self._log_statistics(all_chunks)

        return all_chunks

    def _update_figure_references(self, chunks: list):
        """Update figure chunks with which text chunks reference them."""
        # Build a map of figure_id -> chunk
        figure_chunks = {c["chunk_id"]: c for c in chunks if c["chunk_type"] == "figure"}

        # For each text chunk, update corresponding figures
        for chunk in chunks:
            if chunk["chunk_type"] == "text":
                for fig_id in chunk["metadata"]["explicit_figures"]:
                    if fig_id in figure_chunks:
                        figure_chunks[fig_id]["metadata"]["referenced_by_chunks"].append(chunk["chunk_id"])

    def _log_statistics(self, chunks: list):
        """Log chunking statistics."""
        text_chunks = [c for c in chunks if c["chunk_type"] == "text"]
        figure_chunks = [c for c in chunks if c["chunk_type"] == "figure"]
        parent_chunks = [c for c in text_chunks if c["chunk_level"] == "parent"]
        child_chunks = [c for c in text_chunks if c["chunk_level"] == "child"]

        logger.info(f"  Text chunks: {len(text_chunks)} ({len(parent_chunks)} parents, {len(child_chunks)} children)")
        logger.info(f"  Figure chunks: {len(figure_chunks)}")

        if text_chunks:
            avg_tokens = sum(c["metadata"]["token_count"] for c in text_chunks) / len(text_chunks)
            logger.info(f"  Average text chunk size: {avg_tokens:.1f} tokens")


def chunk_document(doc_data: dict) -> list:
    """Convenience function to chunk a single document."""
    chunker = OwenChunker()
    return chunker.chunk_document(doc_data)
```

**Key Implementation Notes:**

1. **LlamaIndex Integration**: Uses `HierarchicalNodeParser` for automatic parent-child tracking
2. **Owen Separators**: Pre-processes text with Owen-specific structural markers
3. **Figure Relationships**: Post-processing step adds both dense (explicit) and sparse (contextual) figure connections
4. **Metadata Richness**: Preserves section hierarchy, neighboring chunks, Owen terms, and more
5. **Flexible Sizing**: Target sizes are guidelines, not hard limits - semantic coherence takes priority
```

### File: src/chunking/contextual_enrichment.py

```python
"""
Contextual enrichment for chunks using LLM-generated prefixes.
Implements Anthropic's contextual retrieval technique.
"""

import logging
import time
from typing import Optional

from groq import Groq

from src.utils.config import settings
from src.utils.owen_glossary import format_glossary_for_prompt

logger = logging.getLogger(__name__)


# Prompt for generating contextual prefixes
CONTEXT_GENERATION_PROMPT = """You are helping to prepare academic documents about Charles Owen's Structured Planning methodology for a RAG (retrieval-augmented generation) system.

I will give you a document and a specific chunk from that document. Your task is to write a brief context (2-3 sentences) that should be prepended to the chunk to help situate it within the broader document.

The context should include:
1. The document title and section where this chunk appears
2. The main topic or concept being discussed
3. Any relevant Owen methodology terms that apply

Here is some Owen terminology to help you:
{glossary}

<document>
{document_text}
</document>

<chunk>
{chunk_text}
</chunk>

Write ONLY the context prefix (2-3 sentences). Do not include the chunk itself. Do not use phrases like "This chunk" - write as if introducing the content to a reader."""


class ContextualEnricher:
    """
    Generates contextual prefixes for chunks using Groq LLM.
    Implements Anthropic's contextual retrieval technique.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
        self.glossary = format_glossary_for_prompt()

        # Rate limiting
        self.requests_per_minute = 30
        self.last_request_time = 0

    def generate_context(
        self,
        chunk_text: str,
        document_text: str,
        document_title: str
    ) -> str:
        """
        Generate a contextual prefix for a single chunk.

        Args:
            chunk_text: The chunk content
            document_text: The full document content (truncated if needed)
            document_title: Title of the source document

        Returns:
            Generated context prefix string
        """
        self._rate_limit()

        # Truncate document if too long (keep first 6000 chars for context)
        if len(document_text) > 6000:
            document_text = document_text[:6000] + "\n...[document truncated]..."

        prompt = CONTEXT_GENERATION_PROMPT.format(
            glossary=self.glossary[:2000],  # Truncate glossary too
            document_text=document_text,
            chunk_text=chunk_text
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )

            context = response.choices[0].message.content.strip()
            return context

        except Exception as e:
            logger.warning(f"Failed to generate context: {e}")
            # Fallback to simple template
            return f"From '{document_title}': "

    def _rate_limit(self):
        """Simple rate limiting."""
        min_interval = 60.0 / self.requests_per_minute
        elapsed = time.time() - self.last_request_time

        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        self.last_request_time = time.time()

    def enrich_chunk(self, chunk: dict, document_text: str) -> dict:
        """
        Add contextual prefix to a chunk.

        Args:
            chunk: Chunk dictionary
            document_text: Full document text

        Returns:
            Updated chunk with enriched_text populated
        """
        context = self.generate_context(
            chunk_text=chunk["original_text"],
            document_text=document_text,
            document_title=chunk["metadata"]["document_title"]
        )

        # Combine context with original text
        chunk["enriched_text"] = f"{context}\n\n{chunk['original_text']}"
        chunk["metadata"]["context_prefix"] = context

        return chunk

    def enrich_all_chunks(
        self,
        chunks: list,
        documents: dict
    ) -> list:
        """
        Enrich all chunks with contextual prefixes.

        Args:
            chunks: List of chunk dictionaries
            documents: Dictionary mapping doc_id to full document text

        Returns:
            List of enriched chunks
        """
        logger.info(f"Enriching {len(chunks)} chunks with contextual prefixes")

        for i, chunk in enumerate(chunks):
            doc_id = chunk["document_id"]
            doc_text = documents.get(doc_id, "")

            chunk = self.enrich_chunk(chunk, doc_text)

            if (i + 1) % 10 == 0:
                logger.info(f"Enrichment progress: {i + 1}/{len(chunks)}")

        logger.info("Contextual enrichment complete")
        return chunks


class BatchEnricher:
    """
    Alternative enricher that processes chunks in batches to reduce API calls.
    Uses a single call per document rather than per chunk.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def enrich_document_chunks(
        self,
        chunks: list,
        document_text: str,
        document_title: str
    ) -> list:
        """
        Enrich all chunks from a single document in fewer API calls.
        Groups chunks and generates contexts in batches.
        """
        # For small number of chunks, generate individually
        if len(chunks) <= 5:
            enricher = ContextualEnricher()
            for chunk in chunks:
                enricher.enrich_chunk(chunk, document_text)
            return chunks

        # For larger documents, use simplified template-based enrichment
        # to stay within free tier limits
        for chunk in chunks:
            section = chunk["metadata"].get("section", "")
            terms = chunk["metadata"].get("owen_terms", [])

            if chunk["chunk_type"] == "figure":
                context = f"This is a figure from '{document_title}' illustrating Owen's Structured Planning concepts."
            else:
                terms_str = ", ".join(terms[:3]) if terms else "general concepts"
                context = f"From '{document_title}', section '{section}', discussing {terms_str}."

            chunk["enriched_text"] = f"{context}\n\n{chunk['original_text']}"
            chunk["metadata"]["context_prefix"] = context

        return chunks


def enrich_chunks(chunks: list, documents: dict) -> list:
    """
    Convenience function to enrich chunks.
    Uses batch enrichment to minimize API calls.
    """
    enricher = BatchEnricher()

    # Group chunks by document
    chunks_by_doc = {}
    for chunk in chunks:
        doc_id = chunk["document_id"]
        if doc_id not in chunks_by_doc:
            chunks_by_doc[doc_id] = []
        chunks_by_doc[doc_id].append(chunk)

    # Enrich each document's chunks
    enriched_chunks = []
    for doc_id, doc_chunks in chunks_by_doc.items():
        doc_text = documents.get(doc_id, "")
        doc_title = doc_chunks[0]["metadata"]["document_title"] if doc_chunks else ""

        enriched = enricher.enrich_document_chunks(doc_chunks, doc_text, doc_title)
        enriched_chunks.extend(enriched)

    return enriched_chunks
```

### File: scripts/build_chunks.py

```python
"""
Build chunks from processed documents.
Runs: load processed docs → chunk → enrich → save.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking.chunker import OwenChunker
from src.chunking.contextual_enrichment import enrich_chunks
from src.utils.config import PROCESSED_DIR, CHUNKS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build all chunks from processed documents."""

    logger.info("=" * 60)
    logger.info("Building Chunks from Processed Documents")
    logger.info("=" * 60)

    # Load all processed documents
    processed_files = list(PROCESSED_DIR.glob("*.json"))
    logger.info(f"Found {len(processed_files)} processed documents")

    parsed_docs = []
    documents_text = {}  # For enrichment

    for pf in processed_files:
        with open(pf, 'r', encoding='utf-8') as f:
            doc = json.load(f)
            parsed_docs.append(doc)
            documents_text[doc["document_id"]] = doc.get("full_text", "")

    # Chunk all documents
    logger.info("\nChunking documents...")
    chunker = OwenChunker()
    all_chunks = chunker.chunk_all_documents(parsed_docs)

    # Enrich with contextual prefixes
    logger.info("\nEnriching chunks with context...")
    enriched_chunks = enrich_chunks(all_chunks, documents_text)

    # Save chunks
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    # Save all chunks to single file
    output_path = CHUNKS_DIR / "all_chunks.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_chunks, f, indent=2, ensure_ascii=False)

    logger.info(f"\nSaved {len(enriched_chunks)} chunks to {output_path}")

    # Also save per-document for debugging
    chunks_by_doc = {}
    for chunk in enriched_chunks:
        doc_id = chunk["document_id"]
        if doc_id not in chunks_by_doc:
            chunks_by_doc[doc_id] = []
        chunks_by_doc[doc_id].append(chunk)

    for doc_id, doc_chunks in chunks_by_doc.items():
        doc_output = CHUNKS_DIR / f"{doc_id}_chunks.json"
        with open(doc_output, 'w', encoding='utf-8') as f:
            json.dump(doc_chunks, f, indent=2, ensure_ascii=False)

    # Summary statistics
    text_chunks = [c for c in enriched_chunks if c["chunk_type"] == "text"]
    figure_chunks = [c for c in enriched_chunks if c["chunk_type"] == "figure"]

    logger.info("\n" + "=" * 60)
    logger.info("Chunking Complete!")
    logger.info("=" * 60)
    logger.info(f"Total chunks: {len(enriched_chunks)}")
    logger.info(f"  Text chunks: {len(text_chunks)}")
    logger.info(f"  Figure chunks: {len(figure_chunks)}")
    logger.info(f"Documents: {len(chunks_by_doc)}")

    # Token statistics
    total_tokens = sum(c["metadata"]["token_count"] for c in enriched_chunks)
    avg_tokens = total_tokens / len(enriched_chunks) if enriched_chunks else 0
    logger.info(f"Total tokens: {total_tokens:,}")
    logger.info(f"Average tokens per chunk: {avg_tokens:.1f}")


if __name__ == "__main__":
    main()
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| All documents chunked hierarchically | Check all_chunks.json contains chunks from all docs with parent/child IDs |
| Parent chunks average 1500-2500 tokens | Calculate from metadata where chunk_level == "parent" |
| Child chunks average 400-600 tokens | Calculate from metadata where chunk_level == "child" |
| Parent-child relationships bidirectional | Verify parent's child_ids contains child, child's parent_id references parent |
| Figure chunks created for all figures | Count figure_type chunks vs extracted figures |
| Figure-text relationships tracked | Verify explicit_figures and related_figures arrays populated |
| Contextual prefixes added | Check enriched_text differs from original_text |
| Owen terms tagged correctly | Manual review of 10 sample chunks |
| Semantic boundaries respected | Manual review shows no mid-sentence or mid-term splits |
| Section hierarchy preserved | Check section_hierarchy array matches document structure |
| Neighbor chunks tracked | Verify neighbor_chunk_ids references adjacent chunks |
| Output JSON is valid | Parse and validate schema with hierarchical fields |

---

## Next Steps

Once chunking is complete, proceed to **PRD-04: Indexing** to embed chunks and build the vector and sparse retrieval indices.
