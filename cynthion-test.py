from tycho import *

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
        set_boost_supply(5.0, 0.1)
        connect_boost_supply_to(supply_port)

        # Ramp the supply in 50mV steps up to 6.25V.
        for voltage in range(5.0, 6.25, 0.05):
            set_boost_supply(voltage, 0.1)
            sleep(0.05)

            # Up to 5.5V, there must be only a diode drop.
            if voltage <= 5.5:
                minimum = voltage - schottky_drop_max
                maximum = voltage - schottky_drop_min
            # Between 5.5V and 6.0V, OVP may kick in.
            elif 5.5 <= 6.0:
                minimum = 0
                maximum = voltage - schottky_drop_min
            # Above 6.0V, OVP must kick in.
            else:
                minimum = 0
                maximum = 6.0 - schottky_drop_min

            # Check voltage at +5V rail.
            test_voltage('+5V', minimum, maximum)

            # Check for leakage to other ports.
            for port in ('CONTROL', 'AUX', 'TARGET-C', 'TARGET-A'):
                if port != supply_port:
                    test_leakage(port)

        disconnect_supply_and_discharge()

    # Test passthrough of Target-C VBUS to Target-A VBUS with power off.
    set_boost_supply(5.0, 0.1)
    connect_boost_supply_to('TARGET-C')
    test_voltage('TARGET_A_VBUS', 4.95, 5.05)
    disconnect_supply_and_discharge()

    # Check that the Target-A cable is not connected yet.
    test_voltage('VBUS_TA', 0, 0.05)

    # Power at +5V through the control port for following tests.
    set_boost_supply(5.0, 0.1)
    connect_boost_supply_to('CONTROL')

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

    # Hand off EUT supply from boost converter to host.
    set_boost_supply(4.5, 0.1)
    connect_host_supply_to('CONTROL')
    connect_boost_supply_to(None)

    # Connect boost supply to AUX at a voltage higher than the host supply,
    # but less than the minimum OVP cutoff.
    set_boost_supply(5.4, 0.1)
    connect_boost_supply_to('AUX')

    # Define ranges to distinguish high and low supplies.
    high_min = 5.35 - schottky_drop_max
    high_max = 5.45 - schottky_drop_min
    low_min = 4.75 - schottky_drop_max
    low_max = 5.25 - schottky_drop_min

    # Ensure that ranges are distinguishable.
    assert(high_min > low_max)

    # 5V rail should be switched to the higher supply.
    test_voltage('+5V', high_min, high_max)

    # Tell the FPGA to disable the AUX supply input.
    # 5V rail should be switched to the lower host supply on CONTROL.
    enable_supply_input('AUX', False)
    test_voltage('+5V', low_min, low_max)

    # Re-enable AUX supply, check 5V rail is switched back to it.
    enable_supply_input('AUX', True)
    test_voltage('+5V', high_min, high_max)

    # Swap ports between host and boost converter.
    set_boost_supply(4.5, 0.1)
    connect_host_supply_to('AUX')
    connect_boost_supply_to('CONTROL')

    # Increase boost voltage to identifiable level.
    set_boost_supply(5.4, 0.1)
    test_voltage('+5V', high_min, high_max)

    # Tell the FPGA to disable the CONTROL supply input.
    # 5V rail should be switched to the lower host supply on AUX.
    enable_supply_input('CONTROL', False)
    test_voltage('+5V', low_min, low_max)

    # Re-enable CONTROL supply, check 5V rail is switched back to it.
    enable_supply_input('CONTROL', True)
    test_voltage('+5V', high_min, high_max)

    # Swap back to powering from host.
    set_boost_supply(4.5, 0.1)
    connect_host_supply_to('CONTROL')
    connect_boost_supply_to(None)

    # Request the operator connect a cable to Target-A.
    request_target_a_cable()

    # Check that the Target-A cable is connected.
    set_boost_supply(5.0, 0.1)
    connect_boost_supply_to('TARGET-C')
    test_voltage('VBUS_TA', 4.95, 5.05)
    connect_boost_supply_to(None)

    # Tell the FPGA to put the target PHY in passive mode, then test
    # passthrough to a USB FS device created on the GF1.
    connect_host_to('CONTROL')
    set_target_passive()
    connect_host_to('TARGET-C')
    test_usb_fs()

    # VBUS distribution testing.
    for (voltage, load_current, load_resistor) in (
        ( 5.0, 3.0, RESISTOR_HIGH_CURRENT),
        (20.0, 0.5, RESISTOR_LOW_CURRENT)):

        # Set limits for voltage and current measurements.
        vmin_off = 0.00
        vmax_off = 0.01
        imin_off = -0.01
        imax_off =  0.01
        vmin_on  = voltage * 0.98 - 0.01
        vmax_on  = voltage * 1.02 + 0.01

        # Test with passthrough off, and then with passthrough to load.
        for (passthrough, current, resistor) in (
            (False, 0.0, None),
            (True, load_current, load_resistor)):

            imin_on = current * 0.98 - 0.01
            imax_on = current * 1.02 + 0.01

            # Supply through each input port.
            for input_port in ('TARGET-C', 'CONTROL', 'AUX'):

                # Move host supply to another port if necessary.
                if input_port == 'CONTROL':
                    connect_host_supply_to('CONTROL', 'AUX')
                    connect_host_supply_to('AUX')
                elif input_port == 'AUX':
                    connect_host_supply_to('CONTROL', 'AUX')
                    connect_host_supply_to('CONTROL')

                # Configure boost supply and connect.
                set_boost_supply(voltage, current + 0.1)
                set_load_resistor(resistor)
                connect_boost_supply_to(input_port)
                set_passthrough(input_port, 'TARGET-A', passthrough)

                # Check voltage and current on each port.
                for port in ('CONTROL', 'AUX', 'TARGET-A', 'TARGET-C'):

                    # Check voltage and positive current on input port.
                    if port == input_port:
                        test_vbus(input_port, vmin_on, vmax_on)
                        test_eut_voltage(input_port, vmin_on, vmax_on)
                        test_eut_current(input_port, imin_on, imax_on)
                    # Check voltage and negative current on output port.
                    elif port == 'TARGET-A' and passthrough:
                        test_vbus(port, vmin_on, vmax_on)
                        test_eut_voltage(port, vmin_on, vmax_on)
                        test_eut_current(port, -imin_on, -imax_on)
                    # Exclude the host-supplied port from measurements.
                    elif (input_port, port) in (
                        ('CONTROL', 'AUX'), ('AUX', 'CONTROL')):
                        continue
                    # Check all other ports have zero leakage.
                    else:
                        test_vbus(port, vmin_off, vmax_off)
                        test_eut_voltage(port, vmin_off, vmax_off)
                        test_eut_current(port, imin_off, imax_off)

                # Disconnect.
                set_passthrough(input_port, 'TARGET-A', False)
                connect_boost_supply_to(None)
                set_load_resistor(None)

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

    # Power off EUT.
    connect_host_supply_to(None)

    # VBUS distribution testing with EUT off.
    for (voltage, current, resistor) in (
        ( 5.0, 3.0, RESISTOR_HIGH_CURRENT),
        (20.0, 0.5, RESISTOR_LOW_CURRENT)):

        # Set limits for voltage and current measurements.
        vmin_off = 0.00
        vmax_off = 0.01
        vmin_on  = voltage * 0.98 - 0.01
        vmax_on  = voltage * 1.02 + 0.01
        imin_on  = current * 0.95 - 0.01
        imax_on  = current * 1.05 + 0.01

        # Configure boost supply and connect.
        set_boost_supply(voltage, current + 0.1)
        set_load_resistor(resistor)
        connect_boost_supply_to('TARGET-C')

        # Check voltages and current.
        test_vbus('TARGET-C', vmin_on, vmax_on)
        test_vbus('TARGET-A', vmin_on, vmax_on)
        test_vbus('CONTROL', vmin_off, vmax_off)
        test_vbus('AUX', vmin_off, vmax_off)
        test_boost_current(imin_on, imax_on)

        # Disconnect.
        connect_boost_supply_to(None)
        set_load_resistor(None)


# Helper functions for testing.

def test_leds(leds, set_led):
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

schottky_drop_min, schottky_drop_max = (0.505, 0.565) # PMEG10010ELR at 0.1A
