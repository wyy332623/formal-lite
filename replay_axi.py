#!/usr/bin/env python3
"""Replay known AXI failures using Yosys netlist + Icarus, not the formal checker."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import run
import worker


def replay():
    config = run.read_json(run.ROOT / "workspace.json")
    suite = Path(config["toolchain_root"]).expanduser()
    metadata = run.read_json(run.ROOT / "cases/axi/source.json")
    source = run.ROOT / "sources/calab-main-10d248a" / metadata["source"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("Pinned DUT hash mismatch")
    target = run.ROOT / ".cache/axi-replay" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target.mkdir(parents=True)
    shutil.copyfile(source, target / "dut.v")
    shutil.copyfile(run.ROOT / "cases/axi/replay_tb.sv", target / "replay_tb.sv")
    (target / "export.ys").write_text(
        "read_verilog dut.v\nprep -top axi_bridge\nwrite_verilog -noattr dut-netlist.v\n", encoding="utf-8")
    env = worker.child_env(suite)
    versions = worker.doctor(config)["tools"]
    for name in ("iverilog", "vvp"):
        check = subprocess.run([str(suite / "bin" / name), "-V"], env=env, capture_output=True, text=True, timeout=20)
        versions[name] = {"path": str(suite / "bin" / name), "version": (check.stdout + check.stderr).splitlines()[0]}
    with (target / "export.log").open("w", encoding="utf-8") as log:
        subprocess.run([str(suite / "bin/yosys"), "-s", "export.ys"], cwd=target, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    subprocess.run([str(suite / "bin/iverilog"), "-g2012", "-s", "replay_tb", "-o", "replay.out",
                    "dut-netlist.v", "replay_tb.sv"], cwd=target, env=env, check=True, timeout=30)
    simulation = subprocess.run([str(suite / "bin/vvp"), "replay.out"], cwd=target, env=env,
                                capture_output=True, text=True, timeout=30)
    (target / "simulation.log").write_text(simulation.stdout + simulation.stderr, encoding="utf-8")
    confirmed = simulation.returncode == 0 and simulation.stdout.count("REPRODUCED:") == 2
    result = {"confirmed_two_design_failures": confirmed, "returncode": simulation.returncode,
              "source_metadata": metadata, "tools": versions,
              "method": "unmodified RTL exported by Yosys, deterministic port-only Icarus testbench",
              "limitation": "Yosys infers undeclared rd_busy as a register; direct original-RTL Icarus compatibility is not claimed"}
    (target / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(simulation.stdout)
    print("Replay evidence: " + str(target))
    return 0 if confirmed else 1


if __name__ == "__main__":
    try:
        if os.name == "nt":
            settings = run.read_json(run.ROOT / "workspace.json")
            invocation = subprocess.run(["wsl.exe", "--distribution", settings["wsl_distribution"], "--exec",
                                         "/usr/bin/python3", run.linux_path(__file__)], capture_output=True)
            print(invocation.stdout.decode("utf-8", errors="replace"), end="")
            if invocation.returncode and invocation.stderr:
                data = invocation.stderr
                encoding = "utf-16-le" if data.count(b"\x00") > len(data) // 8 else "utf-8"
                print(data.decode(encoding, errors="replace"), file=sys.stderr)
            sys.exit(invocation.returncode)
        sys.exit(replay())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(2)
