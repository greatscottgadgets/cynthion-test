file bootloader.elf
target extended-remote /dev/ttyACM0
monitor swdp_scan
attach 1
monitor unlock_bootprot
monitor erase_mass
load
monitor lock_bootprot 4
kill
