from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .source_discovery import utc_now_iso


def _sort_registry_entries(entries: List[Dict[str, Any]], key_name: str) -> List[Dict[str, Any]]:
    return sorted(entries, key=lambda item: str(item.get(key_name, "")).lower())


def _merge_notes(existing_notes: str, new_note: str) -> str:
    existing = existing_notes.strip()
    if not existing:
        return new_note
    if new_note in existing:
        return existing
    return f"{existing}; {new_note}"


def _promotion_note(record: Dict[str, Any], promoted_at: str) -> str:
    company = str(record.get("company", "")).strip()
    source_score = float(record.get("source_score", 0.0) or 0.0)
    internship_likelihood = float(record.get("internship_likelihood", 0.0) or 0.0)
    return (
        f"promoted from discovered sources on {promoted_at}"
        f" (company={company or 'unknown'}, score={source_score:.2f}, internship_likelihood={internship_likelihood:.2f})"
    )


def _build_lever_registry_entry(record: Dict[str, Any], promoted_at: str) -> Dict[str, Any]:
    internship_likelihood = float(record.get("internship_likelihood", 0.0) or 0.0)
    return {
        "site_name": str(record.get("source_identifier", "")).strip(),
        "active": True,
        "internship_only": internship_likelihood >= 0.5,
        "notes": _promotion_note(record, promoted_at),
    }


def _build_greenhouse_registry_entry(record: Dict[str, Any], promoted_at: str) -> Dict[str, Any]:
    return {
        "board_token": str(record.get("source_identifier", "")).strip(),
        "active": True,
        "notes": _promotion_note(record, promoted_at),
    }


def _promotable(record: Dict[str, Any], *, min_score: float, require_internship_signal: bool) -> tuple[bool, str]:
    status = str(record.get("status", "")).strip().lower()
    if status != "validated":
        return False, "status"

    source_score = float(record.get("source_score", 0.0) or 0.0)
    if source_score < min_score:
        return False, "score"

    internship_likelihood = float(record.get("internship_likelihood", 0.0) or 0.0)
    if require_internship_signal and internship_likelihood <= 0.0:
        return False, "internship"

    source_type = str(record.get("source_type", "")).strip().lower()
    source_identifier = str(record.get("source_identifier", "")).strip()
    if source_type not in {"lever", "greenhouse"} or not source_identifier:
        return False, "unsupported"

    return True, ""


def promote_validated_sources(
    discovered_records: Sequence[Dict[str, Any]],
    *,
    lever_registry: Sequence[Dict[str, Any]],
    greenhouse_registry: Sequence[Dict[str, Any]],
    min_score: float,
    require_internship_signal: bool,
    promoted_at: str | None = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    promoted_at_value = promoted_at or utc_now_iso()
    updated_discovered: List[Dict[str, Any]] = []
    updated_lever_registry = [dict(entry) for entry in lever_registry]
    updated_greenhouse_registry = [dict(entry) for entry in greenhouse_registry]

    lever_by_site = {
        str(entry.get("site_name", "")).strip(): entry
        for entry in updated_lever_registry
        if str(entry.get("site_name", "")).strip()
    }
    greenhouse_by_board = {
        str(entry.get("board_token", "")).strip(): entry
        for entry in updated_greenhouse_registry
        if str(entry.get("board_token", "")).strip()
    }

    summary = {
        "promoted": 0,
        "reactivated": 0,
        "already_active": 0,
        "skipped_status": 0,
        "skipped_score": 0,
        "skipped_internship": 0,
        "skipped_unsupported": 0,
    }

    for record in discovered_records:
        updated_record = dict(record)
        can_promote, reason = _promotable(
            record,
            min_score=min_score,
            require_internship_signal=require_internship_signal,
        )

        if not can_promote:
            if reason == "status":
                summary["skipped_status"] += 1
            elif reason == "score":
                summary["skipped_score"] += 1
            elif reason == "internship":
                summary["skipped_internship"] += 1
            else:
                summary["skipped_unsupported"] += 1
            updated_discovered.append(updated_record)
            continue

        source_type = str(record.get("source_type", "")).strip().lower()
        source_identifier = str(record.get("source_identifier", "")).strip()
        promotion_note = _promotion_note(record, promoted_at_value)

        if source_type == "lever":
            existing_entry = lever_by_site.get(source_identifier)
            if existing_entry is None:
                new_entry = _build_lever_registry_entry(record, promoted_at_value)
                updated_lever_registry.append(new_entry)
                lever_by_site[source_identifier] = new_entry
                summary["promoted"] += 1
            elif bool(existing_entry.get("active", True)):
                existing_entry["notes"] = _merge_notes(str(existing_entry.get("notes", "")), promotion_note)
                summary["already_active"] += 1
            else:
                existing_entry["active"] = True
                existing_entry["internship_only"] = (
                    bool(existing_entry.get("internship_only", False))
                    or float(record.get("internship_likelihood", 0.0) or 0.0) >= 0.5
                )
                existing_entry["notes"] = _merge_notes(str(existing_entry.get("notes", "")), promotion_note)
                summary["reactivated"] += 1
        else:
            existing_entry = greenhouse_by_board.get(source_identifier)
            if existing_entry is None:
                new_entry = _build_greenhouse_registry_entry(record, promoted_at_value)
                updated_greenhouse_registry.append(new_entry)
                greenhouse_by_board[source_identifier] = new_entry
                summary["promoted"] += 1
            elif bool(existing_entry.get("active", True)):
                existing_entry["notes"] = _merge_notes(str(existing_entry.get("notes", "")), promotion_note)
                summary["already_active"] += 1
            else:
                existing_entry["active"] = True
                existing_entry["notes"] = _merge_notes(str(existing_entry.get("notes", "")), promotion_note)
                summary["reactivated"] += 1

        updated_record["status"] = "active"
        updated_record["last_promoted_at"] = promoted_at_value
        updated_discovered.append(updated_record)

    return (
        updated_discovered,
        _sort_registry_entries(updated_lever_registry, "site_name"),
        _sort_registry_entries(updated_greenhouse_registry, "board_token"),
        summary,
    )
