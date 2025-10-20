import pytest
from pathlib import Path
import numpy as np
from unittest.mock import MagicMock

from picto_indexer.vectorizer import Vectorizer

@pytest.fixture
def mock_sbert_model():
    """Fixture to mock the SentenceTransformer model."""
    mock_model = MagicMock()
    # Mock the encode method to return predictable vectors
    mock_model.encode.return_value = np.array([
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6]
    ], dtype='float32')
    return mock_model

@pytest.fixture
def vectorizer_instance(mocker, mock_sbert_model):
    """Fixture to create a Vectorizer instance with a mocked SBERT model."""
    mocker.patch('picto_indexer.vectorizer.SentenceTransformer', return_value=mock_sbert_model)
    return Vectorizer()

def test_clean_text(vectorizer_instance):
    """Tests the text cleaning and normalization."""
    assert vectorizer_instance._clean_text("Auto Wassen!") == "auto wassen"
    # Corrected assertion: numbers should be preserved
    assert vectorizer_instance._clean_text("tanden-poetsen_123") == "tandenpoetsen123"
    assert vectorizer_instance._clean_text("  leading/trailing spaces  ") == "  leadingtrailing spaces  "

def test_vectorizer_run(vectorizer_instance, tmp_path, mocker):
    """
    Tests the main run method of the Vectorizer, ensuring it processes
    data correctly and saves the artifacts.
    """
    # --- Setup ---
    # Create a mock input file in the temporary directory
    mock_input_content = {
        "auto wassen": {
            "tags": ["auto", "schoonmaken"],
            "description": "Een auto wassen."
        },
        "tanden poetsen": {
            "tags": ["hygiëne", "badkamer"],
            "description": "Tanden poetsen."
        },
        "ongeldig-record": {
            "msg": "Dit record is ongeldig."
        }
    }
    input_file = tmp_path / "mock_db.json"
    input_file.write_text(str(mock_input_content).replace("'", '"'))

    output_dir = tmp_path / "output"

    # Mock the file_io functions
    mock_save = mocker.patch('picto_indexer.file_io.save_final_artifacts')
    mock_progress = MagicMock()

    # --- Execution ---
    vectorizer_instance.run(input_file, output_dir, mock_progress)

    # --- Assertions ---

    # 1. Assert that the SBERT model's encode method was called
    vectorizer_instance.model.encode.assert_called_once()

    # 2. Check the content that was passed to the encode method
    call_args = vectorizer_instance.model.encode.call_args[0][0]
    assert len(call_args) == 2 # ongeldig-record should be skipped
    assert call_args[0] == "auto wassen. een auto wassen. auto schoonmaken"
    assert call_args[1] == "tanden poetsen. tanden poetsen. hygiëne badkamer"

    # 3. Assert that the save function was called
    mock_save.assert_called_once()

    # 4. Check the data that was passed to the save function
    save_args = mock_save.call_args[0]
    saved_data = save_args[0]
    saved_vectors = save_args[1]

    assert len(saved_data) == 2
    assert "auto wassen" in saved_data
    assert "ongeldig-record" not in saved_data
    assert saved_data["tanden poetsen"]["concept_nl"] == "tanden poetsen"

    assert isinstance(saved_vectors, np.ndarray)
    assert saved_vectors.shape == (2, 3)
    assert saved_vectors.dtype == 'float32'
