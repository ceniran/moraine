# Caller integration

Moraine deliberately returns IDs and scores instead of full private document
objects. The caller remains responsible for authorization, fetching content,
keyword matching, ranking policy, and fallbacks.

A resilient retrieval chain looks like this:

1. Run exact-keyword retrieval in the authoritative memory store.
2. Ask Moraine for semantic candidates with a short timeout.
3. Resolve returned IDs against the authoritative store; ignore missing or
   inactive IDs.
4. Fuse exact-keyword and semantic candidates using a deterministic policy.
5. If Moraine is unavailable or returns no valid IDs, call the previous cloud
   semantic retriever.
6. If both semantic paths fail, return exact-keyword results rather than
   failing the memory request.

Example pseudocode:

```text
keyword = store.keyword_search(query)

try:
    semantic = resolve_ids(moraine.search(query, timeout=2.5s))
    if not semantic:
        semantic = cloud.search(query)
except:
    try:
        semantic = cloud.search(query)
    except:
        semantic = []

return fuse(keyword, semantic)
```

Do not let a local embedding model become the only path to retrieval. A smaller
model can be unavailable, can rank a name poorly, and can require a complete
rebuild after a model change. Literal matching and a tested rollback path are
part of the design, not optional polish.
