from luna.gateware.applets.flash_bridge import FlashBridge
from luna import top_level_cli

class ControlPortFlashBridge(FlashBridge):
    def __init__(self):
        super().__init__(phy='control_phy')

top_level_cli(ControlPortFlashBridge)
