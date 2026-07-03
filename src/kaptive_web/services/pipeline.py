import asyncio
import os
import orjson
from pathlib import Path
from typing import List

from kaptive.core.genome import GenomeAssembly
from kaptive_web.core.state import state
from kaptive_web.db.repository import Repository
from kaptive_web.core.config import settings

async def process_genomes(run_id: str, species: str, file_paths: List[str]):
    """
    Background task to process a list of genome fasta files sequentially.
    """
    repo = Repository(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    
    try:
        await repo.update_run_status(run_id, "RUNNING")
        
        # Get the pipeline and evaluator for the requested species
        pipeline_dict = state.get_pipeline(species)
        evaluator = state.get_evaluator(species)
        
        for file_path in file_paths:
            try:
                assembly = await asyncio.to_thread(GenomeAssembly.from_file, file_path)
                
                # Remove the temporary UUID prefix from the genome ID
                import dataclasses
                if assembly.id.startswith(f"{run_id}_"):
                    assembly = dataclasses.replace(assembly, id=assembly.id[len(run_id)+1:])
                
                genome_results = {}
                for kwd, serotyper in pipeline_dict.items():
                    result = await asyncio.to_thread(serotyper, assembly)
                    if result:
                        is_typeable = evaluator(result)
                        result_dict = result.to_dict()
                        result_dict["is_typeable"] = is_typeable
                        genome_results[kwd] = result_dict
    
                from datetime import datetime
                completed_at = datetime.utcnow().isoformat()
                result_json = orjson.dumps(genome_results, option=orjson.OPT_SERIALIZE_NUMPY).decode("utf-8")
                await repo.add_run_result(run_id, assembly.id, result_json, completed_at)
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                
        # All completed
        await repo.update_run_status(run_id, "COMPLETED")
    except Exception as e:
        import traceback
        traceback.print_exc()
        # In a real app we'd log the exception properly
        await repo.update_run_status(run_id, "FAILED")
        # Ensure cleanup on failure
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except OSError:
                pass
