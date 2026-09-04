from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
from typing import Iterable, Mapping


DEFAULT_BASE_STRENGTH = {
    "context": 15, "status": 20, "event": 30, "reflection": 35,
    "project": 40, "preference": 45, "decision": 50,
    "relationship": 50, "identity": 70, "unknown": 30,
}
BANDS = ((0, 19, "transient"), (20, 39, "ordinary"), (40, 59, "stable"),
         (60, 79, "important"), (80, 100, "core"))


def clamp_strength(value: float | int) -> int:
    return max(0, min(100, round(float(value))))


def strength_from_importance(value: object) -> int | None:
    if value is None:
        return None
    try:
        return clamp_strength(float(value) * 100)
    except (TypeError, ValueError):
        return None


def importance_from_strength(value: float | int) -> float:
    return clamp_strength(value) / 100


def band_for(value: float | int) -> str:
    strength = clamp_strength(value)
    return next(label for lower, upper, label in BANDS if lower <= strength <= upper)


@dataclass(frozen=True)
class GovernancePolicy:
    """Deterministic, content-free defaults for import-time suggestions."""

    base_strength: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_BASE_STRENGTH))
    protected_bonus: int = 15
    confirmation_step: int = 2
    confirmation_cap: int = 10
    explicit_priority_weight: float = 0.25
    explicit_identity_weight: float = 0.25
    automatic_ceiling: int = 79

    def __post_init__(self) -> None:
        normalized = {str(kind): clamp_strength(value) for kind, value in self.base_strength.items()}
        normalized.setdefault("unknown", 30)
        object.__setattr__(self, "base_strength", normalized)


def suggest_strength(memory: Mapping[str, object], policy: GovernancePolicy | None = None) -> dict:
    """Suggest strength from metadata only; content is neither read nor returned."""
    policy = policy or GovernancePolicy()
    governance = memory.get("moraine_governance") if isinstance(memory.get("moraine_governance"), Mapping) else {}
    if governance.get("strength_locked") is True:
        current = strength_from_importance(memory.get("importance"))
        return {
            "id": str(memory.get("id") or ""), "kind": str(memory.get("kind") or "unknown"),
            "current_strength": current, "suggested_strength": current,
            "difference": 0, "band": band_for(current or 0), "protected": True,
            "reasons": [{"signal": "manual_lock", "points": 0}], "requires_review": False,
            "method": "metadata_strength_v1",
        }
    kind = str(memory.get("kind") or "unknown")
    base = policy.base_strength.get(kind, policy.base_strength["unknown"])
    score = float(base)
    reasons = [{"signal": "kind_default", "kind": kind, "points": base}]
    decay = memory.get("memory_decay") if isinstance(memory.get("memory_decay"), Mapping) else {}
    lifecycle = memory.get("memory_lifecycle") if isinstance(memory.get("memory_lifecycle"), Mapping) else {}
    protected = bool(memory.get("protected") is True or decay.get("policy") == "protected"
                     or lifecycle.get("protected") is True)
    if protected:
        score += policy.protected_bonus
        reasons.append({"signal": "explicit_protection", "points": policy.protected_bonus})
    confirmations = max(0, int(decay.get("confirmation_count") or 0))
    confirmation_points = min(policy.confirmation_cap, round(log2(confirmations + 1) * policy.confirmation_step))
    if confirmation_points:
        score += confirmation_points
        reasons.append({"signal": "confirmed_use", "count": confirmations, "points": confirmation_points})
    for field_name, weight in (("priority", policy.explicit_priority_weight),
                               ("identity_weight", policy.explicit_identity_weight)):
        if memory.get(field_name) is None:
            continue
        try:
            normalized = max(0.0, min(1.0, float(memory[field_name])))
        except (TypeError, ValueError):
            continue
        points = round((normalized * 100 - base) * weight)
        score += points
        reasons.append({"signal": field_name, "value": normalized, "points": points})
    suggested = min(policy.automatic_ceiling, clamp_strength(score))
    current = strength_from_importance(memory.get("importance"))
    return {
        "id": str(memory.get("id") or ""), "kind": kind,
        "current_strength": current, "suggested_strength": suggested,
        "difference": None if current is None else suggested - current,
        "band": band_for(suggested), "protected": protected, "reasons": reasons,
        "requires_review": protected or kind in {"identity", "relationship"},
        "method": "metadata_strength_v1",
    }


def manual_strength_change(memory: Mapping[str, object], strength: int, *, lock: bool = False,
                           actor: str, reason: str, now: str) -> dict:
    """Build an audited manual change without persisting or mutating its input."""
    actor = str(actor).strip()
    reason = str(reason).strip()
    if not actor or not reason or not str(now).strip():
        raise ValueError("actor, reason and now are required")
    current_governance = memory.get("moraine_governance") if isinstance(memory.get("moraine_governance"), Mapping) else {}
    if current_governance.get("strength_locked") is True:
        raise ValueError("strength is locked; unlock it before changing")
    selected = clamp_strength(strength)
    if lock and selected < 80:
        raise ValueError("only manually assigned core strength (80..100) may be locked")
    updated = dict(memory)
    audit = list(current_governance.get("audit") or [])
    audit.append({"action": "manual_strength_locked" if lock else "manual_strength_changed",
                  "actor": actor, "at": str(now), "reason": reason,
                  "from": strength_from_importance(memory.get("importance")), "to": selected})
    updated["importance"] = importance_from_strength(selected)
    updated["moraine_governance"] = {**dict(current_governance), "strength_locked": lock,
                                      "locked_by": actor if lock else None,
                                      "locked_at": str(now) if lock else None,
                                      "lock_reason": reason if lock else None,
                                      "audit": audit[-50:]}
    return {"record": updated, "persisted": False, "requires_review": True}


def unlock_strength(memory: Mapping[str, object], *, actor: str, reason: str, now: str) -> dict:
    actor = str(actor).strip()
    reason = str(reason).strip()
    if not actor or not reason or not str(now).strip():
        raise ValueError("actor, reason and now are required")
    governance = memory.get("moraine_governance") if isinstance(memory.get("moraine_governance"), Mapping) else {}
    if governance.get("strength_locked") is not True:
        raise ValueError("strength is not locked")
    updated = dict(memory)
    audit = list(governance.get("audit") or [])
    audit.append({"action": "manual_strength_unlocked", "actor": actor, "at": str(now), "reason": reason,
                  "strength": strength_from_importance(memory.get("importance"))})
    updated["moraine_governance"] = {**dict(governance), "strength_locked": False,
                                      "unlocked_by": actor, "unlocked_at": str(now),
                                      "unlock_reason": reason, "audit": audit[-50:]}
    return {"record": updated, "persisted": False, "requires_review": True}


def simulate_strengths(memories: Iterable[Mapping[str, object]], policy: GovernancePolicy | None = None) -> dict:
    suggestions = [suggest_strength(memory, policy) for memory in memories]
    current_bands = {label: 0 for _, _, label in BANDS}
    suggested_bands = {label: 0 for _, _, label in BANDS}
    for suggestion in suggestions:
        if suggestion["current_strength"] is not None:
            current_bands[band_for(suggestion["current_strength"])] += 1
        suggested_bands[suggestion["band"]] += 1
    return {"mode": "read_only_simulation", "method": "metadata_strength_v1", "count": len(suggestions),
            "current_distribution": current_bands, "suggested_distribution": suggested_bands,
            "suggestions": suggestions}


def migration_preview(memories: Iterable[Mapping[str, object]], mode: str = "simulate", *,
                      only_missing: bool = False, policy: GovernancePolicy | None = None) -> dict:
    """Preview import behavior without persisting or mutating caller-owned rows."""
    if mode not in {"preserve", "simulate", "auto_assign", "unassigned"}:
        raise ValueError("unsupported migration mode")
    rows = [dict(memory) for memory in memories]
    suggestions = {item["id"]: item for item in simulate_strengths(rows, policy)["suggestions"]}
    output = []
    for row in rows:
        suggestion = suggestions[str(row.get("id") or "")]
        current = strength_from_importance(row.get("importance"))
        process = not only_missing or current is None
        if mode == "preserve" or not process:
            selected = current
        elif mode == "unassigned":
            selected = None
        else:
            selected = suggestion["suggested_strength"]
        output.append({"id": suggestion["id"], "current_strength": current,
                       "suggested_strength": suggestion["suggested_strength"], "selected_strength": selected,
                       "would_write": mode == "auto_assign" and process and not suggestion["requires_review"],
                       "requires_review": suggestion["requires_review"]})
    return {"mode": mode, "only_missing": only_missing, "count": len(output),
            "records": output, "persisted": False}
