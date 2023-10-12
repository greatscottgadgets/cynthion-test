MAJOR ?= 1
MINOR ?= 2

ENV_PYTHON=environment/bin/python
ENV_INSTALL=environment/bin/pip install
TIMESTAMP=environment/timestamp
PLATFORM=cynthion.gateware.platform:CynthionPlatformRev$(MAJOR)D$(MINOR)
ANALYZER=dependencies/cynthion/gateware/analyzer
APOLLO_VARS=APOLLO_BOARD=cynthion BOARD_REVISION_MAJOR=$(MAJOR) BOARD_REVISION_MINOR=$(MINOR)
FIRMWARE=dependencies/apollo/firmware/_build/cynthion_d11/firmware.bin

all: $(TIMESTAMP)

test: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py

debug: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py debug

firmware: firmware.bin

firmware.bin: $(FIRMWARE)
	cp $< $@

$(FIRMWARE):
	$(APOLLO_VARS) make -C dependencies/apollo/firmware get-deps
	$(APOLLO_VARS) make -C dependencies/apollo/firmware

bitstreams: analyzer.bit flashbridge.bit selftest.bit speedtest.bit

analyzer.bit: $(ANALYZER)/top.py $(ANALYZER)/analyzer.py $(TIMESTAMP)
	LUNA_PLATFORM=$(PLATFORM) $(ENV_PYTHON) $< -o $@

%.bit: %.py $(TIMESTAMP)
	LUNA_PLATFORM=$(PLATFORM) $(ENV_PYTHON) $< -o $@

environment:
	python -m venv environment

$(TIMESTAMP): environment
	$(ENV_INSTALL) dependencies/libgreat/host
	$(ENV_INSTALL) dependencies/greatfet/host
	$(ENV_INSTALL) dependencies/amaranth
	$(ENV_INSTALL) dependencies/amaranth-boards
	$(ENV_INSTALL) dependencies/amaranth-stdio
	$(ENV_INSTALL) dependencies/apollo
	$(ENV_INSTALL) dependencies/python-usb-protocol
	$(ENV_INSTALL) --no-deps dependencies/luna
	$(ENV_INSTALL) dependencies/cynthion/host
	$(ENV_INSTALL) libusb1==1.9.2 colorama ipdb
	rm -rf dependencies/amaranth-stdio/build
	touch $(TIMESTAMP)

clean:
	$(APOLLO_VARS) make -C dependencies/apollo/firmware clean
	rm -rf environment
