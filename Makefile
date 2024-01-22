MAJOR ?= 1
MINOR ?= 4

ENV_PYTHON=environment/bin/python
ENV_INSTALL=environment/bin/pip install
TIMESTAMP=environment/timestamp
PLATFORM=cynthion.gateware.platform:CynthionPlatformRev$(MAJOR)D$(MINOR)
BOARD_VARS=BOARD_REVISION_MAJOR=$(MAJOR) BOARD_REVISION_MINOR=$(MINOR)
APOLLO_VARS=APOLLO_BOARD=cynthion $(BOARD_VARS)
FIRMWARE=dependencies/apollo/firmware/_build/cynthion_d11/firmware.bin
BOOTLOADER=dependencies/saturn-v/bootloader.elf
ANALYZER=cynthion.gateware.analyzer.top

all: $(TIMESTAMP)

test: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py

debug: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py debug

bootloader: bootloader.elf

bootloader.elf: $(BOOTLOADER)
	cp $< $@

$(BOOTLOADER):
	$(BOARD_VARS) make -C dependencies/saturn-v

firmware: firmware.bin

firmware.bin: $(FIRMWARE)
	cp $< $@

$(FIRMWARE):
	$(APOLLO_VARS) make -C dependencies/apollo/firmware get-deps
	$(APOLLO_VARS) make -C dependencies/apollo/firmware

bitstreams: analyzer.bit flashbridge.bit selftest.bit speedtest.bit

analyzer.bit: $(TIMESTAMP)
	LUNA_PLATFORM=$(PLATFORM) $(ENV_PYTHON) -m $(ANALYZER) -o $@

%.bit: %.py $(TIMESTAMP)
	LUNA_PLATFORM=$(PLATFORM) $(ENV_PYTHON) $< -o $@

environment:
	python -m venv environment

$(TIMESTAMP): environment
	$(ENV_INSTALL) -e dependencies/libgreat/host
	$(ENV_INSTALL) -e dependencies/greatfet/host
	$(ENV_INSTALL) -e dependencies/amaranth
	$(ENV_INSTALL) -e dependencies/amaranth-boards
	$(ENV_INSTALL) -e dependencies/amaranth-stdio
	$(ENV_INSTALL) -e dependencies/apollo
	$(ENV_INSTALL) -e dependencies/python-usb-protocol
	$(ENV_INSTALL) --no-deps -e dependencies/luna
	$(ENV_INSTALL) -e dependencies/cynthion/cynthion/python
	$(ENV_INSTALL) -e dependencies/pyfwup
	$(ENV_INSTALL) libusb1==1.9.2 colorama ipdb
	rm -rf dependencies/amaranth-stdio/build
	touch $(TIMESTAMP)

clean:
	$(APOLLO_VARS) make -C dependencies/apollo/firmware clean
	make -C dependencies/saturn-v clean
	rm -f $(BOOTLOADER)
	rm -rf environment
