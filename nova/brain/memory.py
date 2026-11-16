import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from nova.config import DB_PATH

class NovaMemory:
    """Persistent SQLite memory for conversation history, task logs, and user preferences."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_description TEXT,
                    tool_name TEXT NOT NULL,
                    parameters TEXT,
                    result TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tool_calls_json = json.dumps(tool_calls) if tool_calls else None
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, tool_calls_json, time.time())
            )
            conn.commit()

    def get_recent_messages(self, session_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            messages = []
            for row in reversed(rows):
                msg = {"role": row["role"], "content": row["content"]}
                if row["tool_calls"]:
                    try:
                        msg["tool_calls"] = json.loads(row["tool_calls"])
                    except Exception:
                        pass
                messages.append(msg)
            return messages

    def log_task(self, tool_name: str, parameters: Dict[str, Any], result: str, status: str = "success", task_description: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_logs (task_description, tool_name, parameters, result, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (task_description or "", tool_name, json.dumps(parameters), str(result), status, time.time())
            )
            conn.commit()

    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, task_description, tool_name, parameters, result, status, created_at FROM task_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def set_preference(self, key: str, value: Any):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )
            conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default
