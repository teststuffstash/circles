# bake/emit.py — atomic write of the baked artifact (CIR-BAKE-ATOMIC-WRITE)
#
# Requirements owned:
#   CIR-BAKE-ATOMIC-WRITE — temp file + rename so a half-written artifact is never observable.

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def write_artifact(artifact: dict, out_dir: Path) -> Path:
    """Atomic write of *out_dir*/data.json (CIR-BAKE-ATOMIC-WRITE).

    Writes to a temp file in the same directory, then renames atomically over
    the target. If *out_dir* does not exist it is created (parents too).

    Returns the path to the written file.
    """
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

    # Ensure the artifact is world-readable — tempfile.mkstemp() creates with
    # mode 0600 by default, but nginx-unprivileged (non-root user) needs read
    # access (CIR-BAKE-ATOMIC-WRITE#permissions-world-readable).
    target.chmod(0o644)

    return target