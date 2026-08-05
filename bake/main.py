"""circles bake — CLI entry point.

Reads circles.yaml, validates, resolves statuses (P0: manual: only), writes
data.json + index.html to the output directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from bake.config import load_config
from bake.resolve import resolve
from bake.artifact import build_artifact, serialize_artifact
from bake.page import render_page


def main() -> None:
    parser = argparse.ArgumentParser(description="circles bake — P0 MVP")
    parser.add_argument(
        "--config", "-c",
        default="fixtures/alex/circles.yaml",
        help="Path to circles.yaml (default: fixtures/alex/circles.yaml)",
    )
    parser.add_argument(
        "--output", "-o",
        default="public",
        help="Output directory (default: public/)",
    )
    parser.add_argument(
        "--reference-date",
        type=date.fromisoformat,
        default=None,
        help="Reference date for freshness (ISO format, default: today UTC)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output)
    ref_date = args.reference_date or date.today()

    # ── load + validate ───────────────────────────────────────────────────────
    result = load_config(str(config_path))
    for err in result.errors:
        print(f"ERROR: {err.message}", file=sys.stderr)
    if result.errors:
        sys.exit(1)

    # Print warnings
    for w in result.warnings:
        print(f"WARNING: {w.message}", file=sys.stderr)

    assert result.config is not None  # validated above

    # ── resolve statuses ──────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    resolution = resolve(result.config)

    # Print resolution warnings
    for w in resolution.warnings:
        ref = f" [{w.item_ref}]" if w.item_ref else ""
        print(f"WARNING: {w.message}{ref}", file=sys.stderr)

    # ── build artifact ────────────────────────────────────────────────────────
    artifact = build_artifact(
        result.config,
        resolution,
        config_warnings=result.warnings,
        ref_date=ref_date,
        now=now,
    )

    # ── write output ──────────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    # data.json
    data_json = serialize_artifact(artifact)
    (output_dir / "data.json").write_text(data_json)

    # index.html
    html = render_page(artifact)
    (output_dir / "index.html").write_text(html)

    print(f"Baked {config_path.name} → {output_dir}/")
    print(f"  {output_dir / 'data.json'}")
    print(f"  {output_dir / 'index.html'}")
    print(f"  reference date: {ref_date.isoformat()}")
    print(f"  generated at: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")


if __name__ == "__main__":
    main()