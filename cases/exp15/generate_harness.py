from pathlib import Path
import re, json, hashlib, subprocess
case=Path(__file__).resolve().parent
root=case.parents[1]
repo=root/'sources/calab-main-10d248a'
source=repo/'myCPU/axi_bridge.v'
code=source.read_text()
header=re.sub(r'//[^\n]*','',code[:code.index(');')+2])
ports=re.findall(r'\b(input|output)\s+wire\s*(\[[^]]+\])?\s*(\w+)\s*[,)]',header)
assert len(ports)>50 and any(n=='bready' for _,_,n in ports)
lines=['// Generated from the pinned DUT header; no DUT internals are referenced.', 'module bridge_formal(input wire aclk);']
for direction,width,name in ports:
    if name=='aclk': continue
    prefix='(* anyseq *) reg' if direction=='input' else 'wire'
    lines.append(f'{prefix} {width} {name};')
lines+=['axi_bridge dut(.*);','`include "properties.sv"','`include "environment.sv"','endmodule']
(case/'harness.sv').write_text('\n'.join(lines)+'\n')
info={'remote':'https://github.com/wyy332623/calab','branch':'main','commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'module':'axi_bridge','source':'myCPU/axi_bridge.v','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(case/'source.json').write_text(json.dumps(info,indent=2))
print(json.dumps(info,indent=2))
