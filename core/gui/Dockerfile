# Start from the exact image you were using
FROM lscr.io/linuxserver/webtop:ubuntu-xfce

# Set environment to non-interactive to avoid apt prompts
ENV DEBIAN_FRONTEND=noninteractive

# Run all installation steps in a single build layer.
# This happens once, when you build the image, NOT when it starts.
RUN \
  echo "**** install system dependencies ****" && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
    python3-full \
    python3-pip \
    python3-tk \
    scrot && \
  echo "**** install python packages ****" && \
  # We use --break-system-packages because we are adding to the container's system python
  pip3 install --no-cache-dir \
    Pillow && \
  echo "**** cleanup ****" && \
  apt-get clean && \
  rm -rf \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*