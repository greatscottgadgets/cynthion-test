from cynthion.selftest.registers import *
from cynthion.selftest.gateware import SelftestDevice
from cynthion.selftest.host import StandaloneTester
from apollo_fpga.support.selftest import named_test
from luna.gateware.interface.i2c import I2CRegisterInterface
from luna import top_level_cli
from amaranth import Signal, Cat

REGISTER_TARGET_TYPEC_CTL_ADDR  = 22
REGISTER_TARGET_TYPEC_CTL_VALUE = 23
REGISTER_AUX_TYPEC_CTL_ADDR     = 24
REGISTER_AUX_TYPEC_CTL_VALUE    = 25
REGISTER_PWR_MON_ADDR           = 26
REGISTER_PWR_MON_VALUE          = 27

REGISTER_CON_VBUS_EN            = 28
REGISTER_AUX_VBUS_EN            = 29
REGISTER_PASS_CONTROL           = 30
REGISTER_PASS_AUX               = 31
REGISTER_PASS_TARGET_C          = 32

REGISTER_AUX_SBU                = 33
REGISTER_TARGET_SBU             = 34

REGISTER_BUTTON_USER            = 35

REGISTER_PMOD_A_OUT             = 36
REGISTER_PMOD_B_IN              = 37

REGISTER_SENSE_DP               = 38
REGISTER_SENSE_DM               = 39


class AssistedSelftestDevice(SelftestDevice):

    def elaborate(self, platform):
        m = super().elaborate(platform)

        registers = m.submodules.registers

        # VBUS enable registers.
        con_vbus_reg = registers.add_register(REGISTER_CON_VBUS_EN, size=1, reset=True)
        aux_vbus_reg = registers.add_register(REGISTER_AUX_VBUS_EN, size=1, reset=True)

        con_thru_reg = registers.add_register(REGISTER_PASS_CONTROL, size=1, reset=False)
        aux_thru_reg = registers.add_register(REGISTER_PASS_AUX, size=1, reset=False)
        tc_thru_reg = registers.add_register(REGISTER_PASS_TARGET_C, size=1, reset=True)

        m.d.comb += [
            platform.request("control_vbus_in_en", 0, dir="o").o.eq(con_vbus_reg),
            platform.request("aux_vbus_in_en", 0, dir="o").o.eq(aux_vbus_reg),
            platform.request("control_vbus_en", 0, dir="o").o.eq(con_thru_reg),
            platform.request("aux_vbus_en", 0, dir="o").o.eq(aux_thru_reg),
            platform.request("target_c_vbus_en", 0, dir="o").o.eq(tc_thru_reg),
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
        power_mon = self.add_i2c_registers(m, platform,
            i2c_bus="power_monitor",
            dev_address=0b0010000,  # PAC195X slave address when ADDRSEL tied to GND
            register_base=REGISTER_PWR_MON_ADDR,
            data_bytes=2
        )
        m.d.comb += [
            power_mon.slow.o.eq(1),
            power_mon.pwrdn.o.eq(0),
        ]

        # SBU control registers.
        aux_sbu_reg = registers.add_register(REGISTER_AUX_SBU, size=2, reset=0)
        target_sbu_reg = registers.add_register(REGISTER_TARGET_SBU, size=2, reset=0)
        m.d.comb += [
            Cat([aux_type_c.sbu2, aux_type_c.sbu1]).eq(aux_sbu_reg),
            Cat([target_type_c.sbu2, target_type_c.sbu1]).eq(target_sbu_reg),
        ]

        # User button register.
        button_input = platform.request("button_user").i
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

        # PMOD test registers.
        pmod_out = platform.request("user_pmod", 0, dir='o').o
        pmod_in = platform.request("user_pmod", 1, dir='i').i
        pmod_out_reg = registers.add_register(REGISTER_PMOD_A_OUT, size=8)
        m.d.comb += pmod_out.eq(pmod_out_reg)
        registers.add_sfr(REGISTER_PMOD_B_IN, read=pmod_in)

        # D+/D- sense registers.
        usb_dp = platform.request("target_usb_dp", 0, dir='i').i
        usb_dm = platform.request("target_usb_dm", 0, dir='i').i
        registers.add_sfr(REGISTER_SENSE_DP, read=usb_dp)
        registers.add_sfr(REGISTER_SENSE_DM, read=usb_dm)

        return m


    def add_i2c_registers(self, m, platform, *, i2c_bus, dev_address, register_base, data_bytes=1):
        """ Adds a set of I2C registers to the active design. """

        target_i2c = platform.request(i2c_bus, dir={'sbu1': 'o', 'sbu2': 'o', 'slow': 'o', 'pwrdn': 'o'})
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


class AssistedTester(StandaloneTester):

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
    tester = top_level_cli(AssistedSelftestDevice)
