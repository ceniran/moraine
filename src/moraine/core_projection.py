from __future__ import annotations

from typing import Iterable, Mapping

from .temporal import is_current


def _is_explicitly_present(record: Mapping[str, object]) -> bool:
    governance = record.get("moraine_governance")
    return isinstance(governance, Mapping) and governance.get("core_presence") == "always"


def build_core_projection(
    records: Iterable[Mapping[str, object]], *, now: str, max_chars: int = 2000
) -> dict:
    """Build a small, source-linked projection; never mutate authoritative rows."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    eligible = [dict(row) for row in records if _is_explicitly_present(row) and is_current(row, now)]
    eligible.sort(key=lambda row: (-float(row.get("importance") or 0), str(row.get("id") or "")))
    blocks: list[str] = []
    source_ids: list[str] = []
    skipped_ids: list[str] = []
    used = 0
    for row in eligible:
        memory_id = str(row.get("id") or "")
        block = f"{str(row.get('title') or '').strip()}\n{str(row.get('content') or '').strip()}".strip()
        addition = block if not blocks else "\n\n" + block
        if used + len(addition) > max_chars:
            skipped_ids.append(memory_id)
            continue
        blocks.append(block)
        source_ids.append(memory_id)
        used += len(addition)
    return {
        "text": "\n\n".join(blocks),
        "source_ids": source_ids,
        "skipped_ids": skipped_ids,
        "used_chars": used,
        "max_chars": max_chars,
        "persisted": False,
    }
