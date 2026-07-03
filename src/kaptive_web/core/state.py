from kaptive.db import Database, DatabaseManager
from kaptive.serotyping import Serotyper, ConfidenceEvaluator
from kaptive_web.core.config import settings

class AppState:
    def __init__(self):
        # We store shared Database objects grouped by organism.
        # Example: self.databases["Klebsiella pneumoniae Species Complex"]["kpsc_k"] = Database(...)
        self.databases: dict[str, dict[str, Database]] = {}
        # We store serotyper pipelines grouped by organism.
        self.pipelines: dict[str, dict[str, Serotyper]] = {}
        # Evaluators per organism
        self.evaluators: dict[str, ConfidenceEvaluator] = {}

    def init_all(self):
        """Discovers and initializes all installed databases."""
        installed_kwds = DatabaseManager.installed()
        print(f"Found {len(installed_kwds)} installed databases.")
        
        for kwd in installed_kwds:
            try:
                db = DatabaseManager.load(kwd)
                organism = db.metadata.organism
                
                # Initialize organism dictionaries if they don't exist
                if organism not in self.databases:
                    self.databases[organism] = {}
                    self.pipelines[organism] = {}
                    self.evaluators[organism] = ConfidenceEvaluator()
                
                # Cache the database and its initialized Serotyper instance
                self.databases[organism][kwd] = db
                self.pipelines[organism][kwd] = Serotyper(db, max_workers=settings.max_pipeline_workers)
                print(f"Initialized pipeline for {organism}: {kwd}")
                
            except Exception as e:
                print(f"Failed to load database {kwd}: {e}")

    def get_pipeline(self, species: str) -> dict[str, Serotyper]:
        """Returns the serotyper instances for the requested species."""
        if species not in self.pipelines:
            raise KeyError(f"No pipeline initialized for species: {species}")
        return self.pipelines[species]

    def get_evaluator(self, species: str) -> ConfidenceEvaluator:
        if species not in self.evaluators:
            raise KeyError(f"No evaluator initialized for species: {species}")
        return self.evaluators[species]

state = AppState()
