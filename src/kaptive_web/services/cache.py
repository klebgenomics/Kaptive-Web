from pathlib import Path
from typing import Dict, Union
import os

from kaptive.database import Database, _DB_PATH, parse_database, parse_logic


class KaptiveDatabaseCache:
    """A global in-memory cache for Kaptive reference databases."""
    _cache: Dict[str, Database] = {}

    @classmethod
    def get_db(cls, db_path: Union[str, Path], gene_threshold: float = 90.0) -> Database:
        path_str = str(db_path)
        
        # Check if it's already in the cache
        if path_str in cls._cache:
            return cls._cache[path_str]
            
        path = Path(db_path)
        
        # If path doesn't exist directly, try resolving it relative to _DB_PATH
        if not path.is_absolute() and not path.exists():
            resolved_path = Path(_DB_PATH) / path
            if resolved_path.exists():
                path = resolved_path
        
        if not path.is_file():
            raise FileNotFoundError(f"Database file not found: {path}")
            
        db = Database(path.stem)
        
        for locus in parse_database(path): 
            db.add_locus(locus)
            
        logic_file = path.with_suffix('.logic')
        if logic_file.is_file(): 
            for i in parse_logic(logic_file):
                db.add_phenotype(*i)
                
        for n, locus in enumerate(db.loci.values()): 
            locus.index = n
            
        cls._cache[path_str] = db
        return db
