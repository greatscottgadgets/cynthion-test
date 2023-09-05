from colorama import Fore, Back, Style
from selftest import InteractiveSelftest, \
    REGISTER_LEDS, REGISTER_CON_VBUS_EN, REGISTER_AUX_VBUS_EN, \
    REGISTER_AUX_TYPEC_CTL_ADDR, REGISTER_AUX_TYPEC_CTL_VALUE, \
    REGISTER_TARGET_TYPEC_CTL_ADDR, REGISTER_TARGET_TYPEC_CTL_VALUE, \
    REGISTER_PWR_MON_ADDR, REGISTER_PWR_MON_VALUE, \
    REGISTER_PASS_CONTROL, REGISTER_PASS_AUX, REGISTER_PASS_TARGET_C, \
    REGISTER_AUX_SBU, REGISTER_TARGET_SBU
from apollo_fpga import ApolloDebugger
from tps55288 import TPS55288
from greatfet import *
from time import sleep
import colorama
import inspect
import os

gpio_allocations = dict(
    BOOST_EN = ('J2_P25', 0),
    BOOST_VBUS_AUX = ('J2_P16', 0),
    BOOST_VBUS_CON = ('J2_P15', 0),
    BOOST_VBUS_TC = ('J2_P34', 0),
    CC1_test = ('J1_P17', None),
    CC2_test = ('J1_P18', None),
    CC_PULL_UP = ('J1_P7', 1),
    D_S_1 = ('J1_P3', 0),
    D_S_2 = ('J1_P19', 0),
    D_S_3 = ('J1_P26', 0),
    D_OEn_1 = ('J1_P4', 1),
    D_OEn_2 = ('J1_P20', 1),
    D_OEn_3 = ('J1_P28', 1),
    GND_EN = ('J2_P31', 0),
    GND_EUT = ('J2_P33', None),
    SBU1_test = ('J1_P30', None),
    SBU2_test = ('J1_P32', None),
    D_TEST_PLUS = ('J1_P6', None),
    D_TEST_MINUS = ('J1_P8', None),
    V_DIV = ('J1_P9', 0),
    V_DIV_MULT = ('J1_P5', 0),
    REF_LED_EN = ('J1_P35', 0),
    MUX1_EN = ('J1_P15', 0),
    MUX1_A0 = ('J1_P14', 0),
    MUX1_A1 = ('J1_P13', 0),
    MUX1_A2 = ('J1_P12', 0),
    MUX1_A3 = ('J1_P10', 0),
    MUX2_EN = ('J1_P23', 0),
    MUX2_A0 = ('J1_P24', 0),
    MUX2_A1 = ('J1_P21', 0),
    MUX2_A2 = ('J1_P22', 0),
    MUX2_A3 = ('J1_P25', 0),
    TEST_5V = ('J1_P37', 0),
    TEST_20V = ('J1_P33', 0),
    TA_DIS = ('J1_P34', 1),
    HOST_VBUS_CON = ('J2_P13', 0),
    HOST_VBUS_AUX = ('J2_P14', 0),
    SIG1_OEn = ('J2_P24', 1),
    SIG2_OEn = ('J2_P22', 1),
    SIG1_S = ('J2_P23', 0),
    SIG2_S = ('J2_P27', 0),
)

mux_channels = {
    '+1V1': (0, 7),
    '+2V5': (1, 9),
    '+3V3': (1, 8),
    '+5V': (0, 13),
    'VCCRAM': (1, 11),
    'CONTROL_PHY_1V8': (1, 1),
    'CONTROL_PHY_3V3': (0, 6),
    'AUX_PHY_1V8': (1, 0),
    'AUX_PHY_3V3': (1, 2),
    'TARGET_PHY_1V8': (1, 10),
    'TARGET_PHY_3V3': (1, 12),
    'TARGET_A_VBUS': (1, 3),
    'VBUS_CON': (1, 4),
    'VBUS_AUX': (1, 5),
    'VBUS_TA': (1, 7),
    'VBUS_TC': (1, 6),
    'CC1_test': (0, 3),
    'CC2_test': (0, 2),
    'D2_Vf': (0, 1),
    'D3_Vf': (0, 0),
    'D4_Vf': (0, 9),
    'D5_Vf': (0, 8),
    'D6_Vf': (0, 11),
    'D7_Vf': (0, 10),
    'D10_Vf': (0, 12),
    'D11_Vf': (0, 4),
    'D12_Vf': (0, 14),
    'D13_Vf': (0, 5),
    'D14_Vf': (0, 15),
    'CDC': (1, 15),
    'SPARE1': (1, 13),
    'SPARE2': (1, 14),
}

vbus_channels = {
    'CONTROL':  'VBUS_CON',
    'AUX':      'VBUS_AUX',
    'TARGET-A': 'VBUS_TA',
    'TARGET-C': 'VBUS_TC',
}

vbus_registers = {
    'CONTROL': REGISTER_CON_VBUS_EN,
    'AUX':     REGISTER_AUX_VBUS_EN,
}

passthrough_registers = {
    'CONTROL':  REGISTER_PASS_CONTROL,
    'AUX':      REGISTER_PASS_AUX,
    'TARGET-C': REGISTER_PASS_TARGET_C,
}

typec_registers = {
    'AUX': (REGISTER_AUX_TYPEC_CTL_ADDR, REGISTER_AUX_TYPEC_CTL_VALUE),
    'TARGET-C': (REGISTER_TARGET_TYPEC_CTL_ADDR, REGISTER_TARGET_TYPEC_CTL_VALUE),
}

sbu_registers = {
    'AUX': REGISTER_AUX_SBU,
    'TARGET-C': REGISTER_TARGET_SBU
}

mon_voltage_registers = {
    'CONTROL': 0x08,
    'AUX': 0x07,
    'TARGET-C': 0x0A,
    'TARGET-A': 0x09,
}

mon_current_registers = {
    'CONTROL': 0x0C,
    'AUX': 0x0B,
    'TARGET-C': 0x0E,
    'TARGET-A': 0x0D,
}

gf = GreatFET()

for name, (position, state) in gpio_allocations.items():
    pin = gf.gpio.get_pin(position)
    globals()[name] = pin
    if state is None:
        pin.input()
    elif state:
        pin.high()
    else:
        pin.low()

BOOST_EN.high()
boost = TPS55288(gf)
boost.disable()

colorama.init()

indent = 0

def reset():
    for name, (position, state) in gpio_allocations.items():
        pin = globals()[name]
        if state is None:
            pin.input()
        elif state:
            pin.high()
        else:
            pin.low()

def msg(text, end):
    print(("  " * indent) + "• " + text + Style.RESET_ALL, end=end)

def item(text):
    msg(text, "\n")

def begin(text):
    global indent
    msg(text, ":\n")
    indent += 1

def end():
    global indent
    indent -= 1

def start(text):
    msg(text, "... ")

def done():
    print(Fore.GREEN + "OK" + Style.RESET_ALL)

def fail():
    print(Fore.RED + "FAIL" + Style.RESET_ALL)

def todo(text):
    item(Fore.YELLOW + "TODO" + Style.RESET_ALL + ": " + text)

def info(text):
    return Fore.CYAN + str(text) + Style.RESET_ALL

def begin_short_check(a, b, port):
    begin(f"Checking for {info(a)} to {info(b)} short on {info(port)}")

def check_for_shorts(port):
    begin(f"Checking for shorts on {info(port)}")

    connect_tester_to(port)
    connect_tester_cc_sbu_to(port)

    begin_short_check('VBUS', 'GND', port)
    set_pin('GND_EUT', True)
    test_vbus(port, 2.0, 2.9)
    set_pin('GND_EUT', None)
    end()

    begin_short_check('VBUS', 'SBU2', port)
    set_pin('SBU2_test', True)
    test_vbus(port, 0.0, 1.2)
    set_pin('SBU2_test', None)
    end()

    begin_short_check('SBU2', 'CC1', port)
    set_pin('SBU2_test', True)
    test_voltage('CC1_test', 0.0, 1.2)
    set_pin('SBU2_test', None)
    end()

    todo("CC1/D- short check")

    todo("D-/D+ short check")

    todo("D+/SBU1 short check")

    todo("SBU1/CC2 short check")

    todo("CC2/VBUS short check")

    # begin_short_check('SBU1', 'CC2', port)
    # set_pin('SBU1_test', True)
    # test_voltage('CC2_test', 0.0, 1.2)
    # set_pin('SBU1_test', None)
    # end()

    # begin_short_check('CC2', 'VBUS', port)
    # set_pin('CC2_test', True)
    # test_vbus(port, 0.0, 1.2)
    # set_pin('CC2_test', None)
    # end()

    end()

def connect_grounds():
    item("Connecting EUT ground to Tycho ground")
    GND_EN.high()

def connect_tester_to(port):
    todo(f"Connecting tester D+/D- to {info(port)}")

def connect_host_to(port):
    item(f"Connecting host D+/D- to {info(port)}")
    D_OEn_1.high()
    D_OEn_2.high()
    D_OEn_3.high()
    if port is None:
        return
    D_S_1.set_state(0)
    D_S_2.set_state(port != 'CONTROL')
    D_S_3.set_state(port == 'TARGET-C')
    D_OEn_1.low()
    D_OEn_2.low()
    D_OEn_3.low()

def begin_cc_measurement(port):
    connect_tester_cc_sbu_to(port)
    V_DIV.low()
    V_DIV_MULT.low()
    CC_PULL_UP.low()
    CC1_test.input()
    CC2_test.input()

def end_cc_measurement():
    CC_PULL_UP.high()

def check_cc_resistances(port):
    begin(f"Checking CC resistances on {info(port)}")
    begin_cc_measurement(port)
    for pin in ('CC1', 'CC2'):
        check_cc_resistance(pin, 4.1, 6.1)
    end_cc_measurement()
    end()

def check_cc_resistance(pin, minimum, maximum):
    if pin == 'CC2':
        todo(f"Checking resistance on {info(pin)}")
        return
    channel = f'{pin}_test'
    mux_select(channel)
    samples = gf.adc.read_samples(1000)
    voltage = (3.3 / 1024) * sum(samples) / len(samples)
    item(f"Checking voltage on {info(channel)}: {info(f'{voltage:.2f} V')}")
    resistance = (3.3 * 30 - voltage * 35.1) / (voltage - 3.3)
    return test_value("resistance", pin, resistance, 'kΩ', minimum, maximum, ignore=True)

def test_leakage(port):
    test_vbus(port, 0, 0.2)

def set_boost_supply(voltage, current):
    item(f"Setting DC-DC converter to {info(f'{voltage:.2f} V')} {info(f'{current:.2f} A')}")
    boost.set_voltage(voltage)
    boost.set_current_limit(current)
    boost.enable()

def connect_boost_supply_to(port):
    if port is None:
        item(f"Disconnecting DC-DC converter")
    else:
        item(f"Connecting DC-DC converter to {info(port)}")
    BOOST_VBUS_AUX.low()
    BOOST_VBUS_CON.low()
    BOOST_VBUS_TC.low()
    if port == 'AUX':
        BOOST_VBUS_AUX.high()
    if port == 'CONTROL':
        BOOST_VBUS_CON.high()
    if port == 'TARGET-C':
        BOOST_VBUS_TC.high()

def mux_select(channel):
    mux, pin = mux_channels[channel]

    MUX1_EN.low()
    MUX2_EN.low()

    if mux == 0:
        MUX1_A0.write(pin & 1)
        MUX1_A1.write(pin & 2)
        MUX1_A2.write(pin & 4)
        MUX1_A3.write(pin & 8)
        MUX1_EN.high()
    else:
        MUX2_A0.write(pin & 1)
        MUX2_A1.write(pin & 2)
        MUX2_A2.write(pin & 4)
        MUX2_A3.write(pin & 8)
        MUX2_EN.high()

def test_value(qty, src, value, unit, minimum, maximum, ignore=False):
    message = f"Checking {qty} on {info(src)} is within {info(f'{minimum:.2f}')} to {info(f'{maximum:.2f} {unit}')}: "
    result = f"{value:.2f} {unit}"
    if value < minimum:
        item(message + Fore.RED + result)
        if not ignore:
            raise ValueError(f"{qty} too low on {src}: {value:.2f} {unit}, minimum was {minimum:.2f} {unit}")
    elif value > maximum:
        item(message + Fore.RED + result)
        if not ignore:
            raise ValueError(f"{qty} too high on {src}: {value:.2f} {unit}, maximum was {maximum:.2f} {unit}")
    else:
        item(message + Fore.GREEN + result)
    return value

def test_voltage(channel, minimum, maximum):
    if maximum <= 6.6:
        V_DIV.high()
        V_DIV_MULT.low()
        scale = 3.3 / 1024 * 2
    else:
        V_DIV.low()
        V_DIV_MULT.high()
        scale = 3.3 / 1024 * (30 + 5.1) / 5.1

    mux_select(channel)

    samples = gf.adc.read_samples(1000)
    voltage = scale * sum(samples) / len(samples)

    return test_value("voltage", channel, voltage, 'V', minimum, maximum)

def set_pin(pin, level):
    required = ('input' if level is None else
        'output high' if level else 'output low')
    item(f"Setting pin {info(pin)} to {info(required)}")
    pin = globals()[pin]
    if level is None:
        pin.input()
    elif level:
        pin.high()
    else:
        pin.low()

def test_pin(pin, level):
    required = 'high' if level else 'low'
    start(f"Checking pin {info(pin)} is {info(required)}")
    value = globals()[pin].input()
    found = 'high' if value else 'low'
    if value == level:
        done()
    else:
        fail()
        raise ValueError(f"Pin {pin} is {found}, should be {required}")

def disconnect_supply_and_discharge(port):
    item(f"Disconnecting supply and discharging {info(port)}")
    boost.disable()
    mux_select(vbus_channels[port])
    V_DIV.high()
    V_DIV_MULT.high()
    sleep(0.5)
    V_DIV.low()
    V_DIV_MULT.low()

def test_clock():
    todo(f"Checking clock frequency")

def run_command(cmd):
    result = os.system(cmd + " > /dev/null 2>&1")
    if result != 0:
        raise RuntimeError(f"Command '{cmd}' failed with exit status {result}")

def flash_bootloader():
    start(f"Flashing Saturn-V bootloader to MCU via SWD")
    run_command('gdb-multiarch --batch -x flash-bootloader.gdb')
    done()

def flash_firmware():
    start(f"Flashing Apollo to MCU via DFU")
    run_command('dfu-util -a 0 -d 1d50:615c -D luna_d11-firmware.bin')
    done()

def test_apollo_present():
    start(f"Checking for Apollo")
    run_command('apollo info')
    done()

def set_debug_leds(apollo, bitmask):
    start(f"Setting debug LEDs to 0b{bitmask:05b}")
    apollo.set_led_pattern(bitmask)
    done()

def set_fpga_leds(apollo, bitmask):
    start(f"Setting FPGA LEDs to 0b{bitmask:05b}")
    apollo.registers.register_write(REGISTER_LEDS, bitmask)
    assert(apollo.registers.register_read(REGISTER_LEDS) == bitmask)
    done()

def test_jtag_scan(apollo):
    begin("Checking JTAG scan chain")
    apollo.jtag.initialize()
    devices = [(device.idcode(), device.description())
        for device in apollo.jtag.enumerate()]
    for idcode, desc in devices:
        item(f"Found {info(f'0x{idcode:8X}')}: {info(desc)}")
    if devices != [(0x41111043, "Lattice LFE5U-25F ECP5 FPGA")]:
        raise ValueError("JTAG scan chain did not include expected devices")
    end()

def flash_analyzer(apollo):
    todo(f"Flashing analyzer gateware")
    return
    bitstream = open('analyzer.bit', 'rb').read()
    programmer = apollo.create_jtag_programmer(apollo.jtag)
    programmer.unconfigure()
    programmer.erase_flash()
    programmer.flash(bitstream)
    apollo.soft_reset()
    done()

def configure_fpga(apollo):
    start(f"Configuring self-test gateware")
    bitstream = open('selftest.bit', 'rb').read()
    programmer = apollo.create_jtag_programmer(apollo.jtag)
    programmer.configure(bitstream)
    done()

def run_self_test(apollo):
    begin("Running self test")
    selftest = InteractiveSelftest()
    selftest._MustUse__used = True
    selftest.dut = apollo
    for method in [
        selftest.test_debug_connection,
        selftest.test_sideband_phy,
        selftest.test_host_phy,
        selftest.test_target_phy,
        selftest.test_hyperram,
        selftest.test_aux_typec_controller,
        selftest.test_target_typec_controller,
        selftest.test_power_monitor_controller,
    ]:
        description = method.__name__.replace("test_", "")
        try:
            start(description)
            method(apollo)
            done()
        except Exception as e:
            fail()
            raise RuntimeError(f"{description} self-test failed")
    end()

def test_usb_hs(port):
    todo(f"Testing USB HS comms on {info(port)}")

def connect_tester_cc_sbu_to(port):
    item(f"Connecting tester CC/SBU lines to {info(port)}")
    SIG1_OEn.high()
    SIG2_OEn.high()
    if port is None:
        return
    SIG1_S.set_state(port == 'CONTROL')
    SIG2_S.set_state(port == 'TARGET-C')
    SIG1_OEn.low()
    SIG2_OEn.low()

def write_register(apollo, reg, value, verify=False):
    apollo.registers.register_write(reg, value)
    if verify:
        readback = apollo.registers.register_read(reg)
        if readback != value:
            raise ValueError(
                f"Wrote 0x{value:02X} to register {reg} "
                f"but read back 0x{readback:02X}")

def read_register(apollo, reg):
    return apollo.registers.register_read(reg)

def enable_supply_input(apollo, port, enable):
    start(f"{'Enabling' if enable else 'Disabling'} supply input on {info(port)}")
    write_register(apollo, vbus_registers[port], enable)
    done()

def set_cc_levels(apollo, port, levels):
    start(f"Setting CC levels on {info(port)} to {info(levels)}")
    value = 0b01 * levels[0] | 0b10 * levels[1]
    reg_addr, reg_val = typec_registers[port]
    write_register(apollo, reg_addr, (0x02 << 8) | 1)
    write_register(apollo, reg_val, value)
    done()

def set_sbu_levels(apollo, port, levels):
    start(f"Setting SBU levels on {info(port)} to {info(levels)}")
    value = 0b01 * levels[0] | 0b10 * levels[1]
    write_register(apollo, sbu_registers[port], value)
    done()

def connect_host_supply_to(*ports):
    if ports == (None,):
        item("Disconnecting host supply")
    else:
        item(f"Connecting host supply to {str.join(' and ', map(info, ports))}")
    if 'CONTROL' in ports:
        HOST_VBUS_CON.high()
    if 'AUX' in ports:
        HOST_VBUS_AUX.high()
    if 'CONTROL' not in ports:
        HOST_VBUS_CON.low()
    if 'AUX' not in ports:
        HOST_VBUS_AUX.low()

def request_target_a_cable():
    print()
    print(
        Fore.BLUE +
        "=== Connect cable to Target-A port on EUT and press ENTER ===" +
        Style.RESET_ALL)
    input()

def set_passthrough(apollo, port, enable):
    action = 'Enabling' if enable else 'Disabling'
    start(f"{action} VBUS passthrough for {info(port)}")
    write_register(apollo, passthrough_registers[port], enable)
    done()

def set_target_passive():
    todo(f"Setting target PHY to passive mode")

def test_usb_fs():
    todo(f"Testing USB FS comms through target passthrough")

def test_vbus(input_port, vmin, vmax):
    test_voltage(vbus_channels[input_port], vmin, vmax)

def configure_power_monitor(apollo):
    start("Configuring I2C power monitor")
    write_register(apollo, REGISTER_PWR_MON_ADDR, (0x1D << 8) | 2)
    write_register(apollo, REGISTER_PWR_MON_VALUE, 0x5500)
    done()

def test_eut_voltage(apollo, port, vmin, vmax):
    reg = mon_voltage_registers[port]
    write_register(apollo, REGISTER_PWR_MON_ADDR, (0x1F << 8) | 1)
    sleep(0.01)
    write_register(apollo, REGISTER_PWR_MON_VALUE, 0)
    sleep(0.01)
    write_register(apollo, REGISTER_PWR_MON_ADDR, (reg << 8) | 2)
    sleep(0.01)
    value = read_register(apollo, REGISTER_PWR_MON_VALUE)
    voltage = value * 32 / 65536
    return test_value("EUT voltage", port, voltage, 'V', vmin, vmax)

def test_eut_current(apollo, port, imin, imax):
    reg = mon_current_registers[port]
    write_register(apollo, REGISTER_PWR_MON_ADDR, (0x1F << 8) | 1)
    sleep(0.01)
    write_register(apollo, REGISTER_PWR_MON_VALUE, 0)
    sleep(0.01)
    write_register(apollo, REGISTER_PWR_MON_ADDR, (reg << 8) | 2)
    sleep(0.01)
    value = read_register(apollo, REGISTER_PWR_MON_VALUE)
    if value >= 32768:
        value -= 65536

    # ¯\_(ツ)_/¯
    if port == 'CONTROL' and value > 0:
        value *= 1.87

    voltage = value * 0.1 / 32678
    resistance = 0.02
    current = voltage / resistance
    return test_value("EUT current", port, current, 'A', imin, imax)

def request_led_check():
    todo(f"Requesting user check LEDs")

def request_apollo_reset():
    todo(f"Requesting Apollo reset the EUT")

def request_button(button):
    todo(f"Requesting user press the {info(button)} button")

def test_user_button_pressed():
    todo(f"Checking that the {info('USER')} button was pressed")

def request_control_handoff():
    pass

def test_analyzer_present():
    todo(f"Checking for analyzer")

def send_usb_reset():
    pass
