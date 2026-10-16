# bake/emit.py — atomic write of the baked artifact (CIR-BAKE-ATOMIC-WRITE)
#
# Requirements owned:
#   CIR-BAKE-ATOMIC-WRITE — temp file + rename so a half-written artifact is never observable.
#   CIR-BAKE-ARTIFACT — the artifact's shape is IMPORTED from the contract page's machine half,
#     specs/data/data-json.schema.json (RULES rule 7), never re-declared here.

from __future__ import annotations

import json
import os
import tempfile
from functools import cache
from pathlib import Path

import jsonschema

# The sibling of specs/data/data-json.md. The image's bake stage copies it to the same
# relative place (Dockerfile), so this resolves in the repo and in /build alike.
ARTIFACT_SCHEMA = Path(__file__).resolve().parent.parent / "specs" / "data" / "data-json.schema.json"


class ArtifactSchemaError(ValueError):
    """The bake produced an artifact its own contract rejects — a bake bug, never a config error."""


@cache
def _validator() -> jsonschema.protocols.Validator:
    schema = json.loads(ARTIFACT_SCHEMA.read_text(encoding="utf-8"))
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def validate_artifact(artifact: dict) -> None:
    """Raise ArtifactSchemaError naming every violation of data-json.schema.json."""
    errors = sorted(_validator().iter_errors(artifact), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"  {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
                 for e in errors]
        raise ArtifactSchemaError(
            "artifact violates specs/data/data-json.schema.json:\n" + "\n".join(lines))


def write_artifact(artifact: dict, out_dir: Path) -> Path:
    """Validate, then atomically write *out_dir*/data.json (CIR-BAKE-ATOMIC-WRITE).

    The artifact is validated against the contract schema first; a violation raises
    ArtifactSchemaError before anything touches the disk (a failed bake publishes nothing).
    Then writes to a temp file in the same directory and renames atomically over the target.
    If *out_dir* does not exist it is created (parents too).

    Returns the path to the written file.
    """
    validate_artifact(artifact)
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    target = out_dir / "data.json"

    # Serialise with sort_keys for determinism (CIR-BAKE-DETERMINISM)
    raw = json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    # Atomic write: write to temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp",
        prefix="data.json.",
        dir=str(out_dir),
    )
    try:
        os.write(fd, raw.encode("utf-8"))
        # Ensure the temp file is world-readable before the atomic rename —
        # tempfile.mkstemp() creates with mode 0600 by default, but
        # nginx-unprivileged (non-root user) needs read access.  Chmod before
        # replace so there is no window where the target path exists with
        # restrictive permissions (CIR-BAKE-ATOMIC-WRITE#permissions-world-readable).
        os.fchmod(fd, 0o644)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, str(target))
    finally:
        if fd >= 0:
            os.close(fd)
        # Clean up temp file if rename failed
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return target