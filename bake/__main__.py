#!/usr/bin/env python3
# bake/__main__.py — the ONE bake entry point (CIR-PROC-BAKE-ONE-PATH)
#
# Usage:
#   python -m bake --config fixtures/alex/circles.yaml --out dist/ [--reference-date YYYY-MM-DD]
#                  [--evaluate]
#
# --evaluate is the P1 (nightly) switch: freshness: adapters are evaluated against their
# sources. Without it the build-time bake behaves as at P0 — freshness:/command: items are
# ⚪ not-evaluated (CIR-PROC-BAKE-ONE-PATH: one code path, differing only in configuration).
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
from zoneinfo import ZoneInfo

from bake.config import ConfigError, load_config
from bake.emit import write_artifact
from bake.render import add_capacity_warnings, render_page
from bake.resolve import resolve


def default_reference_date(tz_name: str, now: datetime) -> date:
    """Today, derived from the instant *now* in the config's timezone — never the host's.

    CIR-ADAPT-REFERENCE-DATE#reference-date-default-is-config-timezone: an aware instant
    converted to the config's IANA zone, then reduced to its calendar date. The host `TZ`
    plays no part (CIR-BAKE-DETERMINISM#host-timezone-does-not-leak).
    """
    return now.astimezone(ZoneInfo(tz_name)).date()


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
    parser.add_argument(
        "--evaluate",
        action="store_true",
        default=False,
        help="Evaluate freshness: adapters (the nightly bake). Off: freshness/command "
             "items are grey not-evaluated, as at image-build time",
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
        # Default: today in the config's timezone (CIR-ADAPT-REFERENCE-DATE)
        try:
            reference_date = default_reference_date(config.timezone, datetime.now(timezone.utc))
        except Exception as e:  # ZoneInfoNotFoundError / ValueError on a bad zone name
            print(f"Config error: timezone '{config.timezone}' is unknown ({type(e).__name__})",
                  file=sys.stderr)
            sys.exit(1)

    # Capture generated_at at bake start (CIR-BAKE-GENERATED-AT)
    generated_at = datetime.now(timezone.utc)

    # Resolve (CIR-PROC-BAKE-ONE-PATH: resolve once)
    try:
        artifact = resolve(
            config,
            reference_date=reference_date,
            generated_at=generated_at,
            evaluate=args.evaluate,
        )
    except Exception as e:
        print(f"Resolution error: {e}", file=sys.stderr)
        sys.exit(1)

    # Add capacity/min-arc warnings (CIR-RENDER-CAPACITY, CIR-RENDER-MIN-ARC)
    artifact = add_capacity_warnings(artifact)

    # Emit data.json (CIR-BAKE-ATOMIC-WRITE)
    try:
        data_path = write_artifact(artifact, args.out)
        print(f"Wrote {data_path}")
    except OSError as e:
        print(f"Write error: {e}", file=sys.stderr)
        sys.exit(1)

    # Emit index.html from the SAME in-memory artifact (CIR-BAKE-SELF-CONTAINED)
    try:
        html_content = render_page(artifact)
        out_dir = args.out.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        html_path = out_dir / "index.html"
        html_path.write_text(html_content, encoding="utf-8")
        print(f"Wrote {html_path}")
    except OSError as e:
        print(f"Write error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()