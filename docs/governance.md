# Memory governance preview

Moraine's governance module represents **memory strength** from `0` to `100`.
Storage adapters may keep the existing `0..1` `importance`; conversion remains
compatible at two decimal places.

The first policy is deterministic and metadata-only. It never needs memory
content or a text model. Kind supplies a starting point, while explicit
protection, confirmed useful use, priority, and identity weight may adjust it.
Every adjustment is returned as a reason.

Automatic policy is capped at `79`: software may recommend that a memory is
important, but it cannot declare a memory core. Strengths from `80` through
`100` are assigned manually. They may be locked with an actor, timestamp, and
reason; locked strength is excluded from later automatic reassignment. Changing
a locked value requires an explicit, audited unlock first. Locking does not
prevent review, supersession, or archival of the memory itself.

| Kind | Default strength |
| --- | ---: |
| context | 15 |
| status | 20 |
| event | 30 |
| reflection | 35 |
| project | 40 |
| preference | 45 |
| decision | 50 |
| relationship | 50 |
| identity | 70 |

`simulate_strengths()` compares current and suggested distributions without
changing records. `migration_preview()` supports `preserve`, `simulate`,
`auto_assign`, and `unassigned`, plus an `only_missing` scope. Even in
`auto_assign`, identity, relationship, and explicitly protected memories remain
review-only. Every preview reports `persisted: false`.
