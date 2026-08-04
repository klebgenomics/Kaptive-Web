"""Pipeline services module."""

import asyncio
import dataclasses
from datetime import datetime

import structlog
from kaptive.core.genome import GenomeAssembly
from orjson import OPT_SERIALIZE_NUMPY, dumps

from kaptive_web.core.config import settings
from kaptive_web.core.state import AppState
from kaptive_web.db.repository import Repository

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)
_pipeline_lock: asyncio.Lock | None = None


def get_pipeline_lock() -> asyncio.Lock:
    """Get the pipeline concurrency lock."""
    global _pipeline_lock
    if _pipeline_lock is None:
        _pipeline_lock = asyncio.Lock()
    return _pipeline_lock


# Functions ------------------------------------------------------------------------------------------------------------
async def process_genomes(run_id: str, species: str, genomes: list[GenomeAssembly]) -> None:
    """Background task to process a list of genome assemblies sequentially."""
    repo = Repository(settings.database_url.replace("sqlite+aiosqlite:///", ""))

    try:
        await repo.update_run_status(run_id, "RUNNING")

        # Get the pipeline for the requested species
        pipeline_dict = AppState.get_serotypers(species)

        async def _process_single_genome(genome: GenomeAssembly) -> None:
            try:
                # Remove the temporary UUID prefix from the genome ID if it exists
                if genome.id.startswith(f"{run_id}_"):
                    genome = dataclasses.replace(genome, id=genome.id[len(run_id) + 1 :])

                genome_results = {}
                for kwd, serotyper in pipeline_dict.items():
                    async with get_pipeline_lock():
                        if result := await asyncio.to_thread(serotyper, genome):
                            genome_results[kwd] = result.to_dict()

                result_json = dumps(genome_results, option=OPT_SERIALIZE_NUMPY)
                completed_at = datetime.now().isoformat()
                await repo.add_run_result(run_id, genome.id, result_json, completed_at)
            except Exception as e:
                logger.exception(f"Failed to process genome {genome.id}: {e}")

        # Process all genomes in parallel, limited by semaphore
        await asyncio.gather(*[_process_single_genome(g) for g in genomes])

        # All completed
        await repo.update_run_status(run_id, "COMPLETED")

    except Exception as e:
        logger.exception(f"Pipeline failed for run {run_id}: {e}")
        await repo.update_run_status(run_id, "FAILED")
