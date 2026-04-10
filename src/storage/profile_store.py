from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.discovery.source_discovery import utc_now_iso


def default_database_path(project_root: Path) -> Path:
    return project_root / "data" / "app" / "internlens.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path) -> None:
    with _connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                profile_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                feedback_label TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
            )
            """
        )


def _profile_payload_for_storage(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "profile_id": profile["profile_id"],
        "resume_text": profile["resume_text"],
        "degree_level": profile["degree_level"],
        "grad_date": profile["grad_date"],
        "preferred_roles": list(profile.get("preferred_roles", [])),
        "preferred_locations": list(profile.get("preferred_locations", [])),
        "target_industries": list(profile.get("target_industries", [])),
        "sponsorship_need": bool(profile["sponsorship_need"]),
        "extracted_skills": list(profile.get("extracted_skills", [])),
        "years_of_experience": int(profile.get("years_of_experience", 0)),
        "notes": str(profile.get("notes", "")),
    }


def create_profile(db_path: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    initialize_database(db_path)
    now = utc_now_iso()
    serialized = json.dumps(_profile_payload_for_storage(profile), ensure_ascii=False)

    try:
        with _connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO profiles (profile_id, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (profile["profile_id"], serialized, now, now),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Profile already exists: {profile['profile_id']}") from exc

    created = get_profile(db_path, profile["profile_id"])
    if created is None:
        raise ValueError(f"Profile could not be loaded after creation: {profile['profile_id']}")
    return created


def get_profile(db_path: Path, profile_id: str) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT profile_id, profile_json, created_at, updated_at
            FROM profiles
            WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchone()

    if row is None:
        return None

    payload = json.loads(row["profile_json"])
    payload["created_at"] = row["created_at"]
    payload["updated_at"] = row["updated_at"]
    return payload


def update_profile(db_path: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    initialize_database(db_path)
    existing = get_profile(db_path, profile["profile_id"])
    if existing is None:
        raise ValueError(f"Profile not found: {profile['profile_id']}")

    created_at = existing["created_at"]
    updated_at = utc_now_iso()
    serialized = json.dumps(_profile_payload_for_storage(profile), ensure_ascii=False)

    with _connect(db_path) as connection:
        connection.execute(
            """
            UPDATE profiles
            SET profile_json = ?, updated_at = ?
            WHERE profile_id = ?
            """,
            (serialized, updated_at, profile["profile_id"]),
        )

    updated = get_profile(db_path, profile["profile_id"])
    if updated is None:
        raise ValueError(f"Profile could not be loaded after update: {profile['profile_id']}")
    updated["created_at"] = created_at
    return updated


def add_feedback_events(
    db_path: Path,
    profile_id: str,
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    if get_profile(db_path, profile_id) is None:
        raise ValueError(f"Profile not found: {profile_id}")

    now = utc_now_iso()
    with _connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO feedback_events (profile_id, job_id, feedback_label, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (profile_id, event["job_id"], event["feedback_label"], now)
                for event in events
            ],
        )

    return get_feedback_events(db_path, profile_id)


def get_feedback_events(db_path: Path, profile_id: str) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT job_id, feedback_label, created_at
            FROM feedback_events
            WHERE profile_id = ?
            ORDER BY id ASC
            """,
            (profile_id,),
        ).fetchall()

    return [
        {
            "job_id": row["job_id"],
            "feedback_label": row["feedback_label"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
