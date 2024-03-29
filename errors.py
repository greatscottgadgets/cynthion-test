import state
import usb1
import usb

"""
Base class for all exceptions which may be generated by the test.
"""
class CynthionTestError(Exception):
    def __init__(self, msg):
        self.msg = msg
        self.step = ".".join(str(s) for s in state.step)

# Define subclasses with associated three-letter codes.
for code, name in (
    ('EXC', 'UnexpectedError'),  # An unhandled exception occured.
    ('INT', 'TestStoppedError'), # Test stopped by keyboard interrupt.
    ('USR', 'FailButtonError'),  # User pressed the FAIL button.
    ('DEP', 'DependencyError'),  # Software dependency problem.
    ('GF1', 'GF1Error'),         # Problem with GreatFET.
    ('BMP', 'BMPError'),         # Problem with Black Magic Probe.
    ('TYC', 'TychoError'),       # Problem with Tycho.
    ('PSU', 'PowerSupplyError'), # Problem with the power supply.
    ('SCP', 'SCPError'),         # Power supply detected a short circuit in EUT.
    ('OCP', 'OCPError'),         # Power supply detected overcurrent in EUT.
    ('OVP', 'OVPError'),         # Power supply detected overvoltage in EUT.
    ('CAL', 'CalibrationError'), # Calibration data missing or invalid.
    ('LOW', 'ValueLowError'),    # Measured value was too low.
    ('HIG', 'ValueHighError'),   # Measured value was too high.
    ('WRG', 'ValueWrongError'),  # Measured value was wrong.
    ('SHT', 'ShortError'),       # Short circuit detected between EUT USB-C pins.
    ('CMD', 'CommandError'),     # An external command failed.
    ('SLF', 'SelfTestError'),    # An EUT self-test step failed.
    ('REG', 'RegisterError'),    # An EUT register access did not succeed.
    ('BTN', 'ButtonError'),      # An EUT button was not behaving as expected.
    ('CBL', 'CableError'),       # A cable was not in the correct position.
    ('USB', 'USBCommsError'),    # Problem with USB communications to the EUT.
    ('FX2', 'FX2Error'),         # Problem with USB through the EUT to the FX2.
):
    globals()[name] = type(name, (CynthionTestError,), {'code': code})

# Text to identify USB device at fault on USB errors.
USBCommsError.device = "EUT"
GF1Error.device = "GreatFET"
BMPError.device = "Black Magic Probe"
FX2Error.device = "Tycho FX2"

# Override __init__ method in GF1Error to mark the GF1 no longer usable.
def __init__(self, msg):
    CynthionTestError.__init__(self, msg)
    state.gf = None
GF1Error.__init__ = __init__

"""
Takes an exception and if it is not a CynthionTestError, raises a
suitable CynthionTestError wrapper.
"""
def wrap_exception(exc, usb_err_type=USBCommsError):
    usb_exceptions = (usb.USBError, usb1.USBError)
    if isinstance(exc, CynthionTestError):
        return
    elif isinstance(exc, KeyboardInterrupt):
        raise TestStoppedError("Test stopped by keyboard interrupt.")
    elif isinstance(exc, usb_exceptions):
        if hasattr(exc, 'strerror'):
            raise usb_err_type(
                f"{usb_err_type.device} USB error: {exc.strerror}")
        else:
            raise usb_err_type(
                f"{usb_err_type.device} USB error: {str(exc)}")
    else:
        raise UnexpectedError(str(exc))

"""
Context manager which converts non-CynthionTestError exceptions.
"""
class error_conversion():
    def __init__(self, usb_err_type=USBCommsError):
        self.usb_err_type = usb_err_type
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_value is not None:
            wrap_exception(exc_value, self.usb_err_type)
        return False
