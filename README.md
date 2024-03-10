# Cynthion Test Software

This repository contains software for testing a [Cynthion](https://github.com/greatscottgadgets/cynthion-hardware) board using the [Tycho](https://github.com/greatscottgadgets/tycho) test fixture.

## Hardware Required

- 1 x Cynthion r1.4.0 EUT
- 1 x Tycho r2.0.0
- 1 x Sasserides r1.0.0 (A & B boards, assembled in stack with test pins)
- 1 x GreatFET One
- 1 x Black Magic Probe
- 1 x 10-pin ARM debug cable
- 1 x 34-pin 2.54mm ribbon cable
- 1 x Mean Well GST25B24-P1J or equivalent 24V supply
- 2 x Push buttons with trailing wires (PASS & FAIL)
- 3 x ADT-Link UT6A-UT6B-NC cables with U1 pins 1 and 8 connected
- 1 x USB-A to USB-C cable
- Appropriate USB hub & cables to connect the GF1, BMP and Tycho to the host.
- Mechanical arrangements to attach the EUT to Sasserides.

## Assembly

1. Attach the Cynthion EUT to the Sasserides test pins with appropriate hardware.
2. Connect the 34-pin ribbon cable between Tycho and Sasserides.
3. Attach the GreatFET upside down onto Tycho as indicated on the silkscreen.
4. Connect the Black Magic Probe to Tycho via the 10-pin ARM debug cable.
5. Connect the PASS and FAIL buttons to Tycho via the screw terminals.
6. Connect the ADT-Link cables to CONTROL, AUX and TARGET-C ports on Tycho and EUT.
7. Connect the USB-A to USB-C cable to the TARGET-A ports on Tycho and EUT.
8. Connect the 24V supply to Tycho.
9. Connect the GreatFET USB0, Black Magic Probe and Tycho HOST ports to the host.

## Setup

```sh
# Check out the repository, including submodules:
git clone --recurse-submodules https://github.com/greatscottgadgets/cynthion-test
cd cynthion-test

# Install pre-requisites
sudo apt install make python3-venv gdb-multiarch dfu-util fxload

# Build the test environment:
make

# Install udev rules:
make install-udev

# Flash GreatFET firmware:
make flash-greatfet

# Flash Black Magic Probe firmware:
make flash-blackmagic

# Run self-check of test system:
make check

# Calibrate the test system:
make calibrate

# Run the test. Before doing so, disconnect Target-A cable from the EUT.
# You will be prompted to reconnect it during the test.
make test
```
