"""
The command-line interface for the Picto Indexer.
"""
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from . import enricher, vectorizer
from . import file_io
# from .exceptions import PictoIndexerError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log = logging.getLogger(__name__)

def main():
    """Main entry point for the command-line script."""
    parser = argparse.ArgumentParser(description="A tool to enrich pictograms and build a vector search index.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Enrich Command ---
    parser_enrich = subparsers.add_parser("enrich", help="Run only the Gemini data enrichment stage.")
    parser_enrich.add_argument("--image-dir", type=Path, required=True, help="Source directory of pictogram images.")
    parser_enrich.add_argument("--output-file", type=Path, required=True, help="File to store the raw Gemini enrichment data.")
    parser_enrich.add_argument("--model", type=str, help="Specify the Gemini model to use (e.g., 'models/gemini-1.5-flash-latest').")

    # --- Vectorize Command ---
    parser_vectorize = subparsers.add_parser("vectorize", help="Run only the SBERT/FAISS vectorization stage.")
    parser_vectorize.add_argument("--input-file", type=Path, required=True, help="The raw enrichment data file.")
    parser_vectorize.add_argument("--output-dir", type=Path, required=True, help="Destination directory for the final artifacts.")

    # --- Run Command ---
    parser_run = subparsers.add_parser("run", help="Run the full pipeline (enrich then vectorize).")
    parser_run.add_argument("--image-dir", type=Path, required=True, help="Source directory of pictogram images.")
    parser_run.add_argument("--raw-output-file", type=Path, required=True, help="File to store the raw Gemini enrichment data.")
    parser_run.add_argument("--final-output-dir", type=Path, required=True, help="Destination directory for the final artifacts.")
    parser_run.add_argument("--model", type=str, help="Specify the Gemini model to use (e.g., 'models/gemini-1.5-flash-latest').")

    args = parser.parse_args()
    console = Console()
    console.rule(f"[bold green]Picto Indexer: '{args.command}' command[/bold green]")

    try:
        # Resolve paths to be absolute for robustness
        if hasattr(args, "image_dir"): args.image_dir = args.image_dir.resolve()
        if hasattr(args, "output_file"): args.output_file = args.output_file.resolve()
        if hasattr(args, "input_file"): args.input_file = args.input_file.resolve()
        if hasattr(args, "output_dir"): args.output_dir = args.output_dir.resolve()
        if hasattr(args, "raw_output_file"): args.raw_output_file = args.raw_output_file.resolve()
        if hasattr(args, "final_output_dir"): args.final_output_dir = args.final_output_dir.resolve()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}% ({task.completed}/{task.total})"),
            console=console,
        ) as progress:

            if args.command == "enrich":
                e = enricher.Enricher(model_name=args.model)
                e.run(args.image_dir, args.output_file, progress)
            
            elif args.command == "vectorize":
                v = vectorizer.Vectorizer()
                v.run(args.input_file, args.output_dir, progress)

            elif args.command == "run":
                console.log("[bold]Stage 1: Enrichment[/bold]")
                e = enricher.Enricher(model_name=args.model)
                e.run(args.image_dir, args.raw_output_file, progress)
                
                console.log("\n[bold]Stage 2: Vectorization[/bold]")
                v = vectorizer.Vectorizer()
                v.run(args.raw_output_file, args.final_output_dir, progress)
        
        console.print(f"\n[bold green]Command '{args.command}' completed successfully![/bold green]")

    except Exception as e:
        log.critical("An unexpected error occurred: %s", e, exc_info=True)
        console.print(f"\n[bold red]An unexpected error occurred:[/bold red] {e}")
        exit(1)

if __name__ == "__main__":
    main()