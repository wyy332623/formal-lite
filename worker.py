#!/usr/bin/env python3
"""Linux/WSL worker for toolchain checks, installation, and running SBY."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import tempfile
import time


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def child_env(suite):
    env = os.environ.copy()
    env["PATH"] = str(suite / "bin") + os.pathsep + env.get("PATH", "")
    return env


def doctor(config):
    suite = Path(config["toolchain_root"]).expanduser()
    tools = {}
    for name, args in [("yosys", ["-V"]), ("sby", ["--version"]), (config["solver"], ["--version"])]:
        exe = suite / "bin" / name
        if not exe.is_file():
            tools[name] = {"ok": False, "path": str(exe), "message": "missing"}
            continue
        try:
            proc = subprocess.run([str(exe), *args], env=child_env(suite), text=True,
                                  capture_output=True, timeout=20)
            tools[name] = {"ok": proc.returncode == 0, "path": str(exe),
                           "version": (proc.stdout + proc.stderr).strip()}
        except (OSError, subprocess.TimeoutExpired) as exc:
            tools[name] = {"ok": False, "path": str(exe), "message": str(exc)}
    result = {"ready": all(t["ok"] for t in tools.values()), "toolchain": str(suite), "tools": tools}
    return (0 if result["ready"] else 1), result


def bootstrap(config, archive_path, lock_path):
    archive = Path(archive_path)
    lock = read_json(lock_path)
    with archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if "sha256:" + digest != lock["digest"]:
        raise ValueError(f"Toolchain archive digest mismatch: got sha256:{digest}")
    suite = Path(config["toolchain_root"]).expanduser()
    if not suite.exists():
        suite.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=suite.parent, prefix=".install-") as staging:
            print("Extracting toolchain...", flush=True)
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(staging, filter="data")
            (Path(staging) / "oss-cad-suite").rename(suite)
    return doctor(config)


def execute(config, run_dir, mode, timeout_seconds, expected_raw_status="PASS"):
    run_dir = Path(run_dir)
    suite = Path(config["toolchain_root"]).expanduser()
    sby = suite / "bin/sby"
    if not sby.is_file():
        raise FileNotFoundError(f"sby not found at {sby}; run `python run.py bootstrap` first")

    started = time.monotonic()
    deadline_exceeded = False
    with (run_dir / "console.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(sby), "-d", "work", "case.sby"],
            cwd=run_dir,
            env=child_env(suite),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = proc.wait(timeout=timeout_seconds + 30)
        except subprocess.TimeoutExpired:
            deadline_exceeded = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                code = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait()

    status_file = run_dir / "work/status"
    parts = status_file.read_text(encoding="utf-8", errors="replace").split() if status_file.is_file() else []
    raw = "TIMEOUT" if deadline_exceeded else (parts[0].upper() if parts else "ERROR")

    pass_status = {"bmc": "BMC_PASS", "prove": "PROVED", "cover": "COVER_REACHED"}
    status = pass_status.get(mode, raw) if raw == "PASS" else raw
    if mode == "cover" and raw == "FAIL":
        status = "COVER_NOT_REACHED_OR_ASSERT_FAILED"

    accepted = (raw == expected_raw_status) and (raw != "PASS" or code == 0)
    waveforms = sorted(p.relative_to(run_dir).as_posix() for p in run_dir.glob("work/**/*.vcd"))
    result = {
        "status": status,
        "raw_status": raw,
        "returncode": code,
        "expected_raw_status": expected_raw_status,
        "accepted": accepted,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "waveforms": waveforms,
        "log": "console.log",
    }
    return (0 if accepted else 1), result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["doctor", "bootstrap", "run"])
    parser.add_argument("config")
    parser.add_argument("extra", nargs="*")
    args = parser.parse_args()
    config = read_json(args.config)

    if args.action == "doctor":
        code, result = doctor(config)
    elif args.action == "bootstrap":
        code, result = bootstrap(config, args.extra[0], args.extra[1])
    else:
        run_dir, mode, timeout = args.extra[0], args.extra[1], int(args.extra[2])
        expected = args.extra[3] if len(args.extra) > 3 else "PASS"
        code, result = execute(config, run_dir, mode, timeout, expected)

    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
