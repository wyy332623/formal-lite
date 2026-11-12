#!/usr/bin/env python3
"""Personal formal runner; Python standard library only on the host."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def linux_path(path):
    text = str(Path(path).resolve())
    if os.name != "nt":
        return text
    match = re.fullmatch(r"([A-Za-z]):[\\/](.*)", text)
    if not match:
        raise ValueError("Use a local Windows drive, not a UNC path: " + text)
    return "/mnt/" + match[1].lower() + "/" + match[2].replace("\\", "/")


def worker(config, action, *paths):
    args = ["/usr/bin/python3", linux_path(ROOT / "worker.py"), action,
            linux_path(ROOT / "workspace.json"), *[linux_path(p) for p in paths]]
    if os.name == "nt":
        args = ["wsl.exe", "--distribution", config["wsl_distribution"], "--exec", *args]
    process = subprocess.run(args, cwd=ROOT, capture_output=True)
    def decode(data):
        # wsl.exe emits some Windows-side startup diagnostics in UTF-16LE.
        encoding = "utf-16-le" if data.count(b"\x00") > len(data) // 8 else "utf-8"
        return data.decode(encoding, errors="replace").lstrip("\ufeff")
    if process.stdout:
        print(decode(process.stdout).rstrip(), flush=True)
    if process.stderr:
        diagnostic = decode(process.stderr)
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        with (cache / "runtime-diagnostics.log").open("a", encoding="utf-8") as log:
            log.write(datetime.now().isoformat() + " " + action + "\n" + diagnostic + "\n")
        if process.returncode:
            print(diagnostic.rstrip(), file=sys.stderr)
    return process.returncode


def load_case(name):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Invalid case name")
    case_dir = ROOT / "cases" / name
    case = read_json(case_dir / "case.json")
    if not case.get("enabled", True):
        raise ValueError("NEEDS_CONFIGURATION: " + case.get("configuration_needed", name))
    return case_dir, case


def run_case(config, name, task, depth=None, timeout=None):
    case_dir, case = load_case(name)
    if task not in case["tasks"]:
        raise ValueError("Unknown task: " + task)
    selection = case["tasks"][task]
    if selection.get("expected_raw_status", "PASS") not in ("PASS", "FAIL"):
        raise ValueError("Only PASS or an explicit expected FAIL may count as an accepted result")
    mode = selection["mode"]
    if mode not in ("bmc", "prove", "cover"):
        raise ValueError("Unsupported task mode")
    depth = depth or selection.get("depth", config["default_depth"])
    timeout = timeout or selection.get("timeout_seconds", config["default_timeout_seconds"])
    if depth <= 0 or timeout <= 0:
        raise ValueError("Depth and timeout must be positive")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "results" / name / (stamp + "-" + task + "-" + uuid.uuid4().hex[:6])
    files = []
    destinations = set()
    # Validate all inputs before creating a partial result directory.
    for entry in case["files"]:
        entry = {"path": entry} if isinstance(entry, str) else entry
        source = (case_dir / entry["path"]).resolve()
        dest = entry.get("dest", source.name)
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", dest) or ".." in PurePosixPath(dest).parts or dest.startswith("/"):
            raise ValueError("Unsafe or unsupported staging path: " + dest)
        if dest in destinations or not source.is_file():
            raise ValueError("Duplicate destination or missing source: " + str(source))
        destinations.add(dest)
        files.append((source, dest, entry.get("read", source.suffix in (".v", ".sv"))))
    top = case["top"]
    defines = case.get("defines", []) + selection.get("defines", [])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top):
        raise ValueError("Invalid top name")
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(=[A-Za-z0-9_]+)?", d) for d in defines):
        raise ValueError("Invalid define")
    includes = case.get("include_dirs", [])
    if any(not re.fullmatch(r"[A-Za-z0-9_./-]+", d) or ".." in PurePosixPath(d).parts or d.startswith("/") for d in includes):
        raise ValueError("Include directories must refer to staged relative directories")
    run_dir.mkdir(parents=True)
    manifest = []
    for source, dest, read in files:
        target = run_dir / "src" / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append({"path": str(source), "staged_as": dest,
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    flags = " ".join(["-D" + d for d in defines] + ["-I" + d for d in includes])
    sources = " ".join(dest for _, dest, should_read in files if should_read)
    if not sources:
        raise ValueError("Case has no readable RTL source")
    solver = config["solver"]
    if solver not in ("z3", "boolector", "yices", "bitwuzla"):
        raise ValueError("Unsupported solver configuration")
    engine = selection.get("engine", "smtbmc " + solver)
    if engine not in ("abc pdr", "smtbmc z3", "smtbmc boolector", "smtbmc yices", "smtbmc bitwuzla"):
        raise ValueError("Unsupported proof engine")
    text = (f"[options]\nmode {mode}\ndepth {depth}\ntimeout {timeout}\n" +
            ("cover_assert on\n" if mode == "cover" else "") +
            f"\n[engines]\n{engine}\n\n[script]\n" +
            f"read_verilog -formal -sv {flags} {sources}\nprep -top {top}\n\n[files]\n" +
            "\n".join(f"{dest} src/{dest}" for _, dest, _ in files) + "\n")
    (run_dir / "case.sby").write_text(text, encoding="utf-8")
    assumptions = case.get("assumptions_file")
    if assumptions:
        shutil.copy2(case_dir / assumptions, run_dir / "assumptions.md")
    request = {"case": name, "task": task, "mode": mode, "depth": depth,
               "engine": engine,
               "timeout_seconds": timeout, "expected_raw_status": selection.get("expected_raw_status", "PASS"),
               "assumptions_file": "assumptions.md" if assumptions else None, "source_manifest": manifest}
    (run_dir / "request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
    print("Run directory: " + str(run_dir), flush=True)
    code = worker(config, "run", run_dir)
    result_file = run_dir / "result.json"
    if result_file.exists():
        result = read_json(result_file)
        (run_dir / "summary.md").write_text(
            f"# {name} / {task}\n\nStatus: **{result['status']}**\n\n" +
            f"Mode: {mode}; depth: {depth}; elapsed: {result['elapsed_seconds']} s.\n\n" +
            "BMC_PASS only covers the configured depth. PROVED applies to the configured properties and assumptions.\n\n" +
            "See result.json, request.json, assumptions.md (when present), console.log and work/ for details.\n",
            encoding="utf-8")
    return code, run_dir


def bootstrap(config):
    lock_file = ROOT / "toolchain.lock.json"
    lock = read_json(lock_file)
    archive = ROOT / ".cache" / lock["name"]
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists() or archive.stat().st_size != lock["size"]:
        partial = archive.with_suffix(archive.suffix + ".partial")
        print("Downloading pinned toolchain: " + lock["browser_download_url"], flush=True)
        request = urllib.request.Request(lock["browser_download_url"], headers={"User-Agent": "formal-lite"})
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        partial.replace(archive)
    return worker(config, "bootstrap", archive, lock_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("doctor", "bootstrap", "list", "self-test"):
        commands.add_parser(action)
    run = commands.add_parser("run")
    run.add_argument("case")
    run.add_argument("--task", default="prove")
    run.add_argument("--depth", type=int)
    run.add_argument("--timeout", type=int)
    args = parser.parse_args()
    config = read_json(ROOT / "workspace.json")
    if args.command == "doctor":
        return worker(config, "doctor")
    if args.command == "bootstrap":
        return bootstrap(config)
    if args.command == "list":
        for path in sorted((ROOT / "cases").glob("*/case.json")):
            case = read_json(path)
            print(path.parent.name + ": " + ("READY" if case.get("enabled", True) else "TEMPLATE / NEEDS_CONFIGURATION"))
        return 0
    if args.command == "run":
        return run_case(config, args.case, args.task, args.depth, args.timeout)[0]
    outcomes = []
    for task in ("bmc", "prove", "cover", "fault"):
        code, directory = run_case(config, "smoke", task)
        result = read_json(directory / "result.json") if (directory / "result.json").exists() else {}
        ok = code == 0 and result.get("expected_result_observed", False)
        if task == "fault":
            ok = ok and bool(result.get("waveforms")) and result.get("raw_status") == "FAIL"
        outcomes.append({"task": task, "ok": ok, "result_dir": str(directory), "status": result.get("status", "ERROR")})
    (ROOT / "results/self-test-latest.json").write_text(json.dumps(outcomes, indent=2), encoding="utf-8")
    passed = all(item["ok"] for item in outcomes)
    print("SELF-TEST " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
