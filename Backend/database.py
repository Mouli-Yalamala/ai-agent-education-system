import sqlite3
import json
import logging
from typing import List, Optional

from models import RunArtifact

logger = logging.getLogger(__name__)

DB_PATH = "runs.db"

def init_db() -> None:
    """Initializes the SQLite database and creates the run_artifacts table if it doesn't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS run_artifacts (
                    run_id TEXT PRIMARY KEY,
                    input_data TEXT,
                    attempts TEXT,
                    final TEXT,
                    timestamps TEXT
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")

# Call init immediately upon import to ensure table exists before any operation
init_db()


def save_run(artifact: RunArtifact) -> None:
    """Inserts a RunArtifact into the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Serialize the Pydantic models to JSON strings for storage
            cursor.execute('''
                INSERT OR REPLACE INTO run_artifacts 
                (run_id, input_data, attempts, final, timestamps)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                artifact.run_id,
                artifact.input.model_dump_json(),
                json.dumps([a.model_dump(mode="json") for a in artifact.attempts]),
                artifact.final.model_dump_json(),
                artifact.timestamps.model_dump_json()
            ))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save run {artifact.run_id}: {e}")


def get_run_by_id(run_id: str) -> Optional[RunArtifact]:
    """Fetches a specific run by its run_id."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT run_id, input_data, attempts, final, timestamps 
                FROM run_artifacts 
                WHERE run_id = ?
            ''', (run_id,))
            
            row = cursor.fetchone()
            
            if row:
                return _map_row_to_artifact(row)
            return None
    except Exception as e:
        logger.error(f"Failed to fetch run {run_id}: {e}")
        return None


def get_all_runs() -> List[RunArtifact]:
    """Fetches all stored run artifacts."""
    runs = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT run_id, input_data, attempts, final, timestamps FROM run_artifacts')
            for row in cursor.fetchall():
                try:
                    artifact = _map_row_to_artifact(row)
                    runs.append(artifact)
                except Exception as e:
                    logger.error(f"Failed to map row to artifact: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch all runs: {e}")
        
    return runs


def _map_row_to_artifact(row: tuple) -> RunArtifact:
    """Helper method to cleanly deserialize a database row back into a valid RunArtifact Pydantic model."""
    run_id, input_data, attempts, final, timestamps = row
    
    data_dict = {
        "run_id": run_id,
        "input": json.loads(input_data),
        "attempts": json.loads(attempts),
        "final": json.loads(final),
        "timestamps": json.loads(timestamps)
    }
    
    return RunArtifact.model_validate(data_dict)
