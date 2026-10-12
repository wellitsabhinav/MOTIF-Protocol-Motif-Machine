"""Immutable v2 boundary and transparent accounting, separate from legacy evidence."""
import hashlib
import inspect
import json
import subprocess
from pathlib import Path

DIRECTORY=Path("experiments/exchange_decomposition")
MANIFEST=DIRECTORY/"frozen_v2_manifest.json"
PRIMITIVES=["FRAME_ACQUIRE","FRAME_RELEASE","RESET_COUNTER","SHIFT_RX_COUNT","SHIFT_TX","TIMED_SAMPLE",
            "FIELD_DECISION","DIRECTION_HANDOFF","BOUNDARY_RESPONSE","WAIT_POLICY"]


def sha(data):
    return hashlib.sha256(data.replace(b"\r\n",b"\n")).hexdigest()


def inventory():
    files=list(Path("src").rglob("*.sv"))+list(Path("src").rglob("*.json"))+list(Path("motif").rglob("*.py"))
    files.extend(Path(p) for p in ("info.yaml","flow-lock.json",".github/workflows/gds.yml"))
    return {p.as_posix():sha(p.read_bytes()) for p in sorted(files)}


def harness_hashes():
    from tools import exchange_decomposition as trace
    return {"bench":sha(inspect.getsource(trace.bench).encode()),"compare_rtl":sha(inspect.getsource(trace.compare_rtl).encode()),
            "FIELDS":sha(json.dumps(trace.FIELDS).encode()),"MOTIFS":sha(json.dumps(trace.MOTIFS).encode()),"EVENTS":sha(json.dumps(trace.EVENTS).encode())}


def verify():
    frozen=json.loads(MANIFEST.read_text())
    actual=inventory()
    if actual!=frozen["source_hashes"]:
        changed=sorted(p for p in actual.keys()|frozen["source_hashes"].keys() if actual.get(p)!=frozen["source_hashes"].get(p))
        raise ValueError("Frozen v2 implementation changed: "+", ".join(changed))
    if harness_hashes()!=frozen["trace_compiler_hashes"]:
        raise ValueError("Frozen trace compiler changed")
    if sha((DIRECTORY/"preregistered_architecture.json").read_bytes())!=frozen["preregistration_sha256"]:
        raise ValueError("Preregistered semantics changed")
    return frozen


def freeze():
    if MANIFEST.exists(): raise ValueError("Refusing to overwrite immutable v2 freeze")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():
        raise ValueError("Commit all qualification evidence before freezing")
    logical=json.loads((DIRECTORY/"i2c_logical.json").read_text())
    reuse=json.loads((DIRECTORY/"microwire_result.json").read_text())
    current=inventory()
    rtl={p:v for p,v in current.items() if p.startswith("src/") and p.endswith(".sv")}
    if logical["rtl_hashes"]!=rtl or reuse["rtl_hashes"]!=rtl:
        raise ValueError("Qualification does not identify the current RTL")
    if logical["classification"]!="MOTIF_I2C_LOGICAL_QUALIFICATION_PASSED" or reuse["classification"]!="MOTIF_EXCHANGE_DECOMPOSITION_I2C_MICROWIRE_REUSE_CONFIRMED":
        raise ValueError("Both training workloads must pass before freeze")
    contract=json.loads((DIRECTORY/"preregistered_architecture.json").read_text())
    data={"schema_version":2,"source_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
          "source_hashes":current,"rtl_hashes":rtl,"model_hashes":{p:v for p,v in current.items() if p.startswith("motif/")},
          "trace_compiler_hashes":harness_hashes(),"preregistration_sha256":sha((DIRECTORY/"preregistered_architecture.json").read_bytes()),
          "preregistered_commit":"d3ca35e2221f8e7654f4c42fa79ab7992e8ee8d8","primitives":PRIMITIVES,
          "new_primitive_contracts":contract["primitives"],"program":contract["program"],"integration":contract["integration"],
          "configuration_bits_rtl":1096,"table_bits":1024,"transaction_state_bits_declared":28,
          "shared_receive_state_bits_declared":21,"shared_transmit_state_bits_declared":12,
          "configuration_widths":{"control":7,"pins":12,"period":16,"watchdog":16,"fill":8,"open_drain":8,"transaction_control":5,"program":1024},
          "state_widths_declared":{"configuration":1096,"frontend":26,"receive":21,"transmit":12,"timer":26,"watchdog":17,"fifos":82,"transaction":28,"host_spi":47,"core_lifecycle_provenance_diagnostics":23,"host_diagnostics":2},
          "input_events":contract["program"]["triggers"],"output_events":contract["primitives"],
          "data_interfaces":{"initial_field":16,"fifo_data":8,"tx_value":8,"pad_data":8,"pad_oe":8},
          "routing_interfaces":{"instruction_entries":16,"instruction_bits":64,"successor_bits":4,"trigger_selector_bits":2,"pin_selector_bits":3},
          "current_users":["spi_target","uart_rx","timed_stream","i2c_target","bounded_93LC46_x16_READ"],
          "qualification_sha256":{"i2c":sha((DIRECTORY/"i2c_logical.json").read_bytes()),"microwire":sha((DIRECTORY/"microwire_result.json").read_bytes())},
          "allowed_after_freeze":"New declarative configuration data and independent oracle/controller/test/report files; no model, RTL, host decoder, configuration compiler or physical input changes",
          "third_protocol":{"status":"UNSELECTED","research_started":False},
          "counting_contract":"Declared state includes diagnostic-only bits that synthesis may remove or recode. Physical register cells are reported separately. Primitive firings count once per type per cycle; four-entry immediate execution is a separate control bound."}
    MANIFEST.write_text(json.dumps(data,indent=2)+"\n",newline="\n")
    print("FROZEN v2",sha(MANIFEST.read_bytes()))
    return data


def accounting():
    from tools.exchange_decomposition import MOTIFS
    usage={
      "FRAME_ACQUIRE":["spi_target","uart_rx","timed_stream","i2c_target","microwire_read"],
      "FRAME_RELEASE":["spi_target","uart_rx","timed_stream","i2c_target","microwire_read"],
      "RESET_COUNTER":["spi_target","uart_rx","timed_stream","i2c_target","microwire_read"],
      "SHIFT_RX_COUNT":["spi_target","uart_rx","timed_stream","i2c_target","microwire_read"],
      "SHIFT_TX":["spi_target","i2c_target","microwire_read"],
      "TIMED_SAMPLE":["uart_rx","timed_stream","i2c_target"],
      "FIELD_DECISION":["i2c_target","microwire_read"],"DIRECTION_HANDOFF":["i2c_target","microwire_read"],
      "BOUNDARY_RESPONSE":["i2c_target","microwire_read"],"WAIT_POLICY":["i2c_target","microwire_read"]}
    result={"schema_version":2,"primitive_type_count":10,"instruction_opcode_count":8,"configuration_bits":1096,"program_bits":1024,
            "transaction_state_bits_declared":28,"protocol_specific_new_rtl_modules":0,"protocol_specific_new_rtl_lines":0,
            "protocols_per_primitive":usage,"configuration_only_protocols":["spi_target","uart_rx","timed_stream","i2c_target","microwire_read"],
            "sequencing":{"entries":16,"entry_bits":64,"pc_bits":4,"halted_bits":1,"maximum_immediate_entries_per_cycle":4},
            "limitations":["Inherited fixed frame predicates, timer-start routing and byte storage remain explicit vocabulary limits","Synthetic probes and failed unseen attempts are excluded from validated-user counts","Declared registers and synthesized sequential cells are distinct metrics"],
            "protocol_specific_count_scope":"New transaction RTL; diagnostic sequential SPI reference and inherited framing predicates are listed separately",
            "protocols":{}}
    for name,path in (("i2c_target",DIRECTORY/"i2c_logical.json"),("microwire_read",DIRECTORY/"microwire_result.json")):
        report=json.loads(path.read_text())
        reports=report["cases"] if name=="i2c_target" else [report["microwire"]]
        counts={p:sum(r["primitive_firings"].get(p,0) for r in reports) for p in MOTIFS}
        rows=[]
        if name=="i2c_target":
            directories=[Path("build/exchange_decomposition/gate1")/r["name"] for r in reports]
        else: directories=[Path("build/exchange_decomposition/gate2/microwire")]
        frames=[]
        for directory in directories:
            current=None
            for line in (directory/"rtl.jsonl").open():
                row=json.loads(line);rows.append(row)
                if row["events"]&1:
                    if current is not None: frames.append(current)
                    current={p:0 for p in MOTIFS}
                if current is not None:
                    for i,p in enumerate(MOTIFS): current[p]+=bool(row["motifs"]&(1<<i))
                    if row["motifs"]&2: frames.append(current);current=None
        observed_pcs=sorted({r["pc"] for r in rows if r["active"]})
        exemplar=reports[0]["configuration"]
        words=exemplar["program"]
        from motif.transaction import Entry, CHAIN, ALWAYS
        # Registered PC observations omit immediate entries. Include their
        # possible configured successors, labeling this as dependency coverage
        # rather than claiming that every alternate branch fired.
        referenced=set(observed_pcs)
        pending=list(referenced)
        while pending:
            e=Entry.decode(words[pending.pop()])
            if e.flags & CHAIN:
                for index in (e.next,e.alternate):
                    if index not in referenced and Entry.decode(words[index]).trigger==ALWAYS:
                        referenced.add(index);pending.append(index)
        entries={i:Entry.decode(words[i]) for i in sorted(referenced)}
        op_names=["SHIFT_RX_COUNT","FIELD_DECISION","BOUNDARY_RESPONSE","DIRECTION_HANDOFF","WAIT_POLICY","SHIFT_TX","TERMINATE","CONTINUE"]
        sources=["poll","clock_rising","clock_falling","timer_sample"]
        event_groups={(sources[e.trigger],op_names[e.opcode]) for e in entries.values()}
        for e in entries.values():
            if e.opcode==2 and e.argument&3==2:event_groups.add((sources[e.value&3],"BOUNDARY_RESPONSE_COMPLETE"))
            if e.opcode==4:event_groups.add(("fifo_readiness" if e.argument&3==0 else "timer_sample" if e.argument&3==2 else "level/readiness","WAIT_POLICY"))
        event_groups=sorted(event_groups)
        data_groups=["pin->RX","RX_terminal->pending_field","constant_mask/value->decision","TX_FIFO->TX","TX_bit/response_bit->data_request","readiness->wait","requests/ownership->guardian"]
        if name=="i2c_target":data_groups.extend(["pending_field_low_byte->RX_FIFO","timer_sample->wait"])
        fields=sorted(exemplar.keys()-{"program","fill","validate_stop"}-(set() if name=="i2c_target" else {"period","validate_start","hold_clock","pad_timing_check"}))
        result["protocols"][name]={"aggregate_primitive_firings":counts,"closed_frame_epochs":len(frames),"primitive_firings_per_frame_epoch":frames,
                                    "maximum_primitive_types_per_cycle":max(r["motifs"].bit_count() for r in rows),
                                    "observed_registered_pc_values":observed_pcs,"configured_entry_dependencies":sorted(referenced),"active_configuration_fields":fields,
                                    "activity_counting_scope":"PC values are registered observations. Entry dependencies include possible immediate successors, and interface groups describe configured dependencies, not branch coverage or physical wires. State fields are semantic dependencies, not switching/power measurements.",
                                    "event_route_groups":event_groups,"event_route_group_count":len(event_groups),"data_route_groups":data_groups,"data_route_group_count":len(data_groups),
                                    "active_transaction_state_fields":["pc","halted","pending_field","desired_role","accepted","drive_enable","drive_value"]+(["captured_response","hold"] if name=="i2c_target" else []),
                                    "diagnostic_state_fields":["current_role"],
                                    "new_rtl_required_for_protocol":0,"new_rtl_reference":"relative to this preregistered implemented vocabulary; both training workloads influenced its design"}
    return result
