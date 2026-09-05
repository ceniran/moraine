# Moraine

<p align="center">
  <img src="assets/moraine-stone.png" width="240" alt="Moraine stone mark with layered mineral veins">
</p>

[中文说明](README.zh-CN.md)

Moraine is a small local semantic index for private text collections. It
understands approximate meaning rather than requiring exact keywords, updates
changed documents incrementally, persists a resumable index, and searches on
CPU without depending on a cloud embedding quota.

Despite the name, it is not limited to an AI memory store. A "memory" can be a
book description, article, note, support ticket, game guide, email summary,
research abstract, community post, or any other text record with a stable ID.

The name comes from a moraine: fragments of stone carried together until they
form a recognizable landscape. Moraine does the same for scattered text,
turning books, notes, messages, and records into a semantic terrain that can be
searched by meaning.

This public project contains no private memories, credentials, production
paths, or relationship data. Every deployment owns its data and may give its
local instance a separate personal name.

## General capabilities

- CPU-only embeddings through FastEmbed and `BAAI/bge-small-zh-v1.5`;
- meaning-based search even when the query and document use different words;
- JSON-file and authenticated HTTP document sources;
- similarity scores that callers can use for related-item suggestions,
  thematic grouping, and duplicate detection;
- incremental fingerprint-based indexing in small, resumable batches;
- a persisted index that can resume after interruption;
- loopback HTTP endpoints for health, refresh, and semantic search;
- optional API authentication and a hardened systemd template;
- no cloud dependency in the retrieval service itself.

Moraine also includes a deliberately conservative extractive consolidator. It
can remove normalized exact duplicates and shorter sentences repeated verbatim
inside longer ones while preserving source IDs. It does not ask a language
model to rewrite facts, does not guess that paraphrases are equivalent, and
always marks its output for human review.

Keyword fusion and cloud fallback belong in the caller. The retriever returns
stable memory IDs and similarity scores so an existing memory service can merge
or fall back according to its own policy.

See [`docs/integration.md`](docs/integration.md) for the complete caller-side
retrieval chain.

## Example uses

- **Online library:** find books from remembered plot fragments, mood, themes,
  or reading preferences; recommend related books and suggest multi-label
  categories.
- **Personal knowledge base:** search notes and files without remembering their
  exact titles or wording.
- **AI memory:** retrieve earlier events, preferences, decisions, and project
  context before generating a response.
- **Research archive:** locate related papers from a natural-language question
  and group abstracts into emerging themes.
- **Support or issue tracker:** detect similar historical cases, duplicates,
  and previously successful resolutions.
- **Media or game catalog:** search by atmosphere, mechanics, narrative shape,
  or a half-remembered description.
- **Community and mail archive:** find earlier discussions that are semantically
  related to a new post or message.

Moraine works best when people know roughly *what something meant* but do not know
the exact keyword, title, filename, or classification. It is especially useful
for private or modest-sized collections where local processing, predictable
cost, and simple deployment matter more than massive distributed scale.

It should not replace a database. Exact titles, authors, ISBNs, dates, account
IDs, permissions, and numeric filters still belong in structured fields and
keyword search. The strongest design combines those exact tools with Moraine's
semantic candidates.

## Document shape

Every record needs an `id`. These optional fields improve retrieval:

```json
{
  "id": "stable-id",
  "title": "short title",
  "content": "full memory text",
  "kind": "event",
  "tags": ["example"],
  "state": "active",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

The source may be a JSON array or an object containing an `items`, `documents`,
or `memories` array. Records whose `state` is present and not `active` are
removed from the active index. Any content change causes only that record to be
re-embedded.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env

set -a
. ./.env
set +a
.venv/bin/moraine
```

On first run the model is downloaded into `MORAINE_MODEL_CACHE`. For an offline
deployment, download once, then start with `HF_HUB_OFFLINE=1`.

```bash
curl http://127.0.0.1:4781/health
curl -H "Authorization: Bearer $MORAINE_API_TOKEN" \
  "http://127.0.0.1:4781/search?query=local%20retriever&limit=5"
curl -X POST -H "Authorization: Bearer $MORAINE_API_TOKEN" \
  http://127.0.0.1:4781/refresh
curl -X POST -H "Authorization: Bearer $MORAINE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"memories":[{"id":"a","content":"Repeated fact."}]}' \
  http://127.0.0.1:4781/consolidate
```

## Production boundaries

1. Keep the service on loopback. If it must bind elsewhere, configure
   `MORAINE_API_TOKEN` and use a trusted authenticated proxy.
2. Keep source credentials in a root-readable environment file, never Git.
3. Treat `data/index.json` as private: embeddings and titles can reveal
   information about the source corpus.
4. Use a separate index directory whenever the model or dimensions change.
5. Start with batches of four under a 512-MiB service limit, then measure on
   your own machine.
6. Keep keyword search and a tested fallback path in the calling application.

The sample systemd unit in `deploy/` assumes a dedicated `moraine` user and an
installation at `/opt/moraine`. Adjust explicit paths before installing.

## Tests

The unit tests use a fake embedder and synthetic memories, so they do not
download a model or touch private data.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Read-only memory governance experiment

Moraine includes a configurable, deterministic `0..100` memory-strength policy.
It uses metadata only, explains every adjustment, compares current and suggested
distributions, and previews four import modes without persistence. Identity,
relationship, and explicitly protected records always remain subject to review.
See [`docs/governance.md`](docs/governance.md).
Automatic suggestions are capped at `79`. Core strength (`80..100`) can only be
assigned and locked manually, with actor, timestamp, reason, and an auditable
unlock path.

Episode candidates, bi-temporal validity, and bounded core projections are
documented in [`docs/memory-layers.md`](docs/memory-layers.md).

## License

MIT
