from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_FILE = Path("outputs/internlens_eb_backend.zip")
RUNTIME_PATHS = (
    Path("Procfile"),
    Path("requirements.txt"),
    Path("src"),
)
JOBS_PATH = Path("data/processed/jobs")
REQUIRED_ARCHIVE_FILES = (
    "Procfile",
    "requirements.txt",
    "src/api/app.py",
)
MAX_ELASTIC_BEANSTALK_BUNDLE_MB = 500
IGNORED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an Elastic Beanstalk source bundle for the InternLens FastAPI backend."
    )
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument(
        "--without-jobs",
        action="store_true",
        help="Create a code-only bundle. Use this only if INTERNLENS_JOBS_DIR is populated on the host separately.",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=MAX_ELASTIC_BEANSTALK_BUNDLE_MB,
        help="Fail if the generated source bundle exceeds this size.",
    )
    return parser.parse_args(argv)


def _assert_within_project(path: Path, project_root: Path) -> None:
    try:
        path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path must stay inside the project root: {path}") from exc


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return

    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file():
            continue
        if any(part in IGNORED_PARTS for part in candidate.parts):
            continue
        if candidate.suffix in {".pyc", ".pyo"}:
            continue
        yield candidate


def _archive_name(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _build_include_paths(*, include_jobs: bool) -> list[Path]:
    paths = list(RUNTIME_PATHS)
    if include_jobs:
        paths.append(JOBS_PATH)
    return paths


def build_source_bundle(
    *,
    output_file: Path,
    project_root: Path = PROJECT_ROOT,
    include_jobs: bool = True,
    max_size_mb: int = MAX_ELASTIC_BEANSTALK_BUNDLE_MB,
) -> dict[str, object]:
    project_root = project_root.resolve()
    output_path = (project_root / output_file).resolve() if not output_file.is_absolute() else output_file.resolve()
    _assert_within_project(output_path, project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    include_paths = _build_include_paths(include_jobs=include_jobs)
    files: list[Path] = []
    for relative_path in include_paths:
        source_path = (project_root / relative_path).resolve()
        _assert_within_project(source_path, project_root)
        if not source_path.exists():
            raise FileNotFoundError(f"Required bundle path does not exist: {relative_path.as_posix()}")
        files.extend(_iter_files(source_path))

    archive_names = [_archive_name(path, project_root) for path in files]
    missing_required = [name for name in REQUIRED_ARCHIVE_FILES if name not in archive_names]
    if missing_required:
        raise FileNotFoundError(f"Missing required bundle files: {', '.join(missing_required)}")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
        for file_path, archive_name in sorted(zip(files, archive_names), key=lambda item: item[1]):
            archive.write(file_path, archive_name)

    size_bytes = output_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        output_path.unlink()
        raise ValueError(f"Bundle exceeded {max_size_mb} MB")

    return {
        "output_file": output_path,
        "file_count": len(files),
        "size_bytes": size_bytes,
        "include_jobs": include_jobs,
    }


def _print_summary(summary: dict[str, object]) -> None:
    size_mb = int(summary["size_bytes"]) / (1024 * 1024)
    print("##### Elastic Beanstalk backend bundle created #####")
    print(f"Output: {summary['output_file']}")
    print(f"Files: {summary['file_count']}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Included processed jobs: {'yes' if summary['include_jobs'] else 'no'}")


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)

    summary = build_source_bundle(
        output_file=Path(args.output_file),
        include_jobs=not args.without_jobs,
        max_size_mb=args.max_size_mb,
    )
    _print_summary(summary)


if __name__ == "__main__":
    main()
