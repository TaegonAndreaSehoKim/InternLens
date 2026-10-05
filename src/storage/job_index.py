from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from src.preprocessing.job_parser import load_all_job_postings


def _fingerprint(directory: Path) -> tuple:
    if not directory.is_dir():
        raise FileNotFoundError(f"Job directory not found: {directory}")
    files = []
    for path in sorted(directory.rglob("*.json")):
        metadata = path.stat()
        files.append((str(path.relative_to(directory)), metadata.st_mtime_ns, metadata.st_ctime_ns, metadata.st_size, metadata.st_ino))
    return tuple(files)


class JobIndex:
    """Bounded, per-process detail lookup cache; ranking keeps its active loader."""

    def __init__(self, *, max_corpora: int = 8):
        if max_corpora < 1:
            raise ValueError("max_corpora must be positive")
        self.max_corpora = max_corpora
        self._snapshots: OrderedDict[Path, tuple[tuple, dict[str, dict[str, Any]]]] = OrderedDict()
        self._lock = RLock()

    def get(self, directory: str | Path, job_id: str) -> dict[str, Any] | None:
        root = Path(directory).resolve()
        with self._lock:
            for attempt in range(2):
                try:
                    signature = _fingerprint(root)
                    cached = self._snapshots.get(root)
                    if cached is not None and cached[0] == signature:
                        self._snapshots.move_to_end(root)
                        return deepcopy(cached[1].get(job_id))
                    # Detail views retain expired records and every distinct ID.
                    jobs = load_all_job_postings(root, include_expired=True, suppress_duplicate_content=False)
                    if _fingerprint(root) != signature:
                        continue
                except FileNotFoundError:
                    self._snapshots.pop(root, None)
                    if attempt == 0:
                        continue
                    raise
                except ValueError:
                    self._snapshots.pop(root, None)
                    raise
                by_id = {job["job_id"]: job for job in jobs}
                self._snapshots[root] = (signature, by_id)
                self._snapshots.move_to_end(root)
                while len(self._snapshots) > self.max_corpora:
                    self._snapshots.popitem(last=False)
                return deepcopy(by_id.get(job_id))
            self._snapshots.pop(root, None)
            raise RuntimeError("Job corpus changed during lookup. Please try again.")


job_index = JobIndex()
