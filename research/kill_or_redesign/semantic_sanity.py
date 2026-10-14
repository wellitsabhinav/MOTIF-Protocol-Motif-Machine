"""Bounded P2 representability checks and an atomicity counterexample.

These do not qualify P2. Fixed I2C replay is not a closed-loop controller test;
1-Wire resolves the target's own drive live. Frozen reference is unchanged.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from dataclasses import asdict
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research.kill_or_redesign.analyze import ROOT,sha,save
from research.kill_or_redesign.tournament import BUILD
from tools.v3_trace import bench,FIELDS,Recorder


def live_i2c():
    from motif.protocols.i2c import target
    from tests.i2c_driver import Bus
    cfg=target();d=BUILD/'p2_semantics/i2c_live';d.mkdir(parents=True,exist_ok=True)
    text=bench(cfg,d/'unused.txt',20000).replace('fd=$fopen("'+(d/'unused.txt').as_posix()+'","r");',"fd=32'h80000000;")
    text=text.replace(r'%d\n"',r'%d"')
    text=text.replace('clk=0;#1;',' $fflush();clk=0;#1;')
    (d/'tb.sv').write_text(text)
    cmd=['iverilog','-B',str(Path('.tools')/'ivl'),'-g2012','-s','tb','-o',str(d/'tb.vvp'),
         *[str(p) for p in sorted((BUILD/'p2/src').glob('*.sv'))],str(d/'tb.sv')]
    subprocess.run(cmd,cwd=ROOT,check=True,capture_output=True,timeout=30)
    proc=subprocess.Popen(['vvp',str(d/'tb.vvp')],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    class Adapter:
        host_push=False;host_pop=False;host_data=0;last_oe=0;active=False;rx_fifo=[]
        rows=[];actions=[]
        def step(self,pins):
            action=[pins,0,0,int(self.host_push),int(self.host_pop),self.host_data,1]
            proc.stdin.write(' '.join(map(str,action))+'\n');proc.stdin.flush()
            line=proc.stdout.readline()
            if not line.startswith('ROW '):raise RuntimeError('Live simulation failed: '+line)
            row=dict(zip(FIELDS,map(int,line[4:].split())))
            self.host_push=False;self.host_pop=False;self.last_oe=row['oe'];self.active=bool(row['active'])
            self.rx_fifo=[row['rx_head']]*row['rx_fifo_count'];self.rows.append(row);self.actions.append(action)
            return row
    adapter=Adapter()
    def host(bus,data=None,pop=False):
        value=adapter.rx_fifo[0] if pop and adapter.rx_fifo else None
        adapter.host_push=data is not None;adapter.host_data=data or 0;adapter.host_pop=pop;bus.hold(1)
        return value
    try:
        bus=Bus(adapter,spacing=32);bus.start()
        acks=[bus.write(0xa4),bus.write(0x55),bus.write(0xaa)]
        received=[host(bus,pop=True),host(bus,pop=True)]
        host(bus,0xa5);host(bus,0x5a);bus.start();acks.append(bus.write(0xa5))
        transmitted=[bus.read(ack=True),bus.read(ack=False)];bus.stop()
        observed={'acks':acks,'received':received,'transmitted':transmitted,'released':not adapter.active and not adapter.last_oe}
        passed=all(acks) and received==[0x55,0xaa] and transmitted==[0xa5,0x5a] and observed['released']
        (d/'inputs.txt').write_text(''.join(' '.join(map(str,a))+'\n' for a in adapter.actions))
        (d/'rtl.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in adapter.rows))
        result={'name':'i2c_live','passed':passed,'observed':observed,'cycles':len(adapter.rows),
                'scope':'closed-loop wired-AND controller, repeated START, two-byte write and read, ACK/NACK, stretch; one nominal profile',
                'stimulus_sha256':sha(d/'inputs.txt'),'rtl_sha256':sha(d/'rtl.jsonl')}
    finally:
        proc.terminate();proc.wait(timeout=10)
    return result


def simulate(name,engine,controller=None):
    d=BUILD/'p2_semantics'/name;d.mkdir(parents=True,exist_ok=True)
    actions=engine.actions
    if controller is not None:
        actions=[list(a) for a in actions]
        for a,level in zip(actions,controller):a[0]=248|(7 if level else 0)
    vectors=d/'inputs.txt';vectors.write_text(''.join(' '.join(map(str,a))+'\n' for a in actions))
    text=bench(engine.config,vectors,len(actions))
    if controller is not None:
        text=text.replace('pins=pins_in[7:0];','pins=pins_in[7:0];pins[2]=pins[2] && !pad_oe[2];')
    (d/'tb.sv').write_text(text)
    cmd=['iverilog','-B',str(Path('.tools')/'ivl'),'-g2012','-s','tb','-o',str(d/'tb.vvp')]
    cmd.extend(str(p) for p in sorted((BUILD/'p2/src').glob('*.sv')));cmd.append(str(d/'tb.sv'))
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=30)
    (d/'compile.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stderr[-1500:])
    r=subprocess.run(['vvp',str(d/'tb.vvp')],cwd=ROOT,capture_output=True,text=True,timeout=40)
    (d/'simulation.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stdout[-1000:]+r.stderr[-1000:])
    rows=[dict(zip(FIELDS,map(int,l[4:].split()))) for l in r.stdout.splitlines() if l.startswith('ROW ')]
    assert len(rows)==len(actions)
    first=next(({'cycle':i,'differences':{k:[a[k],b[k]] for k in FIELDS if a[k]!=b[k]}} for i,(a,b) in enumerate(zip(engine.rows,rows)) if a!=b),None)
    meta={'name':name,'cycles':len(rows),'first_frozen_model_divergence':first,
          'stimulus_sha256':sha(vectors),'bench_sha256':sha(d/'tb.sv'),'simulation_sha256':sha(d/'simulation.log')}
    return rows,meta


def main():
    from tools.demo import build_case
    from tools import temporal_campaign,lin_unseen
    results=[]
    for protocol in ['spi','uart','timed_stream','microwire','i2c']:
        engine,expected,observed,pins=build_case(protocol)
        rows,meta=simulate(protocol,engine)
        if protocol in ['spi','uart','timed_stream']:
            visible=['rx_fifo_count','rx_head','data','oe','status','tx_fifo_count','active']
            passed=all(all(a[k]==b[k] for k in visible) for a,b in zip(engine.rows,rows))
            meta['scope']='complete fixed-stimulus visible trace equality; table executor unused in these modes'
        elif protocol=='microwire':
            _,oracle=temporal_campaign.microwire_case()
            bits=[(rows[i]['data']>>3)&1 if rows[i]['oe']&8 else 1 for i in oracle['sample_indices']]
            expected_bits=[int(b) for b in f'{0xa55a:016b}']
            passed=bits==expected_bits and not any(r['oe']&2 for r in rows)
            meta['observed_word_hex']=hex(int(''.join(map(str,bits)),2))
            meta['scope']='independent fixed controller sample indices and no target clock ownership'
        else:
            visible=['rx_fifo_count','rx_head','data','oe','status','tx_fifo_count','active']
            differences=sum(any(a[k]!=b[k] for k in visible) for a,b in zip(engine.rows,rows))
            passed=differences==0;meta['visible_divergence_cycles']=differences
            meta['scope']='fixed resolved-pin replay, not a new closed-loop I2C qualification'
        results.append({**meta,'passed':passed});print(protocol,passed,flush=True)
    workload,cfg=temporal_campaign.repair_specification()
    for name in ['nominal','interrupted_non_reset','restart_then_valid']:
        engine,_=temporal_campaign.repair_case(name)
        rows,meta=simulate('one_wire_'+name,engine,engine.controller)
        oracle=temporal_campaign.evaluate_repair(engine,rows,workload,engine.controller_case)
        results.append({**meta,'passed':oracle['passed'],'independent_wire_oracle':oracle,'scope':'live wired-AND target feedback with unchanged wire oracle'})
        print('one_wire_'+name,oracle['passed'],flush=True)
    selection=lin_unseen.selected()
    case=next(c for c in lin_unseen.cases(selection) if c['name']=='nominal')
    engine,line,controls,end,drains,expected=lin_unseen.model_case(selection,case,lin_unseen.candidate())
    rows,meta=simulate('lin_nominal',engine)
    oracle=lin_unseen.evaluate(rows,line,controls,end,drains,selection)
    results.append({**meta,'passed':not bool(oracle.errors),'independent_wire_oracle':asdict(oracle),'scope':'unchanged independent LIN prefix oracle, one nominal case'})
    print('lin_nominal',asdict(oracle),flush=True)
    from motif import Config
    from motif.transaction import Entry,program,DECIDE,HALT,CHAIN
    engine=Recorder(Config(program=program([Entry(DECIDE,next=1,flags=1|2|CHAIN),Entry(HALT,flags=1)]),frame_active_high=True))
    for _ in range(8):engine.step(254)
    for _ in range(16):engine.step(255)
    rows,meta=simulate('atomic_terminate_cancels_push',engine)
    old=max(r['rx_fifo_count'] for r in engine.rows);new=max(r['rx_fifo_count'] for r in rows)
    assert old==0 and new==1
    results.append({**meta,'passed':False,'expected_negative_reproduced':True,'frozen_max_rx_count':old,'p2_max_rx_count':new,
                    'scope':'two generic entries; termination must suppress same-batch push'})
    save('p2_semantic_sanity.json',{'qualified':False,'cases':results,
         'conclusion':'P2 is a timing lower bound. Atomic commit/event snapshots and lifecycle alignment are required before production use.'})
    result=live_i2c();save('p2_i2c_live.json',result);print(result,flush=True)


if __name__=='__main__':main()
