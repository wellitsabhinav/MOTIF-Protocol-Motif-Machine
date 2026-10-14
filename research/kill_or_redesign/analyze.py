"""Extract compact, reproducible forensic evidence; never mutate official RTL."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "evidence"
RUN = ROOT / "build/v3_physical/attempt_2/artifacts/runs/wokwi"
TOP = "tt_um_wellitsabhinav_motif"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def verilog_cells(path):
    text = path.read_text()
    cells = {}
    for m in re.finditer(r"\b(sg13cmos5l_\w+)\s+(\\[^\s]+|[^\s(]+)\s*\((.*?)\);", text, re.S):
        cells[m[2].lstrip("\\")] = {"type": m[1], "pins": {
            p[1]: p[2].strip().lstrip("\\") for p in re.finditer(r"\.(\w+)\s*\(([^()]*)\)", m[3])}}
    return cells


def category(signals):
    names = " ".join(signals)
    rules = {
        "configuration_table_decode": r"program|invalid_|control\[|pins_low|pins_high|period|open_drain",
        "opcode_decode": r"exchange\.(word|op|trigger|argument|flags)",
        "temporal_logic": r"temporal_|exchange\.field_mask",
        "predicate_logic": r"accepted|response|desired|decision|predicate",
        "executor_control": r"exchange\.|composition|clear|active|inhibit",
        "fifo_control": r"fifo\.(count|write_ptr|read_ptr)|rx_push|tx_load|rx_full|tx_empty",
        "fifo_data": r"fifo\.memory|exchange_rx_data|pending_field|field_value",
        "output_control": r"guardian|pad_oe|pad_data|drive_|stretch",
        "host_configuration_interface": r"host\.|read_data|write_data|address",
        "unrelated_infrastructure": r"rst_n|clk|watchdog|frontend|timer\.",
    }
    return [k for k, pattern in rules.items() if re.search(pattern, names)]


def paths(path, cells, limit=20):
    blocks = re.split(r"(?=Startpoint:)", path.read_text())
    rows = []
    row_re = re.compile(r"^\s*(?:(\d+)\s+)?(?:[+-]?\d+\.\d+\s+){0,2}([+-]?\d+\.\d+)\s+([+-]?\d+\.\d+)\s+[\^v]\s+(\S+)(?:\s+\((\S+)\))?\s*$")
    for block in blocks:
        if not block.startswith("Startpoint:"):
            continue
        slack = re.search(r"([+-]?\d+\.\d+)\s+slack", block)
        arrival = re.search(r"([+-]?\d+\.\d+)\s+data arrival time", block)
        required = re.search(r"([+-]?\d+\.\d+)\s+data required time", block)
        if not (slack and arrival and required):
            continue
        start = re.search(r"Startpoint:\s+(\S+)", block)[1]
        end = re.search(r"Endpoint:\s+(\S+)", block)[1]
        group = re.search(r"Path Group:\s+(\S+)", block)[1]
        parsed = []
        for line in block.split("data arrival time")[0].splitlines():
            m = row_re.match(line)
            if m:
                parsed.append({"fanout": int(m[1]) if m[1] else None, "delay": float(m[2]),
                               "time": float(m[3]), "pin": m[4], "type": m[5]})
        # Clock paths precede data; isolate exactly launch-Q/input through capture-D.
        first = next((i for i, r in enumerate(parsed) if r["pin"] in [start+"/Q", start+"/QN", start]), None)
        last = next((i for i, r in enumerate(parsed) if r["pin"] in [end+"/D", end]), None)
        if first is None or last is None:
            raise ValueError(f"Cannot isolate data rows in {path}: {start} -> {end}")
        data = parsed[first:last+1]
        out_arcs = [r for r in data if r["fanout"] is not None and r["type"] and r["type"].startswith("sg13cmos5l_")]
        comb = [r for r in out_arcs if not re.search(r"_df|_latch", r["type"])]
        buffers = [r for r in comb if "_buf_" in r["type"]]
        signals = []
        for r in data:
            inst = r["pin"].rsplit("/", 1)[0]
            signals.extend(cells.get(inst, {}).get("pins", {}).values())
        start_signal = cells.get(start, {}).get("pins", {}).get("Q", start)
        end_signal = cells.get(end, {}).get("pins", {}).get("Q", end)
        cell_delay = sum(r["delay"] for r in out_arcs)
        net_delay = sum(r["delay"] for r in data if r not in out_arcs)
        row = {"rank": len(rows)+1, "startpoint": start, "endpoint": end, "group": group,
               "start_signal": start_signal, "endpoint_state_signal": end_signal,
               "arrival_ns": float(arrival[1]), "required_ns": float(required[1]), "slack_ns": float(slack[1]),
               "data_path_delay_ns": data[-1]["time"]-data[0]["time"]+data[0]["delay"],
               "cell_delay_ns": cell_delay, "net_and_input_arc_delay_ns": net_delay,
               "comb_cell_count": len(comb), "logic_depth_excluding_buffers": len(comb)-len(buffers),
               "mapped_mux_depth": sum("_mux" in r["type"] for r in comb),
               "buffer_count": len(buffers), "max_path_fanout": max((r["fanout"] or 0 for r in data)),
               "categories_supported_by_named_nets": category([start_signal,end_signal]+signals),
               "rtl_start_hierarchy": start_signal.rsplit(".", 1)[0],
               "rtl_end_hierarchy": end_signal.rsplit(".", 1)[0],
               "source_function": "table operand/validation to action" if "program" in start_signal else "see named start/state signals",
               "internal_opcode_stage_attribution": "not recoverable after flattened ABC mapping",
               "cell_type_histogram": dict(Counter(r["type"] for r in comb))}
        if abs(row["data_path_delay_ns"] - cell_delay-net_delay) > 0.0002:
            raise ValueError("Incremental delay sum does not equal path elapsed delay")
        rows.append(row)
    rows.sort(key=lambda r:r["slack_ns"])
    for i,r in enumerate(rows):r["rank"]=i+1
    return {"report": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
            "reported_paths": len(rows), "scope": "worst reported paths, not exhaustive STA enumeration; mapped mux count excludes Boolean-decomposed muxes",
            "paths": rows[:limit]}


def graph(cells):
    drivers, sinks = {}, defaultdict(list)
    for name, cell in cells.items():
        for pin, net in cell["pins"].items():
            if pin in ["Q","QN","X","Y"]:
                drivers[net] = (name,pin)
            elif pin not in ["VPWR","VGND","VDD","VSS"]:
                sinks[net].append((name,pin))
    cache, visiting = {}, set()
    def depth(net):
        if net in cache:return cache[net]
        driver=drivers.get(net)
        if not driver:return (0,0,0)
        name,pin=driver;c=cells[name]
        if "_df" in c["type"] or "_latch" in c["type"]:return (0,0,0)
        if net in visiting:raise ValueError("Combinational cycle detected: "+net)
        visiting.add(net)
        deps=[depth(n) for p,n in c["pins"].items() if p not in ["Q","QN","X","Y","VPWR","VGND","VDD","VSS"]]
        v=(max((x[0] for x in deps),default=0)+(0 if "_buf_" in c["type"] else 1),
           max((x[1] for x in deps),default=0)+(1 if "_mux" in c["type"] else 0),
           max((x[2] for x in deps),default=0)+1)
        visiting.remove(net);cache[net]=v;return v
    endpoints=[]
    for name,c in cells.items():
        if "_df" in c["type"] and "D" in c["pins"]:
            d=depth(c["pins"]["D"])
            endpoints.append({"endpoint":name,"state":c["pins"].get("Q"),"logic_depth":d[0],"mapped_mux_depth":d[1],"comb_depth_with_buffers":d[2]})
    fanout=[]
    for net,loads in sinks.items():
        driver=drivers.get(net)
        clock=all(p in ["CLK","GATE"] for n,p in loads)
        fanout.append({"net":net,"fanout_pin_count":len(loads),"distinct_sink_cells":len(set(n for n,p in loads)),
                       "driver":driver,"clock_only":clock,"categories":category([net]),
                       "sink_type_histogram":dict(Counter(cells[n]["type"] for n,p in loads)),
                       "buffer_sink_count":sum("_buf_" in cells[n]["type"] for n,p in loads),
                       "first_sinks":loads[:5]})
    fanout.sort(key=lambda x:-x["fanout_pin_count"])
    endpoints.sort(key=lambda x:-x["logic_depth"])
    return {"num_cells":len(cells),"top_nonclock_fanout": [x for x in fanout if not x["clock_only"]][:20],
            "fanout_histogram":dict(sorted(Counter(x["fanout_pin_count"] for x in fanout if not x["clock_only"]).items())),
            "maximum_nonclock_fanout":max(x["fanout_pin_count"] for x in fanout if not x["clock_only"]),
            "top_depth_endpoints":endpoints[:20],"max_logic_depth":max(x["logic_depth"] for x in endpoints),
            "max_mapped_mux_depth":max(x["mapped_mux_depth"] for x in endpoints)}


def main():
    pre=RUN/'06-yosys-synthesis/tt_um_wellitsabhinav_motif.nl.v'
    post=RUN/'final/nl/tt_um_wellitsabhinav_motif.nl.v'
    identities={"baseline_commit":subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                "archive_sha256":sha(ROOT/'build/v3_physical/attempt_2/GDS_logs.zip'),
                "archive_expected_sha256":"5cdff1a5201ebad89713da86188c8bd5b0b7d93afa1737752023c6b7d5e2a7d0"}
    assert identities['archive_sha256']==identities['archive_expected_sha256']
    files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    identities['tracked_input_inventory']={f:sha(ROOT/f) for f in files if not f.startswith('research/kill_or_redesign/')}
    frozen=json.loads((ROOT/'experiments/temporal_qualification/frozen_v3_manifest.json').read_text())
    identities['frozen_rtl_matches']={f:hashlib.sha256((ROOT/f).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h for f,h in frozen['rtl_hashes'].items()}
    assert all(identities['frozen_rtl_matches'].values())
    save('input_identity.json',identities)
    for stage,file in [('pre',pre),('post',post)]:
        cells=verilog_cells(file)
        save(stage+'_graph.json',{"netlist_sha256":sha(file),**graph(cells)})
        directory=RUN/('12-openroad-staprepnr' if stage=='pre' else '55-openroad-stapostpnr')
        for corner in ['nom_fast_1p32V_m40C','nom_typ_1p20V_25C','nom_slow_1p08V_125C']:
            result=paths(directory/corner/'max.rpt',cells)
            save(stage+'_'+corner+'_paths.json',result)
            print(stage,corner,{k:result['paths'][0][k] for k in ['start_signal','endpoint_state_signal','data_path_delay_ns','slack_ns','logic_depth_excluding_buffers','mapped_mux_depth','cell_delay_ns','net_and_input_arc_delay_ns']})


if __name__=='__main__':main()
