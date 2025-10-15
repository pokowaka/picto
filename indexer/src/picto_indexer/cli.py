"""
The command-line interface for the Picto Indexer.
"""
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from . import gemini_client, file_io, enricher, logger
from .exceptions import PictoIndexerError

# Get a logger for this module
log = logging.getLogger(__name__)

def main():
    """Main entry point for the command-line script."""
    
    parser = argparse.ArgumentParser(description="Build a pictogram index using the Gemini AI.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="The directory containing the pictogram .png files."
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        required=True,
        help="The path to the output JSON index file."
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specify the Gemini model to use (e.g., 'models/gemini-1.5-flash-latest'). If not provided, a suitable model will be auto-discovered."
    )
    args = parser.parse_args()
    
    logger.setup_logging()
    console = Console()
    console.rule("[bold green]Picto Indexer (Resumable)[/bold green]")

    try:
        # --- Configuration and Setup ---
        gemini_client.GeminiClient.configure_api()

        if args.model:
            log.info("User specified model: %s", args.model)
            model_name = args.model
        else:
            log.info("No model specified. Discovering available models...")
            model_name = gemini_client.GeminiClient.discover_model()
        
        console.log(f"Using model: [bold green]{model_name}[/bold green]")
        client = gemini_client.GeminiClient(model_name=model_name)

        # --- Load existing data and determine work to be done ---
        existing_data = file_io.load_index(args.output_file)
        all_image_paths = file_io.find_image_files(args.input_dir)
        
        images_to_process = [
            p for p in all_image_paths if p.stem not in existing_data
        ]

        console.log(f"Found {len(all_image_paths)} total images.")
        console.log(f"{len(existing_data)} images are already indexed.")
        
        if not images_to_process:
            console.log("[bold green]No new images to process. Index is up to date.[/bold green]")
            return
            
        console.log(f"Processing {len(images_to_process)} new images...")

        # --- Main Processing Loop ---
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}% ({task.completed}/{task.total})"),
            console=console,
        ) as progress:
            task = progress.add_task("Enriching...", total=len(images_to_process))
            
            for image_path in images_to_process:
                result = enricher.enrich_image(image_path, client)
                if result:
                    base_text, picto_entry = result
                    existing_data[base_text] = picto_entry
                    # Save after each successful enrichment
                    file_io.write_index(existing_data, args.output_file)
                    log.info("Successfully processed and saved '%s'.", base_text)
                
                progress.update(task, advance=1)

        console.print(f"\n[bold green]Success![/bold green] Index updated and saved to [cyan]{args.output_file}[/cyan]")

    except PictoIndexerError as e:
        log.error("A known error occurred: %s", e, exc_info=True)
        console.print(f"\n[bold red]An error occurred:[/bold red] {e}")
        exit(1)
    except Exception as e:
        log.critical("An unexpected error occurred: %s", e, exc_info=True)
        console.print(f"\n[bold red]An unexpected error occurred:[/bold red] {e}")
        exit(1)

if __name__ == "__main__":
    main()
