# Picto Indexer - Refactored Design Protocol

## 1. Mandate

The previous implementation was a monolithic failure. It violated fundamental principles of software engineering, resulting in a brittle, inflexible, and untestable script.

This document outlines the **correct** architecture. Its purpose is to enforce discipline through a rigorous separation of concerns. The system will be rebuilt as a collection of specialized, single-purpose modules that collaborate to perform the indexing task.

This is not a suggestion. This is the required structure.

---

## 2. Core Principles

The new design will strictly adhere to the following principles:

-   **Single Responsibility Principle (SRP):** Each module and function will have one, and only one, reason to change.
-   **Separation of Concerns (SoC):** Logic for the user interface, API communication, and business rules will be completely isolated from one another.
-   **Dependency Inversion / Inversion of Control (IoC):** High-level modules will not depend on low-level modules. Dependencies will be injected. There will be **no global state**.
-   **Explicit Configuration:** All configurable parameters (paths, model names) will be provided externally via command-line arguments, not hardcoded.

---

## 3. New Project Structure

The single `build.py` will be dismantled. The new structure will be:

```
/picto/indexer/src/
└── picto_indexer/
    ├── __init__.py
    ├── cli.py           # Handles command-line interface and user interaction.
    ├── gemini_client.py # Handles all communication with the Google Gemini API.
    ├── enricher.py      # Contains the core business logic for the enrichment process.
    ├── file_io.py       # Handles reading images from and writing JSON to the filesystem.
    └── exceptions.py    # Defines custom, specific exceptions for the application.
```

The `pyproject.toml` entry point will be changed to point to a `main` function within `cli.py`.

---

## 4. Component Breakdown

### 4.1. `cli.py` - The Conductor

-   **Responsibility:** The user-facing entry point.
-   **Tasks:**
    -   Uses `argparse` to define and parse all command-line arguments: `--input-dir` (required), `--output-file` (required), and `--model` (optional).
    -   Initializes all other components (the clients, the enricher).
    -   Handles top-level orchestration:
        1.  Calls the `file_io` module to get the list of images.
        2.  Calls the `gemini_client` to select a model (if not provided by user).
        3.  Passes the image list and dependencies into the `enricher`.
        4.  Calls the `file_io` module to save the final data.
    -   Uses `rich` and `tqdm` to display progress and errors to the user.
    -   Catches all custom exceptions from the application and prints clear, user-friendly error messages.

### 4.2. `gemini_client.py` - The Specialist

-   **Responsibility:** To abstract all interactions with the Gemini API.
-   **Structure:**
    -   Will be a class, e.g., `GeminiClient`.
    -   The constructor `__init__` will take the `model_name` as an argument. It will not use a global variable.
    -   A method `discover_model()` will find the best available model (Flash first, then Pro).
    -   A method `get_enrichment(image: Image, prompt_text: str)` will perform the API call. It will contain the prompt string.
    -   It will handle API-specific logic like retries and exponential backoff.
    -   It will catch low-level API errors and raise a custom `APIError` from `exceptions.py`.

### 4.3. `enricher.py` - The Athlete

-   **Responsibility:** The core business logic of the application.
-   **Structure:**
    -   A primary function, e.g., `process_images(image_paths: list, client: GeminiClient)`.
    -   It takes the list of image paths and an *instance* of the `GeminiClient` as arguments (Dependency Injection).
    -   It contains the main loop that iterates through the images.
    -   For each image, it calls the `file_io` module to open it, then calls the `client.get_enrichment()` method.
    -   It assembles the final dictionary of pictogram data.
    -   It has no knowledge of the command line, the console, or the specific model name. It only knows its task.

### 4.4. `file_io.py` - The Ground Crew

-   **Responsibility:** All filesystem operations.
-   **Structure:**
    -   A function `find_image_files(directory: Path)` that takes a directory path and returns a list of `.png` files. It will raise a `FileSystemError` if the directory is not found.
    -   A function `read_image(path: Path)` that opens an image file.
    -   A function `write_index(data: dict, output_path: Path)` that saves the final dictionary to the specified JSON file. It will raise a `FileSystemError` on permission errors.

### 4.5. `exceptions.py` - The Rulebook

-   **Responsibility:** To define the controlled failure states of the application.
-   **Content:**
    -   `class PictoIndexerError(Exception): pass` (a base exception for all application errors)
    -   `class APIError(PictoIndexerError): pass`
    -   `class FileSystemError(PictoIndexerError): pass`
    -   `class ConfigurationError(PictoIndexerError): pass`

---

## 5. Data Flow (The Routine)

1.  User executes `build-picto-index --input-dir ./img/nl --output-file ./index.json`.
2.  `cli.main()` is called. It parses the arguments.
3.  `cli` creates an instance of `GeminiClient`, either with the user's model or by calling `GeminiClient.discover_model()`.
4.  `cli` calls `file_io.find_image_files()` with the input directory.
5.  `cli` calls `enricher.process_images()`, passing the list of files and the `GeminiClient` instance.
6.  `enricher` loops, calling `file_io.read_image()` and `client.get_enrichment()` for each file.
7.  `enricher` returns the completed data dictionary to `cli`.
8.  `cli` calls `file_io.write_index()` with the data and output path.
9.  If any step fails, a specific exception is raised and caught in `cli`, which prints a precise error message.

This design is not optional. It is the required path to a robust, maintainable, and professional tool. It is the routine you will now practice until it is perfect.
