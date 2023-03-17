from greatfet import GreatFET

gf = GreatFET()

def test():
    # First check for shorts at each EUT USB-C port.
    for port in ('CONTROL', 'AUX', 'TARGET-C'):
        connect_tester_to(port)
        for a, b in usb_c_adjacent_pins:
            check_for_short(port, a, b)

    # Connect EUT GND to tester GND.
    connect_grounds()

    # Check CC resistances with EUT unpowered.
    for port in ('CONTROL', 'AUX', 'TARGET-C'):
        check_cc_resistances(port)

    # Test supplying VBUS through CONTROL and AUX ports.
    for supply_port in ('CONTROL', 'AUX'):

        # Connect 5V supply via this port.
        set_supply(5.0, 0.1)
        connect_supply_to(supply_port)

        # Expected diode drop range:
        drop_min, drop_max = 0.2, 0.3

        # Ramp the supply in 50mV steps up to 6.25V.
        for voltage in range(5.0, 6.25, 0.05):
            set_supply(voltage, 0.1)
            sleep(0.05)

            # Up to 5.5V, there must be only a diode drop.
            if voltage <= 5.5:
                minimum = voltage - drop_max
                maximum = voltage - drop_min
            # Between 5.5V and 6.0V, OVP may kick in.
            elif 5.5 <= 6.0:
                minimum = 0
                maximum = voltage - drop_min
            # Above 6.0V, OVP must kick in.
            else:
                minimum = 0
                maximum = 6.0 - drop_min

            # Check voltage at +5V rail.
            test_voltage('+5V', minimum, maximum)

            # Check for leakage to other ports.
            for port in ('CONTROL', 'AUX', 'TARGET-C', 'TARGET-A'):
                if port != supply_port:
                    test_leakage(port)

        disconnect_supply_and_discharge()

    # Test passthrough of Target-C VBUS to Target-A VBUS with power off.
    set_supply(5.0, 0.1)
    connect_supply_to('TARGET-C')
    test_voltage('TARGET_A_VBUS', 4.95, 5.05)
    disconnect_supply_and_discharge()

    # Power at +5V through the control port for following tests.
    set_supply(5.0, 0.1)
    connect_supply_to('CONTROL')

    # Check all supply voltages.
    for (testpoint, minimum, maximum) in supplies:
        test_voltage(testpoint, minimum, maximum)

    # Check CC resistances with EUT powered.
    for port in ('AUX', 'TARGET-C'):
        check_cc_resistances(port)

    # Check 60MHz clock.
    test_clock()

    # Flash Saturn-V bootloader to MCU via SWD.
    flash_bootloader()

    # Connect host D+/D- to control port.
    connect_host_to('CONTROL')

    # Flash Apollo firmware to MCU via DFU.
    flash_firmware()

    # Check Apollo debugger shows up.
    test_apollo_present()

    # Test debug LEDs.
    test_leds(debug_led, set_debug_led)

    # Check JTAG scan via Apollo finds the FPGA.
    test_jtag_scan()

    # Flash analyzer bitstream.
    flash_analyzer()

    # Configure FPGA with test gateware.
    configure_fpga()

    # Check all PHY supply voltages.
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
    run_self_test()

    # Test USB HS comms on each port against the self-test gateware.
    for port in ('CONTROL', 'AUX', 'TARGET-C'):
        connect_host_to(port)
        test_usb_hs(port)

    # Tell the FPGA to put the target PHY in passive mode, then test
    # passthrough to a USB FS device created on the GF1.
    connect_host_to('CONTROL')
    set_target_passive()
    connect_host_to('TARGET-C')
    test_usb_fs(port)

    # Check FPGA control of CC and SBU lines.
    set_adc_pullup(True)
    for port in ('AUX', 'TARGET-C'):
        connect_tester_cc_sbu_to(port)
        for levels in ((0, 1), (1, 0)):
            set_cc_levels(port, levels)
            test_voltage('CC1', cc_thresholds[levels[0]])
            test_voltage('CC2', cc_thresholds[levels[1]])
            set_sbu_levels(port, levels)
            test_digital_input('SBU1', levels[0])
            test_digital_input('SBU2', levels[1])
    set_adc_pullup(False)

    # TODO: VBUS distribution testing

    # TODO: VBUS voltage/current monitoring testing and calibration.

    # Test FPGA LEDs.
    test_leds(fpga_leds, set_fpga_led)

    # Request visual check of LEDs.
    request_led_check()

    # Request press of USER button, should be detected by FPGA.
    request_button('USER')
    test_user_button_pressed()

    # Tell the FPGA to hand off the control port to the MCU.
    request_control_handoff()
    test_apollo_present()

    # Request Apollo reset, should cause analyzer to enumerate.
    request_apollo_reset()
    test_analyzer_present()

    # Request press of PROGRAM button, should cause Apollo to enumerate.
    request_button('PROGRAM')
    test_apollo_present()

    # Request press of RESET button, should cause analyzer to enumerate.
    request_button('RESET')
    test_analyzer_present()

    # Send USB reset, should cause Apollo to enumerate again.
    send_usb_reset()
    test_apollo_present()


# Helper functions for testing.

def test_leds(leds, set_led)
    for i in range(len(leds)):
        # Turn on LED
        set_led(i, True)

        # Check that this and only this LED is on, with the correct voltage.
        for j, (testpoint, minimum, maximum) in enumerate(leds):
            if i == j:
                test_voltage(testpoint, minimum, maximum)
            else:
                test_voltage(testpoint, 0, 0.05)

        # Turn off LED
        set_led(i, False)

    # Turn on all LEDs for visual check.
    for i in range(len(leds)):
        set_led(i, True)

# Static data required for tests.

usb_c_adjacent_pins = (
    ('GND', ' VBUS'),
    ('VBUS', 'SBU2'),
    ('SBU2', 'CC1' ),
    ('CC1',  'D-'  ),
    ('D-',   'D+'  ),
    ('D+',   'SBU1'),
    ('SBU1', 'CC2' ),
    ('CC2',  'VBUS'))

supplies = (
    ('+3V3',   3.25, 3.35),
    ('+2V5',   2.45, 2.55),
    ('+1V1',   1.05, 1.15),
    ('VCCRAM', 3.25, 3.35))

phy_supplies = (
    ('CONTROL_PHY_3V3', 3.25, 3.35),
    ('CONTROL_PHY_1V8', 1.75, 1.85),
    ('AUX_PHY_3V3',     3.25, 3.35),
    ('AUX_PHY_1V8',     1.75, 1.85),
    ('TARGET_PHY_3V3',  3.25, 3.35),
    ('TARGET_PHY_3V3',  3.25, 3.35))

fpga_leds = ( # Values are 3.3V - Vf
    ('D7_Vf', 0.4, 0.6), # OSVX0603C1E, Purple
    ('D6_Vf', 0.6, 0.8), # ORH-B36G, Blue
    ('D5_Vf', 0.4, 0.6), # ORH-G36G, Green
    ('D4_Vf', 1.2, 1.4), # E6C0603UYAC1UDA, Yellow
    ('D3_Vf', 1.2, 1.4), # E6C0603SEAC1UDA, Orange
    ('D2_Vf', 1.4, 1.6)) # OSR50603C1E, Red

debug_leds = (
    ('D10_Vf', 3.0, 3.2), # MHT192WDT-ICE, Ice Blue
    ('D11_Vf', 2.7, 2.9), # OSK40603C1E, Pink
    ('D12_Vf', 2.7, 2.9), # ORH-W46G, White
    ('D13_Vf', 2.7, 2.9), # OSK40603C1E, Pink
    ('D14_Vf', 3.0, 3.2)) # MHT192WDT-ICE, Ice Blue
