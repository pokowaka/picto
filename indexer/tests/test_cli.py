import pytest
from unittest.mock import patch
from pathlib import Path

from picto_indexer import cli

def test_cli_enrich_command(mocker):
    """Tests that the 'enrich' subcommand calls the Enricher with the correct arguments."""
    mock_enricher_class = mocker.patch('picto_indexer.enricher.Enricher')
    mock_instance = mock_enricher_class.return_value

    with patch('sys.argv', ['build-picto-index', 'enrich', '--image-dir', '/tmp/images', '--output-file', '/tmp/db.json', '--model', 'test-model']):
        cli.main()

    # Assert that an Enricher was instantiated with the correct model
    mock_enricher_class.assert_called_once_with(model_name='test-model')
    
    # Assert that the run method was called with the correct, resolved paths
    run_args = mock_instance.run.call_args[0]
    expected_image_dir = Path('/tmp/images').resolve()
    assert run_args[0] == expected_image_dir
    expected_output_file = Path('/tmp/db.json').resolve()
    assert run_args[1] == expected_output_file

def test_cli_vectorize_command(mocker):
    """Tests that the 'vectorize' subcommand calls the Vectorizer with the correct arguments."""
    mock_vectorizer_class = mocker.patch('picto_indexer.vectorizer.Vectorizer')
    mock_instance = mock_vectorizer_class.return_value

    with patch('sys.argv', ['build-picto-index', 'vectorize', '--input-file', '/tmp/db.json', '--output-dir', '/tmp/output']):
        cli.main()

    # Assert that a Vectorizer was instantiated
    mock_vectorizer_class.assert_called_once()

    # Assert that the run method was called with the correct, resolved paths
    run_args = mock_instance.run.call_args[0]
    expected_input_file = Path('/tmp/db.json').resolve()
    expected_output_dir = Path('/tmp/output').resolve()
    assert run_args[0] == expected_input_file
    assert run_args[1] == expected_output_dir

def test_cli_run_command(mocker):
    """Tests that the 'run' subcommand calls both the Enricher and Vectorizer."""
    mock_enricher_class = mocker.patch('picto_indexer.enricher.Enricher')
    mock_vectorizer_class = mocker.patch('picto_indexer.vectorizer.Vectorizer')
    
    mock_enricher_instance = mock_enricher_class.return_value
    mock_vectorizer_instance = mock_vectorizer_class.return_value

    with patch('sys.argv', [
        'build-picto-index', 'run',
        '--image-dir', '/tmp/images',
        '--raw-output-file', '/tmp/db.json',
        '--final-output-dir', '/tmp/output'
    ]):
        cli.main()

    # Assert that both classes were instantiated and their run methods were called
    mock_enricher_class.assert_called_once()
    mock_enricher_instance.run.assert_called_once()
    
    mock_vectorizer_class.assert_called_once()
    mock_vectorizer_instance.run.assert_called_once()

    # Check that the output of the enricher is the input of the vectorizer
    enricher_output_path = mock_enricher_instance.run.call_args[0][1]
    vectorizer_input_path = mock_vectorizer_instance.run.call_args[0][0]
    assert enricher_output_path == vectorizer_input_path
    expected_path = Path('/tmp/db.json').resolve()
    assert vectorizer_input_path == expected_path
