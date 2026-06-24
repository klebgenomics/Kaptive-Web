import aiosqlite
import uuid
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

@dataclass
class User:
    id: str # Github ID or custom UUID
    username: str
    api_key: str

@dataclass
class Run:
    id: str
    user_id: str
    species: str
    status: str
    created_at: str
    total_genomes: int

@dataclass
class RunResult:
    id: int
    run_id: str
    genome_id: str
    results_json: str
    completed_at: str

class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
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
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS run_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    genome_id TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    completed_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                )
            ''')
            await db.commit()

    async def create_user(self, user_id: str, username: str, api_key: str) -> User:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO users (id, username, api_key) VALUES (?, ?, ?)",
                (user_id, username, api_key)
            )
            await db.commit()
        return User(user_id, username, api_key)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                return User(row['id'], row['username'], row['api_key'])
        return None

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
            row = await cursor.fetchone()
            if row:
                return User(row['id'], row['username'], row['api_key'])
        return None

    async def delete_user_cascade(self, user_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Delete run results
            await db.execute('''
                DELETE FROM run_results 
                WHERE run_id IN (SELECT id FROM runs WHERE user_id = ?)
            ''', (user_id,))
            
            # Delete runs
            await db.execute("DELETE FROM runs WHERE user_id = ?", (user_id,))
            
            # Delete user
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()

    async def get_all_users(self) -> list[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users")
            rows = await cursor.fetchall()
            return [User(row['id'], row['username'], row['api_key']) for row in rows]

    async def create_run(self, user_id: str, species: str, total_genomes: int) -> Run:
        run_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        status = "PENDING"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO runs (id, user_id, species, status, created_at, total_genomes) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, user_id, species, status, created_at, total_genomes)
            )
            await db.commit()
        return Run(run_id, user_id, species, status, created_at, total_genomes)

    async def update_run_status(self, run_id: str, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))
            await db.commit()

    async def get_run(self, run_id: str) -> Optional[Run]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = await cursor.fetchone()
            if row:
                return Run(row['id'], row['user_id'], row['species'], row['status'], row['created_at'], row['total_genomes'])
        return None

    async def get_runs_for_user(self, user_id: str) -> list[Run]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM runs WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = await cursor.fetchall()
            return [Run(row['id'], row['user_id'], row['species'], row['status'], row['created_at'], row['total_genomes']) for row in rows]

    async def add_run_result(self, run_id: str, genome_id: str, results_json: str, completed_at: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO run_results (run_id, genome_id, results_json, completed_at) VALUES (?, ?, ?, ?)",
                (run_id, genome_id, results_json, completed_at)
            )
            await db.commit()

    async def get_run_results(self, run_id: str) -> list[RunResult]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM run_results WHERE run_id = ?", (run_id,))
            rows = await cursor.fetchall()
            return [RunResult(row['id'], row['run_id'], row['genome_id'], row['results_json'], row['completed_at']) for row in rows]

    async def get_all_results_for_user(self, user_id: str) -> list[RunResult]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT rr.* 
                FROM run_results rr
                JOIN runs r ON rr.run_id = r.id
                WHERE r.user_id = ?
                ORDER BY rr.completed_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            return [RunResult(row['id'], row['run_id'], row['genome_id'], row['results_json'], row['completed_at']) for row in rows]
