"""
Handles all filesystem operations for the Picto Indexer.
"""
import json
import logging
from pathlib import Path
from PIL import Image
from .exceptions import FileSystemError

log = logging.getLogger(__name__)

def load_index(path: Path) -> dict:
    """
    Loads the pictogram index from a JSON file.

    Args:
        path: The path to the JSON file.

    Returns:
        A dictionary of the existing pictogram data, or an empty dictionary
        if the file does not exist or is invalid.
    """
    if not path.exists():
        log.info("Index file not found at %s, starting fresh.", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            log.info("Successfully loaded %d existing entries from %s.", len(data), path)
            return data
    except (json.JSONDecodeError, IOError) as e:
        log.warning("Could not read or parse existing index at %s. Starting fresh. Error: %s", path, e)
        return {}

def find_image_files(directory: Path) -> list[Path]:
    """
    Finds all .png files in a given directory.

    Args:
        directory: The path to the directory to scan.

    Returns:
        A list of Path objects for each found image.

    Raises:
        FileSystemError: If the directory does not exist or is not a directory.
    """
    if not directory.is_dir():
        raise FileSystemError(f"Input directory not found or is not a directory: {directory}")
    
    try:
        return sorted(list(directory.glob("*.png")))
    except Exception as e:
        raise FileSystemError(f"Failed to scan directory {directory}: {e}")

def read_image(path: Path) -> Image.Image:
    """
    Reads an image file and converts it to RGB.

    Args:
        path: The path to the image file.

    Returns:
        A Pillow Image object.

    Raises:
        FileSystemError: If the image cannot be opened or read.
    """
    try:
        with Image.open(path) as img:
            return img.convert("RGB")
    except IOError as e:
        raise FileSystemError(f"Could not open or read image {path}: {e}")

def write_index(data: dict, output_path: Path):
    """
    Saves the final dictionary to a JSON file.

    Args:
        data: The dictionary of enriched pictogram data.
        output_path: The path to the output JSON file.

    Raises:
        FileSystemError: If the file cannot be written.
    """
    try:
        # Write to a temporary file first to prevent corruption on interruption
        temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomically rename the temporary file to the final destination
        temp_path.rename(output_path)
    except IOError as e:
        raise FileSystemError(f"Could not write to output file {output_path}: {e}")