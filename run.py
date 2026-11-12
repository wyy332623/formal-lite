#!/usr/bin/env python3
"""Formal verification platform CLI."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid

import worker

ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def linux_path(path):
    text = str(Path(path).resolve())
    if os.name != "nt":
        return text
    match = re.fullmatch(r"([A-Za-z]):[\\/](.*)", text)
    if not match:
        raise ValueError("Use a local Windows drive path, not UNC: " + text)
    return "/mnt/" + match[1].lower() + "/" + match[2].replace("\\", "/")


def decode_output(data):
    encoding = "utf-16-le" if data.count(b"\x00") > len(data) // 8 else "utf-8"
    return data.decode(encoding, errors="replace").lstrip("\ufeff")


def invoke_worker(config, action, *args):
    if os.name != "nt":
        if action == "doctor":
            return worker.doctor(config)
        if action == "bootstrap":
            return worker.bootstrap(config, args[0], args[1])
        return worker.execute(config, args[0], args[1], int(args[2]), args[3])

    cmd = [
        "wsl.exe", "--distribution", config["wsl_distribution"], "--exec",
        "/usr/bin/python3", linux_path(ROOT / "worker.py"), action,
        linux_path(ROOT / "workspace.json"),
        *[linux_path(a) if isinstance(a, Path) else str(a) for a in args],
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True)
    stdout = decode_output(proc.stdout).strip()
    stderr = decode_output(proc.stderr).strip()
    if stderr and proc.returncode:
        print(stderr, file=sys.stderr)
    if not stdout:
        raise RuntimeError(stderr or f"worker {action} exited with code {proc.returncode}")
    # bootstrap may print progress lines before the final JSON payload.
    json_start = stdout.find("{")
    if json_start == -1:
        raise RuntimeError(stdout)
    if json_start > 0:
        print(stdout[:json_start].rstrip(), flush=True)
    return proc.returncode, json.loads(stdout[json_start:])


def load_case(name):
    case_dir = ROOT / "cases" / name
    case_file = case_dir / "case.json"
    if not case_file.is_file():
        raise FileNotFoundError(f"Case not found: {name}")
    return case_dir, read_json(case_file)


def run_case(config, name, task="prove", depth=None, timeout=None, engine=None):
    case_dir, case = load_case(name)
    tasks = case["tasks"]
    if task not in tasks:
        available = ", ".join(tasks)
        raise KeyError(f"Unknown task '{task}' for case '{name}' (available: {available})")

    selection = tasks[task]
    mode = selection["mode"]
    depth = selection.get("depth", config["default_depth"]) if depth is None else depth
    timeout = selection.get("timeout_seconds", config["default_timeout_seconds"]) if timeout is None else timeout
    engine = engine or selection.get("engine") or f"smtbmc {config['solver']}"
    expected = selection.get("expected_raw_status", "PASS")
    defines = case.get("defines", []) + selection.get("defines", [])
    includes = case.get("include_dirs", [])

    files = []
    for entry in case["files"]:
        entry = {"path": entry} if isinstance(entry, str) else entry
        source = (case_dir / entry["path"]).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Missing source file: {source}")
        dest = entry.get("dest", source.name)
        read = entry.get("read", source.suffix in (".v", ".sv"))
        files.append((source, dest, read))

    sources = [dest for _, dest, should_read in files if should_read]
    if not sources:
        raise ValueError(f"Case '{name}' has no readable RTL source")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "results" / name / f"{stamp}-{task}-{uuid.uuid4().hex[:6]}"
    run_dir.mkdir(parents=True)

    for source, dest, _ in files:
        target = run_dir / "src" / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    flags = ["-D" + d for d in defines] + ["-I" + d for d in includes]
    read_cmd = " ".join(["read_verilog -formal -sv", *flags, *sources])
    cover_opt = "cover_assert on\n" if mode == "cover" else ""
    sby_text = (
        f"[options]\nmode {mode}\ndepth {depth}\ntimeout {timeout}\n{cover_opt}\n"
        f"[engines]\n{engine}\n\n"
        f"[script]\n{read_cmd}\nprep -top {case['top']}\n\n"
        f"[files]\n" + "\n".join(f"{dest} src/{dest}" for _, dest, _ in files) + "\n"
    )
    (run_dir / "case.sby").write_text(sby_text, encoding="utf-8")

    print(f"Running {name}/{task} -> {run_dir}", flush=True)
    code, payload = invoke_worker(config, "run", run_dir, mode, timeout, expected)
    result = {
        "case": name,
        "task": task,
        "mode": mode,
        "engine": engine,
        "depth": depth,
        "timeout_seconds": timeout,
        **payload,
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "accepted": result["accepted"],
        "elapsed_seconds": result["elapsed_seconds"],
        "waveforms": result["waveforms"],
    }))
    return code, run_dir, result


def cmd_bootstrap(config):
    lock_file = ROOT / "toolchain.lock.json"
    lock = read_json(lock_file)
    archive = ROOT / ".cache" / lock["name"]
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists() or archive.stat().st_size != lock["size"]:
        partial = archive.with_suffix(archive.suffix + ".partial")
        print("Downloading toolchain: " + lock["browser_download_url"], flush=True)
        req = urllib.request.Request(lock["browser_download_url"], headers={"User-Agent": "formal-lite"})
        with urllib.request.urlopen(req, timeout=60) as resp, partial.open("wb") as out:
            shutil.copyfileobj(resp, out, length=1024 * 1024)
        partial.replace(archive)
    code, result = invoke_worker(config, "bootstrap", archive, lock_file)
    print(json.dumps(result, indent=2))
    return code


def cmd_list():
    for path in sorted((ROOT / "cases").glob("*/case.json")):
        case = read_json(path)
        print(f"{path.parent.name}: {', '.join(case.get('tasks', {}))}")
    return 0


def cmd_self_test(config):
    passed = True
    for task in ("bmc", "prove", "cover", "fault"):
        code, _, result = run_case(config, "smoke", task)
        ok = code == 0 and result.get("accepted", False)
        if task == "fault":
            ok = ok and result.get("raw_status") == "FAIL" and bool(result.get("waveforms"))
        passed = passed and ok
    print("SELF-TEST " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("doctor", "bootstrap", "list", "self-test"):
        commands.add_parser(action)
    run_cmd = commands.add_parser("run")
    run_cmd.add_argument("case")
    run_cmd.add_argument("--task", default="prove")
    run_cmd.add_argument("--depth", type=int)
    run_cmd.add_argument("--timeout", type=int)
    run_cmd.add_argument("--engine")
    args = parser.parse_args()

    config = read_json(ROOT / "workspace.json")
    if args.command == "doctor":
        code, result = invoke_worker(config, "doctor")
        print(json.dumps(result, indent=2))
        return code
    if args.command == "bootstrap":
        return cmd_bootstrap(config)
    if args.command == "list":
        return cmd_list()
    if args.command == "run":
        return run_case(config, args.case, args.task, args.depth, args.timeout, args.engine)[0]
    return cmd_self_test(config)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
