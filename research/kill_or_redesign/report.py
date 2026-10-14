"""Generate compact tables and four evidence-driven figures from study receipts."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research.kill_or_redesign.analyze import ROOT,OUT,sha,save
from tools.demo_render import _plotting

HERE=Path(__file__).resolve().parent
VARIANTS=['v2','v3','elided','state_clamp','p1','p2']


def read(n):return json.loads((OUT/(n+'.json')).read_text())
def write(n,text):(HERE/n).write_text(text.strip()+'\n',encoding='utf-8',newline='\n')
def num(x):return f'{x:.6f}'


def tournament():
    table='| Variant | Area µm² | Δ area vs v3 | Worst delay ns | WNS ns | Logic depth | Max fanout | Critical path type | Extra state | Latency change |\n'
    table+='|---|---:|---:|---:|---:|---:|---:|---|---:|---|\n'
    states={'v2':-18,'v3':0,'elided':-18,'state_clamp':-18,'p1':64,'p2':66}
    latency={'v2':'historical','v3':'0','elided':'temporal absent','state_clamp':'temporal absent','p1':'cache alignment pending','p2':'chains spread across cycles'}
    summary=[]
    for v in VARIANTS:
        m=read(v+'_mapping');t=read(v+'_timing')['buffered_slow'];g=read(v+'_buffered_graph')
        delta=(m['area_um2']/read('v3_mapping')['area_um2']-1)*100
        table+=f"| {v} | {m['area_um2']:.4f} | {delta:+.4f}% | {t['data_path_delay_ns']:.6f} | {t['slack_ns']:+.6f} | {t['logic_depth_excluding_buffers']} | {g['maximum_nonclock_fanout']} | {t['start_signal']} → {t['endpoint_state_signal']} | {states[v]:+d} | {latency[v]} |\n"
        summary.append({'variant':v,'area_um2':m['area_um2'],'delta_area_percent':delta,
                        'buffered_area_um2':m['buffered_area_um2'],'full_slow':t,'register_slow':read(v+'_timing')['buffered_slow_reg'],
                        'cells':m['cells'],'sequential_cells':m['sequential_cells'],'combinational_cells':m['cells']-m['sequential_cells'],
                        'max_graph_depth':g['max_logic_depth'],'max_graph_mux_depth':g['max_mapped_mux_depth'],
                        'fixed_tree_buffers':m['fixed_tree_buffers'],'extra_declared_state':states[v]})
    for v in ['p3','p4']:table+=f'| {v} | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | mapping timeout | '+('9' if v=='p3' else '0')+' | '+('FIFO +1 cycle' if v=='p3' else '0; exact relation proved')+' |\n'
    save('tournament.json',{'rows':summary,'unmeasured':['p3','p4'],'scope':'raw area; timing after identical ideal-wire fanout-eight trees; worst delay belongs to worst constrained setup path, excludes input budget/clock latency; max fanout excludes clocks/constants'})
    write('tournament.md',table+'''
Area is raw matched mapping, before fixed buffers. Timing is slow PVT, the worst
**constrained setup** path after the common fixed tree. Its data delay excludes
the 4 ns external input budget; a register-launched path can have a longer data
delay but better slack. No waived input/configuration/reset path is used.
Graph-wide depth/mux maxima differ from depth on the worst timed path.
P3/P4's timeouts are missing measurements, not evidence of bad timing.
''')
    return table


def timing_table():
    s='| Evidence | Start → endpoint | Data delay ns | WNS ns | Logic levels | Buffers | Cell ns | Net/input arc ns |\n|---|---|---:|---:|---:|---:|---:|---:|\n'
    for stage in ['pre','post']:
        for corner in ['nom_fast_1p32V_m40C','nom_typ_1p20V_25C','nom_slow_1p08V_125C']:
            r=read(stage+'_'+corner+'_paths')['paths'][0]
            s+=f"| attempt 2 {stage} {corner} | {r['start_signal']} → {r['endpoint_state_signal']} | {num(r['data_path_delay_ns'])} | {num(r['slack_ns'])} | {r['logic_depth_excluding_buffers']} | {r['buffer_count']} | {num(r['cell_delay_ns'])} | {num(r['net_and_input_arc_delay_ns'])} |\n"
    return s


def tables():
    for stage in ['pre','post']:
        g=read(stage+'_graph')
        s=f"# {stage} implementation fanout\n\nClock nets and constant ties are excluded. Pin count includes multiple pins on one cell. `cone` is the combinational predecessor cone, stopped at registers/inputs. Raw net names may lack unique RTL attribution.\n\n| Rank | Net | Fanout pins | Driver | Buffer sinks | Cone cells | Named source examples |\n|---|---|---:|---|---:|---:|---|\n"
        for i,r in enumerate(g['top_nonclock_fanout'],1):
            s+=f"| {i} | {r['net']} | {r['fanout_pin_count']} | {r['driver']} | {r['buffer_sink_count']} | {r['comb_cone_cells']} | {', '.join(r['named_source_examples'][:4])} |\n"
        write(stage+'_fanout.md',s)
    s='| Netlist | Raw cells | Sequential | Combinational | Max logic depth | Max mapped mux depth | Raw nonclock fanout |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for v in VARIANTS:
        m=read(v+'_mapping');g=read(v+'_raw_graph')
        s+=f"| {v} | {m['cells']} | {m['sequential_cells']} | {m['cells']-m['sequential_cells']} | {g['max_logic_depth']} | {g['max_mapped_mux_depth']} | {g['maximum_nonclock_fanout']} |\n"
    write('logic_depth_table.md',s)


def figures():
    plt=_plotting();d=HERE/'figures';d.mkdir(exist_ok=True)
    preview=ROOT/'build/kill_or_redesign/figures';preview.mkdir(parents=True,exist_ok=True)
    def output(fig,name):
        fig.savefig(d/(name+'.svg'),metadata={'Date':None})
        fig.savefig(preview/(name+'.png'),dpi=140)
        plt.close(fig)
    def boxes(ax,labels,y,color='#dfe8ef'):
        xs=[.10+i*.20 for i in range(len(labels))]
        for x,label in zip(xs,labels):
            ax.text(x,y,label,ha='center',va='center',fontsize=10,bbox={'boxstyle':'round,pad=.55','fc':color,'ec':'#253f56'})
        for a,b in zip(xs,xs[1:]):ax.annotate('',(b-.055,y),(a+.055,y),arrowprops={'arrowstyle':'->','lw':1.5,'color':'#253f56'})
    fig,ax=plt.subplots(figsize=(13,4));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    boxes(ax,['16 × 64 table\nindirect read','opcode / event\noperand decode','predicate / temporal\nworking state','action and\nfault selection','FIFO storage /\noutput requests'],.55)
    ax.text(.5,.94,'Figure 1 — Current execution dependency',ha='center',fontsize=16)
    ax.annotate('Successor PC selects another word: up to four dependent actions per cycle',(.11,.64),(.50,.79),ha='center',arrowprops={'arrowstyle':'->','color':'#b74738'},color='#b74738',fontsize=11)
    ax.text(.50,.28,'Global configuration validity, lifecycle and watchdog qualify execution through this cone',ha='center',fontsize=11)
    ax.text(.50,.10,'Measured: program[928] → RX FIFO; 63 / 62 non-buffer levels at typical / slow post-route PVT.\nRTL dependency sketch; individual optimized cells are not uniquely assigned to opcode stages.',ha='center',fontsize=10)
    output(fig,'01_current_path')
    fig,ax=plt.subplots(figsize=(9,4));corners=['typical','slow'];cell=[];net=[]
    for c in ['nom_typ_1p20V_25C','nom_slow_1p08V_125C']:
        r=read('post_'+c+'_paths')['paths'][0];cell.append(r['cell_delay_ns']);net.append(r['net_and_input_arc_delay_ns'])
    ax.barh(corners,cell,label='Cell arcs, including launch Q',color='#253f56');ax.barh(corners,net,left=cell,label='Net and input arcs',color='#dd8b65')
    for i,(a,b) in enumerate(zip(cell,net)):ax.text(a/2,i,f'{a:.2f} ns',color='white',va='center',ha='center');ax.text(a+b+.3,i,f'+ {b:.2f} ns',va='center')
    ax.set(xlim=(0,53),xlabel='Data-path incremental delay (ns)',title='Figure 2 — Attempt 2 post-route timing breakdown');ax.legend(loc='lower right');fig.tight_layout();output(fig,'02_timing_breakdown')
    fig,ax=plt.subplots(figsize=(8,5))
    for v in VARIANTS:
        m=read(v+'_mapping');t=read(v+'_timing')['buffered_slow'];x=m['area_um2']/1000;y=t['slack_ns']
        offsets={'v2':(8,12),'v3':(9,-16),'elided':(-49,-20),'state_clamp':(-24,22),'p1':(9,8),'p2':(9,9)}
        ax.scatter(x,y,s=85,color='#31746b' if v=='p2' else '#253f56');ax.annotate(v,(x,y),xytext=offsets[v],textcoords='offset points')
    ax.axhline(0,color='#b74738',ls='--');ax.set(xlim=(150,225),ylim=(-8.5,11.2),xlabel='Raw matched mapped area (1000 µm²)',ylabel='Slow-corner full-top WNS (ns)',title='Figure 3 — Controlled variant tournament');ax.grid(alpha=.2);fig.tight_layout();output(fig,'03_variants')
    fig,ax=plt.subplots(figsize=(13,5));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    ax.text(.5,.96,'Figure 4 — Proposed replacement, informed by P2',ha='center',fontsize=16)
    boxes(ax,['table + select','4-action\ncombinational chain','FIFO / pad effect'],.76)
    boxes(ax,['table + select','F: registered\n66-bit µop','E: one operation\nper clock','C: atomic packet\ncommit','local FIFO /\nguarded outputs'],.41,color='#deeee9')
    ax.text(.5,.18,'Snapshot the event and pre-edge FIFO/TX inputs; track up to four distinct entries.\nStage side effects until the chain passes fault/termination checks; temporal observer runs every core cycle.',ha='center',fontsize=11)
    ax.text(.5,.06,'P2 timing kernel measured; snapshot/atomic-commit integration is a specified replacement, not measured RTL.',ha='center',fontsize=10,color='#b74738')
    output(fig,'04_redesign')
    save('figure_identity.json',{'source_receipts':{n:sha(OUT/(n+'.json')) for n in ['tournament','post_nom_typ_1p20V_25C_paths','post_nom_slow_1p08V_125C_paths']},'figures':{p.name:sha(p) for p in d.glob('*.svg')},'scope':'static plots from measured data; diagrams are sourced RTL dependencies/proposed design, not recovered placement'})


if __name__=='__main__':
    tournament();tables();figures();write('timing_table.md',timing_table())
