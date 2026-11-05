"""Shared, reproducible text extraction for PDF source snapshots.

Original PDFs remain immutable under raw_data/. Extracted text and its metadata
are derived artifacts under derived_data/pdf_text/, keyed by the original
repository-relative path. This extracts embedded text only; it does not OCR
scanned/image-only pages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = ROOT / "raw_data"
DEFAULT_OUTPUT_ROOT = ROOT / "derived_data" / "pdf_text"


class PdfTextError(RuntimeError):
    """PDF text extraction or derived-artifact integrity failure."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_pdf_file(path: Path) -> bool:
    """Identify PDFs by signature rather than relying on a filename extension."""
    try:
        with path.open("rb") as stream:
            return b"%PDF-" in stream.read(1024)
    except OSError:
        return False


def _relative_source_path(source_path: Path) -> Path:
    resolved = source_path.resolve()
    try:
        return resolved.relative_to((ROOT / "raw_data").resolve())
    except ValueError:
        try:
            return resolved.relative_to(ROOT.resolve())
        except ValueError:
            return Path(source_path.name)


def _artifact_paths(source_path: Path, output_root: Path) -> tuple[Path, Path]:
    relative = _relative_source_path(source_path)
    text_path = output_root / relative.parent / f"{relative.name}.txt"
    return text_path, text_path.with_suffix(text_path.suffix + ".json")


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _pypdf_version() -> str:
    try:
        return version("pypdf")
    except PackageNotFoundError:
        return "unknown"


def _read_pages(text: str) -> list[str]:
    parts = re.split(r"(?m)^--- PAGE (\d+) ---\n", text)
    if len(parts) <= 1:
        return []
    return [parts[index].strip() for index in range(2, len(parts), 2)]


def extract_pdf_text(
    source_path: Path,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    """Create or verify a text sidecar for one PDF; never overwrite derivatives."""
    source_path = Path(source_path)
    if not is_pdf_file(source_path):
        return {"status": "not_pdf", "source_path": str(source_path)}

    source_hash = sha256_file(source_path)
    text_path, metadata_path = _artifact_paths(source_path, Path(output_root))
    if text_path.exists() or metadata_path.exists():
        if not text_path.is_file() or not metadata_path.is_file():
            raise PdfTextError(f"Incomplete existing PDF text artifact; refusing overwrite: {text_path}")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PdfTextError(f"Cannot read PDF text metadata {metadata_path}: {exc}") from exc
        text_hash = sha256_file(text_path)
        if metadata.get("source_sha256") != source_hash or metadata.get("text_sha256") != text_hash:
            raise PdfTextError(f"Existing PDF text artifact does not match its source: {text_path}")
        text = text_path.read_text(encoding="utf-8")
        return {
            **metadata,
            "status": metadata.get("status", "text_extracted"),
            "source_path": _display_path(source_path),
            "text_path": _display_path(text_path),
            "metadata_path": _display_path(metadata_path),
            "pages": _read_pages(text),
            "reused": True,
        }

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfTextError("PDF text extraction requires pypdf; install the project dependencies.") from exc

    try:
        reader = PdfReader(str(source_path), strict=True)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        document_metadata = reader.metadata
        rendered = "\n\n".join(
            f"--- PAGE {number} ---\n{page}" for number, page in enumerate(pages, start=1)
        ) + "\n"
    except Exception as exc:
        raise PdfTextError(f"Cannot extract text from PDF {source_path}: {exc}") from exc

    text_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with text_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        metadata = {
            "pdf_text_schema_version": 1,
            "status": "text_extracted" if any(pages) else "no_embedded_text",
            "source_path": _display_path(source_path),
            "source_sha256": source_hash,
            "text_path": _display_path(text_path),
            "text_sha256": sha256_file(text_path),
            "page_count": len(pages),
            "pages_with_text": sum(bool(page) for page in pages),
            "extractor": "pypdf",
            "extractor_version": _pypdf_version(),
            "document_metadata": (
                {str(key): str(value) for key, value in document_metadata.items()}
                if document_metadata else {}
            ),
        }
        with metadata_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception:
        text_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise

    return {
        **metadata,
        "metadata_path": _display_path(metadata_path),
        "pages": pages,
        "reused": False,
    }


def extract_pdf_tree(
    raw_root: Path = DEFAULT_RAW_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    """Backfill text derivatives for all PDF files already present under raw_root."""
    results: list[dict[str, Any]] = []
    for path in sorted(Path(raw_root).rglob("*")):
        if not path.is_file() or not is_pdf_file(path):
            continue
        try:
            results.append(extract_pdf_text(path, output_root))
        except Exception as exc:
            results.append({"status": "failed", "source_path": str(path), "error": str(exc)})
    counts: dict[str, int] = {}
    for row in results:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return {
        "raw_root": str(raw_root),
        "output_root": str(output_root),
        "pdf_count": len(results),
        "status_counts": counts,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create text derivatives for PDF snapshots under raw_data.")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    report = extract_pdf_tree(args.raw_root, args.output_root)
    if not args.quiet:
        print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
        for row in report["results"]:
            if row["status"] == "failed":
                print(f"FAILED {row['source_path']}: {row['error']}", file=sys.stderr)
    return 1 if report["status_counts"].get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
