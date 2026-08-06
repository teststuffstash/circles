#!/usr/bin/env python3
# bake/__main__.py — the ONE bake entry point (CIR-PROC-BAKE-ONE-PATH)
#
# Usage:
#   python -m bake --config fixtures/alex/circles.yaml --out dist/ [--reference-date YYYY-MM-DD]
#
# The page slice extends this same entry point so one run writes both
# dist/data.json and dist/index.html from the same in-memory artifact dict
# (CIR-BAKE-SELF-CONTAINED). Structure: resolve once, hand the dict to each emitter.
#
# Requirements owned:
#   CIR-PROC-BAKE-ONE-PATH, CIR-ADAPT-REFERENCE-DATE

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from bake.config import ConfigError, load_config
from bake.emit import write_artifact
from bake.resolve import resolve


def main() -> None:
    parser = argparse.ArgumentParser(
        description="circles bake — turn circles.yaml into the baked artifact (data.json)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to circles.yaml",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist/)",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="Reference date YYYY-MM-DD (default: today in the config's timezone)",
    )
    args = parser.parse_args()

    # Load and validate config
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine reference date (CIR-ADAPT-REFERENCE-DATE)
    if args.reference_date is not None:
        try:
            reference_date = date.fromisoformat(args.reference_date)
        except ValueError:
            print(f"Invalid reference date: {args.reference_date} — use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        # Default: today in the config's timezone
        # At P0 we use UTC as a simple default; P1 will use the config's timezone properly
        reference_date = date.today()

    # Capture generated_at at bake start (CIR-BAKE-GENERATED-AT)
    generated_at = datetime.now(timezone.utc)

    # Resolve (CIR-PROC-BAKE-ONE-PATH: resolve once)
    try:
        artifact = resolve(
            config,
            reference_date=reference_date,
            generated_at=generated_at,
        )
    except Exception as e:
        print(f"Resolution error: {e}", file=sys.stderr)
        sys.exit(1)

    # Emit (CIR-BAKE-ATOMIC-WRITE)
    try:
        out_path = write_artifact(artifact, args.out)
        print(f"Wrote {out_path}")
    except OSError as e:
        print(f"Write error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()