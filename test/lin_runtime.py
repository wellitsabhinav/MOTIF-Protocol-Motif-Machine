"""Runtime host checks for selected LIN scope; usable on RTL and routed netlists."""
import json
from pathlib import Path

import cocotb

from test import Driver, load_table
from motif.transaction import configuration
from tools.lin_oracle import LinContract, reference
from tools.lin_unseen import selected, cases, schedule

ROOT = Path(__file__).resolve().parents[1]


@cocotb.test()
async def runtime_lin_unseen(dut):
    selection = selected()
    contract = LinContract.from_selection(selection)
    config = configuration(json.loads((ROOT / "experiments/temporal_qualification/unseen/config.json").read_text()))
    chosen = {"nominal", "one_cycle_high_split", "pending_sync_recovery", "back_to_back"}
    for case in [case for case in cases(selection) if case["name"] in chosen]:
        driver = Driver(dut)
        dut.rst_n.value = 0
        dut.ena.value = 1
        await driver.tick(4)
        dut.rst_n.value = 1
        await driver.tick()
        assert await driver.transaction(1, 21) == 3
        await load_table(driver, config.program)
        await driver.transaction(2, 1, config.frame_pin | (config.clock_pin << 3))
        await driver.transaction(2, 2, config.rx_pin | (config.tx_pin << 3))
        await driver.transaction(2, 3, config.period & 255)
        await driver.transaction(2, 4, config.period >> 8)
        await driver.transaction(2, 6, config.open_drain)
        await driver.transaction(2, 22, 1)
        for _ in range(4):
            await driver.transaction(2, 16, 255)
        await driver.transaction(2, 0, 15)
        assert await driver.transaction(1, 0) == 15, "Host rejected selected configuration"
        line, controls = schedule(selection, case)
        assert not controls, "Selected runtime subset has no lifecycle host assistance"
        wanted = [token.value for token in reference(line, controls, contract)]
        assert wanted == case["expected_tokens"], "Independent wire fixture expectation changed"
        cursor = [0]
        def wire(current):
            cycle = cursor[0]
            assert int(dut.uio_oe.value) == 0, (case["name"], cycle, "Receive-only output enabled")
            current.pins = 255 if line[cycle] else 251
            cursor[0] += 1
        driver.on_tick = wire
        await driver.tick(len(line))
        driver.on_tick = None
        driver.pins = 255
        await driver.tick(5001)
        assert int(dut.uio_oe.value) == 0
        assert (await driver.transaction(1, 19) & 7) == len(wanted), (case["name"], "Public FIFO count")
        observed = [await driver.transaction(1, 17) for _ in wanted]
        assert observed == wanted, (case["name"], wanted, observed)
        assert (await driver.transaction(1, 19) & 7) == 0, "Extra token after independent drain"
        assert await driver.transaction(1, 18) == 0, "Runtime configuration/guardian/FIFO fault"
        dut._log.info("PASS selected LIN runtime %s: expected=%s observed=%s", case["name"], wanted, observed)
