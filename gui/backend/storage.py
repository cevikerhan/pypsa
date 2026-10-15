import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "pypsa_studio.db"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"


def init_db() -> None:
    """Initialize local SQLite storage for scenarios and uploaded files."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                network_name TEXT NOT NULL,
                mode TEXT NOT NULL,
                solver TEXT NOT NULL,
                horizon INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_scenario(payload: dict[str, Any]) -> int:
    """Persist a scenario in the local database."""

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            """
            INSERT INTO scenarios (name, network_name, mode, solver, horizon, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("name") or "Untitled scenario",
                payload.get("network_name") or "ac_dc_meshed",
                payload.get("mode") or "lopf",
                payload.get("solver") or "highs",
                int(payload.get("horizon") or 24),
                json.dumps(payload.get("metadata") or {}),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def list_scenarios() -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT id, name, network_name, mode, solver, horizon, created_at
            FROM scenarios
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "network_name": row[2],
            "mode": row[3],
            "solver": row[4],
            "horizon": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def save_uploaded_network(filename: str, file_path: str, metadata: dict[str, Any] | None = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            """
            INSERT INTO networks (name, file_path, metadata)
            VALUES (?, ?, ?)
            """,
            (filename, file_path, json.dumps(metadata or {})),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()
