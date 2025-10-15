# Picto Indexer - Design Document

This document outlines the design for the `indexer` subproject. Its sole purpose is to scan the pictogram image directories, enrich the data using the Google Gemini API's **multimodal capabilities**, and produce a structured `pictogram_index.json` file in the project's root directory.

This will be a modern, installable Python package managed with `pyproject.toml`.

---

## 1. Project Structure

The `indexer` directory will be structured as a standard Python package. This allows for clean dependency management and makes the tool easy to run via a command-line script.

```
/picto/
├── indexer/
│   ├── pyproject.toml
│   └── src/
│       └── picto_indexer/
│           ├── __init__.py
│           └── build.py
│
└── img/
    └── nl/
        └── ...
```

- **`pyproject.toml`**: Defines project metadata, dependencies, and the command-line entry point.
- **`src/picto_indexer/`**: The source code for our installable package.
  - **`build.py`**: The main script containing all logic for scanning files, **reading image data**, calling the AI, and writing the output.

---

## 2. Dependency and Package Management (`pyproject.toml`)

We will use a `pyproject.toml` file to define the project. This is the modern standard for Python packaging.

**`pyproject.toml` Content:**

```toml
[project]
name = "picto-indexer"
version = "0.1.0"
description = "A tool to scan and enrich pictograms using an AI."
dependencies = [
    "google-generativeai",
    "tqdm",
    "rich",
    "Pillow"
]

[project.scripts]
build-picto-index = "picto_indexer.build:main"
```

- **Dependencies:**
  - `google-generativeai`: The official SDK for the Gemini API.
  - `tqdm`: To provide a progress bar during the indexing process.
  - `rich`: For clean and readable console output.
  - **`Pillow`**: The Python Imaging Library, required for opening and handling image data to pass to the Gemini API.
- **`[project.scripts]`**: This section creates a command-line tool. After installing the package, we can simply run `build-picto-index` from the terminal to execute the `main` function in our `build.py` script.

---

## 3. Indexing Workflow (`build.py`)

The `build.py` script will be the heart of the indexer.

**1. Configuration:**
   - Constants will be defined at the top of the file for input directory (`img/nl`), output file (`pictogram_index.json` in the project root), and a list of sample files to process.

**2. Core Functions:**
   - **`get_gemini_enrichment(text_prompt: str, image: Image) -> dict | None`**:
     - Takes a Dutch phrase (from the filename) and a Pillow `Image` object as input.
     - **Constructs a multimodal prompt:** This will be a list containing both the text instructions and the image object.
     - Handles the API call to a multimodal model (Gemini 1.5 Flash), including error handling.
     - Uses the `rich` library to print clean error messages.
     - Returns a dictionary with the enriched data or `None` on failure.
   - **`main()`**:
     - This is the main entry point for the script.
     - It will use `pathlib` to locate the source image directory and the root directory for the output file.
     - It will iterate through the configured list of sample pictogram files.
     - For each file:
       - It will **open the image file using Pillow**.
       - It will extract the base text from the filename.
       - It will call `get_gemini_enrichment()` with both the text and the image object.
     - It will use `tqdm` to show a progress bar for the loop.
     - It will assemble the final list of enriched pictogram objects.
     - Finally, it will write the complete list to `pictogram_index.json` in the project root.

**3. AI Prompt Design (Multimodal):**
   - The prompt will be engineered to instruct the AI to analyze the visual content of the image first and foremost, using the filename as a contextual hint.

   **Example Multimodal Prompt:**
   ```python
   # This is a conceptual example of the list passed to the API
   [
       """
       You are an expert data enricher for a pictogram system. Your task is to analyze the provided image and generate metadata for it. The image's filename, which is "{base_text}", is a hint in Dutch for the primary action depicted.

       Return a single, minified JSON object (no newlines) with the following exact structure:
       - "translations": An object with keys for "en", "fr", and "de".
       - "tags": An array of 5-7 relevant English keywords, in lowercase, that categorize the action.
       - "description": A concise, objective sentence in English describing the action shown in the pictogram.
       """,
       image_object  # The actual Pillow Image object
   ]
   ```

---

## 4. Usage

To run the indexer:

1.  **Navigate to the directory:**
    ```bash
    cd /path/to/picto/indexer
    ```
2.  **Install the package (or update):**
    ```bash
    pip install -e .
    ```
3.  **Set the API Key:**
    ```bash
    export GEMINI_API_KEY="your_api_key_here"
    ```
4.  **Run the indexer:**
    - **To use auto-discovery (recommended):**
      ```bash
      build-picto-index
      ```
    - **To specify a model (e.g., for cost savings):**
      Use the `--model` flag.
      ```bash
      build-picto-index --model models/gemini-1.5-flash-latest
      ```

This revised design ensures the AI's analysis is based on the actual visual data, leading to a much more accurate and powerful indexing system.
