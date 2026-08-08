# ADR-005: Client Identity & Matching Strategy

## Status
Accepted.

## Context
Sprint 3 (Relationship Memory) requires deciding whether two mentions of a
person across separate conversations refer to the same real-world client.
Get this wrong in one direction (false merge) and a Realtor sees another
client's private preferences attached to the wrong name. Get it wrong in
the other direction (false negative) and the product simply fails to
remember someone it already met — a worse UX, but not a trust-destroying
one. This asymmetry is why the Founder's decision (FD-003) explicitly
biases toward precision over recall: *"Never auto-merge on name alone.
Require at least one corroborating attribute for automatic reconciliation."*

ADR-001 provisioned pgvector specifically "for future semantic
memory/search," which made semantic/embedding-based matching an available
option, not just a deterministic one — this ADR is the record of choosing
between them for Sprint 3 specifically, not a claim that semantic matching
is wrong in general.

## Decision
**Deterministic matching**: a `Person` extracted from a conversation
matches an existing `Client` only if both the normalized name (case-
insensitive, trimmed) and the role (e.g. "buyer", "seller") match exactly.
If role is absent on either side, no automatic match is attempted — a new
`Client` is created instead of guessing. This is `ClientService.
find_or_create` in `app/client/service.py`.

No new provider abstraction (e.g. an `EmbeddingProvider` sibling to
`AIProvider`/`TranscriptionProvider`) was introduced. Semantic matching
remains available as a future option per ADR-001's original reasoning, not
foreclosed by this decision — just not chosen for Sprint 3.

## Alternatives Considered
1. **Semantic/embedding matching** (pgvector similarity over person
   mentions) — higher recall potential, could catch name variations
   ("Jane Smith" vs. "J. Smith"), but meaningfully more complex, harder to
   explain/audit when it gets something wrong, and — discovered during
   implementation, not anticipated in the original spec — Sprint 2's
   extraction doesn't yet produce anything richer than a bare name to
   embed against, so the recall advantage wouldn't have materialized
   without also changing Sprint 2's extraction. Deferred, not rejected.
2. **Match on name alone** — explicitly ruled out by FD-003. Real estate
   conversations plausibly involve common names; matching on name alone
   would produce confident-looking but wrong client profiles, which is a
   worse failure mode than the current "doesn't recognize a returning
   client" gap, because a wrong profile actively misleads a Realtor rather
   than just failing to help them.
3. **Deterministic, name + role required** (chosen) — conservative,
   explainable, auditable (a human can look at two rows and understand
   exactly why they did or didn't match), and needs no new infrastructure.

## Consequences
- **The corroborating "role" signal doesn't actually exist in production
  data yet.** Sprint 2's `ExtractionResult.people` is `list[str]` — names
  only. `Person.role` is a schema column that nothing currently populates.
  This means Sprint 3's matching logic is correct but **currently inert**
  against real conversations: every reconciliation creates a new client
  rather than ever matching one. This was discovered during Sprint 3's
  implementation, not anticipated in the approved spec, and is the single
  most important open item for Sprint 4 — see `Sprint3.md`'s Technical
  Debt (TD-006).
- Extending extraction to capture role (or, for a stronger signal,
  email/phone) is explicitly future work, not bundled into this ADR or
  this sprint — doing so would have meant modifying Sprint 2's tested
  extraction prompt, which was out of Sprint 3's approved scope.
- `Client.role` stores only the *last-reconciled* role, not a history of
  roles a person has held across different deals (a client could be a
  buyer in one transaction and a seller in another). This is a real
  simplification: a person whose role changes between conversations won't
  auto-match against their own earlier record. Conservative by design
  (consistent with FD-003's precision bias), but worth revisiting if it
  proves too conservative in practice.
- Because matching happens entirely within `client/repository.py` using
  data already on `Client` (no live query against `people`), the
  `client/` slice never needs to import `memory/`'s repository directly —
  keeps the slice boundary clean per Rule 5, at the cost of `Client`
  carrying a `role` field that's a slight simplification of reality.
