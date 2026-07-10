import structlog
from kaptive.db import Database, DatabaseManager
from kaptive.serotyping import Serotyper

from kaptive_web.core.config import settings

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)


# Classes --------------------------------------------------------------------------------------------------------------
class AppState:
    # We store shared Database objects grouped by organism.
    # Example: self.databases["Klebsiella pneumoniae Species Complex"]["kpsc_k"] = Database(...)
    databases: dict[str, dict[str, Database]] = {}
    # We store serotyper pipelines grouped by organism.
    serotypers: dict[str, dict[str, Serotyper]] = {}
    
    @classmethod
    def load_databases(cls) -> None:
        """Discovers and initializes all installed databases."""
        logger.info("Discovering and loading databases into memory...")
        installed_kwds = DatabaseManager.installed()
        logger.info(f"Found {len(installed_kwds)} installed databases.")

        for kwd in installed_kwds:
            try:
                db = DatabaseManager.load(kwd)
                organism = db.metadata.organism
                # Initialize organism dictionaries if they don't exist
                if organism not in cls.databases:
                    cls.databases[organism] = {}
                    cls.serotypers[organism] = {}
                # Cache the database and its initialized Serotyper instance
                cls.databases[organism][kwd] = db
                cls.serotypers[organism][kwd] = Serotyper(db, max_workers=settings.max_pipeline_workers)
                logger.info(f"Initialized Serotyper for {organism}: {kwd}")

            except Exception as e:
                logger.exception(f"Failed to load database {kwd}: {e}")

        logger.info("Initialization complete.")

    @classmethod
    def get_serotypers(cls, species: str) -> dict[str, Serotyper]:
        """Returns the serotyper instances for the requested species."""
        if species not in cls.serotypers:
            raise KeyError(f"No Serotypers initialized for species: {species}")
        return cls.serotypers[species]

