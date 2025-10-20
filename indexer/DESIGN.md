# DESIGN: Picto Indexer (V0.3)

## 1. Overview

This document outlines the technical design for the Picto Indexer, a command-line tool responsible for processing raw pictogram images, enriching them with AI-generated metadata, and creating a searchable vector index. This tool is a prerequisite for the main `picto-backend` service.

## 2. System Architecture



The indexer is a standalone Python application. It does not run as a service but as a CLI tool that is executed manually or as part of a build script. Its primary purpose is to generate the data artifacts required by the backend.



The architecture is a two-stage pipeline:



1.  **Enrichment:** Uses a multimodal generative AI (Gemini) to analyze images and generate descriptive metadata (tags, descriptions).

2.  **Vectorization:** Uses a Sentence Transformer (SBERT) model to convert the textual metadata into vector embeddings and builds a **ChromaDB** index for efficient similarity search.



```

+------------------+     +----------------------+     +---------------------+

| .png Image Files |---->|   Stage 1: Enricher  |---->|  Raw Data (db.json) |

+------------------+     |     (Gemini API)     |     +---------------------+

                         +----------------------+

                                                            |

                                                            |

                                                            v

                         +------------------------+   +-------------------------+

                         | Stage 2: Vectorizer    |   |   Final Artifacts       |

                         | (SBERT / ChromaDB)     |-->| - pictogram_data.json |

                         +------------------------+   | - chroma_db/ (dir)    |

                                                      +-------------------------+

```



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

    3.  **Clean & Combine Text:** For each pictogram, it creates a composite `embedding_text` by cleaning (lowercase, remove numbers and special characters) and combining the `concept_nl`, `description_nl`, and `tags_nl` fields into a structured string: `f"Concept: {concept_nl}. Description: {description_nl}. Tags: {tags_nl}"`.

    4.  **Generate Vectors:**

        *   Loads the SBERT model using `sentence_transformers.SentenceTransformer('all-mpnet-base-v2')`.

        *   Encodes the list of `embedding_text` strings into a list of 768-dimension vectors. The output is a `numpy.ndarray`.

    5.  **Build & Save Index:**

        *   Initializes a `chromadb.PersistentClient` pointing to the output directory.

        *   Creates (or gets) a collection named "pictograms".

        *   Adds the vectors, their corresponding pictogram IDs, and the cleaned metadata to the collection in batches.

-   **Output:** Two artifacts:

    1.  `pictogram_data.json`: The cleaned, transformed metadata.

    2.  `chroma_db/`: A directory containing the ChromaDB vector index.



---



## 4. Usage



The command-line interface is designed for flexibility, allowing the user to run each stage of the pipeline independently or sequentially. All file paths provided by the user will be resolved to absolute paths internally to ensure reliability.



### 4.1. Subcommand Structure



The tool uses three subcommands:



*   `enrich`: Runs only the Gemini data enrichment stage.

*   `vectorize`: Runs only the SBERT/ChromaDB vectorization stage.

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