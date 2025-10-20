# Picto Indexer - Design Document (V3)

This document outlines the expanded design for the `indexer` subproject. Its purpose is now twofold:
1.  To scan pictogram image directories and **enrich** the data using the Google Gemini API's multimodal capabilities.
2.  To process this enriched data, **vectorize** it using a Sentence-BERT (SBERT) model, and produce a FAISS index for semantic search.

The indexer is the sole tool responsible for the entire data preparation pipeline, creating the final artifacts required by the backend service.

---

## 1. Project Structure

The project will use a modular structure to separate concerns. The `cli.py` module will act as the main entry point, dispatching tasks to the other modules.

```
/picto/
├── indexer/
│   ├── pyproject.toml
│   └── src/
│       └── picto_indexer/
│           ├── __init__.py
│           ├── cli.py           # Main entry point, handles subcommands (enrich, vectorize, run)
│           ├── enricher.py      # Logic for Gemini API calls
│           ├── vectorizer.py    # Logic for SBERT/FAISS index generation
│           └── file_io.py       # Utilities for reading/writing files
│
└── ...
```

---

## 2. Dependency and Package Management (`pyproject.toml`)

The dependencies will be updated to include the libraries required for vectorization.

**`pyproject.toml` Content:**

```toml
[project]
name = "picto-indexer"
version = "0.3.0"
description = "A tool to enrich pictograms and build a vector search index."
dependencies = [
    "google-generativeai",
    "tqdm",
    "rich",
    "Pillow",
    "sentence-transformers",
    "faiss-cpu",
    "numpy"
]

[project.scripts]
build-picto-index = "picto_indexer.cli:main"
```

- **New/Specified Dependencies:**
  - `sentence-transformers`: For loading SBERT models and encoding text.
  - `faiss-cpu`: For creating and saving the FAISS vector index.
  - `numpy`: A core dependency for `faiss-cpu`, used for handling the vector arrays.

---

## 3. Indexing Workflow

The `indexer` operates as a two-stage pipeline. The CLI provides the flexibility to run each stage independently or both in sequence.

### Stage 1: Enrichment

-   **Responsibility:** Generate AI-enriched data from raw images.
-   **Module:** `enricher.py`
-   **Input:** A directory of `.png` image files.
-   **Process:**
    1.  Scans the input directory for images that are not already present in the output file (resumable).
    2.  For each new image, it uses a multimodal call to the Gemini API.
-   **Output:** A single JSON file (`db.json` by default) containing the raw enriched data.

### Stage 2: Vectorization

-   **Responsibility:** Transform the raw data into final, searchable artifacts.
-   **Module:** `vectorizer.py`
-   **Input:** The raw enriched JSON file from Stage 1.
-   **Process & Technical Details:**
    1.  **Load & Validate Data:** Reads the raw JSON data. Each record is validated to ensure it contains the required fields (e.g., `description`, `tags`) before processing. Malformed records are skipped and reported to the user.
    2.  **Transform Schema:** Transforms the schema to match the `PM.md` specification (adding `id`, `concept_nl`, etc.).
    3.  **Clean & Combine Text:** For each pictogram, it creates a composite `embedding_text` by cleaning (lowercase, remove special characters) and combining the `concept_nl`, `description_nl`, and `tags_nl` fields.
    4.  **Generate Vectors:**
        *   Loads the SBERT model using `sentence_transformers.SentenceTransformer('distiluse-base-multilingual-cased-v1')`.
        *   Encodes the list of `embedding_text` strings into a list of 512-dimension vectors. The output is a `numpy.ndarray`.
    5.  **Build & Save Index:**
        *   Initializes a FAISS index using `faiss.IndexFlatL2(d)`, where `d` is the vector dimension (512). This index performs an exact, exhaustive search.
        *   Adds the `numpy` array of vectors to the index.
        *   Serializes and saves the index to a binary file using `faiss.write_index()`.
-   **Output:** Two artifact files:
    1.  `pictogram_data.json`: The cleaned, transformed metadata.
    2.  `faiss_index.bin`: The binary FAISS index file.

---

## 4. Usage

The command-line interface is designed for flexibility, allowing the user to run each stage of the pipeline independently or sequentially. All file paths provided by the user will be resolved to absolute paths internally to ensure reliability.

### 4.1. Subcommand Structure

The tool uses three subcommands:

*   `enrich`: Runs only the Gemini data enrichment stage.
*   `vectorize`: Runs only the SBERT/FAISS vectorization stage.
*   `run`: Runs the full pipeline (enrich then vectorize) in a single command.

### 4.2. Examples

**1. Run only the enrichment stage:**
(Useful for the initial, expensive API calls)
```bash
build-picto-index enrich \
  --image-dir ../img/nl \
  --output-file ./db.json
```

**2. Run only the vectorization stage:**
(Useful for re-generating the index with a new model or logic without re-running enrichment)
```bash
build-picto-index vectorize \
  --input-file ./db.json \
  --output-dir ../backend/data
```

**3. Run the full, end-to-end pipeline:**
(Convenience command for the most common use case)
```bash
build-picto-index run \
  --image-dir ../img/nl \
  --raw-output-file ./db.json \
  --final-output-dir ../backend/data
```
This revised command structure provides the necessary flexibility for both development and production workflows, addressing the need to run stages independently for experimentation, debugging, or recovery.
