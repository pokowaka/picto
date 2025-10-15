"""
Contains the core business logic for the pictogram enrichment process.
"""
import logging
from pathlib import Path
from .gemini_client import GeminiClient
from .file_io import read_image
from .exceptions import PictoIndexerError

# Get a logger for this module
log = logging.getLogger(__name__)

def enrich_image(
    image_path: Path, 
    client: GeminiClient
) -> tuple[str, dict] | None:
    """
    Processes a single image file to generate enriched metadata.

    Args:
        image_path: The Path object for the image to process.
        client: An initialized GeminiClient instance.

    Returns:
        A tuple containing the base_text and the enriched data dictionary,
        or None if enrichment fails.
    """
    base_text = image_path.stem
    
    try:
        image = read_image(image_path)
        enriched_data = client.get_enrichment(base_text, image)
        
        if enriched_data:
            picto_entry = {
                "image_path": str(Path("img") / "nl" / image_path.name),
                **enriched_data
            }
            return base_text, picto_entry
        else:
            log.warning("No enrichment data returned for '%s'.", base_text)
            return None

    except PictoIndexerError as e:
        # Log errors for individual files but continue the process
        log.warning("Skipping '%s': %s", base_text, e)
        return None
