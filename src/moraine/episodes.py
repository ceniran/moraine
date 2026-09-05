from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from typing import Iterable, Mapping

from .temporal import parse_time


def _source_key(row: Mapping[str, object]) -> tuple[str, str]:
    source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
    return str(source.get("type") or "unknown"), str(source.get("ref") or "")


def _bucket_key(row: Mapping[str, object]) -> tuple[str, str, str, str]:
    source_type, source_ref = _source_key(row)
    return (
        source_type,
        source_ref,
        str(row.get("workspace") or "default"),
        str(row.get("project_id") or ""),
    )


def build_episode_candidates(
    rows: Iterable[Mapping[str, object]], *, window_minutes: int = 60
) -> list[dict]:
    """Group same-source observations into review-only episode candidates.

    This preserves original records and never declares a long-term fact active.
    """
    if not 1 <= int(window_minutes) <= 24 * 60:
        raise ValueError("window_minutes must be between 1 and 1440")
    prepared = []
    for raw in rows:
        row = dict(raw)
        if not row.get("id"):
            raise ValueError("every episode member must have an id")
        source_type, source_ref = _source_key(row)
        if source_type == "unknown" or not source_ref:
            raise ValueError("every episode member must have a source type and reference")
        observed = parse_time(row.get("observed_at") or row.get("created_at"))
        if observed is None:
            raise ValueError("every episode member must have observed_at or created_at")
        prepared.append((_bucket_key(row), observed, row))
    prepared.sort(key=lambda item: (item[0], item[1], str(item[2]["id"])))

    groups: list[list[tuple]] = []
    for item in prepared:
        if not groups:
            groups.append([item])
            continue
        previous = groups[-1][-1]
        same_key = previous[0] == item[0]
        within_window = item[1] - previous[1] <= timedelta(minutes=window_minutes)
        if same_key and within_window:
            groups[-1].append(item)
        else:
            groups.append([item])

    candidates = []
    for group in groups:
        key = group[0][0]
        ids = [str(item[2]["id"]) for item in group]
        seed = "|".join((*key, *ids))
        candidates.append({
            "episode_id": f"episode_{sha256(seed.encode()).hexdigest()[:16]}",
            "status": "pending_review",
            "source": {"type": key[0], "ref": key[1]},
            "workspace": key[2],
            "project_id": key[3] or None,
            "window_minutes": int(window_minutes),
            "started_at": group[0][1].isoformat().replace("+00:00", "Z"),
            "ended_at": group[-1][1].isoformat().replace("+00:00", "Z"),
            "member_ids": ids,
            "member_count": len(ids),
            "allowed_decisions": ["promote", "supplement", "relate", "supersede", "keep_episode"],
            "persisted": False,
        })
    return candidates
