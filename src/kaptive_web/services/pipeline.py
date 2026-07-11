import asyncio
import dataclasses
from datetime import datetime
from pathlib import Path

import structlog
from kaptive.core.genome import GenomeAssembly
from orjson import OPT_SERIALIZE_NUMPY, dumps

from kaptive_web.core.config import settings
from kaptive_web.core.state import AppState
from kaptive_web.db.repository import Repository

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)


# Functions ------------------------------------------------------------------------------------------------------------
async def process_genomes(run_id: str, species: str, file_paths: list[Path]):
    """
    Background task to process a list of genome fasta files sequentially.
    """
    repo = Repository(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    
    try:
        await repo.update_run_status(run_id, "RUNNING")
        
        # Get the pipeline for the requested species
        pipeline_dict = AppState.get_serotypers(species)
        
        for file_path in file_paths:
            try:
                genome = await asyncio.to_thread(GenomeAssembly.from_file, file_path)
                
                # Remove the temporary UUID prefix from the genome ID
                if genome.id.startswith(f"{run_id}_"):
                    genome = dataclasses.replace(genome, id=genome.id[len(run_id)+1:])
                
                genome_results = {}
                for kwd, serotyper in pipeline_dict.items():
                    if result := await asyncio.to_thread(serotyper, genome):
                        genome_results[kwd] = result.to_dict()

                result_json = dumps(genome_results, option=OPT_SERIALIZE_NUMPY)
                completed_at = datetime.now().isoformat()
                await repo.add_run_result(run_id, genome.id, result_json, completed_at)
            finally:
                Path(file_path).unlink(missing_ok=True)
                
        # All completed
        await repo.update_run_status(run_id, "COMPLETED")

    except Exception as e:
        logger.exception(f"Pipeline failed for run {run_id}: {e}")
        await repo.update_run_status(run_id, "FAILED")
        # Ensure cleanup on failure
        for file_path in file_paths:
            Path(file_path).unlink(missing_ok=True)
