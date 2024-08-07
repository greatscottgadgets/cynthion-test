# For use with GSG's Jenkins-based HITL test server.
FROM ubuntu:20.04
USER root

# copy device calibration and udev rules files from jenkins controller
RUN mkdir /etc/udev && mkdir /etc/udev/rules.d
COPY --from=gsg-jenkins /cyn_cal.dat /tmp/calibration.dat
COPY --from=gsg-jenkins /60-tycho.rules /etc/udev/rules.d/60-tycho.rules

# Override interactive installations and install dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    dfu-util \
    fxload \
    gdb-multiarch \
    git \
    make \
    python-is-python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install git+https://github.com/CapableRobot/CapableRobot_USBHub_Driver --upgrade

# Inform Docker that the container is listening on port 8080 at runtime
EXPOSE 8080
