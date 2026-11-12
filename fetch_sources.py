#!/usr/bin/env python3
"""Fetch pinned upstream RTL sources listed in sources.lock.json."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def fetch():
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    target = (ROOT / lock["directory"]).resolve()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-checkout", lock["remote"], str(target)], check=True)
        if "core.autocrlf" in lock:
            autocrlf = "true" if lock["core.autocrlf"] else "false"
            subprocess.run(["git", "-C", str(target), "config", "core.autocrlf", autocrlf], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", lock["commit"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    if actual != lock["commit"]:
        raise RuntimeError(f"Existing checkout at {target} is {actual}, expected {lock['commit']}")
    print("Sources ready: " + lock["commit"])
    return 0


if __name__ == "__main__":
    sys.exit(fetch())
