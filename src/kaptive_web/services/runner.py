from sqlalchemy.orm import Session
from datetime import datetime
import os
import logging
from typing import Dict, List, Any

from kaptive_web.models.database import Job
from kaptive.assembly import Assembly
from kaptive.typing import typing_pipeline

from kaptive_web.services.cache import KaptiveDatabaseCache

logger = logging.getLogger(__name__)


class KaptiveRunner:
    def __init__(self, db_session: Session, job_id: str):
        self.db = db_session
        self.job_id = job_id
        self.job = self.db.query(Job).filter(Job.id == self.job_id).first()

    def set_status(self, status: str, error: str = None, results: dict = None):
        """Helper to safely update database state."""
        self.job.status = status
        if error:
            self.job.error_message = error
        if results is not None:
            self.job.results = results

        if status in ["Finished", "Failed"]:
            self.job.finish_time = datetime.utcnow()

        self.db.commit()


    def execute(self, assembly_paths: list[str], databases_to_run: dict[str, str],
                min_cov: float = 90.0, percent_expected: float = 100.0, max_other_genes: int = 0):

        self.set_status("Running")
        grouped_results: Dict[str, List[Dict[str, Any]]] = {db_name: [] for db_name in databases_to_run.keys()}

        try:
            # 1. Pre-load all assemblies into memory ONCE for this specific job
            loaded_assemblies = {}
            for path in assembly_paths:
                # Load it as an Assembly object right off the bat
                loaded_assemblies[path] = Assembly(path)

            # 2. Loop through the requested databases
            for db_name, db_path in databases_to_run.items():
                try:
                    # Fetch the pre-loaded global database object from RAM (Zero disk I/O!)
                    kaptive_db = KaptiveDatabaseCache.get_db(db_path, gene_threshold=min_cov)

                    # 3. Loop through our already-in-memory assemblies
                    for path, assembly_obj in loaded_assemblies.items():
                        try:
                            result = typing_pipeline(
                                assembly=assembly_obj,
                                db=kaptive_db,
                                threads=1,
                                min_cov=min_cov,
                                percent_expected_genes=percent_expected,
                                max_other_genes=max_other_genes,
                                score_metric=0,
                                weight_metric=3
                            )

                            if result:
                                grouped_results[db_name].append({
                                    "sample_name": os.path.basename(path),
                                    "best_match": result.best_match.name if result.best_match else "None",
                                    "confidence": result.match_confidence,
                                    "coverage": round(result.locus_coverage, 2),
                                    "identity": round(result.locus_identity, 2)
                                })
                        except Exception as alignment_err:
                            logger.error(f"Error during alignment ingestion for {path}: {alignment_err}")
                except Exception as db_err:
                    logger.error(f"Error processing database {db_name} gracefully continuing: {db_err}")

            self.set_status("Finished", results=grouped_results)

        except Exception as e:
            logger.exception("Job failed unexpectedly")
            self.set_status("Failed", error=str(e))
