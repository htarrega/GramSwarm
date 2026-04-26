import os
import pathlib
import typer
from loguru import logger

from .core.reader import ProfileLoader
from .core.engine import SimulationEngine
from .providers.anthropic import AnthropicProvider
from .services.io import RunManager
from .services.analyzer import RunAnalyzer

app = typer.Typer(help="GramSwarm: Synthetic Alpha Readers for Novelists")

@app.command()
def run(
    chapter: pathlib.Path = typer.Argument(..., help="Path to the chapter or story text file"),
    chunk_size: int = typer.Option(500, help="Approximate word count per chunk"),
):
    """
    Simulates a panel of readers on a single chapter or story.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise typer.Exit(code=1)

    if not chapter.exists():
        logger.error(f"Chapter file not found: {chapter}")
        raise typer.Exit(code=1)

    # Setup
    loader = ProfileLoader()
    readers = loader.load_all()
    if not readers:
        logger.error("No reader profiles found in readers_profiles/")
        raise typer.Exit(code=1)

    run_manager = RunManager(chapter_name=chapter.stem)
    provider = AnthropicProvider(api_key=api_key)
    engine = SimulationEngine(provider, run_manager, chunk_size=chunk_size)

    # Execution
    logger.info(f"Starting simulation for {chapter.name} with {len(readers)} readers...")
    run_manager.save_meta({
        "chapter": chapter.name,
        "chunk_size": chunk_size,
        "reader_count": len(readers),
        "model": provider.model
    })

    try:
        engine.run(chapter, readers)
        logger.success(f"Simulation complete. Results saved to: {run_manager}")
    except Exception as e:
        logger.exception(f"Simulation failed: {e}")
        raise typer.Exit(code=1)

@app.command()
def analyze(
    run_dir: pathlib.Path = typer.Argument(..., help="Path to the run directory"),
):
    """
    Analyzes a run and prints the continue-pressure chart.
    """
    if not run_dir.is_dir():
        logger.error(f"Run directory not found: {run_dir}")
        raise typer.Exit(code=1)

    analyzer = RunAnalyzer(str(run_dir))
    data = analyzer.analyze_pressure()
    abandons = analyzer.analyze_abandons()
    cohesion = analyzer.analyze_cohesion()
    analyzer.render_ascii_chart(data, abandons)
    analyzer.render_cohesion_gauge(cohesion)

if __name__ == "__main__":
    app()
