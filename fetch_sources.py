#!/usr/bin/env python3
"""Fetch the pinned, unmodified RTL input; never update an existing checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def fetch():
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    target = (ROOT / lock["directory"]).resolve()
    if not target.is_relative_to(ROOT / "sources"):
        raise ValueError("Source checkout must stay inside sources/")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-checkout", lock["remote"], str(target)], check=True)
        # The historical Windows input has CRLF, including a blob stored as LF.
        # Explicitly reproduce that checkout on every host; never depend on the
        # user's global Git newline settings.
        autocrlf = "true" if lock["checkout"]["core.autocrlf"] else "false"
        subprocess.run(["git", "-C", str(target), "config", "core.autocrlf", autocrlf], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", lock["commit"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    if actual != lock["commit"]:
        raise ValueError("Existing checkout has a different commit; it was not changed")
    for relative, expected in lock["sha256"].items():
        actual_hash = hashlib.sha256((target / relative).read_bytes()).hexdigest()
        if actual_hash != expected:
            raise ValueError("Input hash mismatch: " + relative + "; checkout was not changed")
        blob = subprocess.check_output(["git", "-C", str(target), "show", "HEAD:" + relative])
        if hashlib.sha256(blob).hexdigest() != lock["git_blob_sha256"][relative]:
            raise ValueError("Git blob hash mismatch: " + relative)
    print("Pinned RTL ready: " + lock["commit"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(fetch())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(2)
