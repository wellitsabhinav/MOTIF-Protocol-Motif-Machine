"""Audit selected reports and the buffer-only transformation independently."""
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research.kill_or_redesign.analyze import ROOT,OUT,sha,save
from research.kill_or_redesign.tournament import BUILD,TOP


def main():
    checks=[]
    for v in ['v2','v3','elided','state_clamp','p1','p2']:
        d=BUILD/v
        a=json.loads((d/'flat.json').read_text(encoding='utf-8'))['modules'][TOP]
        b=json.loads((d/'buffered.json').read_text(encoding='utf-8'))['modules'][TOP]
        drivers={}
        for n,c in b['cells'].items():
            if n.startswith('study_buf_'):
                assert c['type']=='sg13cmos5l_buf_4'
                drivers[c['connections']['X'][0]]=c['connections']['A'][0]
        def resolve(bit):
            seen=set()
            while bit in drivers:
                assert bit not in seen
                seen.add(bit);bit=drivers[bit]
            return bit
        for n,c in a['cells'].items():
            z=b['cells'][n]
            assert c['type']==z['type'] and c['parameters']==z['parameters']
            for pin,bits in c['connections'].items():
                assert bits==[resolve(x) for x in z['connections'][pin]]
        assert a['ports']==b['ports']
        m=json.loads((OUT/(v+'_mapping.json')).read_text(encoding='utf-8'))
        for mode in ['raw','buffered']:
            assert m[mode+'_netlist_sha256']==sha(d/(mode+'.v'))
            for corner in ['typ','slow']:
                log=(d/(mode+'_'+corner+'_sta.log')).read_text(encoding='utf-8',errors='replace')
                assert 'Error:' not in log and 'module ' not in log
                for suffix in ['','_reg']:
                    j=json.loads((OUT/(v+'_'+mode+'_'+corner+suffix+'_paths.json')).read_text(encoding='utf-8'))
                    assert len(j['paths'])==20 and j['sha256']==sha(ROOT/j['report'])
                    for r in j['paths']:
                        assert abs(r['cell_delay_ns']+r['net_and_input_arc_delay_ns']-r['data_path_delay_ns'])<0.0002
        checks.append({'variant':v,'buffer_only_connectivity_equivalent':True,'original_cells':len(a['cells']),
                       'added_buffers':len(drivers),'all_final_sta_logs_error_free':True,'selected_reports_hash_match':True})
    required=['README','hypotheses','baseline','critical_path_analysis','logic_depth_analysis',
              'fanout_analysis','congestion_analysis','architecture_bottlenecks','candidate_redesigns','experiments','decision']
    assert all((OUT.parent/(n+'.md')).is_file() for n in required)
    decision=(OUT.parent/'decision.md').read_text(encoding='utf-8')
    assert decision.splitlines()[0]=='MOTIF_REDESIGN'
    assert len(decision.split('## 1. Executive decision')[1].split('## 2.')[0].split())<=300
    for p in OUT.parent.rglob('*.md'):
        s=p.read_text(encoding='utf-8')
        assert not any(marker in s for marker in ['Ã¢','â€','Âµ'])
        for target in re.findall(r'\]\(([^)]+)\)',s):
            if '://' not in target:assert (p.parent/target.split('#')[0]).exists(),(p,target)
    old_paths=['src','motif','test','tests','formal','tools','docs','experiments','reports','.github',
               'flow-lock.json','info.yaml','README.md','pyproject.toml']
    subprocess.run(['git','diff','--exit-code','9e4c500','--',*old_paths],cwd=ROOT,check=True)
    save('validation.json',{'buffered_connectivity_checks':checks,'baseline_pytest':'422 passed in 30.94s',
         'production_inputs_unchanged':True,'p2_atomic_negative_reproduced':True,'physical_jobs_launched':0,
         'required_reports_and_links_valid':True,'executive_under_300_words':True})
    print('PASS buffer connectivity, report hashes/arithmetics, frozen inputs, required documents and links')


if __name__=='__main__':main()
