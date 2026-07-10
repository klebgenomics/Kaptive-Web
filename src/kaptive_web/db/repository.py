import structlog
import uuid
from dataclasses import dataclass
from datetime import datetime

import aiosqlite

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)


# Models ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class User:
    id: str # Github ID or custom UUID
    api_key: str

@dataclass(frozen=True, slots=True)
class Run:
    id: str
    user_id: str
    species: str
    status: str
    created_at: str
    total_genomes: int
    name: str | None = None

@dataclass(frozen=True, slots=True)
class RunResult:
    id: int
    run_id: str
    genome_id: str
    results_json: bytes
    completed_at: str


# Classes --------------------------------------------------------------------------------------------------------------
class Repository:
    _db: aiosqlite.Connection | None = None

    @staticmethod
    def _map_run(row: aiosqlite.Row) -> Run:
        return Run(
            row['id'], row['user_id'], row['species'], row['status'], 
            row['created_at'], row['total_genomes'], row['name']
        )

    @staticmethod
    def _map_result(row: aiosqlite.Row) -> RunResult:
        return RunResult(
            row['id'], row['run_id'], row['genome_id'],
            row['results_json'] if isinstance(row['results_json'], bytes) else row['results_json'].encode('utf-8'),
            row['completed_at']
        )

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database connection is not initialized. Call Repository.connect() first.")
        return self._db

    @classmethod
    async def connect(cls, db_path: str):
        if cls._db is None:
            cls._db = await aiosqlite.connect(db_path)
            await cls._db.execute("PRAGMA journal_mode=WAL;")
            await cls._db.execute("PRAGMA synchronous=NORMAL;")
            cls._db.row_factory = aiosqlite.Row

    @classmethod
    async def close(cls):
        if cls._db:
            await cls._db.close()
            cls._db = None

    async def init_db(self):
        db = self.db
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                species TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                total_genomes INTEGER DEFAULT 0,
                name TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS run_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                genome_id TEXT NOT NULL,
                results_json BLOB NOT NULL,
                completed_at TIMESTAMP NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
        ''')
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_runs_user_id ON runs(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_run_results_run_id ON run_results(run_id)")
        await db.commit()

    async def create_user(self, user_id: str, api_key: str) -> User:
        await self.db.execute(
            "INSERT INTO users (id, api_key) VALUES (?, ?)",
            (user_id, api_key)
        )
        await self.db.commit()
        return User(user_id, api_key)

    async def get_user_by_id(self, user_id: str) -> User | None:
        async with self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(row['id'], row['api_key'])
            return None

    async def get_user_by_api_key(self, api_key: str) -> User | None:
        async with self.db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(row['id'], row['api_key'])
            return None

    async def delete_user_cascade(self, user_id: str):
        # Delete run results
        await self.db.execute('''
            DELETE FROM run_results 
            WHERE run_id IN (SELECT id FROM runs WHERE user_id = ?)
        ''', (user_id,))
        
        # Delete runs
        await self.db.execute("DELETE FROM runs WHERE user_id = ?", (user_id,))
        
        # Delete user
        await self.db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await self.db.commit()

    async def get_all_users(self) -> list[User]:
        async with self.db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [User(row['id'], row['api_key']) for row in rows]

    async def create_run(self, user_id: str, species: str, total_genomes: int, name: str | None = None) -> Run:
        run_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        status = "PENDING"
        await self.db.execute(
            "INSERT INTO runs (id, user_id, species, status, created_at, total_genomes, name) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, user_id, species, status, created_at, total_genomes, name)
        )
        await self.db.commit()
        return Run(run_id, user_id, species, status, created_at, total_genomes, name)

    async def update_run_status(self, run_id: str, status: str):
        await self.db.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))
        await self.db.commit()

    async def get_run(self, run_id: str) -> Run | None:
        async with self.db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._map_run(row)
            return None

    async def get_runs_for_user(self, user_id: str) -> list[Run]:
        async with self.db.execute("SELECT * FROM runs WHERE user_id = ? ORDER BY created_at DESC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [self._map_run(row) for row in rows]

    async def add_run_result(self, run_id: str, genome_id: str, results_json: bytes, completed_at: str):
        await self.db.execute(
            "INSERT INTO run_results (run_id, genome_id, results_json, completed_at) VALUES (?, ?, ?, ?)",
            (run_id, genome_id, results_json, completed_at)
        )
        await self.db.commit()

    async def get_run_results(self, run_id: str) -> list[RunResult]:
        async with self.db.execute("SELECT * FROM run_results WHERE run_id = ?", (run_id,)) as cursor:
            rows = await cursor.fetchall()
            return [self._map_result(row) for row in rows]

    async def get_all_results_for_user(self, user_id: str) -> list[RunResult]:
        async with self.db.execute('''
            SELECT rr.* FROM run_results rr
            JOIN runs r ON rr.run_id = r.id
            WHERE r.user_id = ?
            ORDER BY rr.completed_at DESC
        ''', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [self._map_result(row) for row in rows]

    async def delete_results(self, user_id: str, genome_ids: list[str]):
        if not genome_ids:
            return
        placeholders = ','.join('?' for _ in genome_ids)
        query = f'''
            DELETE FROM run_results 
            WHERE genome_id IN ({placeholders}) 
            AND run_id IN (SELECT id FROM runs WHERE user_id = ?)
        '''
        params = list(genome_ids) + [user_id]
        await self.db.execute(query, params)
        await self.db.commit()
