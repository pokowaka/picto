import logging
import os
import json
import time
import google.generativeai as genai
from PIL import Image
from .exceptions import APIError, ConfigurationError

# Get a logger for this module
log = logging.getLogger(__name__)

class GeminiClient:
    """A client to interact with the Gemini API for pictogram enrichment."""

    def __init__(self, model_name: str):
        """
        Initializes the Gemini Client.

        Args:
            model_name: The specific Gemini model to use for API calls.
        """
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)
        self._prompt_template = """
You are an expert data enricher for a Dutch pictogram system. Your task is to analyze the provided image and generate metadata for it, **entirely in Dutch**. The image's filename, "{base_text}", is the primary action.

Return a single, minified JSON object (no newlines) with the following exact structure:
- "tags": An array of 5-7 relevant keywords **in Dutch**.
- "description": A concise, objective sentence **in Dutch** describing the action.

Example Output Format for an image of a car being washed with filename "auto wassen":
{{"tags":["auto","wassen","schoonmaken","water","voertuig","taak"],"description":"Een persoon wast de buitenkant van een auto met zeep en water."}}
"""

    @staticmethod
    def configure_api():
        """Configures the Gemini API with the key from environment variables."""
        try:
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        except KeyError:
            raise ConfigurationError("The GEMINI_API_KEY environment variable is not set.")

    @staticmethod
    def discover_model() -> str:
        """
        Finds the best available vision model, prioritizing Flash for cost.

        Returns:
            The name of the best available model.

        Raises:
            APIError: If no suitable model is found.
        """
        flash_model = None
        pro_model = None
        log.info("Discovering available Gemini models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'vision' in m.name:
                if 'flash' in m.name:
                    flash_model = m.name
                elif 'pro' in m.name:
                    pro_model = m.name
        
        # Prioritize the cheaper, faster model if available.
        model_to_return = flash_model or pro_model
        if not model_to_return:
            raise APIError("Could not discover a suitable Gemini vision model.")
        log.info("Discovered model: %s", model_to_return)
        return model_to_return

    def get_enrichment(self, base_text: str, image: Image.Image, retries: int = 3, delay: int = 2) -> dict:
        """
        Calls the Gemini API with an image and text to get structured metadata.

        Args:
            base_text: The base text from the filename.
            image: The Pillow Image object.
            retries: The number of times to retry the API call.
            delay: The delay in seconds between retries.

        Returns:
            A dictionary containing the enriched data.

        Raises:
            APIError: If the API call fails after all retries.
        """
        log.info("Requesting enrichment for '%s'...", base_text)
        prompt = self._prompt_template.format(base_text=base_text)
        
        for attempt in range(retries):
            try:
                response = self.model.generate_content([prompt, image])
                cleaned_json = response.text.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned_json)
            except Exception as e:
                log.warning("Attempt %s failed for '%s'. Error: %s", attempt + 1, base_text, e)
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise APIError(f"Failed to enrich '{base_text}' after {retries} attempts: {e}")
        # This line should be unreachable, but is here for safety.
        raise APIError(f"Exhausted retries for '{base_text}' without returning or raising a final error.")
