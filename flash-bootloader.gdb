file bootloader.elf
target extended-remote /dev/ttyACM0
monitor swdp_scan
attach 1
monitor erase_mass
load
kill
