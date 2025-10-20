"""
Handles all filesystem operations for the Picto Indexer.
"""
import json
import logging
from pathlib import Path
from PIL import Image
import faiss
import numpy as np

# from .exceptions import FileSystemError

log = logging.getLogger(__name__)

def find_image_files(directory: Path) -> list[Path]:
    """
    Finds all .png files in a given directory.
    """
    if not directory.is_dir():
        # raise FileSystemError(f"Input directory not found or is not a directory: {directory}")
        raise NotADirectoryError(f"Input directory not found or is not a directory: {directory}")
    
    try:
        return sorted(list(directory.glob("*.png")))
    except Exception as e:
        # raise FileSystemError(f"Failed to scan directory {directory}: {e}")
        raise IOError(f"Failed to scan directory {directory}: {e}")

def read_image(path: Path) -> Image.Image:
    """
    Reads an image file and converts it to RGB.
    """
    try:
        with Image.open(path) as img:
            # Ensure image is in a consistent format for the model
            return img.convert("RGB")
    except IOError as e:
        # raise FileSystemError(f"Could not open or read image {path}: {e}")
        raise IOError(f"Could not open or read image {path}: {e}")

def load_enrichment_data(path: Path) -> dict:
    """
    Loads the raw enrichment data from a JSON file.
    Returns an empty dict if the file doesn't exist.
    """
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
    """
    Saves the raw enrichment data to a JSON file.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file first to prevent corruption on interruption
        temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomically rename the temporary file to the final destination
        temp_path.rename(output_path)
    except IOError as e:
        # raise FileSystemError(f"Could not write to output file {output_path}: {e}")
        raise IOError(f"Could not write to output file {output_path}: {e}")

def save_final_artifacts(
    pictogram_data: dict, 
    vectors: np.ndarray, 
    output_dir: Path
):
    """
    Saves the final pictogram data and the FAISS index to the specified directory.
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # --- Save pictogram metadata ---
        data_path = output_dir / "pictogram_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(pictogram_data, f, indent=2, ensure_ascii=False)
        log.info("Final pictogram data saved to %s", data_path)

        # --- Save FAISS index ---
        index_path = output_dir / "faiss_index.bin"
        d = vectors.shape[1]
        index = faiss.IndexFlatL2(d)
        index.add(vectors)
        faiss.write_index(index, str(index_path))
        log.info("FAISS index saved to %s", index_path)

    except (IOError, Exception) as e:
        # raise FileSystemError(f"Could not write final artifacts to {output_dir}: {e}")
        raise IOError(f"Could not write final artifacts to {output_dir}: {e}")
