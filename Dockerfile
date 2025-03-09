FROM ubuntu:22.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Python and Tcl/Tk
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the project files
COPY . /app

# Install Python dependencies
RUN pip3 install --upgrade pip \
    && pip3 install pyinstaller ttkbootstrap platformdirs influxdb darkdetect

# Build the executable
CMD ["pyinstaller", "--clean", "influx_data_cleaner.spec"]