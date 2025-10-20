"""
Handles all file system operations for the indexer.
"""
import json
import logging
from pathlib import Path
from PIL import Image
import numpy as np
import chromadb

log = logging.getLogger(__name__)

def find_image_files(directory: Path) -> list[Path]:
    """Finds all .png files in a given directory."""
    if not directory.is_dir():
        raise NotADirectoryError(f"Input directory not found or is not a directory: {directory}")
    try:
        return sorted(list(directory.glob("*.png")))
    except Exception as e:
        raise IOError(f"Failed to scan directory {directory}: {e}")

def read_image(path: Path) -> Image.Image:
    """Reads an image file and converts it to RGB."""
    try:
        with Image.open(path) as img:
            return img.convert("RGB")
    except IOError as e:
        raise IOError(f"Could not open or read image {path}: {e}")

def load_enrichment_data(path: Path) -> dict:
    """Loads the raw enrichment data from a JSON file."""
    if not path.exists():
        log.info("Enrichment data file not found at %s, starting fresh.", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            log.info("Successfully loaded %d existing entries from %s.", len(data), path)
            return data
    except (json.JSONDecodeError, IOError) as e:
        log.warning("Could not read or parse existing enrichment data at %s. Starting fresh. Error: %s", path, e)
        return {}

def save_enrichment_data(data: dict, output_path: Path):
    """Saves the raw enrichment data to a JSON file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.rename(output_path)
    except IOError as e:
        raise IOError(f"Could not write to output file {output_path}: {e}")

def save_final_artifacts_chroma(
    pictogram_data: dict,
    pictogram_ids: list,
    vectors: list,
    metadatas: list,
    output_dir: Path
):
    """Saves the final pictogram data and the ChromaDB index."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Save pictogram metadata ---
        data_path = output_dir / "pictogram_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(pictogram_data, f, indent=2, ensure_ascii=False)
        log.info("Final pictogram data saved to %s", data_path)

        # --- Save ChromaDB index ---
        chroma_db_path = str(output_dir / "chroma_db")
        client = chromadb.PersistentClient(path=chroma_db_path)
        try:
            client.delete_collection("pictograms")
        except Exception:
            pass
        collection = client.get_or_create_collection("pictograms")

        batch_size = 1000
        for i in range(0, len(pictogram_ids), batch_size):
            collection.add(
                ids=pictogram_ids[i:i+batch_size],
                embeddings=vectors[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )
        log.info("ChromaDB index saved to %s", chroma_db_path)

    except (IOError, Exception) as e:
        raise IOError(f"Could not write final artifacts to {output_dir}: {e}")
