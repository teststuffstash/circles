# process — test tiers and requirement linkage

This page records the ruled test-tier terminology the goal issue quotes. It is recorded, not
re-litigated: the tiers are the contract the builder's tests must fit into.

## Test tiers

- **unit** — pure logic, no real components: e.g. status resolution, freshness window math,
  command-output parsing, share normalization. Runs fast, no cluster.
- **system testing** — logic against real components in a local cluster (kind): e.g. the bake
  job reading a real git repo of dated notes, the page served by the real nginx image and
  fetched over HTTP. Runs in a kind cluster.
- **e2e** — the actual target environment: the deployed page in the homelab cluster, hit over
  its real ingress. Runs in CI against the real deployment.

A requirement is "unit-tested", "system-tested", or "e2e-tested" only when a test at that tier
actually exercises it. Verified-ness is derived from a linked test, never declared by a status
marker.

## How decision-table rows link to tests

Every decision-table row in `specs/` has a `description` that is usable as a test id verbatim.
The doctrine (same as the fixture doctrine):

1. A parametrized test loads the relevant decision table (or the fixture person's rows) and
   asserts the behavior per row, using the row's `description` as the test id.
2. New cases are **rows** in the table, not copy-pasted test functions.
3. Test inputs are built **from the row at runtime** — no hidden/binary fixtures.
4. A requirement without a linked test row is simply unevidenced; the linkage is added by the
   builder later, never fabricated in the spec.

### CIR-PROC-TEST-TIERS — tier assignment
Each requirement's testability is stated by which tier it belongs to. Pure-logic requirements
(data resolution, freshness math) are unit-tier; anything touching a real component (bake over a
real repo, page over the real image) is system-tier; the deployed page is e2e-tier. Phase: P0.

### CIR-PROC-TABLE-LINKAGE — rows become test ids
A decision-table row's `description` is a stable test id; the parametrized test that loads the
table uses it verbatim. Adding a behavior means adding a row, not a new test function. Phase: P0.

## ⚖ AMBIGUITY entries

### ⚖ PROC-1 — where the gate grows
The goal says product lint/test steps are ADDED to `scripts/ci.sh` as the product lands, but
does not say which tier runs in the local `devbox run ci` gate vs CI.
- Options: (a) `devbox run ci` runs unit + chart tests locally; system/e2e run only in CI;
  (b) `devbox run ci` runs everything including a kind cluster.
- **Recommendation: (a)** — keep the local gate fast (unit + chart); system/e2e need a cluster
  and belong in CI. This keeps `devbox run ci` green in this ride (no docker/kind here) while
  the spec's testability is still served. Flagged as a PR Follow-up for the operator to ratify
  the exact gate split.
