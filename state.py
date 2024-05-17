# Global test state

# Bus and address of the last new USB device detected.
last_bus = None
last_addr = None

# Current indent level for formatting.
indent = 0

# Whether test step numbering is currently enabled.
numbering = False
# Curent step numbering.
step = [0]

# GreatFET instance.
gf = None

# Serial port device to use for Black Magic Probe.
blackmagic_port = None

# MCU serial number of the current EUT.
mcu_serial = None

# SPI Flash serial number of the current EUT.
flash_serial = None

# EUT port that the boost converter is currently supplying.
boost_port = None

# Calibration data.
calibration = dict(
    greatfet_serial = None,
    voltage_scale_upper = 1.0,
    voltage_scale_lower = 1.0,
    current_offset = 0.0,
)
