"""
Contains the core logic for the vectorization process.
"""
import logging
import re
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from rich.progress import Progress
import chromadb

from . import file_io

log = logging.getLogger(__name__)

class Vectorizer:
    """
    Handles the transformation of enriched data into a searchable vector index.
    """
    def __init__(self, model_name: str = 'all-mpnet-base-v2'):
        self.model_name = model_name
        log.info("Loading SBERT model: %s", self.model_name)
        self.model = SentenceTransformer(self.model_name)
        log.info("SBERT model loaded successfully.")

    def _clean_text(self, text: str) -> str:
        """Normalizes text by converting to lowercase, removing numbers and special characters."""
        if not isinstance(text, str):
            return ""
        text = re.sub(r'\d+', '', text) # Remove numbers
        return re.sub(r'[^a-zA-Z\s]', '', text.lower()).strip()

    def run(self, input_file: Path, output_dir: Path, progress: Progress):
        """
        Runs the complete vectorization and data transformation pipeline.
        """
        log.info("Starting vectorization process...")

        # 1. Load & Validate Data
        raw_data = file_io.load_enrichment_data(input_file)
        if not raw_data:
            log.warning("Input file is empty or could not be read. Nothing to vectorize.")
            return

        pictogram_data = {}
        embedding_texts = []
        picto_ids = []
        metadatas = []

        validation_task = progress.add_task("Validating and transforming data...", total=len(raw_data))

        for picto_id, data in raw_data.items():
            if not isinstance(data, dict) or "description" not in data or "tags" not in data:
                log.warning("Skipping invalid record with ID '%s': missing 'description' or 'tags'.", picto_id)
                progress.update(validation_task, advance=1)
                continue

            concept_nl = self._clean_text(picto_id.replace('_', ' ').replace('-', ' '))
            description_nl = self._clean_text(data["description"])
            tags_nl = [self._clean_text(tag) for tag in data["tags"]]

            # Prepare metadata for ChromaDB (tags as a single string)
            metadata = {
                "id": picto_id,
                "image_path": str(Path("img") / "nl" / f"{picto_id}.png"),
                "concept_nl": concept_nl,
                "description_nl": description_nl,
                "tags_nl": " ".join(tags_nl)
            }
            metadatas.append(metadata)
            pictogram_data[picto_id] = metadata


            embedding_text = f"Concept: {concept_nl}. Description: {description_nl}. Tags: {' '.join(tags_nl)}"
            embedding_texts.append(embedding_text)
            picto_ids.append(picto_id)
            progress.update(validation_task, advance=1)

        if not embedding_texts:
            log.error("No valid data found to vectorize.")
            return

        embedding_task = progress.add_task("Generating SBERT embeddings...", total=len(embedding_texts))
        vectors = self.model.encode(
            embedding_texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        progress.update(embedding_task, completed=len(embedding_texts))

        log.info("Saving final data and ChromaDB index...")
        file_io.save_final_artifacts_chroma(pictogram_data, picto_ids, vectors.tolist(), metadatas, output_dir)
        log.info("Vectorization process completed successfully.")
