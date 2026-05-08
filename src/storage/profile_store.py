from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.discovery.source_discovery import utc_now_iso


JOB_STATES = {"saved", "dismissed", "applied"}
DEFAULT_USER_ID = "local_user"


def default_database_path(project_root: Path) -> Path:
    return project_root / "data" / "app" / "internlens.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _normalize_user_id(user_id: Optional[str] = None) -> str:
    normalized = str(user_id or DEFAULT_USER_ID).strip()
    return normalized or DEFAULT_USER_ID


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _ensure_recommendation_run_schema(connection: sqlite3.Connection) -> None:
    # Add newly introduced recommendation run columns for existing databases.
    columns = _table_columns(connection, "recommendation_runs")

    if "suppress_similar_results" not in columns:
        connection.execute(
            """
            ALTER TABLE recommendation_runs
            ADD COLUMN suppress_similar_results INTEGER NOT NULL DEFAULT 0
            """
        )


def _create_user_scoped_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, profile_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            feedback_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id, profile_id) REFERENCES profiles(user_id, profile_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_runs (
            run_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            jobs_dir TEXT NOT NULL,
            top_k INTEGER NOT NULL,
            eligible_only INTEGER NOT NULL,
            applyable_only INTEGER NOT NULL,
            suppress_similar_results INTEGER NOT NULL DEFAULT 0,
            include_feedback INTEGER NOT NULL,
            include_debug INTEGER NOT NULL,
            reranking_applied INTEGER NOT NULL,
            feedback_source TEXT,
            total_jobs_scored INTEGER NOT NULL,
            returned_jobs INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id, profile_id) REFERENCES profiles(user_id, profile_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_run_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            rank_index INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES recommendation_runs(run_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_job_states (
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            state TEXT NOT NULL,
            source_run_id TEXT,
            snapshot_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, profile_id, job_id),
            FOREIGN KEY(user_id, profile_id) REFERENCES profiles(user_id, profile_id) ON DELETE CASCADE,
            FOREIGN KEY(source_run_id) REFERENCES recommendation_runs(run_id) ON DELETE SET NULL
        )
        """
    )


def _migrate_legacy_profile_schema(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "profiles"):
        if _table_exists(connection, "recommendation_runs") and "user_id" not in _table_columns(
            connection, "recommendation_runs"
        ):
            for table_name in ("recommendation_run_results", "recommendation_runs"):
                if _table_exists(connection, table_name):
                    connection.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_legacy_user_scope")
            _create_user_scoped_schema(connection)
            for table_name in ("recommendation_run_results", "recommendation_runs"):
                legacy_name = f"{table_name}_legacy_user_scope"
                if _table_exists(connection, legacy_name):
                    connection.execute(f"DROP TABLE {legacy_name}")
        return

    if "user_id" in _table_columns(connection, "profiles"):
        return

    _ensure_recommendation_run_schema(connection)
    legacy_tables = [
        "profile_job_states",
        "recommendation_run_results",
        "recommendation_runs",
        "feedback_events",
        "profiles",
    ]
    for table_name in legacy_tables:
        if _table_exists(connection, table_name):
            connection.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_legacy_user_scope")

    _create_user_scoped_schema(connection)

    connection.execute(
        """
        INSERT INTO profiles (user_id, profile_id, profile_json, created_at, updated_at)
        SELECT ?, profile_id, profile_json, created_at, updated_at
        FROM profiles_legacy_user_scope
        """,
        (DEFAULT_USER_ID,),
    )

    if _table_exists(connection, "feedback_events_legacy_user_scope"):
        connection.execute(
            """
            INSERT INTO feedback_events (id, user_id, profile_id, job_id, feedback_label, created_at)
            SELECT id, ?, profile_id, job_id, feedback_label, created_at
            FROM feedback_events_legacy_user_scope
            """,
            (DEFAULT_USER_ID,),
        )

    if _table_exists(connection, "recommendation_runs_legacy_user_scope"):
        connection.execute(
            """
            INSERT INTO recommendation_runs (
                run_id,
                user_id,
                profile_id,
                jobs_dir,
                top_k,
                eligible_only,
                applyable_only,
                suppress_similar_results,
                include_feedback,
                include_debug,
                reranking_applied,
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at
            )
            SELECT
                run_id,
                ?,
                profile_id,
                jobs_dir,
                top_k,
                eligible_only,
                applyable_only,
                suppress_similar_results,
                include_feedback,
                include_debug,
                reranking_applied,
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at
            FROM recommendation_runs_legacy_user_scope
            """,
            (DEFAULT_USER_ID,),
        )

    if _table_exists(connection, "recommendation_run_results_legacy_user_scope"):
        connection.execute(
            """
            INSERT INTO recommendation_run_results (id, run_id, rank_index, result_json)
            SELECT id, run_id, rank_index, result_json
            FROM recommendation_run_results_legacy_user_scope
            """
        )

    if _table_exists(connection, "profile_job_states_legacy_user_scope"):
        connection.execute(
            """
            INSERT INTO profile_job_states (
                user_id,
                profile_id,
                job_id,
                state,
                source_run_id,
                snapshot_json,
                created_at,
                updated_at
            )
            SELECT
                ?,
                profile_id,
                job_id,
                state,
                source_run_id,
                snapshot_json,
                created_at,
                updated_at
            FROM profile_job_states_legacy_user_scope
            """,
            (DEFAULT_USER_ID,),
        )

    for table_name in legacy_tables:
        legacy_name = f"{table_name}_legacy_user_scope"
        if _table_exists(connection, legacy_name):
            connection.execute(f"DROP TABLE {legacy_name}")


def initialize_database(db_path: Path) -> None:
    with _connect(db_path) as connection:
        _migrate_legacy_profile_schema(connection)
        _create_user_scoped_schema(connection)
        _ensure_recommendation_run_schema(connection)


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


def create_profile(db_path: Path, profile: Dict[str, Any], *, user_id: Optional[str] = None) -> Dict[str, Any]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    now = utc_now_iso()
    serialized = json.dumps(_profile_payload_for_storage(profile), ensure_ascii=False)

    try:
        with _connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO profiles (user_id, profile_id, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (owner_id, profile["profile_id"], serialized, now, now),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Profile already exists: {profile['profile_id']}") from exc

    created = get_profile(db_path, profile["profile_id"], user_id=owner_id)
    if created is None:
        raise ValueError(f"Profile could not be loaded after creation: {profile['profile_id']}")
    return created


def get_profile(db_path: Path, profile_id: str, *, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT user_id, profile_id, profile_json, created_at, updated_at
            FROM profiles
            WHERE user_id = ? AND profile_id = ?
            """,
            (owner_id, profile_id),
        ).fetchone()

    if row is None:
        return None

    payload = json.loads(row["profile_json"])
    payload["user_id"] = row["user_id"]
    payload["created_at"] = row["created_at"]
    payload["updated_at"] = row["updated_at"]
    return payload


def update_profile(db_path: Path, profile: Dict[str, Any], *, user_id: Optional[str] = None) -> Dict[str, Any]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    existing = get_profile(db_path, profile["profile_id"], user_id=owner_id)
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
            WHERE user_id = ? AND profile_id = ?
            """,
            (serialized, updated_at, owner_id, profile["profile_id"]),
        )

    updated = get_profile(db_path, profile["profile_id"], user_id=owner_id)
    if updated is None:
        raise ValueError(f"Profile could not be loaded after update: {profile['profile_id']}")
    updated["created_at"] = created_at
    return updated


def add_feedback_events(
    db_path: Path,
    profile_id: str,
    events: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    if get_profile(db_path, profile_id, user_id=owner_id) is None:
        raise ValueError(f"Profile not found: {profile_id}")

    now = utc_now_iso()
    with _connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO feedback_events (user_id, profile_id, job_id, feedback_label, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (owner_id, profile_id, event["job_id"], event["feedback_label"], now)
                for event in events
            ],
        )

    return get_feedback_events(db_path, profile_id, user_id=owner_id)


def get_feedback_events(db_path: Path, profile_id: str, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT job_id, feedback_label, created_at
            FROM feedback_events
            WHERE user_id = ? AND profile_id = ?
            ORDER BY id ASC
            """,
            (owner_id, profile_id),
        ).fetchall()

    return [
        {
            "job_id": row["job_id"],
            "feedback_label": row["feedback_label"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def create_recommendation_run(
    db_path: Path,
    *,
    profile_id: str,
    user_id: Optional[str] = None,
    jobs_dir: str,
    top_k: int,
    eligible_only: bool,
    applyable_only: bool,
    suppress_similar_results: bool,
    include_feedback: bool,
    include_debug: bool,
    reranking_applied: bool,
    feedback_source: Optional[str],
    total_jobs_scored: int,
    returned_jobs: int,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    if get_profile(db_path, profile_id, user_id=owner_id) is None:
        raise ValueError(f"Profile not found: {profile_id}")

    run_id = f"run_{uuid.uuid4().hex}"
    created_at = utc_now_iso()

    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO recommendation_runs (
                run_id,
                user_id,
                profile_id,
                jobs_dir,
                top_k,
                eligible_only,
                applyable_only,
                suppress_similar_results,
                include_feedback,
                include_debug,
                reranking_applied,
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                owner_id,
                profile_id,
                jobs_dir,
                top_k,
                int(eligible_only),
                int(applyable_only),
                int(suppress_similar_results),
                int(include_feedback),
                int(include_debug),
                int(reranking_applied),
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at,
            ),
        )
        connection.executemany(
            """
            INSERT INTO recommendation_run_results (run_id, rank_index, result_json)
            VALUES (?, ?, ?)
            """,
            [
                (run_id, index, json.dumps(result, ensure_ascii=False))
                for index, result in enumerate(results, start=1)
            ],
        )

    run = get_recommendation_run(db_path, profile_id, run_id, user_id=owner_id)
    if run is None:
        raise ValueError(f"Recommendation run could not be loaded after creation: {run_id}")
    return run


def list_recommendation_runs(db_path: Path, profile_id: str, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                run_id,
                user_id,
                profile_id,
                jobs_dir,
                top_k,
                eligible_only,
                applyable_only,
                suppress_similar_results,
                include_feedback,
                include_debug,
                reranking_applied,
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at
            FROM recommendation_runs
            WHERE user_id = ? AND profile_id = ?
            ORDER BY created_at DESC, run_id DESC
            """,
            (owner_id, profile_id),
        ).fetchall()

    return [
        {
            "run_id": row["run_id"],
            "user_id": row["user_id"],
            "profile_id": row["profile_id"],
            "jobs_dir": row["jobs_dir"],
            "top_k": row["top_k"],
            "eligible_only": bool(row["eligible_only"]),
            "applyable_only": bool(row["applyable_only"]),
            "suppress_similar_results": bool(row["suppress_similar_results"]),
            "include_feedback": bool(row["include_feedback"]),
            "include_debug": bool(row["include_debug"]),
            "reranking_applied": bool(row["reranking_applied"]),
            "feedback_source": row["feedback_source"],
            "total_jobs_scored": row["total_jobs_scored"],
            "returned_jobs": row["returned_jobs"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_recommendation_run(
    db_path: Path,
    profile_id: str,
    run_id: str,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    with _connect(db_path) as connection:
        run_row = connection.execute(
            """
            SELECT
                run_id,
                user_id,
                profile_id,
                jobs_dir,
                top_k,
                eligible_only,
                applyable_only,
                suppress_similar_results,
                include_feedback,
                include_debug,
                reranking_applied,
                feedback_source,
                total_jobs_scored,
                returned_jobs,
                created_at
            FROM recommendation_runs
            WHERE user_id = ? AND profile_id = ? AND run_id = ?
            """,
            (owner_id, profile_id, run_id),
        ).fetchone()

        if run_row is None:
            return None

        result_rows = connection.execute(
            """
            SELECT rank_index, result_json
            FROM recommendation_run_results
            WHERE run_id = ?
            ORDER BY rank_index ASC
            """,
            (run_id,),
        ).fetchall()

    return {
        "run_id": run_row["run_id"],
        "user_id": run_row["user_id"],
        "profile_id": run_row["profile_id"],
        "jobs_dir": run_row["jobs_dir"],
        "top_k": run_row["top_k"],
        "eligible_only": bool(run_row["eligible_only"]),
        "applyable_only": bool(run_row["applyable_only"]),
        "suppress_similar_results": bool(run_row["suppress_similar_results"]),
        "include_feedback": bool(run_row["include_feedback"]),
        "include_debug": bool(run_row["include_debug"]),
        "reranking_applied": bool(run_row["reranking_applied"]),
        "feedback_source": run_row["feedback_source"],
        "total_jobs_scored": run_row["total_jobs_scored"],
        "returned_jobs": run_row["returned_jobs"],
        "created_at": run_row["created_at"],
        "results": [json.loads(row["result_json"]) for row in result_rows],
    }


def upsert_profile_job_state(
    db_path: Path,
    *,
    profile_id: str,
    user_id: Optional[str] = None,
    job_id: str,
    state: str,
    source_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    if get_profile(db_path, profile_id, user_id=owner_id) is None:
        raise ValueError(f"Profile not found: {profile_id}")

    if state not in JOB_STATES:
        raise ValueError(f"Unsupported job state: {state}")

    snapshot: Optional[Dict[str, Any]] = None
    if source_run_id is not None:
        run = get_recommendation_run(db_path, profile_id, source_run_id, user_id=owner_id)
        if run is None:
            raise ValueError(f"Recommendation run not found: {source_run_id}")
        snapshot = next((result for result in run["results"] if result.get("job_id") == job_id), None)
        if snapshot is None:
            raise ValueError(f"Job not found in recommendation run: {job_id}")

    now = utc_now_iso()
    with _connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT created_at
            FROM profile_job_states
            WHERE user_id = ? AND profile_id = ? AND job_id = ?
            """,
            (owner_id, profile_id, job_id),
        ).fetchone()

        created_at = existing["created_at"] if existing is not None else now
        connection.execute(
            """
            INSERT INTO profile_job_states (
                user_id,
                profile_id,
                job_id,
                state,
                source_run_id,
                snapshot_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, profile_id, job_id)
            DO UPDATE SET
                state = excluded.state,
                source_run_id = excluded.source_run_id,
                snapshot_json = excluded.snapshot_json,
                updated_at = excluded.updated_at
            """,
            (
                owner_id,
                profile_id,
                job_id,
                state,
                source_run_id,
                json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None,
                created_at,
                now,
            ),
        )

    stored_state = get_profile_job_state(db_path, profile_id, job_id, user_id=owner_id)
    if stored_state is None:
        raise ValueError(f"Profile job state could not be loaded after update: {job_id}")
    return stored_state


def get_profile_job_state(
    db_path: Path,
    profile_id: str,
    job_id: str,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                user_id,
                profile_id,
                job_id,
                state,
                source_run_id,
                snapshot_json,
                created_at,
                updated_at
            FROM profile_job_states
            WHERE user_id = ? AND profile_id = ? AND job_id = ?
            """,
            (owner_id, profile_id, job_id),
        ).fetchone()

    if row is None:
        return None

    return {
        "user_id": row["user_id"],
        "profile_id": row["profile_id"],
        "job_id": row["job_id"],
        "state": row["state"],
        "source_run_id": row["source_run_id"],
        "job_snapshot": json.loads(row["snapshot_json"]) if row["snapshot_json"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_profile_job_states(
    db_path: Path,
    profile_id: str,
    state: str,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    if state not in JOB_STATES:
        raise ValueError(f"Unsupported job state: {state}")

    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                user_id,
                profile_id,
                job_id,
                state,
                source_run_id,
                snapshot_json,
                created_at,
                updated_at
            FROM profile_job_states
            WHERE user_id = ? AND profile_id = ? AND state = ?
            ORDER BY updated_at DESC, job_id ASC
            """,
            (owner_id, profile_id, state),
        ).fetchall()

    return [
        {
            "user_id": row["user_id"],
            "profile_id": row["profile_id"],
            "job_id": row["job_id"],
            "state": row["state"],
            "source_run_id": row["source_run_id"],
            "job_snapshot": json.loads(row["snapshot_json"]) if row["snapshot_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def clear_profile_job_state(
    db_path: Path,
    profile_id: str,
    job_id: str,
    state: str,
    *,
    user_id: Optional[str] = None,
) -> bool:
    initialize_database(db_path)
    owner_id = _normalize_user_id(user_id)
    if state not in JOB_STATES:
        raise ValueError(f"Unsupported job state: {state}")

    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT state
            FROM profile_job_states
            WHERE user_id = ? AND profile_id = ? AND job_id = ?
            """,
            (owner_id, profile_id, job_id),
        ).fetchone()

        if row is None or row["state"] != state:
            return False

        connection.execute(
            """
            DELETE FROM profile_job_states
            WHERE user_id = ? AND profile_id = ? AND job_id = ?
            """,
            (owner_id, profile_id, job_id),
        )

    return True
