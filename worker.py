#!/usr/bin/env python3
"""Linux worker. Receives paths as argv, never through a generated shell command."""
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
    result = os.environ.copy()
    result["PATH"] = str(suite / "bin") + os.pathsep + result.get("PATH", "")
    return result


def doctor(config, engine=None):
    suite = Path(config["toolchain_root"]).expanduser()
    versions = {}
    checks = [("yosys", ["-V"]), ("sby", ["--version"]), (config["solver"], ["--version"])]
    if engine == "abc pdr":
        checks.append(("yosys-abc", ["-c", "version"]))
    elif engine and engine.startswith("smtbmc "):
        selected_solver = engine.split()[1]
        if selected_solver != config["solver"]:
            checks.append((selected_solver, ["--version"]))
    for name, args in checks:
        exe = suite / "bin" / name
        if not exe.is_file():
            versions[name] = {"ok": False, "path": str(exe), "message": "missing"}
            continue
        try:
            p = subprocess.run([str(exe), *args], env=child_env(suite), text=True,
                               capture_output=True, timeout=20)
            versions[name] = {"ok": p.returncode == 0, "path": str(exe),
                              "version": (p.stdout + p.stderr).strip()}
        except (OSError, subprocess.TimeoutExpired) as exc:
            versions[name] = {"ok": False, "path": str(exe), "message": str(exc)}
    return {"ready": all(v["ok"] for v in versions.values()), "toolchain": str(suite), "tools": versions}


def bootstrap(config, archive, lock):
    archive = Path(archive)
    with archive.open("rb") as archive_source:
        digest = hashlib.file_digest(archive_source, "sha256").hexdigest()
    if archive.stat().st_size != lock["size"] or "sha256:" + digest != lock["digest"]:
        raise ValueError("Toolchain archive does not match the pinned GitHub asset digest")
    suite = Path(config["toolchain_root"]).expanduser()
    if not suite.exists():
        suite.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=suite.parent, prefix=".install-") as staging:
            print("Verified archive SHA-256; extracting isolated toolchain...", flush=True)
            with tarfile.open(archive, "r:gz") as package:
                package.extractall(staging, filter="data")
            candidate = Path(staging) / "oss-cad-suite"
            for name in ("yosys", "sby", config["solver"]):
                if not (candidate / "bin" / name).is_file():
                    raise ValueError("Incomplete toolchain: " + name)
            candidate.rename(suite)
    result = doctor(config)
    (suite.parent / "installation.json").write_text(json.dumps({"asset": lock, "doctor": result}, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


def execute(config, run_dir):
    run_dir = Path(run_dir)
    request = read_json(run_dir / "request.json")
    suite = Path(config["toolchain_root"]).expanduser()
    inspection = doctor(config, request.get("engine"))
    if not inspection["ready"]:
        raise RuntimeError("Toolchain is not ready; run bootstrap/doctor first")
    started = time.monotonic()
    deadline_exceeded = False
    with (run_dir / "console.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(suite / "bin/sby"), "-d", "work", "case.sby"],
                                   cwd=run_dir, env=child_env(suite), stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=request["timeout_seconds"] + 30)
        except subprocess.TimeoutExpired:
            deadline_exceeded = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
    status_file = run_dir / "work/status"
    raw = status_file.read_text().strip().split()[0] if status_file.exists() else "ERROR"
    raw = "TIMEOUT" if deadline_exceeded else raw.upper()
    status = raw
    if raw == "PASS":
        status = {"bmc": "BMC_PASS", "prove": "PROVED", "cover": "COVER_REACHED"}[request["mode"]]
    if request["mode"] == "cover" and raw == "FAIL":
        status = "COVER_NOT_REACHED_OR_ASSERT_FAILED"
    expected = request["expected_raw_status"]
    accepted = raw == expected and ((raw == "PASS" and code == 0) or raw != "PASS")
    result = {"case": request["case"], "task": request["task"], "mode": request["mode"],
              "engine": request.get("engine"),
              "status": status, "raw_status": raw, "returncode": code,
              "expected_raw_status": expected, "expected_result_observed": accepted,
              "depth": request["depth"], "timeout_seconds": request["timeout_seconds"],
              "elapsed_seconds": round(time.monotonic() - started, 3), "tools": inspection["tools"],
              "source_manifest": request["source_manifest"],
              "source_metadata": request.get("source_metadata"),
              "defines": request.get("defines", []),
              "case_config_sha256": request.get("case_config_sha256"),
              "waveforms": [str(p.relative_to(run_dir)) for p in run_dir.glob("work/**/*.vcd")],
              "assumptions_file": request.get("assumptions_file"), "log": "console.log"}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "expected_result_observed": accepted,
                      "elapsed_seconds": result["elapsed_seconds"], "waveforms": result["waveforms"]}))
    return 0 if accepted else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["doctor", "bootstrap", "run"])
    parser.add_argument("config")
    parser.add_argument("extra", nargs="*")
    args = parser.parse_args()
    config = read_json(args.config)
    if args.action == "doctor":
        result = doctor(config)
        print(json.dumps(result, indent=2))
        return 0 if result["ready"] else 1
    if args.action == "bootstrap":
        return bootstrap(config, args.extra[0], read_json(args.extra[1]))
    return execute(config, args.extra[0])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), flush=True)
        raise SystemExit(2)
