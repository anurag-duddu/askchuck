#!/usr/bin/env python3
"""
Regenerate figure descriptions for all processed documents.
Uses the updated Llama 4 Scout vision model.

This script:
1. Reads existing processed JSON files
2. Re-generates descriptions for all figures using the new vision model
3. Updates the JSON files with new descriptions
4. Preserves all other data (extraction, uploads, etc.)
"""

import json
import logging
import sys
from pathlib import Path

from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.figure_describer import FigureDescriber
from src.utils.config import FIGURES_DIR, PROCESSED_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def regenerate_descriptions(dry_run: bool = False):
    """
    Regenerate descriptions for all figures in processed documents.

    Args:
        dry_run: If True, show what would be done without making changes
    """
    logger.info("=" * 70)
    logger.info("FIGURE DESCRIPTION REGENERATION")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    logger.info(f"Vision Model: meta-llama/llama-4-scout-17b-16e-instruct")
    logger.info("=" * 70)

    # Find all processed JSON files
    json_files = sorted(PROCESSED_DIR.glob("*.json"))
    logger.info(f"\nFound {len(json_files)} processed documents")

    if not json_files:
        logger.error("No processed JSON files found!")
        return

    # Initialize describer
    describer = FigureDescriber()

    # Statistics
    total_figures = 0
    total_updated = 0
    total_failed = 0

    # Process each document
    for json_path in tqdm(json_files, desc="Processing documents", unit="doc"):
        try:
            # Load document data
            with open(json_path, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            figures = doc_data.get("figures", [])
            if not figures:
                logger.info(f"\n  {json_path.name}: No figures, skipping")
                continue

            logger.info(f"\n  {json_path.name}: {len(figures)} figures")
            total_figures += len(figures)

            # Regenerate descriptions
            if not dry_run:
                updated_figures = []
                for i, figure in enumerate(figures):
                    try:
                        # Get figure path
                        figure_path = Path(figure["local_path"])
                        if not figure_path.exists():
                            logger.warning(f"    Figure not found: {figure_path.name}")
                            total_failed += 1
                            updated_figures.append(figure)
                            continue

                        caption = figure.get("caption", "")

                        # Generate new description
                        logger.info(
                            f"    Describing figure {i+1}/{len(figures)}: {figure_path.name}"
                        )
                        description = describer.describe_figure(figure_path, caption)

                        # Update figure data
                        figure["description"] = description
                        updated_figures.append(figure)
                        total_updated += 1

                    except Exception as e:
                        logger.error(f"    Failed to describe figure {i+1}: {e}")
                        total_failed += 1
                        updated_figures.append(figure)
                        continue

                # Update document data
                doc_data["figures"] = updated_figures

                # Save updated JSON
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(doc_data, f, indent=2, ensure_ascii=False)

                logger.info(f"    ✓ Updated {json_path.name}")
            else:
                logger.info(f"    Would regenerate {len(figures)} descriptions")
                total_updated += len(figures)

        except Exception as e:
            logger.error(f"  ✗ Failed to process {json_path.name}: {e}")
            continue

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("REGENERATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total figures: {total_figures}")
    logger.info(f"Successfully updated: {total_updated}")
    logger.info(f"Failed: {total_failed}")

    if dry_run:
        logger.info("\nThis was a DRY RUN. No files were modified.")
        logger.info("Run without --dry-run to actually update the files.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Regenerate figure descriptions using updated vision model"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    try:
        regenerate_descriptions(dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
