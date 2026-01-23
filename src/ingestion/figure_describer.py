"""
Figure description generation using Groq Vision API.
Generates rich semantic descriptions for figures using Llama 3.2 Vision model.
"""

import base64
import logging
import time
from pathlib import Path
from typing import Optional

from groq import Groq

from src.utils.config import settings

logger = logging.getLogger(__name__)


class FigureDescriber:
    """
    Generates semantic descriptions for figures using Groq Vision API.
    Optimized for Owen's academic diagrams and illustrations.
    """

    # System prompt for figure description
    SYSTEM_PROMPT = """You are an expert at describing academic diagrams and figures from design and innovation literature.

Your task is to generate detailed, accurate descriptions of figures that will be used for text-based retrieval in a RAG system.

Focus on:
1. **Figure type**: Is it a diagram, chart, table, flowchart, matrix, hierarchy, etc.?
2. **Content**: What concepts, entities, or data are shown?
3. **Relationships**: How are elements connected or organized?
4. **Labels**: What text labels, categories, or annotations are present?
5. **Semantic meaning**: What does the figure illustrate or explain?

Use terminology from Charles Owen's Structured Planning methodology when appropriate:
- Function, Design Factor, Speculation, Information Structure
- Abstraction Ladder, Means/Ends Analysis, VTCON, RELATN
- Systems thinking, human-centered design

Be concise but comprehensive. The description should enable someone to understand the figure's content and purpose without seeing it."""

    def __init__(self):
        """Initialize the figure describer with Groq API."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_vision_model

    def describe_figure(self, figure_path: Path, caption: str = "") -> str:
        """
        Generate a description for a single figure.

        Args:
            figure_path: Path to the figure image
            caption: Figure caption (if available)

        Returns:
            Generated description text
        """
        logger.info(f"Describing figure: {figure_path.name}")

        try:
            # Read and encode image
            image_data = self._encode_image(figure_path)

            # Create user prompt with caption
            user_prompt = self._create_user_prompt(caption)

            # Call Groq Vision API
            description = self._call_vision_api(image_data, user_prompt)

            logger.info(f"Generated description ({len(description)} chars)")
            return description

        except Exception as e:
            logger.error(f"Failed to describe figure {figure_path.name}: {e}")
            # Fallback to caption only
            return f"Figure showing: {caption}" if caption else "Figure content"

    def describe_figures_batch(
        self, figures: list, rate_limit_delay: float = 1.0
    ) -> list:
        """
        Generate descriptions for multiple figures with rate limiting.

        Args:
            figures: List of figure metadata dicts
            rate_limit_delay: Delay between API calls (seconds)

        Returns:
            Updated list of figure metadata with descriptions
        """
        logger.info(f"Describing {len(figures)} figures")

        for i, figure in enumerate(figures):
            try:
                # Get figure path
                figure_path = Path(figure["local_path"])
                caption = figure.get("caption", "")

                # Generate description
                description = self.describe_figure(figure_path, caption)

                # Update figure metadata
                figure["description"] = description

                # Rate limiting
                if i < len(figures) - 1:
                    time.sleep(rate_limit_delay)

            except Exception as e:
                logger.error(f"Failed to describe figure {i + 1}/{len(figures)}: {e}")
                figure["description"] = (
                    f"Figure {figure.get('figure_number', '')} - {figure.get('caption', '')}"
                )
                continue

        return figures

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
        return image_data

    def _create_user_prompt(self, caption: str) -> str:
        """Create user prompt including caption if available."""
        if caption:
            return f"""Describe this academic figure in detail.

Figure caption: {caption}

Provide a comprehensive description that captures:
- The type of diagram/visualization
- All elements, labels, and categories shown
- Relationships and connections between elements
- The conceptual framework or methodology illustrated
- How it relates to design thinking or Structured Planning concepts"""
        else:
            return """Describe this academic figure in detail.

Provide a comprehensive description that captures:
- The type of diagram/visualization
- All elements, labels, and categories shown
- Relationships and connections between elements
- The conceptual framework or methodology illustrated
- How it relates to design thinking or innovation concepts"""

    def _call_vision_api(self, image_data: str, user_prompt: str) -> str:
        """
        Call Groq Vision API with image and prompt.

        Args:
            image_data: Base64-encoded image
            user_prompt: User prompt text

        Returns:
            Generated description
        """
        # Create messages with image
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ],
            },
        ]

        # Call API
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, max_tokens=500, temperature=0.3
        )

        # Extract description
        description = response.choices[0].message.content.strip()

        return description


def describe_figure(figure_path: str, caption: str = "") -> str:
    """Convenience function to describe a single figure."""
    describer = FigureDescriber()
    return describer.describe_figure(Path(figure_path), caption)
