# CLAUDE.md — circles (circles stack)

A life-areas status page: one self-contained HTML page (a sunburst of rings/items with
traffic-light freshness colors) built from data files in this repo, shipped as an nginx image +
Helm chart. **Spec-first repo**: `specs/` is the contract — product code converges on the specs,
not the other way around. The repo is currently at the vanilla-bootstrap stage (new-stack
2026-08-03): the chart/Dockerfile/public hello page prove the deploy pipeline end-to-end; the
real page arrives via the specs and the goal issue.

## Read order

1. `specs/README.md` — the spec tree + conventions (requirement IDs, decision tables).
2. `chart/` — the deployable unit (values.schema.json is authoritative for values).
3. `scripts/` — the CI gate + build/deploy seams (`ci.sh` is the one place the gate grows).

## The CI gate

`devbox run ci` must be green before ANY PR (currently: chart validation + chart unit tests —
product lint/tests are added to `scripts/ci.sh` as the product lands). `devbox run scan-secrets`
must be clean. CI YAML is thin by convention: all logic lives in `devbox run <task>`.

## Invariants

- **This repo is PUBLIC. Committed data is SYNTHETIC only** — the fixture person under
  `fixtures/` is invented and doubles as the spec's key examples. Real people's data is
  deploy-time content and must NEVER be committed here.
- **Chart-is-deployable-unit**: `deploy.yaml` stamps chart version == appVersion == image tag
  (`2026.<m>.<d>-g<sha>`); circles-iac pins ONLY the chart version.
- The vanilla Dockerfile/public page is a placeholder — replace it via specs, never grow it
  in place.
- Workers clone ONLY this repo; the dispatched issue carries all cross-repo context.

## Related repos

- https://github.com/teststuffstash/circles-iac — the stack's deployment truth (app-of-apps,
  AgentStack claim, version pins). Deploys are automated bump PRs opened by `deploy.yaml`.
- https://github.com/teststuffstash/homelab — the platform (cluster, agent loop, CI runners).
