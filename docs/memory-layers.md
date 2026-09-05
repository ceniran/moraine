# Memory layers: episodes, temporal validity, and core projection

Moraine remains a derived, rebuildable layer. The authoritative store owns memory text,
versions, review decisions, and lifecycle state. The contracts below only produce
review candidates or prompt projections; they do not activate, rewrite, or delete memory.

## Episode candidates

`build_episode_candidates()` groups records sharing source type/reference, workspace, and
project when consecutive observations fall within a configurable 30–60 minute window.
Every group remains `pending_review`. Grouping is not a claim that the records are
duplicates: review may promote a fact, supplement an existing record, relate separate
events, supersede an older fact, or retain the raw episode.

An integration should initially store the raw conversation outside the active long-term
fact set. A language model may propose a relationship, but only the authoritative store's
review path may create or supersede an active record.

## Bi-temporal boundary

`valid_from` and `valid_to` describe when a fact is true in the represented world. They
are separate from `created_at` and `updated_at`, which describe when the system recorded
or changed a record. Validity uses a half-open interval: `valid_from <= t < valid_to`.
Moraine indexes only records that are both `state=active` and valid at the refresh time.
Historical questions should hydrate authoritative history rather than revive inactive
vectors as current facts.

## Core projection

High strength alone does not make a record permanently present. A record enters the
projection only when governance explicitly sets `core_presence: always`, it is active,
it is currently valid, it belongs to the requested workspace, it is not contested, and
its sensitivity is not `secret`. Missing sensitivity is treated as `private` for backward
compatibility; generic core projection never accepts secret text. `build_core_projection()` selects whole blocks under a strict
character budget and returns source IDs plus skipped IDs. It never silently truncates a
record and never becomes a second source of truth.

The projection is intended for a very small set of current identity, boundary, and
operating-context records. Events and ordinary project logs continue through retrieval.
