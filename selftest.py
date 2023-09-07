#!/usr/bin/env python3
#
# This file is part of LUNA.
#
# Copyright (c) 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-License-Identifier: BSD-3-Clause

import operator
from functools import reduce

from amaranth import Signal, Elaboratable, Module, Cat, ClockDomain, ClockSignal, ResetSignal
from amaranth.lib.cdc import FFSynchronizer

from luna                             import top_level_cli
from luna.gateware.utils.cdc          import synchronize
from luna.gateware.architecture.car   import LunaECP5DomainGenerator
from luna.gateware.interface.jtag     import JTAGRegisterInterface
from luna.gateware.interface.ulpi     import ULPIRegisterWindow
from luna.gateware.interface.psram    import HyperRAMInterface
from luna.gateware.interface.i2c      import I2CRegisterInterface

from apollo_fpga.support.selftest     import ApolloSelfTestCase, named_test


CLOCK_FREQUENCIES = {
    "fast": 60,
    "sync": 60,
    "usb":  60
}



# Store the IDs for Cypress and Winbond HyperRAMs.
ALLOWED_HYPERRAM_IDS = (0x0c81, 0x0c86)


REGISTER_ID             = 1
REGISTER_LEDS           = 2

REGISTER_CON_VBUS_EN    = 3
REGISTER_AUX_VBUS_EN    = 4

REGISTER_TARGET_ADDR    = 7
REGISTER_TARGET_VALUE   = 8
REGISTER_TARGET_RXCMD   = 9

REGISTER_AUX_ADDR      = 10
REGISTER_AUX_VALUE     = 11
REGISTER_AUX_RXCMD     = 12

REGISTER_CONTROL_ADDR  = 13
REGISTER_CONTROL_VALUE = 14
REGISTER_CONTROL_RXCMD = 15

REGISTER_RAM_REG_ADDR   = 20
REGISTER_RAM_VALUE      = 21

REGISTER_TARGET_TYPEC_CTL_ADDR  = 22
REGISTER_TARGET_TYPEC_CTL_VALUE = 23
REGISTER_AUX_TYPEC_CTL_ADDR     = 24
REGISTER_AUX_TYPEC_CTL_VALUE    = 25
REGISTER_PWR_MON_ADDR           = 26
REGISTER_PWR_MON_VALUE          = 27

REGISTER_PASS_CONTROL  = 28
REGISTER_PASS_AUX      = 29
REGISTER_PASS_TARGET_C = 30

REGISTER_AUX_SBU = 31
REGISTER_TARGET_SBU = 32

REGISTER_BUTTON_USER = 33


class InteractiveSelftest(Elaboratable, ApolloSelfTestCase):
    """ Hardware meant to demonstrate use of the Debug Controller's register interface.

    Registers:
        0 -- register/address size auto-negotiation for Apollo

        1 -- gateware ID register (TEST)
        2 -- fpga LEDs

        7 -- target PHY ULPI register address
        8 -- target PHY ULPI register value
        9 -- last target PHY RxCmd

        10 -- host PHY ULPI register address
        11 -- host PHY ULPI register value
        12 -- last host PHY RxCmd

        13 -- sideband PHY ULPI register address
        14 -- sideband PHY ULPI register value
        15 -- last sideband PHY RxCmd

        20 -- HyperRAM register address
        21 -- HyperRAM register value
    """

    def elaborate(self, platform):
        m = Module()

        # Generate our clock domains.
        clocking = LunaECP5DomainGenerator(clock_frequencies=CLOCK_FREQUENCIES)
        m.submodules.clocking = clocking

        registers = JTAGRegisterInterface(default_read_value=0xDEADBEEF)
        m.submodules.registers = registers

        # Simple applet ID register.
        registers.add_read_only_register(REGISTER_ID, read=0x54455354)

        # LED test register.
        led_reg = registers.add_register(REGISTER_LEDS, size=6, name="leds", reset=0)
        led_out   = Cat([platform.request("led", i, dir="o") for i in range(0, 6)])
        m.d.comb += led_out.eq(led_reg)

        # VBUS enable registers.
        con_vbus_reg = registers.add_register(REGISTER_CON_VBUS_EN, size=1, reset=True)
        aux_vbus_reg = registers.add_register(REGISTER_AUX_VBUS_EN, size=1, reset=True)

        con_thru_reg = registers.add_register(REGISTER_PASS_CONTROL, size=1, reset=False)
        aux_thru_reg = registers.add_register(REGISTER_PASS_AUX, size=1, reset=False)
        tc_thru_reg = registers.add_register(REGISTER_PASS_TARGET_C, size=1, reset=True)

        m.d.comb += [
            platform.request("control_vbus_in_en", 0, dir="o").eq(con_vbus_reg),
            platform.request("aux_vbus_in_en", 0, dir="o").eq(aux_vbus_reg),
            platform.request("control_vbus_en", 0, dir="o").eq(con_thru_reg),
            platform.request("aux_vbus_en", 0, dir="o").eq(aux_thru_reg),
            platform.request("target_c_vbus_en", 0, dir="o").eq(tc_thru_reg),
        ]

        #
        # ULPI PHY windows
        #
        self.add_ulpi_registers(m, platform,
            ulpi_bus="target_phy",
            register_base=REGISTER_TARGET_ADDR
        )
        self.add_ulpi_registers(m, platform,
            ulpi_bus="aux_phy",
            register_base=REGISTER_AUX_ADDR
        )
        self.add_ulpi_registers(m, platform,
            ulpi_bus="control_phy",
            register_base=REGISTER_CONTROL_ADDR
        )


        #
        # HyperRAM test connections.
        #
        ram_bus = platform.request('ram')
        psram = HyperRAMInterface(bus=ram_bus, **platform.ram_timings)
        m.submodules += psram

        psram_address_changed = Signal()
        psram_address = registers.add_register(REGISTER_RAM_REG_ADDR, write_strobe=psram_address_changed)

        registers.add_sfr(REGISTER_RAM_VALUE, read=psram.read_data)

        # Hook up our PSRAM.
        m.d.comb += [
            ram_bus.reset          .eq(0),
            psram.single_page      .eq(0),
            psram.perform_write    .eq(0),
            psram.register_space   .eq(1),
            psram.final_word       .eq(1),
            psram.start_transfer   .eq(psram_address_changed),
            psram.address          .eq(psram_address),
        ]

        #
        # I2C registers interface
        #
        target_type_c = self.add_i2c_registers(m, platform,
            i2c_bus="target_type_c",
            dev_address=0b0100010,  # FUSB302BMPX slave address
            register_base=REGISTER_TARGET_TYPEC_CTL_ADDR
        )
        aux_type_c = self.add_i2c_registers(m, platform,
            i2c_bus="aux_type_c",
            dev_address=0b0100010,  # FUSB302BMPX slave address
            register_base=REGISTER_AUX_TYPEC_CTL_ADDR
        )
        self.add_i2c_registers(m, platform,
            i2c_bus="power_monitor",
            dev_address=0b0010000,  # PAC195X slave address when ADDRSEL tied to GND
            register_base=REGISTER_PWR_MON_ADDR,
            data_bytes=2
        )

        # SBU control registers.
        aux_sbu_reg = registers.add_register(REGISTER_AUX_SBU, size=2, reset=0)
        target_sbu_reg = registers.add_register(REGISTER_TARGET_SBU, size=2, reset=0)
        m.d.comb += [
            Cat([aux_type_c.sbu2, aux_type_c.sbu1]).eq(aux_sbu_reg),
            Cat([target_type_c.sbu2, target_type_c.sbu1]).eq(target_sbu_reg),
        ]

        # User button register.
        button_input = platform.request("button_user")
        button_pressed = Signal()
        button_reset = Signal()
        registers.add_sfr(
            REGISTER_BUTTON_USER,
            read=button_pressed,
            write_strobe=button_reset,
            write_signal=Signal())
        with m.If(button_reset):
            m.d.usb += button_pressed.eq(False)
        with m.Elif(button_input):
            m.d.usb += button_pressed.eq(True)

        return m


    def add_ulpi_registers(self, m, platform, *, ulpi_bus, register_base):
        """ Adds a set of ULPI registers to the active design. """

        target_ulpi      = platform.request(ulpi_bus)

        ulpi_reg_window  = ULPIRegisterWindow()
        m.submodules  += ulpi_reg_window

        m.d.comb += [
            ulpi_reg_window.ulpi_data_in  .eq(target_ulpi.data.i),
            ulpi_reg_window.ulpi_dir      .eq(target_ulpi.dir.i),
            ulpi_reg_window.ulpi_next     .eq(target_ulpi.nxt.i),

            target_ulpi.clk      .eq(ClockSignal("usb")),
            target_ulpi.rst      .eq(ResetSignal("usb")),
            target_ulpi.stp      .eq(ulpi_reg_window.ulpi_stop),
            target_ulpi.data.o   .eq(ulpi_reg_window.ulpi_data_out),
            target_ulpi.data.oe  .eq(~target_ulpi.dir.i)
        ]

        register_address_change  = Signal()
        register_value_change    = Signal()

        # ULPI register address.
        registers = m.submodules.registers
        registers.add_register(register_base + 0,
            write_strobe=register_address_change,
            value_signal=ulpi_reg_window.address,
            size=6
        )
        m.submodules.clocking.stretch_sync_strobe_to_usb(m,
            strobe=register_address_change,
            output=ulpi_reg_window.read_request,
        )

        # ULPI register value.
        registers.add_sfr(register_base + 1,
            read=ulpi_reg_window.read_data,
            write_signal=ulpi_reg_window.write_data,
            write_strobe=register_value_change
        )
        m.submodules.clocking.stretch_sync_strobe_to_usb(m,
            strobe=register_value_change,
            output=ulpi_reg_window.write_request
        )

    def add_i2c_registers(self, m, platform, *, i2c_bus, dev_address, register_base, data_bytes=1):
        """ Adds a set of I2C registers to the active design. """

        target_i2c = platform.request(i2c_bus, dir={'sbu1': 'o', 'sbu2': 'o'})
        i2c_if     = I2CRegisterInterface(pads=target_i2c, period_cyc=300, address=dev_address, data_bytes=data_bytes)
        m.submodules += i2c_if

        register_address_change  = Signal()
        register_value_change    = Signal()

        reg_size                 = Signal(8)
        m.d.comb += i2c_if.size.eq(reg_size)

        # I2C register address.
        registers = m.submodules.registers
        registers.add_register(register_base + 0,
            write_strobe=register_address_change,
            value_signal=Cat(reg_size, i2c_if.address),  # 16-bit value: (address << 8) | size
        )
        m.d.sync += i2c_if.read_request.eq(register_address_change)

        # I2C register value.
        registers.add_sfr(register_base + 1,
            read=i2c_if.read_data,
            write_signal=i2c_if.write_data,
            write_strobe=register_value_change
        )
        m.d.sync += i2c_if.write_request.eq(register_value_change)

        return target_i2c

    def assertPhyRegister(self, phy_register_base: int, register: int, expected_value: int):
        """ Asserts that a PHY register contains a given value.

        Parameters:
            phy_register_base -- The base address of the PHY window in the debug SPI
                                 address range.
            register          -- The PHY register to check.
            value             -- The expected value of the relevant PHY register.
        """

        # Set the address of the ULPI register we're going to read from.
        self.dut.registers.register_write(phy_register_base, register)
        self.dut.registers.register_write(phy_register_base, register)

        # ... and read back its value.
        actual_value = self.dut.registers.register_read(phy_register_base + 1)

        # Finally, validate it.
        if actual_value != expected_value:
            raise AssertionError(f"PHY register {register} was {actual_value}, not expected {expected_value}")


    def assertPhyReadBack(self, phy_register_base: int, value: int):
        """ Writes a value to the PHY scratch register and asserts that the read-back matches.

        Parameters:
            phy_register_base -- The base address of the PHY window in the debug SPI
                                 address range.
            value             -- The value written to the scratch register.
        """

        # Set the address of the ULPI register we're going to read from.
        self.dut.registers.register_write(phy_register_base, 0x16)

        # Write the value to it.
        self.dut.registers.register_write(phy_register_base + 1, value)

        # Set the address again to perform the read.
        self.dut.registers.register_write(phy_register_base, 0x16)

        # ... and read back the value.
        actual_value = self.dut.registers.register_read(phy_register_base + 1)

        # Finally, validate it.
        if actual_value != value:
            raise AssertionError(f"PHY scratch register read-back was {actual_value}, not expected {value}")


    def assertPhyPresence(self, register_base: int):
        """ Assertion that fails iff the given PHY isn't detected. """

        # Check the value of our four ID registers, which should
        # read 2404:0900 (vendor: microchip; product: USB3343).
        self.assertPhyRegister(register_base, 0, 0x24)
        self.assertPhyRegister(register_base, 1, 0x04)
        self.assertPhyRegister(register_base, 2, 0x09)
        self.assertPhyRegister(register_base, 3, 0x00)

        # Write some patterns to the scratch register & read them back
        # to exercise all the DATA# lines.
        self.assertPhyReadBack(register_base, 0x00)
        self.assertPhyReadBack(register_base, 0xff)
        for i in range(8):
            self.assertPhyReadBack(register_base, (1 << i))


    def assertHyperRAMRegister(self, address: int, expected_values: int):
        """ Assertion that fails iff a RAM register doesn't hold the expected value. """

        self.dut.registers.register_write(REGISTER_RAM_REG_ADDR, address)
        self.dut.registers.register_write(REGISTER_RAM_REG_ADDR, address)
        actual_value =  self.dut.registers.register_read(REGISTER_RAM_VALUE)

        if actual_value not in expected_values:
            raise AssertionError(f"RAM register {address} was {actual_value}, not one of expected {expected_values}")


    @named_test("Debug module")
    def test_debug_connection(self, dut):
        self.assertRegisterValue(1, 0x54455354)


    @named_test("AUX PHY")
    def test_host_phy(self, dut):
        self.assertPhyPresence(REGISTER_AUX_ADDR)


    @named_test("TARGET PHY")
    def test_target_phy(self, dut):
        self.assertPhyPresence(REGISTER_TARGET_ADDR)


    @named_test("CONTROL PHY")
    def test_sideband_phy(self, dut):
        self.assertPhyPresence(REGISTER_CONTROL_ADDR)


    @named_test("HyperRAM")
    def test_hyperram(self, dut):
        self.assertHyperRAMRegister(0, ALLOWED_HYPERRAM_IDS)

    @named_test("TARGET Type-C")
    def test_target_typec_controller(self, dut):
        self.dut.registers.register_write(REGISTER_TARGET_TYPEC_CTL_ADDR, (0x01 << 8) | 1)
        actual_value = self.dut.registers.register_read(REGISTER_TARGET_TYPEC_CTL_VALUE)
        if actual_value & 0b11001100 != 0b10000000:
            raise AssertionError(f"TARGET Type-C ID device ID register was {bin(actual_value)}, not 0b10xx00xx")

    @named_test("AUX Type-C")
    def test_aux_typec_controller(self, dut):
        self.dut.registers.register_write(REGISTER_AUX_TYPEC_CTL_ADDR, (0x01 << 8) | 1)
        actual_value = self.dut.registers.register_read(REGISTER_AUX_TYPEC_CTL_VALUE)
        if actual_value & 0b11001100 != 0b10000000:
            raise AssertionError(f"TARGET Type-C ID device ID register was {bin(actual_value)}, not 0b10xx00xx")

    @named_test("Power monitor")
    def test_power_monitor_controller(self, dut):
        self.dut.registers.register_write(REGISTER_PWR_MON_ADDR, (0xFE << 8) | 1)
        actual_value = self.dut.registers.register_read(REGISTER_PWR_MON_VALUE)
        if actual_value != 0x54:
            raise AssertionError(f"Power Monitor manufacturer ID register 0x{actual_value:x} != 0x54")

if __name__ == "__main__":
    tester = top_level_cli(InteractiveSelftest)

    if tester:
        tester.run_tests()

    print()
