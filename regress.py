#!/usr/bin/env python3
"""Run a named multi-module regression and retain every individual outcome."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import uuid

import run


def main():
    plan = run.read_json(run.ROOT / "regression.json")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=plan, default="quick")
    args = parser.parse_args()
    config = run.read_json(run.ROOT / "workspace.json")
    if run.worker(config, "doctor"):
        return 2
    outcomes = []
    for case, task in plan[args.profile]:
        print(f"\nChecking {case}/{task}", flush=True)
        try:
            code, directory = run.run_case(config, case, task)
            result_path = directory / "result.json"
            result = run.read_json(result_path) if result_path.exists() else {}
            accepted = code == 0 and result.get("expected_result_observed", False)
            if result.get("expected_raw_status") == "FAIL":
                accepted = accepted and result.get("raw_status") == "FAIL" and any(
                    (directory / wave).is_file() for wave in result.get("waveforms", []))
            item = {"case": case, "task": task, "status": result.get("status", "ERROR"),
                    "accepted": accepted, "expected_raw_status": result.get("expected_raw_status"),
                    "result_dir": str(directory.relative_to(run.ROOT)).replace("\\", "/"),
                    "elapsed_seconds": result.get("elapsed_seconds")}
        except (OSError, ValueError, KeyError) as exc:
            item = {"case": case, "task": task, "status": "ERROR", "accepted": False, "error": str(exc)}
        outcomes.append(item)
    passed = all(item["accepted"] for item in outcomes)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    directory = run.ROOT / "results/regress" / (stamp + "-" + args.profile)
    directory.mkdir(parents=True)
    report = {"profile": args.profile, "selection": plan[args.profile], "accepted": passed,
              "source_lock": run.read_json(run.ROOT / "sources.lock.json"), "outcomes": outcomes}
    (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {args.profile} regression", "", "Accepted: " + str(passed), "",
             "Expected checker FAIL is a sensitivity check, not a design pass.", "",
             "| Case | Task | Status | Expected | Accepted |", "| --- | --- | --- | --- | --- |"]
    lines.extend(f"| {v['case']} | {v['task']} | {v['status']} | {v.get('expected_raw_status', '')} | {v['accepted']} |" for v in outcomes)
    (directory / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines) + "\nReport: " + str(directory))
    return 0 if passed else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
