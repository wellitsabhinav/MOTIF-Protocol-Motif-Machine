import cocotb
from cocotb.triggers import Timer


class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.ui = 2
        self.pins = 255

    async def tick(self, count=8):
        self.dut.ui_in.value = self.ui
        self.dut.uio_in.value = self.pins
        for _ in range(count):
            self.dut.clk.value = 0
            await Timer(10, unit="ns")
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
