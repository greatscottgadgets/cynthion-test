ENV_PYTHON=environment/bin/python
ENV_INSTALL=environment/bin/pip install
TIMESTAMP=environment/timestamp
PLATFORM=cynthion.gateware.platform:CynthionPlatformRev1D2
ANALYZER=dependencies/cynthion/gateware/analyzer

all: $(TIMESTAMP)

test: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py

debug: $(TIMESTAMP)
	$(ENV_PYTHON) cynthion-test.py debug

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
	rm -rf environment
