from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from app.database import connection


ATTACHMENT_FIELD_LABELS = {
    "electronic_invoice_path": "file hóa đơn điện tử",
    "warehouse_invoice_path": "file hóa đơn xuất kho",
}


ATTACHMENT_FIELD_PREFIXES = {
    "electronic_invoice_path": "hoa-don-dien-tu",
    "warehouse_invoice_path": "hoa-don-xuat-kho",
}


def invoice_attachments_root_dir() -> Path:
    return connection.DATA_DIR / "invoice_attachments"


def invoice_attachment_dir(invoice_no: str) -> Path:
    safe_invoice_no = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in str(invoice_no).strip())
    safe_invoice_no = safe_invoice_no.strip("-_") or "invoice"
    return invoice_attachments_root_dir() / safe_invoice_no


def _is_within_directory(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def stage_invoice_attachments(invoice_no: str, invoice_data: dict) -> tuple[dict, list[Path], set[Path]]:
    staged_invoice_data = dict(invoice_data)
    created_paths: list[Path] = []
    kept_paths: set[Path] = set()
    target_dir = invoice_attachment_dir(invoice_no)
    target_dir_resolved = target_dir.resolve()

    for field_name, prefix in ATTACHMENT_FIELD_PREFIXES.items():
        source_raw = str(invoice_data.get(field_name, "") or "").strip()
        if not source_raw:
            staged_invoice_data[field_name] = ""
            continue

        source_path = Path(source_raw).expanduser()
        if not source_path.exists():
            raise ValueError(f"Không tìm thấy {ATTACHMENT_FIELD_LABELS[field_name]} tại:\n{source_path}")

        resolved_source = source_path.resolve()
        if _is_within_directory(resolved_source, target_dir_resolved):
            staged_invoice_data[field_name] = str(resolved_source)
            kept_paths.add(resolved_source)
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        destination_path = target_dir / f"{prefix}-{uuid4().hex[:8]}{source_path.suffix}"
        shutil.copy2(resolved_source, destination_path)
        resolved_destination = destination_path.resolve()
        staged_invoice_data[field_name] = str(resolved_destination)
        created_paths.append(resolved_destination)
        kept_paths.add(resolved_destination)

    return staged_invoice_data, created_paths, kept_paths


def remove_staged_invoice_attachments(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue


def cleanup_obsolete_invoice_attachments(invoice_no: str, kept_paths: set[Path]) -> None:
    target_dir = invoice_attachment_dir(invoice_no)
    if not target_dir.exists():
        return

    normalized_kept_paths = {path.resolve() for path in kept_paths}
    for child in target_dir.iterdir():
        if child.is_file() and child.resolve() not in normalized_kept_paths:
            try:
                child.unlink()
            except OSError:
                continue

    try:
        next(target_dir.iterdir())
    except StopIteration:
        try:
            target_dir.rmdir()
        except OSError:
            pass


def delete_invoice_attachment_dir(invoice_no: str) -> None:
    shutil.rmtree(invoice_attachment_dir(invoice_no), ignore_errors=True)