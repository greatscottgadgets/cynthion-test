from tests import *
import tests
import pickle

def calibrate():
    # Use a dummy calibration while taking uncalibrated measurements.
    tests.calibration = dict(
        voltage_scale_upper = 1.0,
        voltage_scale_lower = 1.0
    )

    # Have user disconnect TARGET-C cable so we can power it without a load.
    # Using TARGET-C because it won't power up the EUT if they get it wrong.
    request("disconnect TARGET-C cable from EUT")
    connect_boost_supply_to('TARGET-C')

    # Power TARGET-C at 5V and calibrate lower range.
    with group("Calibrating low range"):
        set_boost_supply(5.0, 0.1)
        # Boost converter needs a moment to stabilise on first startup.
        sleep(0.1)
        scale_low = 5.0 / test_vbus('TARGET-C', Range(4.9, 5.1))
        item(f"Calibration factor: {info(scale_low)}")

    # Increase voltage to 15V and repeat.
    with group("Calibrating high range"):
        set_boost_supply(15.0, 0.1)
        scale_high = 15.0 / test_vbus('TARGET-C', Range(14.5, 15.5))
        item(f"Calibration factor: {info(scale_high)}")

    # Write out calibration.
    calibration = dict(
        voltage_scale_lower=scale_low,
        voltage_scale_upper=scale_high,
    )
    pickle.dump(calibration, open('calibration.dat', 'wb'))

if __name__ == "__main__":
    try:
        calibrate()
        ok("Calibration complete")
    except KeyboardInterrupt:
        fail("Calibration stopped by user")
    reset()
