from tests import *
import ipdb
import sys

def test():
    # First check for shorts at each EUT USB-C port.
    with group("Checking for shorts on all USB-C ports"):
        for port in ('CONTROL', 'AUX', 'TARGET-C'):
            check_for_shorts(port)

    # Connect EUT GND to tester GND.
    connect_grounds()

    # Check CC resistances with EUT unpowered.
    with group("Checking CC resistances with EUT unpowered"):
        for port in ('CONTROL', 'AUX', 'TARGET-C'):
            check_cc_resistances(port)

    # Discharge any residual voltage from all ports.
    with group("Discharging ports"):
        for port in ('CONTROL', 'AUX', 'TARGET-C'):
            with task(f"Discharging {info(port)}"):
                discharge(port)

    # Apply power at TARGET-C port.
    with group(f"Testing with VBUS applied to {info('TARGET-C')}"):
        set_boost_supply(5.0, 0.05)
        connect_boost_supply_to('TARGET-C')
        test_vbus('TARGET-C', 4.85, 5.05)

        # Check the voltage reaches the EUT's TARGET-A port.
        test_voltage('TARGET_A_VBUS', 4.85, 5.05)

        # Make sure TARGET-A cable is disconnected.
        test_target_a_cable(False)

        # Make sure there is no leakage to CONTROL and AUX ports.
        for port in ('CONTROL', 'AUX'):
            test_leakage(port)

        # Finished testing with supply from TARGET-C.
        disconnect_supply_and_discharge('TARGET-C')

    # Test supplying VBUS through CONTROL and AUX ports.
    for port in ('CONTROL', 'AUX'):
        test_supply_port(port)

    # Supply EUT through CONTROL port for subsequent tests.
    with group("Powering EUT for testing"):
        set_boost_supply(5.0, 0.25)
        connect_boost_supply_to('CONTROL')

    # Check all supply rails come up correctly.
    with group("Checking all supply voltages"):
        for (testpoint, minimum, maximum) in supplies:
            test_voltage(testpoint, minimum, maximum)

    # Re-check the CC resistances now that the Type-C controllers have power.
    with group("Checking CC resistances with EUT powered"):
        for port in ('AUX', 'TARGET-C'):
            check_cc_resistances(port)

    # Check 60MHz clock.
    test_clock()

    # Flash Saturn-V bootloader to MCU via SWD.
    flash_bootloader()

    # Connect host D+/D- to control port.
    connect_host_to('CONTROL')

    # Check Saturn-V enumerates.
    test_saturnv_present()

    # Wait a moment before starting DFU.
    sleep(0.5)

    # Flash Apollo firmware to MCU via DFU.
    flash_firmware()

    # Simulate pressing the RESET then PROGRAM buttons.
    simulate_reset_button()
    simulate_program_button()

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
    with group("Checking all PHY supply voltages"):
        for (testpoint, minimum, maximum) in phy_supplies:
            test_voltage(testpoint, minimum, maximum)

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

    # Check that the FPGA can control the CC and SBU lines.
    with group("Checking FPGA control of CC and SBU lines"):
        for port in ('AUX', 'TARGET-C'):
            test_cc_sbu_control(apollo, port)

    # Run HS speed test.
    with group("Testing USB HS comms on all ports"):
        configure_fpga(apollo, 'speedtest.bit')
        request_control_handoff_to_fpga(apollo)
        for port in ('TARGET-C', 'AUX'):
            connect_boost_supply_to(port)
            test_usb_hs(port)
            disconnect_supply_and_discharge(port)
        handle = test_usb_hs('CONTROL')

    # Request handoff and reconnect to Apollo.
    with group("Switching to Apollo via handoff"):
        request_control_handoff_to_mcu(handle)
        apollo = test_apollo_present()

    # Flash analyzer bitstream.
    flash_bitstream(apollo, 'analyzer.bit')

    # Simulate pressing the RESET button, should cause analyzer to enumerate.
    simulate_reset_button()
    test_analyzer_present()

    # Trigger handoff by button and reconnect to Apollo.
    with group("Switching to Apollo via button"):
        simulate_program_button()
        apollo = test_apollo_present()

    # Configure FPGA with test gateware again.
    configure_fpga(apollo, 'selftest.bit')

    # Request the operator connect a cable to Target-A.
    request("connect cable to EUT Target-A port")

    # Check that the Target-A cable is connected.
    set_boost_supply(5.0, 0.25)
    connect_boost_supply_to('TARGET-C')
    test_target_a_cable(True)
    connect_boost_supply_to(None)

    todo("Test USB HS comms through target passthrough")

    # Test VBUS distribution at full voltages and currents.
    with group("Testing VBUS distribution"):
        configure_power_monitor(apollo)
        for (voltage, load_resistance, load_pin) in (
                ( 5.0,  1.72, 'TEST_5V' ),
                (10.0, 38.38, 'TEST_20V')):
            for passthrough in (False, True):
                for input_port in ('CONTROL', 'AUX'):
                    test_vbus_distribution(
                        apollo, voltage, load_resistance,
                        load_pin, passthrough, input_port)

    # Test all LEDs.
    with group("Testing LEDs"):
        test_leds(apollo, "debug", debug_leds, set_debug_leds, 2.9, 3.4)
        test_leds(apollo, "FPGA", fpga_leds, set_fpga_leds, 2.7, 3.4)

        with group("Checking visual appearance of LEDs"):
            # Turn on all LEDs.
            set_fpga_leds(apollo, 0b111111)
            set_debug_leds(apollo, 0b11111)
            set_pin('REF_LED_EN', True)

            # Ask the user to check the LEDs appear correct.
            request("check LEDs match reference")

            # Turn off LEDs.
            set_pin('REF_LED_EN', False)
            set_debug_leds(apollo, 0)
            set_fpga_leds(apollo, 0)

    # Request press of USER button, should be detected by FPGA.
    test_user_button(apollo)

    # Request press of RESET button, should cause analyzer to enumerate.
    request('press the RESET button')
    test_analyzer_present()

    # Request press of PROGRAM button, should cause Apollo to enumerate.
    request('press the PROGRAM button')
    test_apollo_present()

    # Power down the EUT.
    with group("Powering off EUT"):
        connect_boost_supply_to(None)
        connect_host_supply_to(None)

    # Repeat VBUS distribution tests for TARGET-C -> TARGET-A with EUT off.
    with group(f"Testing VBUS distribution with EUT off"):
        for (voltage, load_resistance, load_pin) in (
                ( 5.0,  1.72, 'TEST_5V' ),
                (10.0, 38.38, 'TEST_20V')):
            test_vbus_distribution(
                None, voltage, load_resistance, load_pin, True, 'TARGET-C')

if __name__ == "__main__":
    try:
        test()
        ok("All tests completed")
    except KeyboardInterrupt:
        fail("Test stopped by user")
    except Exception as e:
        fail(str(e))
        if 'debug' in sys.argv[1:]:
            ipdb.post_mortem()
    reset()
