import pytest
from pathlib import Path
import os
from unittest.mock import MagicMock, patch

from picto_indexer.enricher import Enricher

@pytest.fixture
def mock_gemini_model():
    """Fixture to mock the Gemini API model."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"tags": ["mock tag"], "description": "mock description"}'
    mock_model.generate_content.return_value = mock_response
    return mock_model

@pytest.fixture
def enricher_instance(mocker, mock_gemini_model):
    """Fixture to create an Enricher instance with a mocked Gemini API."""
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "fake_api_key"})
    mocker.patch('google.generativeai.configure')
    mocker.patch('google.generativeai.GenerativeModel', return_value=mock_gemini_model)
    mocker.patch('picto_indexer.enricher.Enricher._discover_model', return_value='mock-model')
    return Enricher()

def test_enricher_run_processes_new_images(enricher_instance, tmp_path, mocker):
    """
    Tests that the enricher correctly identifies and processes only the images
    that are not already in the existing data file.
    """
    # --- Setup ---
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "image1.png").touch()
    (image_dir / "image2.png").touch()
    (image_dir / "image3.png").touch()

    output_file = tmp_path / "db.json"

    # Mock existing data: image1 is already processed
    existing_data = {"image1": {"tags": [], "description": ""}}

    # Mock file_io functions
    mocker.patch('picto_indexer.file_io.load_enrichment_data', return_value=existing_data)
    mock_save = mocker.patch('picto_indexer.file_io.save_enrichment_data')
    mocker.patch('picto_indexer.file_io.read_image', return_value=MagicMock()) # Mock image reading

    mock_progress = MagicMock()

    # --- Execution ---
    enricher_instance.run(image_dir, output_file, mock_progress)

    # --- Assertions ---

    # 1. Assert that the Gemini model was called exactly twice (for image2 and image3)
    assert enricher_instance.model.generate_content.call_count == 2

    # 2. Assert that the save function was called twice
    assert mock_save.call_count == 2

    # 3. Check the final state of the data that was saved
    final_data = mock_save.call_args[0][0]
    assert "image1" in final_data
    assert "image2" in final_data
    assert "image3" in final_data
    assert final_data["image2"]["description"] == "mock description"

def test_enricher_handles_api_failure(enricher_instance, tmp_path, mocker):
    """
    Tests that the enricher skips a file if the API call fails after retries,
    but continues processing other files.
    """
    # --- Setup ---
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "good_image.png").touch()
    (image_dir / "bad_image.png").touch()

    output_file = tmp_path / "db.json"

    # Mock the Gemini model to fail for a specific image
    def side_effect(prompt_and_image):
        prompt = prompt_and_image[0]
        if "bad_image" in prompt:
            raise Exception("API Error")
        else:
            response = MagicMock()
            response.text = '{"tags": ["good"], "description": "good image"}'
            return response

    enricher_instance.model.generate_content.side_effect = side_effect

    mocker.patch('picto_indexer.file_io.load_enrichment_data', return_value={})
    mock_save = mocker.patch('picto_indexer.file_io.save_enrichment_data')
    mocker.patch('picto_indexer.file_io.read_image', return_value=MagicMock())
    mocker.patch('time.sleep') # Prevent sleeping during tests

    mock_progress = MagicMock()

    # --- Execution ---
    enricher_instance.run(image_dir, output_file, mock_progress)

    # --- Assertions ---

    # 1. Assert the model was called for both images (with retries for the bad one)
    assert enricher_instance.model.generate_content.call_count == 1 + 3 # 1 for good, 3 for bad

    # 2. Assert that save was only called once (for the good image)
    mock_save.assert_called_once()

    # 3. Check the content of the saved data
    final_data = mock_save.call_args[0][0]
    assert "good_image" in final_data
    assert "bad_image" not in final_data