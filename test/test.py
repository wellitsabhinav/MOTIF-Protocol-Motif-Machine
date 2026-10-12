import cocotb
from cocotb.triggers import Timer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motif.protocols.i2c import target
from motif.transaction import host_bytes, Entry, RX, RISING
from tools.exchange_decomposition import microwire_config


async def load_table(driver, words, start=0, end=128):
    data=host_bytes(words)
    for index in range(start,end):
        await driver.transaction(2,128+index,data[index])


class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.ui = 2
        self.pins = 255
        self.cycle = 0
        self.on_tick = None

    async def tick(self, count=8):
        self.dut.ui_in.value = self.ui
        self.dut.uio_in.value = self.pins
        for _ in range(count):
            if self.on_tick:
                self.on_tick(self)
            self.dut.uio_in.value = self.pins
            self.dut.clk.value = 0
            await Timer(10, unit="ns")
            self.cycle += 1
            self.dut.clk.value = 1
            await Timer(10, unit="ns")
        self.dut.clk.value = 0

    async def byte(self, data):
        result = 0
        for bit in range(7, -1, -1):
            self.ui = (self.ui & ~5) | (((data >> bit) & 1) << 2)
            await self.tick()
            self.ui |= 1
            await self.tick()
            result = (result << 1) | (int(self.dut.uo_out.value) & 1)
            self.ui &= ~1
            await self.tick()
        return result

    async def transaction(self, command, address, value=0):
        self.ui &= ~2
        await self.tick()
        await self.byte(command)
        await self.byte(address)
        result = await self.byte(value)
        self.ui |= 2
        await self.tick()
        return result


@cocotb.test()
async def runtime_protocol_configurations(dut):
    driver = Driver(dut)
    dut.rst_n.value = 0
    dut.ena.value = 1
    await driver.tick(4)
    dut.rst_n.value = 1
    await driver.tick(8)
    assert int(dut.uio_oe.value) == 0

    assert await driver.transaction(1, 3) == 178
    await driver.transaction(2, 2, 2)
    await driver.transaction(2, 0, 9)
    driver.pins &= ~3
    await driver.tick()
    assert int(dut.uio_oe.value) == 0
    assert await driver.transaction(1, 18) & 1
    dut.rst_n.value = 0
    await driver.tick(4)
    driver.pins = 255
    dut.rst_n.value = 1
    await driver.tick()
    await driver.transaction(2, 0, 9)
    await driver.transaction(2, 16, 165)
    driver.pins &= ~2
    await driver.tick()
    driver.pins &= ~1
    await driver.tick()
    result = 0
    for bit in range(7, -1, -1):
        driver.pins = (driver.pins & ~4) | (((85 >> bit) & 1) << 2)
        await driver.tick()
        driver.pins |= 2
        await driver.tick()
        result = (result << 1) | ((int(dut.uio_out.value) >> 3) & 1)
        driver.pins &= ~2
        await driver.tick()
    driver.pins |= 1
    await driver.tick()
    assert int(dut.uio_oe.value) == 0
    assert result == 165
    assert await driver.transaction(1, 17) == 85
    await driver.transaction(2, 3, 17)
    assert await driver.transaction(1, 3) == 178
    await driver.transaction(2, 0, 8)
    await driver.transaction(2, 6, 8)
    await driver.transaction(2, 0, 9)
    driver.pins &= ~1
    await driver.tick()
    assert not int(dut.uio_oe.value) & 8
    driver.pins |= 1
    await driver.tick()
    assert await driver.transaction(1, 18) & 1
    await driver.transaction(2, 0, 8)
    await driver.transaction(2, 6, 0)
    await driver.transaction(2, 1, 10)
    await driver.transaction(2, 3, 32)
    await driver.transaction(2, 4, 0)
    await driver.transaction(2, 0, 119)
    driver.pins |= 4
    await driver.tick(32)
    driver.pins &= ~4
    await driver.tick(32)
    for bit in range(8):
        driver.pins = (driver.pins & ~4) | (((37 >> bit) & 1) << 2)
        await driver.tick(32)
    driver.pins |= 4
    await driver.tick(40)
    assert await driver.transaction(1, 17) == 37
    assert int(dut.uio_oe.value) == 0
    await driver.transaction(2, 0, 0)
    await driver.transaction(2, 3, 4)
    await driver.transaction(2, 0, 119)
    inject_start = driver.cycle + 420
    def inject_uart(controller):
        offset = controller.cycle - inject_start
        if 0 <= offset < 36:
            bit = 0 if offset < 4 else (37 >> ((offset - 4) // 4)) & 1
            controller.pins = (controller.pins & ~4) | (bit << 2)
        elif offset >= 36:
            controller.pins |= 4
    driver.on_tick = inject_uart
    assert await driver.transaction(1, 17) == 0
    driver.on_tick = None
    assert await driver.transaction(1, 17) == 37
    await driver.transaction(2, 0, 0)
    await driver.transaction(2, 1, 8)
    await driver.transaction(2, 3, 16)
    await driver.transaction(2, 0, 5)
    driver.pins |= 1
    await driver.tick()
    driver.pins &= ~1
    await driver.tick(4)
    for bit in range(7, -1, -1):
        driver.pins = (driver.pins & ~4) | (((170 >> bit) & 1) << 2)
        await driver.tick(16)
    driver.pins |= 1
    await driver.tick()
    assert await driver.transaction(1, 17) == 170
    dut.ena.value = 0
    await driver.tick()
    assert int(dut.uio_oe.value) == 0


class I2CController:
    """Independent wired-AND controller, also used against the routed netlist."""
    def __init__(self, driver):
        self.driver = driver
        self.scl = self.sda = 1
        driver.on_tick = self.resolve

    def resolve(self, driver):
        oe = int(driver.dut.uio_oe.value)
        data = int(driver.dut.uio_out.value)
        assert data == 0 and oe & ~6 == 0, "I2C drove high or acquired an unrelated pad"
        driver.pins = (255 & ~6) | ((self.scl and not (oe & 2)) << 1) | ((self.sda and not (oe & 4)) << 2)

    async def hold(self, cycles=8, scl=None, sda=None):
        if scl is not None:
            self.scl = scl
        if sda is not None:
            self.sda = sda
        await self.driver.tick(cycles)

    async def start(self):
        await self.hold(scl=0, sda=1)
        await self.hold(scl=1)
        await self.hold(sda=0)
        await self.hold(scl=0)

    async def stop(self):
        await self.hold(scl=0, sda=0)
        await self.high()
        await self.hold(sda=1)

    async def high(self):
        self.scl = 1
        for _ in range(4096):
            if not int(self.driver.dut.uio_oe.value) & 2:
                break
            await self.hold(1)
        else:
            raise AssertionError("Stretch did not finish")
        await self.hold()

    async def write(self, value):
        for bit in range(7, -1, -1):
            await self.hold(scl=0, sda=(value >> bit) & 1)
            await self.high()
        await self.hold(scl=0, sda=1)
        await self.high()
        ack = bool(int(self.driver.dut.uio_oe.value) & 4)
        await self.hold(scl=0)
        return ack

    async def read(self, ack=False):
        value = 0
        await self.hold(sda=1)
        for _ in range(8):
            await self.high()
            value = (value << 1) | int(not (int(self.driver.dut.uio_oe.value) & 4))
            await self.hold(scl=0)
        await self.hold(sda=0 if ack else 1)
        await self.high()
        await self.hold(scl=0)
        await self.hold(sda=1)
        return value


@cocotb.test()
async def runtime_i2c_qualification(dut):
    driver = Driver(dut)
    dut.rst_n.value = 0
    dut.ena.value = 1
    await driver.tick(4)
    dut.rst_n.value = 1
    await driver.tick()
    assert await driver.transaction(1, 21) == 2
    assert await driver.transaction(1, 9) == 0
    assert await driver.transaction(1, 10) == 0
    await load_table(driver,target().program)
    # Invalid hold ownership cannot enable the generic transaction path.
    await driver.transaction(2, 22, 27)
    await driver.transaction(2, 0, 9)
    assert await driver.transaction(1, 0) == 8
    assert await driver.transaction(1, 18) & 1
    await driver.transaction(2, 2, 18)
    await driver.transaction(2, 6, 6)
    await driver.transaction(2, 3, 63)
    await driver.transaction(2, 4, 0)
    invalid_first=Entry(RX,RISING,1,argument=0).encode().to_bytes(8,"little")
    for index,value in enumerate(invalid_first):
        await driver.transaction(2,128+index,value)
    await driver.transaction(2, 0, 9)
    assert await driver.transaction(1, 0) == 8, "Invalid receive length enabled"
    await load_table(driver,target().program,0,8)
    await driver.transaction(2, 0, 9)
    bus = I2CController(driver)
    await bus.hold(16)
    await bus.start()
    assert not await bus.write(0xa6)
    await bus.stop()
    await bus.start()
    assert await bus.write(0xa4)
    for value in (0, 255, 85, 170):
        assert await bus.write(value)
    assert not await bus.write(99)
    await bus.stop()
    assert [await driver.transaction(1, 17) for _ in range(4)] == [0, 255, 85, 170]
    await bus.start()
    assert await bus.write(0xa4) and await bus.write(37)
    await driver.transaction(2, 16, 165)
    await bus.start()  # RX -> TX through repeated START.
    assert await bus.write(0xa5)
    assert await bus.read(ack=True) == 165
    await bus.hold(100, scl=1)
    assert int(dut.uio_oe.value) & 2
    await driver.transaction(2, 16, 90)  # Host progresses while target stretches.
    assert await bus.read() == 90
    await bus.stop()
    assert await driver.transaction(1, 17) == 37
    assert await driver.transaction(1, 20) == 0
    original_byte=await driver.transaction(1,128)
    await driver.transaction(2,128,original_byte ^ 255)
    assert await driver.transaction(1,128)==original_byte, "Enabled configuration changed"
    await driver.transaction(2, 0, 8)
    await load_table(driver,target(ack_data=False).program,64,72)
    await driver.transaction(2, 0, 9)
    await bus.start()
    assert await bus.write(0xa4) and not await bus.write(85)
    await bus.stop()
    await bus.start()
    assert await bus.write(0xa5)
    await bus.hold(20, scl=1)
    assert int(dut.uio_oe.value) & 2
    dut.rst_n.value = 0
    await driver.tick(4)
    assert int(dut.uio_oe.value) == 0
    dut.rst_n.value = 1
    await driver.tick()
    assert await driver.transaction(1, 21) == 2
    assert await driver.transaction(1, 22) == 0
    assert await driver.transaction(1, 19) == 0


@cocotb.test()
async def runtime_microwire_qualification(dut):
    driver=Driver(dut)
    dut.rst_n.value=0;dut.ena.value=1
    driver.pins=252
    await driver.tick(4)
    dut.rst_n.value=1
    await driver.tick()
    await load_table(driver,microwire_config().program)
    await driver.transaction(2,22,5)
    await driver.transaction(2,0,9)

    def resolve(current):
        oe=int(dut.uio_oe.value);value=int(dut.uio_out.value)
        assert oe & ~8==0, "Microwire target acquired a controller pin"
        level=(value>>3)&1 if oe&8 else 1
        current.pins=(current.pins & ~8)|(level<<3)

    driver.on_tick=resolve
    for _ in range(2):
        await driver.transaction(2,16,0xa5)
        await driver.transaction(2,16,0x5a)
        driver.pins |= 1
        await driver.tick(32)
        for bit in [1,1,0,0,0,0,0,0,0]:
            driver.pins=(driver.pins & ~6)|(bit<<2)
            await driver.tick(32)
            driver.pins |= 2
            await driver.tick(32)
            driver.pins &= ~2
            await driver.tick(32)
        assert int(dut.uio_oe.value)&8 and not int(dut.uio_out.value)&8, "Missing dummy zero"
        word=0
        for _bit in range(16):
            driver.pins |= 6
            await driver.tick(32)
            assert int(dut.uio_oe.value)&8, "Interrupted continuous response"
            value=int(dut.uio_out.value)&8
            word=(word<<1)|int(bool(value))
            driver.pins &= ~2
            await driver.tick(32)
            assert int(dut.uio_out.value)&8==value, "Falling edge advanced response"
        assert word==0xa55a
        driver.pins &= ~1
        await driver.tick(8)
        assert int(dut.uio_oe.value)==0
    assert await driver.transaction(1,20)==0
