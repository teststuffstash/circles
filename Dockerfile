# circles production image — multi-stage bake-then-serve
#
# Stage 1: bake — run the circles bake against the fixture config to produce
# data.json + index.html.  The bake step runs at image-build time (P0); at P1
# the nightly scheduler runs the same bake independently.
#
# Stage 2: nginx-unprivileged — serve the baked static site.

# ── Stage 1: bake ──────────────────────────────────────────────────────────
FROM python:3.11-alpine AS bake

WORKDIR /build

# Install uv (deterministic Python toolchain, pinned via devbox)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Copy the bake module, fixture config, and project metadata
COPY bake/ bake/
COPY fixtures/ fixtures/
COPY pyproject.toml uv.lock ./

# Install dependencies (bake/ must exist on disk before uv sync so setuptools
# can discover the circles-bake package for the editable install declared in uv.lock)
RUN uv sync --frozen --no-dev

# Run the bake (P0: fixture person, reference date 2026-08-03 for reproducibility)
RUN uv run --frozen python -m bake \
    --config fixtures/alex/circles.yaml \
    --out dist/ \
    --reference-date 2026-08-03

# ── Stage 2: serve ─────────────────────────────────────────────────────────
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Copy the baked artifacts from stage 1
COPY --from=bake --chmod=644 /build/dist/ /usr/share/nginx/html/

# Copy the production nginx config (Content-Type for .json, etc.)
COPY --chmod=644 nginx.conf /etc/nginx/conf.d/default.conf
