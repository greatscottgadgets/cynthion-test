from tests import *
import ipdb
import sys

def test(user_present: bool):
    # Set up test system.
    setup()

    # Load calibration data.
    load_calibration()

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
        test_vbus('TARGET-C', Range(4.85, 5.05))
        test_boost_current(Range(0, 0.1))

        # Check no voltage reaches the EUT's TARGET-A port.
        test_voltage('TARGET_A_VBUS', Range(0, 0.05), discharge=True)

        # Make sure there is no leakage to CONTROL and AUX ports.
        for port in ('CONTROL', 'AUX'):
            test_leakage(port)

        # Finished testing with supply from TARGET-C.
        disconnect_supply_and_discharge('TARGET-C')

    # Check whether TARGET-A cable is connected.
    test_target_a_cable(not user_present)

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
            test_voltage(testpoint, Range(minimum, maximum))

    # Check supply current.
    test_boost_current(Range(0, 0.1))

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

    # VBUS passthrough from Target-C to Target-A should now be on.
    with group(f"Testing with VBUS applied to {info('TARGET-C')}"):
        # Apply VBUS power to TARGET-C.
        connect_boost_supply_to('CONTROL', 'TARGET-C')
        test_vbus('TARGET-C', Range(4.85, 5.05))

        # Check the voltage now reaches the EUT's TARGET-A port.
        test_voltage('TARGET_A_VBUS', Range(4.85, 5.05))

        # Disconnect TARGET-C supply.
        connect_boost_supply_to('CONTROL')

    # Check all PHY supply voltages.
    with group("Checking all PHY supply voltages"):
        # Check +3V3 supply rail as sanity check before checking PHY supplies
        state.step[1] = -1
        (testpoint, minimum, maximum) = supplies[0]
        test_voltage(testpoint, Range(minimum, maximum))
        for (testpoint, minimum, maximum) in phy_supplies:
            test_voltage(testpoint, Range(minimum, maximum))

    # Run self-test routine. Should include:
    #
    # - ULPI test to each PHY.
    # - HyperRAM read/write test.
    # - I2C test to all peripherals.
    # - PMOD loopback test.
    # - FPGA sensing of target D+/D-, driven by target PHY.
    # 
    run_self_test(apollo, user_present)

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
            if port == 'TARGET-C' and not user_present:
                # TARGET-A cable connected, skip TARGET-C speed test.
                continue
            connect_boost_supply_to('CONTROL', port)
            test_usb_hs(port)
            connect_host_to(None)
        connect_boost_supply_to('CONTROL')
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

    if user_present:
        # Request the operator connect a cable to Target-A.
        request("connect cable to EUT Target-A port")

        # Check that the Target-A cable is connected.
        with group("Checking Target-A cable is connected"):
            test_target_a_cable(True)

    # Check that the FX2 enumerates through the passthrough.
    with group("Testing Target-C to Target-A data passthrough"):
        # Supply is already connected to CONTROL.
        # Now connect it to TARGET-C also.
        connect_boost_supply_to('CONTROL', 'TARGET-C')
        connect_host_to('TARGET-C')
        # Test USB through EUT to Tycho FX2 device.
        test_fx2()
        # Connect supply to CONTROL alone, disconnecting from TARGET-C.
        connect_boost_supply_to('CONTROL')

    with group("Reconnecting to Apollo"):
        connect_host_to('CONTROL')
        apollo = test_apollo_present()

    # Test VBUS distribution at full voltages and currents.
    with group("Testing VBUS distribution"):
        configure_power_monitor(apollo)
        for (voltage, load_resistance, load_pin) in (
                ( 6.25, Range(1.782, 1.818), 'TEST_5V' ),
                (20.00, Range( 39.6,  40.4), 'TEST_20V')):
            for passthrough in (False, True):
                for input_port in ('CONTROL', 'AUX'):
                    test_vbus_distribution(
                        apollo, voltage, load_resistance,
                        load_pin, passthrough, input_port)
        with group("Switching EUT back to DC-DC supply"):
            set_boost_supply(5.0, 0.25)
            connect_boost_supply_to('CONTROL')
            test_vbus('CONTROL', Range(4.85, 5.05))
            connect_host_supply_to(None)

    # Test all LEDs.
    with group("Testing LEDs"):
        test_leds(apollo, "debug", debug_leds, set_debug_leds)
        test_leds(apollo, "FPGA", fpga_leds, set_fpga_leds)

        if user_present:
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
    if user_present:
        test_user_button(apollo)

    # Request press of RESET button, should cause analyzer to enumerate.
    if user_present:
        request('press the RESET button')
    else:
        simulate_reset_button()
    test_analyzer_present()

    # Request press of PROGRAM button, should cause Apollo to enumerate.
    if user_present:
        request('press the PROGRAM button')
    else:
        simulate_program_button()
    test_apollo_present()

    # Power down the EUT.
    with group("Powering off EUT"):
        connect_boost_supply_to(None)
        connect_host_supply_to(None)

if __name__ == "__main__":
    user_present = 'unattended' not in sys.argv[1:]
    if user_present:
        enable_numbering(True)
    try:
        with error_conversion():
            test(user_present)
            ok("All tests completed")
            retcode = 0
    except CynthionTestError as error:
        retcode = 1
        fail(error)
        if 'debug' in sys.argv[1:]:
            ipdb.post_mortem()
    enable_numbering(False)
    reset()
    sys.exit(retcode)
