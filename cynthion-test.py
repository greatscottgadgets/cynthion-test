from time import sleep
from tycho import *
import numpy as np

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
    for supply_port in ('CONTROL', 'AUX'):
        begin(f"Testing VBUS supply though {info(supply_port)}")

        # Connect 5V supply via this port.
        set_boost_supply(5.0, 0.2)
        connect_boost_supply_to(supply_port)

        # Check supply present at port.
        test_vbus(supply_port, 4.85, 5.1)

        # Ramp the supply in 50mV steps up to 6.25V.
        for voltage in np.arange(5.0, 6.25, 0.05):
            begin(f"Testing with {info(f'{voltage:.2f} V')} supply "
                  f"on {info(supply_port)}")
            set_boost_supply(voltage, 0.2)
            sleep(0.05)

            schottky_drop_min, schottky_drop_max = (0.35, 0.8)

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

            begin("Checking for leakage to other ports")
            for port in ('CONTROL', 'AUX', 'TARGET-C', 'TARGET-A'):
                if port != supply_port:
                    test_leakage(port)
            end()

            end()

        disconnect_supply_and_discharge(supply_port)
        end()

    begin("Testing passthrough at low current with power off")
    set_boost_supply(5.0, 0.2)
    connect_boost_supply_to('TARGET-C')
    test_voltage('TARGET_A_VBUS', 4.85, 5.05)
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

    sleep(1)

    # Connect host D+/D- to control port.
    connect_host_to('CONTROL')

    sleep(1)

    # Flash Apollo firmware to MCU via DFU.
    flash_firmware()

    sleep(0.1)

    # Simulate pressing the PROGRAM button.
    simulate_program_button()

    sleep(0.7)

    # Connect to the Apollo debug interface.
    start("Connecting to Apollo")
    apollo = ApolloDebugger()
    done()

    # Check JTAG scan via Apollo finds the FPGA.
    test_jtag_scan(apollo)

    # Flash analyzer bitstream.
    flash_analyzer(apollo)

    # Configure FPGA with test gateware.
    configure_fpga(apollo)

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

    begin("Testing FPGA control of VBUS input selection")

    begin("Handing off EUT supply from boost converter to host")
    set_boost_supply(4.5, 0.2)
    connect_host_supply_to('CONTROL')
    connect_boost_supply_to(None)
    end()

    begin("Connect DC-DC to AUX at a voltage higher than the host supply")
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
    end()

    begin("Test FPGA control of AUX supply input")
    # Tell the FPGA to disable the AUX supply input.
    # 5V rail should be switched to the lower host supply on CONTROL.
    enable_supply_input(apollo, 'AUX', False)
    test_voltage('+5V', low_min, low_max)
    # Re-enable AUX supply, check 5V rail is switched back to it.
    enable_supply_input(apollo, 'AUX', True)
    test_voltage('+5V', high_min, high_max)
    end()

    begin("Swap ports between host and boost converter")
    set_boost_supply(4.5, 0.2)
    connect_host_supply_to('AUX')
    connect_boost_supply_to('CONTROL')
    end()

    begin("Increase boost voltage to identifiable level")
    set_boost_supply(5.4, 0.2)
    test_voltage('+5V', high_min, high_max)
    end()

    begin("Test FPGA control of CONTROL supply input")
    # Tell the FPGA to disable the CONTROL supply input.
    # 5V rail should be switched to the lower host supply on AUX.
    enable_supply_input(apollo, 'CONTROL', False)
    test_voltage('+5V', low_min, low_max)
    # Re-enable CONTROL supply, check 5V rail is switched back to it.
    enable_supply_input(apollo, 'CONTROL', True)
    test_voltage('+5V', high_min, high_max)
    end()

    begin("Swap back to powering from host")
    set_boost_supply(4.5, 0.2)
    connect_host_supply_to('CONTROL')
    connect_boost_supply_to(None)
    end()

    end()

    begin("Checking FPGA control of CC and SBU lines")
    for port in ('AUX', 'TARGET-C'):
        begin(f"Checking control of {info(port)} CC lines")
        begin_cc_measurement(port)
        for levels in ((0, 1), (1, 0)):
            set_cc_levels(apollo, port, levels)
            for pin, level in zip(('CC1', 'CC2'), levels):
                if level:
                    check_cc_resistance(pin, 4.1, 6.1)
                else:
                    check_cc_resistance(pin, 50, 200)
        end_cc_measurement()
        end()
        begin(f"Checking control of {info(port)} SBU lines")
        for levels in ((0, 1), (1, 0)):
            set_sbu_levels(apollo, port, levels)
            test_pin('SBU1_test', levels[0])
            test_pin('SBU2_test', levels[1])
        end()
    end()

    todo("Test USB HS comms on each port")
    #for port in ('CONTROL', 'AUX', 'TARGET-C'):
    #    connect_host_to(port)
    #    test_usb_hs(port)

    # Request the operator connect a cable to Target-A.
    # request_target_a_cable()

    # # Check that the Target-A cable is connected.
    # set_boost_supply(5.0, 0.2)
    # connect_boost_supply_to('TARGET-C')
    # test_voltage('VBUS_TA', 4.95, 5.05)
    # connect_boost_supply_to(None)

    # todo("Test USB FS comms through target passthrough")
    # #connect_host_to('TARGET-C')
    # #test_usb_fs()

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
    set_debug_leds(apollo, 0b11111)
    set_fpga_leds(apollo, 0b111111)
    set_pin('REF_LED_EN', True)
    request("check LEDs match reference")
    set_pin('REF_LED_EN', False)
    set_debug_leds(apollo, 0)
    set_fpga_leds(apollo, 0)
    end()
    end()

    # Request press of USER button, should be detected by FPGA.
    test_user_button(apollo)

    # Tell the FPGA to hand off the control port to the MCU.
    request_control_handoff()
    test_apollo_present()

    # Request Apollo reset, should cause analyzer to enumerate.
    request_apollo_reset()
    test_analyzer_present()

    # Request press of PROGRAM button, should cause Apollo to enumerate.
    request('press the PROGRAM button')
    test_apollo_present()

    # Request press of RESET button, should cause analyzer to enumerate.
    request('press the RESET button')
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
