from time import sleep
from tycho import *

def test():
    # First check for shorts at each EUT USB-C port.
    begin("Checking for shorts on all USB-C ports")
    for port in ('CONTROL', 'AUX', 'TARGET-C'):
        check_for_shorts(port)
    end()

    # Connect EUT GND to tester GND.
    connect_grounds()

    # Check CC resistances with EUT unpowered.
    begin("Checking CC resistances with EUT unpowered")
    for port in ('CONTROL', 'AUX', 'TARGET-C'):
        check_cc_resistances(port)
    end()

    # Test supplying VBUS through CONTROL and AUX ports.
    for port in ('CONTROL', 'AUX'):
        test_supply_port(port)

    begin("Testing passthrough at low current with power off")
    set_boost_supply(5.0, 0.2)
    connect_boost_supply_to('TARGET-C')
    test_voltage('TARGET_A_VBUS', 4.85, 5.05)
    test_target_a_cable(False)
    disconnect_supply_and_discharge('TARGET-C')
    end()

    begin("Powering EUT for testing")
    set_boost_supply(5.0, 0.2)
    connect_boost_supply_to('CONTROL')
    end()

    begin("Checking all supply voltages")
    for (testpoint, minimum, maximum) in supplies:
        test_voltage(testpoint, minimum, maximum)
    end()

    begin("Checking CC resistances with EUT powered")
    for port in ('AUX', 'TARGET-C'):
        check_cc_resistances(port)
    end()

    # Check 60MHz clock.
    test_clock()

    # Flash Saturn-V bootloader to MCU via SWD.
    flash_bootloader()

    # Connect host D+/D- to control port.
    connect_host_to('CONTROL')

    sleep(1)

    # Check Saturn-V enumerates.
    test_saturnv_present()

    # Flash Apollo firmware to MCU via DFU.
    flash_firmware()

    sleep(0.1)

    # Simulate pressing the PROGRAM button.
    simulate_program_button()

    sleep(0.7)

    # Check Apollo enumerates, and open it.
    apollo = test_apollo_present()

    # Check JTAG scan via Apollo finds the FPGA.
    test_jtag_scan(apollo)

    # Unconfigure FPGA.
    unconfigure_fpga(apollo)

    # Check flash chip ID via the FPGA.
    test_flash_id(apollo, 0xEF, 0xEF4016)

    # Configure FPGA with test gateware.
    configure_fpga(apollo, 'selftest.bit')

    # Check all PHY supply voltages.
    begin("Checking all PHY supply voltages")
    for (testpoint, minimum, maximum) in phy_supplies:
        test_voltage(testpoint, minimum, maximum)
    end()

    # Run self-test routine. Should include:
    #
    # - ULPI test to each PHY.
    # - HyperRAM read/write test.
    # - I2C test to all peripherals.
    # - PMOD loopback test.
    # - FPGA sensing of target D+/D-, driven by target PHY.
    # 
    run_self_test(apollo)

    # Check that the FPGA can control the supply selection.
    test_supply_selection(apollo)

    begin("Checking FPGA control of CC and SBU lines")
    for port in ('AUX', 'TARGET-C'):
        test_cc_sbu_control(apollo, port)
    end()

    # Run HS speed test.
    begin("Testing USB HS comms on all ports")
    configure_fpga(apollo, 'speedtest.bit')
    request_control_handoff_to_fpga(apollo)
    for port in ('TARGET-C',):
        connect_boost_supply_to(port)
        test_usb_hs(port)
        disconnect_supply_and_discharge(port)
    todo(f"Testing USB HS comms on {info('AUX')}")
    handle = test_usb_hs('CONTROL')
    end()

    # Request handoff and reconnect to Apollo.
    begin("Switching to Apollo via handoff")
    request_control_handoff_to_mcu(handle)
    sleep(0.7)
    apollo = test_apollo_present()
    end()

    # Flash analyzer bitstream.
    flash_bitstream(apollo, 'analyzer.bit')

    # Simulate pressing the RESET button, should cause analyzer to enumerate.
    simulate_reset_button()
    sleep(1)
    test_analyzer_present()

    # Trigger handoff by button and reconnect to Apollo.
    begin("Switching to Apollo via button")
    simulate_program_button()
    sleep(0.7)
    apollo = test_apollo_present()
    end()

    # Configure FPGA with test gateware again.
    configure_fpga(apollo, 'selftest.bit')

    # Request the operator connect a cable to Target-A.
    request("connect cable to EUT Target-A port")

    # Check that the Target-A cable is connected.
    set_boost_supply(5.0, 0.2)
    connect_boost_supply_to('TARGET-C')
    test_target_a_cable(True)
    connect_boost_supply_to(None)

    todo("Test USB HS comms through target passthrough")

    configure_power_monitor(apollo)

    begin("Testing VBUS distribution")
    for (voltage, load_resistance, load_pin) in (
            ( 5.0,  1.72, 'TEST_5V' ),
            (10.0, 38.38, 'TEST_20V')):
        for passthrough in (False, True):
            for input_port in ('CONTROL', 'AUX'):
                test_vbus_distribution(
                    apollo, voltage, load_resistance,
                    load_pin, passthrough, input_port)
    end()

    begin("Testing LEDs")
    test_leds(apollo, "debug", debug_leds, set_debug_leds, 2.9, 3.4)
    test_leds(apollo, "FPGA", fpga_leds, set_fpga_leds, 2.7, 3.4)
    begin("Checking visual appearance of LEDs")
    set_fpga_leds(apollo, 0b111111)
    set_debug_leds(apollo, 0b11111)
    set_pin('REF_LED_EN', True)
    request("check LEDs match reference")
    set_pin('REF_LED_EN', False)
    set_debug_leds(apollo, 0)
    set_fpga_leds(apollo, 0)
    end()
    end()

    # Request press of USER button, should be detected by FPGA.
    test_user_button(apollo)

    # Request press of PROGRAM button, should cause Apollo to enumerate.
    request('press the PROGRAM button')
    sleep(1)
    test_apollo_present()

    # Request press of RESET button, should cause analyzer to enumerate.
    request('press the RESET button')
    sleep(1)
    test_analyzer_present()

    begin("Powering off EUT")
    connect_boost_supply_to(None)
    connect_host_supply_to(None)
    end()

    begin(f"Testing VBUS distribution with EUT off")
    for (voltage, load_resistance, load_pin) in (
            ( 5.0,  1.72, 'TEST_5V' ),
            (10.0, 38.38, 'TEST_20V')):
        test_vbus_distribution(
            None, voltage, load_resistance, load_pin, True, 'TARGET-C')
    end()

# Static data required for tests.

supplies = (
    ('+3V3',   3.2, 3.4),
    ('+2V5',   2.4, 2.6),
    ('+1V1',   1.0, 1.2),
    ('VCCRAM', 3.2, 3.4))

phy_supplies = (
    ('CONTROL_PHY_3V3', 3.15, 3.4),
    ('CONTROL_PHY_1V8', 1.65, 1.9),
    ('AUX_PHY_3V3',     3.15, 3.4),
    ('AUX_PHY_1V8',     1.65, 1.9),
    ('TARGET_PHY_3V3',  3.15, 3.4),
    ('TARGET_PHY_3V3',  3.15, 3.4))

fpga_leds = (
    ('D7_Vf', 0.6, 0.8), # OSVX0603C1E, Purple
    ('D6_Vf', 0.7, 0.9), # ORH-B36G, Blue
    ('D5_Vf', 0.9, 1.1), # ORH-G36G, Green
    ('D4_Vf', 1.3, 1.5), # E6C0603UYAC1UDA, Yellow
    ('D3_Vf', 1.3, 1.5), # E6C0603SEAC1UDA, Orange
    ('D2_Vf', 1.4, 1.6)) # OSR50603C1E, Red

debug_leds = ( # Values are 3.3V - Vf
    ('D10_Vf', 2.4, 2.6), # MHT192WDT-ICE, Ice Blue
    ('D11_Vf', 2.4, 2.7), # OSK40603C1E, Pink
    ('D12_Vf', 2.5, 2.7), # ORH-W46G, White
    ('D13_Vf', 2.4, 2.7), # OSK40603C1E, Pink
    ('D14_Vf', 2.4, 2.6)) # MHT192WDT-ICE, Ice Blue

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print()
        print(Fore.RED + "FAIL" + Style.RESET_ALL + ": " + str(e))
        print()
    reset()
