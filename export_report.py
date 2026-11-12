#!/usr/bin/env python3
"""Export compact, versionable evidence; keep large solver working files local."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil

import run


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/main-10d248a")
    args = parser.parse_args()
    target = (run.ROOT / args.output).resolve()
    if not target.is_relative_to(run.ROOT / "reports"):
        raise ValueError("Reports must stay within reports/")
    target.mkdir(parents=True, exist_ok=True)
    config = run.read_json(run.ROOT / "workspace.json")
    rows = []
    for name in ("mul", "div", "axi"):
        case_dir, case = run.load_case(name)
        current = {}
        for entry in case["files"]:
            entry = {"path": entry} if isinstance(entry, str) else entry
            path = (case_dir / entry["path"]).resolve()
            current[entry.get("dest", path.name)] = digest(path)
        for task, selection in case["tasks"].items():
            candidates = []
            for result_path in (run.ROOT / "results" / name).glob("*/result.json"):
                result = run.read_json(result_path)
                if result.get("task") != task:
                    continue
                directory = result_path.parent
                request = run.read_json(directory / "request.json")
                expected_defines = case.get("defines", []) + selection.get("defines", [])
                manifest = {m["staged_as"]: m["sha256"] for m in request["source_manifest"]}
                matching = (manifest == current and
                            request.get("defines") == expected_defines and
                            request["mode"] == selection["mode"] and
                            request["depth"] == selection["depth"] and
                            request["timeout_seconds"] == selection["timeout_seconds"] and
                            request.get("engine") == selection.get("engine", "smtbmc " + config["solver"]) and
                            (directory / "assumptions.md").read_bytes() == (case_dir / "assumptions.md").read_bytes())
                if matching:
                    candidates.append(directory)
            if not candidates:
                rows.append({"case": name, "task": task, "status": "NOT_RUN_WITH_CURRENT_INPUTS"})
                continue
            source = sorted(candidates)[-1]
            result = run.read_json(source / "result.json")
            evidence = target / "evidence" / name / task
            evidence.mkdir(parents=True, exist_ok=True)
            for filename in ("result.json", "request.json", "case.sby", "assumptions.md", "console.log"):
                shutil.copyfile(source / filename, evidence / filename)
            # Config files are not RTL inputs, but retain their exact bytes when
            # they match the hash captured by the runner.
            if digest(case_dir / "case.json") == result.get("case_config_sha256"):
                shutil.copyfile(case_dir / "case.json", evidence / "case.json")
            # Preserve exact RTL/harness bytes for standalone evidence review.
            for path in (source / "src").rglob("*"):
                if path.is_file():
                    dest = evidence / "src" / path.relative_to(source / "src")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, dest)
            for wave in result.get("waveforms", []):
                original = source / wave
                dest = evidence / wave
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, dest)
            rows.append({"case": name, "task": task, "status": result["status"],
                         "mode": result["mode"], "engine": result["engine"],
                         "depth": result["depth"], "timeout_seconds": result["timeout_seconds"],
                         "elapsed_seconds": result["elapsed_seconds"],
                         "expected_raw_status": result["expected_raw_status"],
                         "expected_result_observed": result["expected_result_observed"],
                         "original_run": str(source.relative_to(run.ROOT)).replace("\\", "/"),
                         "evidence": str(evidence.relative_to(target)).replace("\\", "/")})
    replay_runs = sorted((run.ROOT / ".cache/axi-replay").glob("*/result.json"))
    if replay_runs:
        latest = replay_runs[-1].parent
        replay_target = target / "evidence/axi/replay"
        replay_target.mkdir(parents=True, exist_ok=True)
        for filename in ("result.json", "simulation.log", "export.log", "export.ys", "dut.v", "dut-netlist.v", "replay_tb.sv", "replay.vcd"):
            shutil.copyfile(latest / filename, replay_target / filename)
    if (run.ROOT / "results/self-test-latest.json").is_file():
        shutil.copyfile(run.ROOT / "results/self-test-latest.json", target / "self-test.json")
    payload = {"generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
               "source_lock": run.read_json(run.ROOT / "sources.lock.json"), "tasks": rows,
               "note": "Only results matching current RTL, harness, assumptions, task options and defines are exported. NOT_RUN is not PASS."}
    (target / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = ["# 形式化任务结果索引", "", "源码提交：`" + payload["source_lock"]["commit"] + "`。", "",
             "BMC_PASS 仅限所列深度；PROVED 仅限任务性质与假设；故障注入 FAIL 不表示 DUT 错误；TIMEOUT/NOT_RUN 均未获得证明。", "",
             "| 模块 | 任务 | 结果 | 深度 | 超时/秒 | 引擎 | 证据 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        link = f"[记录]({row['evidence']}/result.json)" if "evidence" in row else "—"
        lines.append(f"| {row['case']} | {row['task']} | {row['status']} | {row.get('depth', '—')} | {row.get('timeout_seconds', '—')} | {row.get('engine', '—')} | {link} |")
    (target / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {str(p.relative_to(target)).replace("\\", "/"): digest(p) for p in sorted(target.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Exported " + str(target))
    print("\n".join(f"{r['case']}/{r['task']}: {r['status']}" for r in rows))


if __name__ == "__main__":
    main()
