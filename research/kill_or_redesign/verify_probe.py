"""Prove P4's complete combinational transition relation, not selected programs."""
from pathlib import Path
import json
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research.kill_or_redesign.analyze import ROOT, sha, save
from research.kill_or_redesign.tournament import sources,q,BUILD


def transition(text,name):
    # State ports become arbitrary common inputs. Compare every externally used
    # combinational output and every next-state bit of the original module.
    for old in [
        'output reg [3:0] pc_o',
        'output reg desired_role_o, role_o, accepted_o, response_o',
        'output reg [15:0] pending_field_o',
        'output reg drive_enable_o, drive_value_o, hold_o, halted_o',
        'output reg [15:0] temporal_count_o',
        'output reg temporal_started_o, temporal_done_o']:
        assert text.count(old)==1
        text=text.replace(old,old.replace('output reg','input wire'))
    states={'pc_next':4,'desired_next':1,'role_next':1,'accepted_next':1,'response_next':1,
            'pending_next':16,'enable_next':1,'value_next':1,'hold_next':1,'halted_next':1,
            'temporal_count_next':16,'temporal_started_next':1,'temporal_done_next':1}
    extra=',\n'+',\n'.join('    output wire '+(f'[{w-1}:0] ' if w>1 else '')+'compare_'+n for n,w in states.items())
    text=text.replace('output reg [2:0] executed_count_o','output reg [2:0] executed_count_o'+extra)
    text=text[:text.index('    always @(posedge clk)begin')]
    text+='\n'+''.join(f'    assign compare_{n}={n};\n' for n in states)+'endmodule\n'
    return text.replace('module motif_transaction (','module '+name+' (')


def main():
    d=BUILD/'p4_equivalence';d.mkdir(parents=True,exist_ok=True)
    # Use the actual measured P4 source, without regeneration during analysis.
    p4=BUILD/'p4/src/motif_transaction.sv'
    for name,source in [('gold',ROOT/'src/motif_transaction.sv'),('gate',p4)]:
        (d/(name+'.sv')).write_text(transition(source.read_text(),name),encoding='utf-8')
    script=f'read_verilog -sv {q(d/"gold.sv")} {q(d/"gate.sv")}; miter -equiv -flatten gold gate miter; prep -top miter; flatten; memory_map; opt; sat -verify -prove trigger 0 -show-inputs -timeout 60'
    (d/'prove.ys').write_text(script,encoding='utf-8')
    t=time.monotonic()
    try:
        r=subprocess.run(['yosys','-Q','-T','-s',str(d/'prove.ys')],cwd=ROOT,capture_output=True,timeout=100)
    except subprocess.TimeoutExpired:
        save('p4_equivalence.json',{'passed':False,'reason':'100 second fixed timeout'});return
    (d/'prove.log').write_bytes(r.stdout+r.stderr)
    passed=r.returncode==0 and b'no model found: SUCCESS' in r.stdout
    receipt={'passed':passed,'scope':'all table words, live controls, arbitrary current state, all combinational output ports and all 46 next-state bits; sequential priorities unchanged',
             'frozen_transaction_sha256':sha(ROOT/'src/motif_transaction.sv'),
             'p4_transaction_sha256':sha(p4),'miter_sha256':{'gold.sv':sha(d/'gold.sv'),'gate.sv':sha(d/'gate.sv')},
             'command_sha256':sha(d/'prove.ys'),'log_sha256':sha(d/'prove.log'),'seconds':time.monotonic()-t,'exit_code':r.returncode}
    save('p4_equivalence.json',receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
