from tps55288 import TPS55288
from greatfet import *
from time import sleep
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

gf = GreatFET()

for name, (position, state) in gpio_allocations.items():
    pin = gf.gpio.get_pin(position)
    globals()[name] = pin
    if state is None:
        print(f"Setting {name} to input")
        pin.input()
    elif state:
        print(f"Setting {name} to output high")
        pin.high()
    else:
        print(f"Setting {name} to output low")
        pin.low()

BOOST_EN.high()
boost = TPS55288(gf)
boost.disable()

def check_for_shorts(port):
    # Pull mux output low to detect a high at the mux.
    V_DIV.high()
    vmin = 0.0
    vmax = 0.2

    connect_tester_to(port)
    connect_tester_cc_sbu_to(port)

    print(f"Checking for VBUS/GND short on {port}")
    GND_EUT.high()
    test_vbus(port, vmin, vmax)
    GND_EUT.low()

    print(f"Checking for VBUS/SBU2 short on {port}")
    SBU2_test.high()
    test_vbus(port, vmin, vmax)

    print(f"Checking for SBU2/CC1 short on {port}")
    CC1_test.input()
    SBU2_test.low()
    test_pin('CC1_test', True)

    print(f"Checking for CC1/D- short on {port}")
    D_TEST_MINUS.low()
    test_pin('CC1_test', True)

    print(f"Checking for D-/D+ short on {port}")
    D_TEST_PLUS.input()
    D_TEST_MINUS.low()
    test_pin('D_TEST_PLUS', True)

    print(f"Checking for D+/SBU1 short on {port}")
    SBU1_test.low()
    test_pin('D_TEST_PLUS', True)

    print(f"Checking for SBU1/CC2 short on {port}")
    CC2_test.low()
    test_pin('SBU1_test', True)

    print(f"Checking for CC2/VBUS short on {port}")
    test_vbus(port, vmin, vmax)

def connect_grounds():
    GND_EN.high()

def connect_usb(mode, port):
    print(f"Connecting {port} to {mode}")
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

def connect_tester_to(port):
    raise NotImplemented
    connect_usb('TEST', port)

def connect_host_to(port):
    connect_usb('HOST', port)

def check_cc_resistances(port):
    print(f"Checking CC resistances on {port}")
    pass

def test_leakage(port):
    print(f"Checking leakage on {port}")
    pass

def set_boost_supply(voltage, current):
    print(f"Setting DC-DC converter to {voltage:.1f}V {current:.1f}A")
    boost.set_voltage(voltage)
    boost.set_current_limit(current)
    boost.enable()

def connect_boost_supply_to(port):
    print(f"Connecting DC-DC converter to {port}")
    BOOST_VBUS_AUX.low()
    BOOST_VBUS_CON.low()
    BOOST_VBUS_TC.low()
    if port == 'AUX':
        BOOST_VBUS_AUX.high()
    if port == 'CONTROL':
        BOOST_VBUS_CON.high()
    if port == 'TARGET-C':
        BOOST_VBUS_TC.high()

def test_voltage(channel, minimum, maximum):
    if maximum <= 3.3:
        V_DIV.low()
        V_DIV_MULT.low()
        scale = 3.3 / 1024
    elif maximum <= 6.6:
        V_DIV.high()
        V_DIV_MULT.low()
        scale = 3.3 / 1024 * 2
    else:
        V_DIV.low()
        V_DIV_MULT.high()
        scale = 3.3 / 1024 * (30 + 5.1) / 5.1

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

    samples = gf.adc.read_samples(1000)
    voltage = scale * sum(samples) / len(samples)

    print(f"Checking voltage on {channel} is within {minimum:.2f} to {maximum:.2f} V: {voltage:.2f} V")

    if voltage < minimum:
        raise ValueError(f"Voltage too low on {channel}: {voltage:.2f} V, minimum was {minimum:.2f} V")
    elif voltage > maximum:
        raise ValueError(f"Voltage too high on {channel}: {voltage:.2f} V, maximum was {maximum:.2f} V")

    return voltage

def test_pin(pin, level):
    print(f"Checking pin {pin} is {'high' if level else 'low'}")
    pass

def disconnect_supply_and_discharge():
    print(f"Disconnecting and discharging supply")
    boost.disable()
    TEST_20V.high()
    sleep(0.01)
    TEST_20V.low()

def test_clock():
    print(f"Checking clock frequency")
    pass

def run_command(cmd):
    result = os.system(cmd)
    if result != 0:
        raise RuntimeError(f"Command '{cmd}' failed with exit status {result}")

def flash_bootloader():
    print(f"Flashing Saturn-V...")
    run_command('gdb-multiarch --batch -x flash-bootloader.gdb')

def flash_firmware():
    print(f"Flashing Apollo...")
    run_command('dfu-util -a 0 -d 1d50:615c -D luna_d11-firmware.bin')

def test_apollo_present():
    print(f"Checking for Apollo")
    run_command('apollo info')

def set_debug_leds(bitmask):
    print(f"Setting debug LEDs to 0b{bitmask:05b}")
    run_command(f"apollo leds {bitmask}")

def test_jtag_scan():
    pass

def flash_analyzer():
    print(f"Flashing analyzer gateware...")
    run_command('apollo force-offline')
    run_command('apollo flash-erase')
    run_command('apollo flash-program analyzer.bit')

def configure_fpga():
    print(f"Configuring self-test gateware...")
    run_command('apollo configure selftest.bit')

def test_usb_hs(port):
    pass

def set_adc_pullup(enable):
    pass

def connect_tester_cc_sbu_to(port):
    pass

def set_cc_levels(port, levels):
    pass

def set_sbu_levels(port, levels):
    pass

def connect_host_supply_to(port):
    pass

def enable_supply_input(port, enable):
    pass

def request_target_a_cable():
    pass

def set_target_passive():
    pass

def test_usb_fs():
    pass

def set_load_resistor(resistor):
    pass

def set_passthrough(input_port, output_port, enable):
    pass

def test_vbus(input_port, vmin, vmax):
    test_voltage(vbus_channels[input_port], vmin, vmax)

def test_eut_voltage(input_port, vmin, vmax):
    pass

def test_eut_current(input_port, imin, imax):
    pass

def request_led_check():
    pass

def request_button(button):
    pass

def test_user_button_pressed():
    pass

def request_control_handoff():
    pass

def test_analyzer_present():
    pass

def send_usb_reset():
    pass
