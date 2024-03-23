from greatfet.interfaces.i2c.register_based import I2CRegisterBasedDevice
from errors import *

VREF_L, VREF_H, IOUT_LIMIT, VOUT_SR, VOUT_FS, CDC, MODE, STATUS = range(8)

SCP = 0x80
OCP = 0x40
OVP = 0x20

class TPS55288(I2CRegisterBasedDevice):

    def __init__(self, gf):
        super().__init__(gf.i2c, device_address=0x74)

    def read(self, reg):
        with error_conversion(GF1Error):
            return super().read(reg)

    def write(self, reg, value):
        with error_conversion(GF1Error):
            return super().write(reg, value)

    def disable(self):
        self.write(MODE, 0x20)

    def enable(self):
        self.write(VOUT_SR, 0x11)
        self.write(MODE, 0xA0)

    def set_voltage(self, voltage):
        if voltage < 0.8 or voltage > 20.0:
            raise ValueError("Voltage out of range")
        value = int((voltage - 0.8) / 0.02)
        self.write(VREF_L, value & 0xFF)
        self.write(VREF_H, value >> 8)

    def set_current_limit(self, limit):
        if limit < 0 or limit > 6.35:
            raise ValueError("Current limit out of range")
        value = int(limit / 0.05)
        self.write(IOUT_LIMIT, 0x80 | value)

    def status(self):
        print("Voltage: %.2fV" % self.voltage())
        print("Current: %.1fmA" % (self.current() * 1000))

    def check_fault(self):
        status = self.read(STATUS)
        if status & SCP:
            raise SCPError("Short circuit detected by power supply")
        if status & OCP:
            raise OCPError("Overcurrent detected by power supply")
        if status & OVP:
            raise OVPError("Overvoltage detected by power supply")
