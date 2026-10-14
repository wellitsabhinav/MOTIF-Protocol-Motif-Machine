"""Bounded forensic variants, matched CMOS5L mapping and ideal-wire STA.

Generated cuts are not qualified redesigns. All generated sources and full logs
stay under build/. Each mutation is checked against the diagnosed frozen text.
"""
import argparse
from collections import defaultdict
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research.kill_or_redesign.analyze import ROOT, OUT, TOP, RUN, sha, save, paths, graph, verilog_cells

BUILD=ROOT/'build/kill_or_redesign'
LIB=ROOT/'build/pdk/sg13cmos5l_stdcell_typ_1p20V_25C.lib'
V2='490a50c3e03f1be96784fd27f9d64b718c2aa5cc'
DISTRO='PACT-OpenSTA-Review420'


def q(p):return '"'+str(Path(p).resolve()).replace('\\','/')+'"'
def linux(p):
    p=Path(p).resolve().as_posix()
    return '/mnt/'+p[0].lower()+p[2:]


def run(command,log,timeout=180):
    t=time.monotonic()
    try:
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as e:
        log.write_bytes((e.stdout or b'')+(e.stderr or b''))
        raise
    log.write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(f'{command[0]} failed; see {log}')
    return time.monotonic()-t


def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Nonunique mutation: '+old[:75])
    return text.replace(old,new)


def cache_validation(s):
    s=replace(s,'    reg invalid_program;','    reg invalid_program;\n    reg invalid_program_comb;\n    always @(posedge clk) invalid_program <= invalid_program_comb;')
    a=s.index('    always @* begin');b=s.index('    wire invalid_exchange',a)
    s=s[:a]+s[a:b].replace('invalid_program','invalid_program_comb')+s[b:]
    return s


def temporal_elision(s,state_only=False):
    if not state_only:
        s=s.replace('else if(op==WAIT && flags[2] && temporal_seen)execute=0;','else if(1\'b0)execute=0;')
        s=replace(s,'                            if(flags[2])begin','                            if(1\'b0)begin')
        s=s.replace('first_word[55]','1\'b0')
        s=replace(s,'else if(temporal_seen && program_i[pc_next*64 +: 3]==WAIT && program_i[pc_next*64+55])execute=0;',"else if(1'b0)execute=0;")
    # Clamp only state in D; retain all decoding and checks to distinguish it
    # from elision C. Synthesis is allowed to optimize resulting constant logic.
    s=replace(s,'temporal_count_o<=temporal_count_next;temporal_started_o<=temporal_started_next;temporal_done_o<=temporal_done_next;',
                  'temporal_count_o<=0;temporal_started_o<=0;temporal_done_o<=0;')
    s=s.replace('temporal_count_o<=1;temporal_started_o<=1;temporal_done_o<=first_word[52:37]==1;',
                'temporal_count_o<=0;temporal_started_o<=0;temporal_done_o<=0;')
    return s


def fetch_cut(s,predecode=False):
    declaration='    wire [63:0] current_word = program_i[pc_o*64 +: 64];'
    if not predecode:
        s=replace(s,declaration,'    reg [63:0] table_q;\n    always @(posedge clk) table_q <= program_i[pc_next*64 +: 64];\n'+declaration)
        s=replace(s,'word=program_i[pc_next*64 +: 64];op=word[2:0];', 'word=stage==0 ? table_q : program_i[pc_next*64 +: 64];op=word[2:0];')
        return s
    # A 66-bit uop: op one-hot 8; event one-hot 4; next/alt 8;
    # argument 8; value/mask 32; meaningful flags 0..4 and chain flag 10.
    new='''    wire [63:0] fetch_word = program_i[pc_next*64 +: 64];
    reg [65:0] uop_q;
    always @(posedge clk) uop_q <= {8'b1 << fetch_word[2:0], 4'b1 << fetch_word[4:3],
        fetch_word[8:5], fetch_word[12:9], fetch_word[20:13], fetch_word[36:21],
        fetch_word[52:37], fetch_word[63], fetch_word[57:53]};
'''+declaration
    s=replace(s,declaration,new)
    s=replace(s,'for(stage=0;stage<4;stage=stage+1)begin','for(stage=0;stage<1;stage=stage+1)begin')
    s=replace(s,'word=program_i[pc_next*64 +: 64];op=word[2:0];trigger=word[4:3];successor=word[8:5];alternate=word[12:9];\n                argument=word[20:13];constant=word[36:21];field_mask=word[52:37];flags=word[63:53];',
        '''word=0;op=0;trigger=0;
                successor=uop_q[53:50];alternate=uop_q[49:46];argument=uop_q[45:38];
                constant=uop_q[37:22];field_mask=uop_q[21:6];flags={uop_q[5],5'b0,uop_q[4:0]};
                if(uop_q[55])trigger=1;else if(uop_q[56])trigger=2;else if(uop_q[57])trigger=3;''')
    s=replace(s,'capture=op==RESPOND && argument[1:0]==2;','capture=uop_q[60] && argument[1:0]==2;')
    s=replace(s,'else if(op==WAIT && flags[2] && temporal_seen)execute=0;','else if(uop_q[62] && flags[2] && temporal_seen)execute=0;')
    s=replace(s,'case(op)','case(1\'b1)')
    for i,name in enumerate(['RX','DECIDE','RESPOND','HANDOFF','WAIT','TX','HALT','CONTINUE']):
        s=replace(s,name+':begin',f'uop_q[{58+i}]:begin')
    return s


def fifo_cut(s):
    old='''    motif_fifo rx_fifo(clk, rst_n, rx_push, host_rx_pop_i,
                       exchange_i ? exchange_rx_data : validate_stop_i ? validated_byte : rx_next, host_rx_data_o,'''
    new='''    reg rx_push_q;
    reg [7:0] rx_data_q;
    always @(posedge clk) begin
        if(!rst_n)begin rx_push_q<=0;rx_data_q<=0;end
        else begin rx_push_q<=rx_push;rx_data_q<=exchange_i ? exchange_rx_data : validate_stop_i ? validated_byte : rx_next;end
    end
    motif_fifo rx_fifo(clk, rst_n, rx_push_q, host_rx_pop_i,
                       rx_data_q, host_rx_data_o,'''
    return replace(s,old,new)


def commit_control(s):
    """P4: compute the instruction cone independently of global live control.

    Mask at commit, preserving the complete combinational port/next-state
    relation. No register, latency, opcode or configuration change.
    """
    s=replace(s,'execute=rst_n && run_i && !clear_i && !halted_o;','execute=!halted_o;')
    marker='        if(rst_n && acquire_i && first_word[2:0]==WAIT && first_word[55])begin'
    mask='''        if(!rst_n || !run_i || clear_i)begin
            pc_next=pc_o;desired_next=desired_role_o;role_next=role_o;accepted_next=accepted_o;response_next=response_o;
            pending_next=pending_field_o;enable_next=drive_enable_o;value_next=drive_value_o;hold_next=hold_o;halted_next=halted_o;
            temporal_count_next=temporal_count_o;temporal_started_next=temporal_started_o;temporal_done_next=temporal_done_o;
            executed_pcs_o=0;executed_count_o=0;
            rx_fire_o=0;tx_fire_o=0;tx_load_o=0;rx_push_o=0;rx_data_o=pending_field_o[7:0];
            rx_next_o=rx_value_i;rx_count_next_o=rx_count_i;rx_length_o=8;rx_timer_o=0;
            turnaround_o=0;mismatch_o=0;fault_o=0;terminate_o=0;field_complete_o=0;completed_field_o=0;
            fires_o=0;events_o=0;
        end
'''
    return replace(s,marker,mask+marker)


def sources(variant):
    dest=BUILD/variant/'src';dest.mkdir(parents=True,exist_ok=True)
    for file in sorted((ROOT/'src').glob('*.sv')):
        if variant=='v2':
            original=subprocess.check_output(['git','show',V2+':src/'+file.name],cwd=ROOT).decode()
        else:original=file.read_text()
        s=original
        if file.name=='motif_transaction.sv':
            if variant in ['elided','state_clamp']:s=temporal_elision(s,variant=='state_clamp')
            if variant=='p1':s=fetch_cut(s)
            if variant in ['p2','p2_cached']:s=fetch_cut(s,True)
            if variant=='p4':s=commit_control(s)
        if file.name=='motif_core.sv' and variant=='p3':s=fifo_cut(s)
        if file.name=='tt_um_wellitsabhinav_motif.sv' and variant in ['cached','p2_cached']:s=cache_validation(s)
        (dest/file.name).write_text(s,encoding='utf-8',newline='\n')
        if s!=original:
            diff=''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='frozen/'+file.name,tofile=variant+'/'+file.name))
            (BUILD/variant/(file.stem+'.patch')).write_text(diff,encoding='utf-8')
    return dest


def buffer_netlist(data,limit=8):
    """Fixed, technology-buffer-only fanout tree. No Boolean function changes.

    Ideal wires and arbitrary sink grouping make this an optimistic bound,
    never placement or congestion evidence. Applied identically to every variant.
    """
    m=data['modules'][TOP];cells=m['cells'];loads=defaultdict(list);clock_bits=set(m['ports']['clk']['bits'])
    maxbit=max(b for n in m['netnames'].values() for b in n['bits'] if isinstance(b,int))
    for name,c in list(cells.items()):
        for p,bits in c['connections'].items():
            if c['port_directions'].get(p)=='input':
                for i,b in enumerate(bits):
                    if isinstance(b,int) and b not in clock_bits:loads[b].append((name,p,i))
    count=0
    def tree(root,sinks):
        nonlocal count,maxbit
        if len(sinks)<=limit:
            for name,p,i in sinks:cells[name]['connections'][p][i]=root
            return
        # Balance by groups of at most fanout limit at each tree level.
        groups=min(limit,(len(sinks)+limit-1)//limit)
        width=(len(sinks)+groups-1)//groups
        for start in range(0,len(sinks),width):
            count+=1;maxbit+=1;net=maxbit;name=f'study_buf_{count}'
            cells[name]={'hide_name':0,'type':'sg13cmos5l_buf_4','parameters':{},'attributes':{},
                         'port_directions':{'A':'input','X':'output'},'connections':{'A':[root],'X':[net]}}
            m['netnames'][name+'_net']={'hide_name':0,'bits':[net],'attributes':{}}
            tree(net,sinks[start:start+width])
    for net,sinks in list(loads.items()):tree(net,sinks)
    return count


def synth(variant):
    dest=sources(variant);d=dest.parent
    cmd=f'read_verilog -sv '+ ' '.join(q(p) for p in sorted(dest.glob('*.sv')))+f'; synth -top {TOP} -noabc; dfflibmap -liberty {q(LIB)}; abc -exe {q(ROOT/".tools/abc.exe")} -liberty {q(LIB)}; clean; write_json {q(d/"mapped.json")}; stat -liberty {q(LIB)} -json'
    (d/'synth.ys').write_text(cmd,encoding='utf-8')
    try:
        seconds=run(['yosys','-Q','-T','-s',str(d/'synth.ys')],d/'synth.log')
    except subprocess.TimeoutExpired:
        save(variant+'_timeout.json',{'variant':variant,'status':'180_second_mapping_timeout','area_um2':None,'wns_ns':None,
             'command_sha256':sha(d/'synth.ys'),'partial_log_sha256':sha(d/'synth.log'),
             'source_hashes':{p.name:sha(p) for p in dest.glob('*.sv')},'interpretation':'incomplete measurement; not architectural timing failure'})
        print(variant,'mapping limit reached; no area/timing claim',flush=True)
        return
    log=(d/'synth.log').read_text();offset=log.rfind('\n{\n   "creator"');stats=json.JSONDecoder().raw_decode(log[offset:].lstrip())[0]
    data=json.loads((d/'mapped.json').read_text())
    script=f'read_liberty -lib {q(LIB)}; read_json {q(d/"mapped.json")}; hierarchy -top {TOP}; flatten; write_json {q(d/"flat.json")}; write_verilog -noattr -simple-lhs {q(d/"raw.v")}'
    run(['yosys','-Q','-T','-p',script],d/'flatten.log',60)
    flat=json.loads((d/'flat.json').read_text());buffers=buffer_netlist(flat)
    (d/'buffered.json').write_text(json.dumps(flat),encoding='utf-8')
    run(['yosys','-Q','-T','-p',f'read_json {q(d/"buffered.json")}; write_verilog -noattr -simple-lhs {q(d/"buffered.v")}'],d/'buffer_export.log',60)
    # Extract precise buffer area from the actual mapping library.
    block=LIB.read_text().split('cell (sg13cmos5l_buf_4)',1)[1]
    buf_area=float(re.search(r'area\s*:\s*([\d.]+)',block)[1])
    report={'variant':variant,'synthesis_seconds':seconds,'yosys':stats['creator'],
        'library_sha256':sha(LIB),'mapping_command_sha256':hashlib.sha256(cmd.encode()).hexdigest(),
        'source_hashes':{p.name:sha(p) for p in dest.glob('*.sv')},
        'area_um2':stats['design']['area'],'cells':stats['design']['num_cells'],
        'sequential_cells':sum(n for name,n in stats['design']['num_cells_by_type'].items() if '_df' in name),
        'modules':{k:{'area_um2':v.get('area'),'cells':v['num_cells']} for k,v in stats['modules'].items()},
        'fixed_tree_buffers':buffers,'buffered_area_um2':stats['design']['area']+buffers*buf_area,
        'raw_netlist_sha256':sha(d/'raw.v'),'buffered_netlist_sha256':sha(d/'buffered.v'),
        'extra_config_bits':0,'diagnostic_only':variant not in ['v2','v3']}
    for mode in ['raw','buffered']:
        save(variant+'_'+mode+'_graph.json',{'netlist_sha256':sha(d/(mode+'.v')),**graph(verilog_cells(d/(mode+'.v')))})
    save(variant+'_mapping.json',report)
    # Same constraints as archived flow, but ideal clock and zero wire parasitics.
    sdc=(RUN/'final/sdc/tt_um_wellitsabhinav_motif.sdc').read_text().replace('set_propagated_clock [get_clocks {clk}]','')
    (d/'constraints.sdc').write_text(sdc,encoding='utf-8')
    for mode in ['raw','buffered']:
        for corner in ['typ','slow']:
            library=LIB if corner=='typ' else BUILD/'toolchain/sg13cmos5l_stdcell_slow_1p08V_125C.lib'
            tcl=f'''read_liberty {{{linux(library)}}}
read_verilog {{{linux(d/(mode+'.v'))}}}
link_design {TOP}
read_sdc {{{linux(d/'constraints.sdc')}}}
report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -digits 6 -fields {{slew cap fanout input net}} > {{{linux(d/(mode+'_'+corner+'.rpt'))}}}
report_check_types -max_slew -max_capacitance -max_fanout -violators > {{{linux(d/(mode+'_'+corner+'_electrical.rpt'))}}}
exit
'''
            (d/(mode+'_'+corner+'.tcl')).write_text(tcl,encoding='utf-8')
    print(variant,report['area_um2'],report['cells'],'cells',report['fixed_tree_buffers'],'fixed buffers',flush=True)


def sta(variant):
    d=BUILD/variant;results={}
    # Older OpenSTA cannot parse concatenations on assignment LHS or reliably
    # open Liberty filenames with spaces. Re-export identical connectivity and
    # use local basenames; this does not resynthesize any logic.
    for mode,jsonfile in [('raw','flat.json'),('buffered','buffered.json')]:
        run(['yosys','-Q','-T','-p',f'read_json {q(d/jsonfile)}; write_verilog -noattr -simple-lhs {q(d/(mode+".v"))}'],d/(mode+'_sta_export.log'),60)
    shutil.copyfile(LIB,d/'typ.lib')
    shutil.copyfile(BUILD/'toolchain/sg13cmos5l_stdcell_slow_1p08V_125C.lib',d/'slow.lib')
    for mode in ['raw','buffered']:
        cells=verilog_cells(d/(mode+'.v'))
        for corner in ['typ','slow']:
            tcl=f'''read_liberty {corner}.lib
read_verilog {mode}.v
link_design {TOP}
read_sdc constraints.sdc
set_wire_load_model -name Zero
report_checks -path_delay max -group_count 20 -endpoint_count 1 -sort_by_slack -digits 6 -fields {{slew capacitance input_pin net}} > {mode}_{corner}.rpt
report_checks -from [all_registers -output_pins] -path_delay max -group_count 20 -endpoint_count 1 -sort_by_slack -digits 6 -fields {{slew capacitance input_pin net}} > {mode}_{corner}_reg.rpt
report_check_types -max_delay -all_violators > {mode}_{corner}_violations.rpt
exit
'''
            (d/(mode+'_'+corner+'.tcl')).write_text(tcl,encoding='utf-8')
            # OpenSTA 2.0.17 mishandles spaces in cmd_file; source a basename.
            command='cd '+shlex.quote(linux(d))+' && '+shlex.quote(linux(BUILD/'toolchain/opensta/usr/bin/sta'))+' -no_init -no_splash -exit '+mode+'_'+corner+'.tcl'
            cmd=['wsl','-d',DISTRO,'--','bash','-lc',command]
            run(cmd,d/(mode+'_'+corner+'_sta.log'),60)
            if re.search(r'\bError:',(d/(mode+'_'+corner+'_sta.log')).read_text(errors='replace')):raise RuntimeError('STA errors; see '+str(d/(mode+'_'+corner+'_sta.log')))
            rpt=d/(mode+'_'+corner+'.rpt')
            if not rpt.is_file():raise RuntimeError('STA did not produce a report')
            r=paths(rpt,cells);save(variant+'_'+mode+'_'+corner+'_paths.json',r)
            results[mode+'_'+corner]={k:r['paths'][0][k] for k in ['slack_ns','data_path_delay_ns','start_signal','endpoint_state_signal','logic_depth_excluding_buffers','buffer_count']}
            reg=paths(d/(mode+'_'+corner+'_reg.rpt'),cells)
            save(variant+'_'+mode+'_'+corner+'_reg_paths.json',reg)
            results[mode+'_'+corner+'_reg']={k:reg['paths'][0][k] for k in ['slack_ns','data_path_delay_ns','start_signal','endpoint_state_signal','logic_depth_excluding_buffers','buffer_count']}
    mapping=json.loads((OUT/(variant+'_mapping.json')).read_text())
    for mode in ['raw','buffered']:
        p=d/(mode+'.v');mapping[mode+'_netlist_sha256']=sha(p)
        save(variant+'_'+mode+'_graph.json',{'netlist_sha256':sha(p),**graph(verilog_cells(p))})
    save(variant+'_mapping.json',mapping)
    save(variant+'_timing.json',results)
    print(variant,results,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['synth','sta']);p.add_argument('variants',nargs='+',choices=['v2','v3','elided','state_clamp','p1','p2','p3','p4','cached','p2_cached'])
    args=p.parse_args()
    for v in args.variants:(synth if args.action=='synth' else sta)(v)
