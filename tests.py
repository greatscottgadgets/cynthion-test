from selftest import InteractiveSelftest, \
    REGISTER_LEDS, REGISTER_CON_VBUS_EN, REGISTER_AUX_VBUS_EN, \
    REGISTER_AUX_TYPEC_CTL_ADDR, REGISTER_AUX_TYPEC_CTL_VALUE, \
    REGISTER_TARGET_TYPEC_CTL_ADDR, REGISTER_TARGET_TYPEC_CTL_VALUE, \
    REGISTER_PWR_MON_ADDR, REGISTER_PWR_MON_VALUE, \
    REGISTER_PASS_CONTROL, REGISTER_PASS_AUX, REGISTER_PASS_TARGET_C, \
    REGISTER_AUX_SBU, REGISTER_TARGET_SBU, REGISTER_BUTTON_USER, \
    REGISTER_PMOD_A_OUT, REGISTER_PMOD_B_IN
from luna.gateware.applets.flash_bridge import FlashBridgeConnection
from apollo_fpga.ecp5 import ECP5FlashBridgeProgrammer
from apollo_fpga import ApolloDebugger
from formatting import *
from tycho import *
from eut import *
from time import time, sleep
import usb1
import os

context = usb1.USBContext()
last_bus = None
last_addr = None

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
    'CONTROL': 0x0A,
    'AUX': 0x09,
    'TARGET-C': 0x08,
    'TARGET-A': 0x07,
}

mon_current_registers = {
    'CONTROL': 0x0E,
    'AUX': 0x0D,
    'TARGET-C': 0x0C,
    'TARGET-A': 0x0B,
}

def reset():
    for name, (position, state) in gpio_allocations.items():
        pin = globals()[name]
        if state is None:
            pin.input()
        elif state:
            pin.high()
        else:
            pin.low()

def pass_pressed():
    return not PASS.input()

def fail_pressed():
    return not FAIL.input()

def request(text):
    # Wait for any currently pressed button to be released.
    while pass_pressed() or fail_pressed():
        sleep(0.01)
    ask(text)
    while True:
        if fail_pressed():
            raise RuntimeError("Test failed at user request")
        elif pass_pressed():
            return
        sleep(0.001)

def short_check(a, b, port):
    return group(f"Checking for {info(a)} to {info(b)} short on {info(port)}")

def check_for_shorts(port):
    with group(f"Checking for shorts on {info(port)}"):

        connect_tester_to(port)
        connect_tester_cc_sbu_to(port)

        with short_check('VBUS', 'GND', port):
            set_pin('GND_EUT', True)
            test_vbus(port, 0, 0.05)
            set_pin('GND_EUT', None)

        with short_check('VBUS', 'SBU2', port):
            set_pin('SBU2_test', True)
            test_vbus(port, 0.0, 0.05)
            set_pin('SBU2_test', None)

        with short_check('SBU2', 'CC1', port):
            set_pin('SBU2_test', True)
            test_voltage('CC1_test', 0.0, 0.1)
            set_pin('SBU2_test', None)

        todo("CC1/D- short check")

        todo("D-/D+ short check")

        todo("D+/SBU1 short check")

        with short_check('SBU1', 'CC2', port):
            set_pin('SBU1_test', True)
            test_voltage('CC2_test', 0.0, 0.1)
            set_pin('SBU1_test', None)

        with short_check('CC2', 'VBUS', port):
            set_pin('CC2_test', True)
            test_vbus(port, 0.0, 0.05)
            set_pin('CC2_test', None)

        connect_tester_cc_sbu_to(None)

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
    connect_tester_cc_sbu_to(None)

def check_cc_resistances(port):
    with group(f"Checking CC resistances on {info(port)}"):
        begin_cc_measurement(port)
        for pin in ('CC1', 'CC2'):
            check_cc_resistance(pin, 4.1, 6.1)
        end_cc_measurement()

def check_cc_resistance(pin, minimum, maximum):
    channel = f'{pin}_test'
    mux_select(channel)
    samples = gf.adc.read_samples(1000)
    mux_disconnect()
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
    boost.check_fault()

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
    boost.check_fault()

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

def mux_disconnect():
    MUX1_EN.low()
    MUX2_EN.low()

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

def measure_voltage(pulldown):
    pullup = 30
    scale = 3.3 / 1024 * (pulldown + pullup) / pulldown
    samples = gf.adc.read_samples(1000)
    voltage = scale * sum(samples) / len(samples)
    return voltage

def test_voltage(channel, minimum, maximum):
    if maximum <= 6.6:
        V_DIV.high()
        V_DIV_MULT.low()
        pulldown = 30
    else:
        V_DIV.low()
        V_DIV_MULT.high()
        pulldown = 5.1
    mux_select(channel)
    voltage = measure_voltage(pulldown)
    mux_disconnect()
    V_DIV.low()
    V_DIV_MULT.low()
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
    with task(f"Checking pin {info(pin)} is {info(required)}"):
        value = globals()[pin].input()
        found = 'high' if value else 'low'
        if value != level:
            raise ValueError(f"Pin {pin} is {found}, should be {required}")

def disconnect_supply_and_discharge(port):
    item(f"Disconnecting supply and discharging {info(port)}")
    boost.disable()
    discharge(port)

def discharge(port):
    channel = vbus_channels[port]
    mux_select(channel)
    V_DIV.high()
    V_DIV_MULT.high()
    pulldown = (5.1 * 30) / (5.1 + 30)
    while measure_voltage(pulldown) > 0.1:
        sleep(0.05)
    V_DIV.low()
    V_DIV_MULT.low()
    mux_disconnect()

def test_clock():
    reference_hz = 204000000 // 10
    target_hz = 60000000
    tolerance_ppm = 50
    tolerance_hz = target_hz * tolerance_ppm / 1e6
    fmin = target_hz - tolerance_hz
    fmax = target_hz + tolerance_hz
    gf.apis.freq_count.setup_counters(reference_hz)
    gf.apis.freq_count.setup_counters(reference_hz)
    sleep(0.1)
    frequency = gf.apis.freq_count.count_cycles() * 10
    test_value("frequency", "CLK", frequency, 'Hz', fmin, fmax)

def run_command(cmd):
    result = os.system(cmd + " > /dev/null 2>&1")
    if result != 0:
        raise RuntimeError(f"Command '{cmd}' failed with exit status {result}")

def flash_bootloader():
    with task(f"Flashing Saturn-V bootloader to MCU via SWD"):
        run_command('gdb-multiarch --batch -x flash-bootloader.gdb')

def flash_firmware():
    with task(f"Flashing Apollo to MCU via DFU"):
        run_command('dfu-util -a 0 -d 1d50:615c -D firmware.bin')

def test_saturnv_present():
    with group(f"Checking for Saturn-V"):
        return find_device(0x1d50, 0x615c,
                           "Great Scott Gadgets",
                           "Saturn-V")

def test_apollo_present():
    with group(f"Checking for Apollo"):
        find_device(0x1d50, 0x615c,
                    "Great Scott Gadgets",
                    "Apollo Debugger")
    with task("Connecting to Apollo"):
        apollo = ApolloDebugger()
    return apollo

def test_bridge_present():
    with group(f"Checking for flash bridge"):
        return find_device(0x1d50, 0x615b, "LUNA", "Configuration Flash bridge")

def test_analyzer_present():
    with group(f"Checking for analyzer"):
        return find_device(0x1d50, 0x615b, "LUNA", "USB Analyzer")

def simulate_program_button():
    with group(f"Simulating pressing the {info('PROGRAM')} button"):
        set_pin('nBTN_PROGRAM', False)
        sleep(0.1)
        set_pin('nBTN_PROGRAM', None)

def simulate_reset_button():
    with group(f"Simulating pressing the {info('RESET')} button"):
        set_pin('nBTN_RESET', False)
        sleep(0.1)
        set_pin('nBTN_RESET', None)

def set_debug_leds(apollo, bitmask):
    with task(f"Setting debug LEDs to 0b{bitmask:05b}"):
        apollo.set_led_pattern(bitmask)

def set_fpga_leds(apollo, bitmask):
    with task(f"Setting FPGA LEDs to 0b{bitmask:05b}"):
        apollo.registers.register_write(REGISTER_LEDS, bitmask)
        assert(apollo.registers.register_read(REGISTER_LEDS) == bitmask)

def test_leds(apollo, device, leds, set_leds, off_min, off_max):
    with group(f"Testing {device} LEDs"):
        for i in range(len(leds)):
            with group(f"Testing {device} LED {info(i)}"):
                # Turn on LED
                set_leds(apollo, 1 << i)

                # Check that this and only this LED is on,
                # with the correct voltage.
                for j, (testpoint, minimum, maximum) in enumerate(leds):
                    if i == j:
                        test_voltage(testpoint, minimum, maximum)
                    else:
                        test_voltage(testpoint, off_min, off_max)

def test_jtag_scan(apollo):
    with group("Checking JTAG scan chain"):
        with apollo.jtag as jtag:
            devices = [(device.idcode(), device.description())
                for device in jtag.enumerate()]
        for idcode, desc in devices:
            item(f"Found {info(f'0x{idcode:8X}')}: {info(desc)}")
        if devices != [(0x21111043, "Lattice LFE5U-12F ECP5 FPGA")]:
            raise ValueError("JTAG scan chain did not include expected devices")

def unconfigure_fpga(apollo):
    with apollo.jtag as jtag:
        programmer = apollo.create_jtag_programmer(jtag)
        with task("Unconfiguring FPGA"):
            programmer.unconfigure()

def test_flash_id(apollo, expected_mfg, expected_part):
    with group("Checking flash chip ID"):
        with apollo.jtag as jtag:
            programmer = apollo.create_jtag_programmer(jtag)
            with task("Reading flash ID"):
                mfg, part = programmer.read_flash_id()
        with task(f"Checking manufacturer ID is {info(f'0x{expected_mfg:02X}')}"):
            if mfg != expected_mfg:
                raise ValueError(f"Wrong flash chip manufacturer ID: 0x{mfg:02X}")
        with task(f"Checking part ID is {info(f'0x{expected_part:02X}')}"):
            if part != expected_part:
                raise ValueError(f"Wrong flash chip part ID: 0x{part:02X}")

def flash_bitstream(apollo, filename):
    with group(f"Writing {info(filename)} to FPGA configuration flash"):
        bitstream = open(filename, 'rb').read()
        configure_fpga(apollo, 'flashbridge.bit')
        request_control_handoff_to_fpga(apollo)
        test_bridge_present()
        with task("Connecting to flash bridge"):
            bridge = FlashBridgeConnection()
            programmer = ECP5FlashBridgeProgrammer(bridge=bridge)
        with task("Writing flash"):
            programmer.flash(bitstream)

def configure_fpga(apollo, filename):
    with task(f"Configuring FPGA with {info(filename)}"):
        bitstream = open(filename, 'rb').read()
        with apollo.jtag as jtag:
            programmer = apollo.create_jtag_programmer(jtag)
            programmer.configure(bitstream)

def request_control_handoff_to_fpga(apollo):
    with task(f"Requesting MCU handoff {info('CONTROL')} port to FPGA"):
        apollo.honor_fpga_adv()
        apollo.close()

def find_device(vid, pid, mfg, prod):
    global last_bus, last_addr
    with group(f"Looking for device with"):
        item(f"VID: {info(f'0x{vid:04x}')}, PID: {info(f'0x{pid:04x}')}")
        item(f"Manufacturer: {info(mfg)}")
        item(f"Product: {info(prod)}")

        candidates = []

        def callback(context, device, event):
            candidates.append(device)
            return False

        callback_handle = context.hotplugRegisterCallback(
                callback,
                vendor_id=vid,
                product_id=pid,
                events=usb1.HOTPLUG_EVENT_DEVICE_ARRIVED,
                flags=usb1.HOTPLUG_ENUMERATE)

        end = time() + 3

        while (timeout := end - time()) > 0:
            context.handleEventsTimeout(timeout)
            try:
                while device := candidates.pop():
                    bus = device.getBusNumber()
                    addr = device.getDeviceAddress()
                    # New device must be on the same bus as previously.
                    if last_bus is not None and bus != last_bus:
                        continue
                    # New device must have a different address to previous one.
                    if addr == last_addr:
                        continue
                    with group(f"Found at bus {info(bus)} address {info(addr)}"):
                            with task(f"Checking manufacturer is {info(mfg)}"):
                                if (string := device.getManufacturer()) != mfg:
                                    raise ValueError(
                                        f"Wrong manufacturer string: '{string}'")
                            with task(f"Checking product is {info(prod)}"):
                                if (string := device.getProduct()) != prod:
                                    raise ValueError(
                                        f"Wrong product string: '{string}'")
                            serial = device.getSerialNumber()
                            item(f"Device serial is {info(serial)}")
                    context.hotplugDeregisterCallback(callback_handle)
                    last_bus = bus
                    last_addr = addr
                    return device
            except (IndexError, usb1.USBError, ValueError):
                continue
        else:
            context.hotplugDeregisterCallback(callback_handle)
            raise ValueError("Device not found")

def run_self_test(apollo):
    with group("Running self test"):
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
            with task(description):
                try:
                    method(apollo)
                except Exception as e:
                    raise RuntimeError(f"{description} self-test failed")
        with task("PMOD I/O"):
            for value in (0x00, 0xFF, 0xAA, 0x55):
                write_register(apollo, REGISTER_PMOD_A_OUT, value)
                readback = read_register(apollo, REGISTER_PMOD_B_IN)
                if readback != value:
                    raise ValueError(
                        f"Wrote 0x{value:02X} to PMOD A "
                        f"but read back 0x{readback:02X} from PMOD B")


def test_usb_hs(port):
    if port == 'AUX':
        todo(f"Testing USB HS comms on {info('AUX')}")
        return
    with group(f"Testing USB HS comms on {info(port)}"):
        connect_host_to(port)

        pids = {'CONTROL': 0x0001, 'AUX': 0x0002, 'TARGET-C': 0x0003}

        BULK_ENDPOINT_NUMBER = 1
        TEST_DATA_SIZE = 1 * 1024 * 1024
        TEST_TRANSFER_SIZE = 16 * 1024
        TRANSFER_QUEUE_DEPTH = 16

        total_data_exchanged = 0
        failed_out = False

        messages = {
            1: "error'd out",
            2: "timed out",
            3: "was prematurely cancelled",
            4: "was stalled",
            5: "lost the device it was connected to",
            6: "sent more data than expected."
        }

        def should_terminate():
            return (total_data_exchanged > TEST_DATA_SIZE) or failed_out

        def transfer_completed(transfer: usb1.USBTransfer):
            nonlocal total_data_exchanged, failed_out

            status = transfer.getStatus()

            # If the transfer completed.
            if status in (usb1.TRANSFER_COMPLETED,):

                # Count the data exchanged in this packet...
                total_data_exchanged += transfer.getActualLength()

                # ... and if we should terminate, abort.
                if should_terminate():
                    return

                # Otherwise, re-submit the transfer.
                transfer.submit()

            else:
                failed_out = status

        # Grab a reference to our device...
        device = find_device(0x1209, pids[port], "LUNA", "IN speed test")
        handle = device.open()

        # ... and claim its bulk interface.
        handle.claimInterface(0)

        # Submit a set of transfers to perform async comms with.
        active_transfers = []
        for _ in range(TRANSFER_QUEUE_DEPTH):

            # Allocate the transfer...
            transfer = handle.getTransfer()
            transfer.setBulk(0x80 | BULK_ENDPOINT_NUMBER,
                             TEST_TRANSFER_SIZE,
                             callback=transfer_completed,
                             timeout=1000)

            # ... and store it.
            active_transfers.append(transfer)

        # Start our benchmark timer.
        start_time = time()

        # Submit our transfers all at once.
        for transfer in active_transfers:
            transfer.submit()

        # Run our transfers until we get enough data.
        while not should_terminate():
            context.handleEvents()

        # Figure out how long this took us.
        end_time = time()
        elapsed = end_time - start_time

        # Cancel all of our active transfers.
        for transfer in active_transfers:
            if transfer.isSubmitted():
                transfer.cancel()

        # If we failed out; indicate it.
        if failed_out:
            raise RuntimeError(
                f"Test failed because a transfer {messages[failed_out]}.")

        speed = total_data_exchanged / elapsed / 1000000

        test_value("transfer rate", port, speed, 'MB/s', 45, 50)

        return handle

def connect_tester_cc_sbu_to(port):
    if port is None:
        item("Disconnecting tester CC/SBU lines")
    else:
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
    with task(f"{'Enabling' if enable else 'Disabling'} supply input on {info(port)}"):
        write_register(apollo, vbus_registers[port], enable)

def set_cc_levels(apollo, port, levels):
    with task(f"Setting CC levels on {info(port)} to {info(levels)}"):
        value = 0b01 * levels[0] | 0b10 * levels[1]
        reg_addr, reg_val = typec_registers[port]
        write_register(apollo, reg_addr, (0x02 << 8) | 1)
        write_register(apollo, reg_val, value)

def set_sbu_levels(apollo, port, levels):
    with task(f"Setting SBU levels on {info(port)} to {info(levels)}"):
        value = 0b01 * levels[0] | 0b10 * levels[1]
        write_register(apollo, sbu_registers[port], value)

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
    with task(f"{action} VBUS passthrough for {info(port)}"):
        write_register(apollo, passthrough_registers[port], enable)

def test_vbus(input_port, vmin, vmax):
    test_voltage(vbus_channels[input_port], vmin, vmax)

def configure_power_monitor(apollo):
    with task("Configuring I2C power monitor"):
        write_register(apollo, REGISTER_PWR_MON_ADDR, (0x1D << 8) | 2)
        write_register(apollo, REGISTER_PWR_MON_VALUE, 0x5500)

def refresh_power_monitor(apollo):
    write_register(apollo, REGISTER_PWR_MON_ADDR, (0x1F << 8))
    write_register(apollo, REGISTER_PWR_MON_VALUE, 0)
    sleep(0.01)

def test_eut_voltage(apollo, port, vmin, vmax):
    refresh_power_monitor(apollo)
    reg = mon_voltage_registers[port]
    write_register(apollo, REGISTER_PWR_MON_ADDR, (reg << 8) | 2)
    value = read_register(apollo, REGISTER_PWR_MON_VALUE)
    voltage = value * 32 / 65536
    return test_value("EUT voltage", port, voltage, 'V', vmin, vmax)

def test_eut_current(apollo, port, imin, imax):
    refresh_power_monitor(apollo)
    reg = mon_current_registers[port]
    write_register(apollo, REGISTER_PWR_MON_ADDR, (reg << 8) | 2)
    value = read_register(apollo, REGISTER_PWR_MON_VALUE)
    if value >= 32768:
        value -= 65536
    voltage = value * 0.1 / 32678
    resistance = 0.02
    current = voltage / resistance
    return test_value("EUT current", port, current, 'A', imin, imax)

def test_supply_port(supply_port):
    with group(f"Testing VBUS supply though {info(supply_port)}"):

        # Connect 5V supply via this port.
        set_boost_supply(5.0, 0.2)
        connect_boost_supply_to(supply_port)

        # Check supply present at port.
        test_vbus(supply_port, 4.85, 5.1)

        # Ramp the supply in 50mV steps up to 6.25V.
        for voltage in (mv / 1000 for mv in range(5000, 6250, 50)):
            with group(
                    f"Testing with {info(f'{voltage:.2f} V'):} supply "
                    f"on {info(supply_port)}"):

                set_boost_supply(voltage, 0.2)
                sleep(0.01)

                schottky_drop_min, schottky_drop_max = (0.35, 0.85)

                # Up to 5.5V, there must be only a diode drop.
                if voltage <= 5.5:
                    minimum = voltage - schottky_drop_max
                    maximum = voltage - schottky_drop_min
                # Between 5.5V and 6.0V, OVP may kick in.
                elif 5.5 <= voltage <= 6.0:
                    minimum = 0
                    maximum = voltage - schottky_drop_min
                # Above 6.0V, OVP must kick in.
                else:
                    minimum = 0
                    maximum = 6.0 - schottky_drop_min

                # Check voltage at +5V rail.
                test_voltage('+5V', minimum, maximum)

                with group("Checking for leakage to other ports"):
                    for port in ('CONTROL', 'AUX', 'TARGET-C', 'TARGET-A'):
                        if port != supply_port:
                            test_leakage(port)

        disconnect_supply_and_discharge(supply_port)

def test_supply_selection(apollo):
    with group("Testing FPGA control of VBUS input selection"):
        with group("Handing off EUT supply from boost converter to host"):
            set_boost_supply(4.5, 0.2)
            connect_host_supply_to('CONTROL')
            connect_boost_supply_to(None)

        with group("Connect DC-DC to AUX at higher than the host supply"):
            set_boost_supply(5.4, 0.2)
            connect_boost_supply_to('AUX')

            # Define ranges to distinguish high and low supplies.
            schottky_drop_min, schottky_drop_max = (0.65, 0.85)
            high_min = 5.35 - schottky_drop_max
            high_max = 5.45 - schottky_drop_min
            low_min = 3.5
            low_max = 5.05 - schottky_drop_min

            # Ensure that ranges are distinguishable.
            assert(high_min > low_max)

            # 5V rail should be switched to the higher supply.
            test_voltage('+5V', high_min, high_max)

        with group("Test FPGA control of AUX supply input"):
            # Tell the FPGA to disable the AUX supply input.
            # 5V rail should be switched to the lower host supply on CONTROL.
            enable_supply_input(apollo, 'AUX', False)
            test_voltage('+5V', low_min, low_max)
            # Re-enable AUX supply, check 5V rail is switched back to it.
            enable_supply_input(apollo, 'AUX', True)
            test_voltage('+5V', high_min, high_max)

        with group("Swap ports between host and boost converter"):
            set_boost_supply(4.5, 0.2)
            connect_host_supply_to('AUX')
            connect_boost_supply_to('CONTROL')

        with group("Increase boost voltage to identifiable level"):
            set_boost_supply(5.4, 0.2)
            test_voltage('+5V', high_min, high_max)

        with group("Test FPGA control of CONTROL supply input"):
            # Tell the FPGA to disable the CONTROL supply input.
            # 5V rail should be switched to the lower host supply on AUX.
            enable_supply_input(apollo, 'CONTROL', False)
            test_voltage('+5V', low_min, low_max)
            # Re-enable CONTROL supply, check 5V rail is switched back to it.
            enable_supply_input(apollo, 'CONTROL', True)
            test_voltage('+5V', high_min, high_max)

        with group("Swap back to powering from host"):
            set_boost_supply(4.5, 0.2)
            connect_host_supply_to('CONTROL')
            connect_boost_supply_to(None)

def test_cc_sbu_control(apollo, port):
    begin_cc_measurement(port)
    with group(f"Checking control of {info(port)} CC lines"):
        for levels in ((0, 1), (1, 0)):
            set_cc_levels(apollo, port, levels)
            for pin, level in zip(('CC1', 'CC2'), levels):
                if level:
                    check_cc_resistance(pin, 4.1, 6.1)
                else:
                    check_cc_resistance(pin, 50, 200)
    with group(f"Checking control of {info(port)} SBU lines"):
        for levels in ((0, 1), (1, 0)):
            set_sbu_levels(apollo, port, levels)
            test_pin('SBU1_test', levels[0])
            test_pin('SBU2_test', levels[1])
    end_cc_measurement()

def test_vbus_distribution(apollo, voltage, load_resistance,
        load_pin, passthrough, input_port):
    vmin_off = 0.0
    vmax_off = 0.2
    imin_off = -0.01
    imax_off =  0.01
    src_resistance = 0.08
    input_cable_resistance = 0.04
    eut_resistance = 0.1
    output_cable_resistance = 0.07

    if passthrough:
        total_resistance = sum([
            src_resistance, input_cable_resistance, eut_resistance,
            output_cable_resistance, load_resistance])
        current = voltage / total_resistance
    else:
        current = 0

    src_drop = src_resistance * current
    input_cable_drop = input_cable_resistance * current
    eut_drop = eut_resistance * current
    output_cable_drop = output_cable_resistance * current
    vmin_sp = voltage * 0.98 - 0.01 - src_drop
    vmax_sp = voltage * 1.02 + 0.01 - src_drop
    vmin_ip = vmin_sp - input_cable_drop
    vmax_ip = vmax_sp - input_cable_drop
    vmin_op = (vmin_ip - eut_drop) if passthrough else vmin_off
    vmax_op = (vmax_ip - eut_drop) if passthrough else vmax_off
    vmin_ld = vmin_op - output_cable_drop
    vmax_ld = vmax_op - output_cable_drop

    imin_on = current * 0.98 - 0.01
    imax_on = current * 1.02 + 0.01

    supply_ports = {
        'CONTROL': 'AUX',
        'AUX': 'CONTROL',
        'TARGET-C': 'CONTROL',
    }

    supply_port = supply_ports[input_port]

    with group(f"Testing VBUS distribution from {info(input_port):} " +
            f"at {info(f'{voltage:.1f} V')} " +
            f"with passthrough {info('ON' if passthrough else 'OFF')}"):

        if apollo:
            with group(f"Moving EUT supply to {info(supply_port)}"):
                enable_supply_input(apollo, supply_port, True)
                connect_host_supply_to('CONTROL', 'AUX')
                connect_host_supply_to(supply_port)
                enable_supply_input(apollo, input_port, False)

        with group(f"Setting up test conditions"):
            set_boost_supply(voltage, current + 0.3)
            if apollo:
                for port in ('CONTROL', 'AUX', 'TARGET-C'):
                    set_passthrough(apollo, port,
                        passthrough and port is input_port)
            connect_boost_supply_to(input_port)
            if passthrough:
                set_pin(load_pin, True)

        sleep(0.003)

        boost.check_fault()

        if apollo:
            with group("Checking voltage and current on supply port"):
                test_vbus(supply_port, 4.3, 5.25)
                test_eut_voltage(apollo, supply_port, 4.3, 5.25)
                test_eut_current(apollo, supply_port, 0.13, 0.16)

            with group("Checking voltages and positive current on input"):
                test_vbus(input_port, vmin_sp, vmax_sp)
                test_eut_voltage(apollo, input_port, vmin_ip, vmax_ip)
                test_eut_current(apollo, input_port, imin_on, imax_on)

            with group("Checking voltages and negative current on output"):
                test_voltage('TARGET_A_VBUS', vmin_op, vmax_op)
                test_eut_voltage(apollo, 'TARGET-A', vmin_op, vmax_op)
                test_eut_current(apollo, 'TARGET-A', -imax_on, -imin_on)
                test_voltage('VBUS_TA', vmin_ld, vmax_ld)
        else:
            with group("Checking voltages"):
                test_vbus(input_port, vmin_sp, vmax_sp)
                test_voltage('TARGET_A_VBUS', vmin_op, vmax_op)
                test_voltage('VBUS_TA', vmin_ld, vmax_ld)

        with group("Checking for leakage on other ports"):
            for port in ('CONTROL', 'AUX', 'TARGET-C'):
                if port == input_port:
                    continue
                if apollo and port == supply_port:
                    continue
                test_vbus(port, vmin_off, vmax_off)
                if apollo:
                    test_eut_voltage(apollo, port, vmin_off, vmax_off)
                    test_eut_current(apollo, port, imin_off, imax_off)

        with group("Shutting down test"):
            if passthrough:
                set_pin(load_pin, False)
                if apollo:
                    set_passthrough(apollo, input_port, False)
            connect_boost_supply_to(None)

def test_user_button(apollo):
    button = f"{info('USER')} button"
    with group(f"Testing {button}"):
        with task(f"Checking {button} is released"):
            write_register(apollo, REGISTER_BUTTON_USER, 0)
            if read_register(apollo, REGISTER_BUTTON_USER):
                raise ValueError(f"USER button press detected unexpectedly")
        request("press the USER button")
        with task(f"Checking {button} was pressed"):
            if not read_register(apollo, REGISTER_BUTTON_USER):
                raise ValueError(f"USER button press not detected")

def request_control_handoff_to_mcu(handle):
    with task(f"Requesting FPGA handoff {info('CONTROL')} port to MCU"):
        handle.controlWrite(
            usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE, 0xF0, 0, 0, b'', 1)

def test_target_a_cable(required):
    correct = "connected" if required else "disconnected"
    incorrect = "disconnected" if required else "connected"
    with group(f"Checking {info('TARGET-A')} cable is {info(correct)}"):
        vmin, vmax = (4.85, 5.05) if required else (0, 0.05)
        try:
            test_vbus('TARGET-A', vmin, vmax)
            success = True
        except ValueError:
            success = False
    if not success:
        raise ValueError(
            f"TARGET-A cable appears to be {incorrect}, should be {correct}")
