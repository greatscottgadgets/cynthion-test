# For use with GSG's Jenkins-based HIL test server
FROM ubuntu:24.04
USER root

# Copy device calibration and udev rules files from Jenkins container
RUN mkdir /etc/udev && mkdir /etc/udev/rules.d
COPY --from=gsg-jenkins /cyn_cal.dat /tmp/calibration.dat
COPY --from=gsg-jenkins /60-tycho.rules /etc/udev/rules.d/60-tycho.rules

# Copy USB hub port power tool from Jenkins container
COPY --from=gsg-jenkins /startup/hubs.py /startup/hubs.py
COPY --from=gsg-jenkins /startup/.hubs /startup/.hubs
RUN ln -s /startup/hubs.py /usr/local/bin/hubs

# Override interactive installations and install dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    dfu-util \
    fxload \
    gdb-multiarch \
    git \
    jq \
    libusb-1.0-0-dev \
    make \
    python-is-python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install python-dotenv --upgrade --break-system-packages

# install oss-cad-suite 2024-11-01
RUN curl -L $(curl -s "https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/183038843" \
    | jq --raw-output '.assets[].browser_download_url' | grep "linux-x64") --output oss-cad-suite-linux-x64-20241101.tgz \
    && tar zxvf oss-cad-suite-linux-x64-20241101.tgz

USER jenkins

# add oss-cad-suite to PATH for pip/source package installations
ENV PATH="/root/.local/bin:/oss-cad-suite/bin:$PATH"

# Inform Docker that the container is listening on port 8080 at runtime
EXPOSE 8080
