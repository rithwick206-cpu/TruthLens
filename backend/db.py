from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "truthlens.db"


def get_db_path() -> Path:
    env_path = os.getenv("TRUTHLENS_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                review_status TEXT DEFAULT 'needs_review',
                review_notes TEXT DEFAULT '',
                caption_text TEXT,
                files_json TEXT,
                result_json TEXT
            );
            """
        )
        conn.commit()


def _row_to_case_dict(row: sqlite3.Row) -> Dict[str, Any]:
    files = json.loads(row["files_json"]) if row["files_json"] else []
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {
        "id": row["id"],
        "case_id": row["id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "review_status": row["review_status"],
        "review_notes": row["review_notes"],
        "caption_text": row["caption_text"],
        "files": files,
        "result": result,
    }


def create_case(
    case_id: str,
    created_at: str,
    status: str = "ingested",
    caption_text: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    review_status: str = "needs_review",
    review_notes: str = "",
    result: Optional[Dict[str, Any]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    files_json = json.dumps(files or [])
    result_json = json.dumps(result) if result is not None else None

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cases (
                id, created_at, status, review_status, review_notes, caption_text, files_json, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                case_id,
                created_at,
                status,
                review_status,
                review_notes,
                caption_text,
                files_json,
                result_json,
            ),
        )
        conn.commit()

    return {
        "id": case_id,
        "case_id": case_id,
        "created_at": created_at,
        "status": status,
        "review_status": review_status,
        "review_notes": review_notes,
        "caption_text": caption_text,
        "files": files or [],
        "result": result,
    }


def get_case(case_id: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?;", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_case_dict(row)


def list_cases(db_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY datetime(created_at) DESC, id DESC;")
        rows = cursor.fetchall()
        return [_row_to_case_dict(row) for row in rows]


def update_case_result(
    case_id: str,
    arg2: Union[Dict[str, Any], str],
    arg3: Optional[Union[Dict[str, Any], str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    # Handle either (case_id, "analyzed", result_dict) or (case_id, result_dict, "analyzed")
    if isinstance(arg2, str) and isinstance(arg3, (dict, list)):
        status = arg2
        result_json = json.dumps(arg3)
    elif isinstance(arg3, str):
        status = arg3
        result_json = arg2 if isinstance(arg2, str) else json.dumps(arg2)
    else:
        status = "completed"
        result_json = arg2 if isinstance(arg2, str) else json.dumps(arg2)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET result_json = ?, status = ? WHERE id = ?;",
            (result_json, status, case_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_case_review(
    case_id: str,
    review_status: str,
    review_notes: str,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET review_status = ?, review_notes = ? WHERE id = ?;",
            (review_status, review_notes, case_id),
        )
        conn.commit()
        return cursor.rowcount > 0
