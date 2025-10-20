"""
Contains the core logic for the pictogram enrichment process using the Gemini API.
"""
import logging
import os
import json
import time
import google.generativeai as genai
from PIL import Image
from pathlib import Path
from rich.progress import Progress

# from .exceptions import APIError, ConfigurationError
from . import file_io

log = logging.getLogger(__name__)

class Enricher:
    """A client to interact with the Gemini API for pictogram enrichment."""

    def __init__(self, model_name: str | None = None):
        self._configure_api()
        self.model_name = model_name or self._discover_model()
        self.model = genai.GenerativeModel(self.model_name)
        self._prompt_template = """
You are an expert data enricher for a Dutch pictogram system. Your task is to analyze the provided image and generate metadata for it, **entirely in Dutch**. The image's filename, "{base_text}", is the primary action.

Return a single, minified JSON object (no newlines) with the following exact structure:
- "tags": An array of 5-7 relevant keywords **in Dutch**.
- "description": A concise, objective sentence **in Dutch** describing the action.

Example Output Format for an image of a car being washed with filename "auto wassen":
{{"tags":["auto","wassen","schoonmaken","water","voertuig","taak"],"description":"Een persoon wast de buitenkant van een auto met zeep en water."}}
"""

    def _configure_api(self):
        """Configures the Gemini API with the key from environment variables."""
        try:
            api_key = os.environ["GEMINI_API_KEY"]
            if not api_key:
                # raise ConfigurationError("The GEMINI_API_KEY environment variable is set but empty.")
                raise ValueError("The GEMINI_API_KEY environment variable is set but empty.")
            genai.configure(api_key=api_key)
        except KeyError:
            # raise ConfigurationError("The GEMINI_API_KEY environment variable is not set.")
            raise KeyError("The GEMINI_API_KEY environment variable is not set.")

    def _discover_model(self) -> str:
        """Finds the best available vision model, prioritizing Flash."""
        log.info("Discovering available Gemini models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'vision' in m.name:
                if 'flash' in m.name:
                    log.info("Found Flash model: %s", m.name)
                    return m.name
        # raise APIError("Could not discover a suitable Gemini vision model (Flash).")
        raise ConnectionError("Could not discover a suitable Gemini vision model (Flash).")

    def _get_enrichment_for_image(self, base_text: str, image: Image.Image, retries: int = 3, delay: int = 5) -> dict | None:
        """Calls the Gemini API for a single image."""
        log.info("Requesting enrichment for '%s'...", base_text)
        prompt = self._prompt_template.format(base_text=base_text)

        for attempt in range(retries):
            try:
                response = self.model.generate_content([prompt, image])
                # Clean the response to ensure it's valid JSON
                cleaned_json = response.text.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned_json)
            except Exception as e:
                log.warning("Attempt %d/%d failed for '%s'. Error: %s", attempt + 1, retries, base_text, e)
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1)) # Exponential backoff
                else:
                    log.error("Failed to enrich '%s' after %d attempts.", base_text, retries)
                    return None
        return None

    def run(self, image_dir: Path, output_file: Path, progress: Progress):
        """
        Runs the enrichment process for all new images in a directory.
        """
        log.info("Starting enrichment process...")
        log.info("Using model: %s", self.model_name)

        existing_data = file_io.load_enrichment_data(output_file)
        all_image_paths = file_io.find_image_files(image_dir)

        images_to_process = [
            p for p in all_image_paths if p.stem not in existing_data
        ]

        if not images_to_process:
            log.info("No new images to process. Enrichment data is up to date.")
            return

        log.info(f"Found {len(images_to_process)} new images to process.")

        task = progress.add_task("Enriching images...", total=len(images_to_process))

        for image_path in images_to_process:
            base_text = image_path.stem
            try:
                image = file_io.read_image(image_path)
                enriched_data = self._get_enrichment_for_image(base_text, image)

                if enriched_data:
                    existing_data[base_text] = enriched_data
                    # Save after each successful enrichment for resumability
                    file_io.save_enrichment_data(existing_data, output_file)
                    log.info("Successfully processed and saved '%s'.", base_text)
                else:
                    log.warning("Skipping '%s' due to enrichment failure.", base_text)

            except Exception as e:
                log.error("An unexpected error occurred while processing '%s': %s", base_text, e)

            progress.update(task, advance=1)
