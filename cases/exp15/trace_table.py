"""Small VCD reader for the scalar/vector traces emitted by SBY."""
from pathlib import Path
import argparse, json

def read_vcd(path):
    names={}; scope=[]; values={}; samples={}; stamp=0
    with Path(path).open() as source:
        header=True
        for raw in source:
            line=raw.strip()
            if header:
                parts=line.split()
                if line.startswith('$scope'): scope.append(parts[2])
                elif line.startswith('$upscope'): scope.pop()
                elif line.startswith('$var'):
                    names['.'.join(scope+[parts[4]])]=parts[3]
                elif line.startswith('$enddefinitions'): header=False
                continue
            if line.startswith('#'):
                if stamp%10==0 and values: samples[stamp//10]=values.copy()
                stamp=int(line[1:]); continue
            if line.startswith('b'):
                bits,code=line[1:].split(); values[code]=bits
            elif line and line[0] in '01xz': values[line[1:]]=line[0]
    if stamp%10==0: samples[stamp//10]=values.copy()
    rows=[]
    for step, sample in samples.items():
        row={'step':step}
        for name,code in names.items():
            bits=sample.get(code,'x')
            row[name]=int(bits,2) if set(bits)<=set('01') else bits
        rows.append(row)
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('vcd');parser.add_argument('--json');args=parser.parse_args()
    rows=read_vcd(args.vcd)
    if args.json: Path(args.json).write_text(json.dumps(rows,indent=2))
    fields=['aresetn','mem_req','mem_addr_ok','mem_wr','mem_addr','arvalid','arready','arid','awvalid','awready','wvalid','wready','rvalid','rid','rdata','bvalid','mem_data_ok','mem_rdata','mem_count','mem_head','mem_done']
    print('step '+ ' '.join(fields))
    for row in rows:
        print(str(row['step'])+' '+' '.join(str(row.get('bridge_formal.'+f,'-')) for f in fields))
