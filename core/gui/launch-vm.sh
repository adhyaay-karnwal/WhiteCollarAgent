#!/bin/bash

# Set exit on error to stop the script if any step fails
set -e

# ==========================================
# === Configuration & Constants ===
# ==========================================
# Define IP addresses for the host and the VM side of the tap interface
TAP_DEV="tap0"
HOST_IP="172.16.0.1"
VM_IP="172.16.0.2"
NETMASK_LEN="/24"
# Generate a random MAC address to avoid conflicts
FC_MAC=$(printf '02:%02X:%02X:%02X:%02X:%02X\n' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))

# Firecracker version to download
FC_VERSION="v1.7.0"

# ==========================================
# === 1. Prerequisites Checks ===
# ==========================================
echo "--- 1. Checking Prerequisites ---"

# Check for root privileges (Required for networking setup)
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root to configure networking and KVM."
    echo "Please rerun with: sudo $0"
    exit 1
fi

# Check for KVM existence and write permissions
if [ ! -w "/dev/kvm" ]; then
    echo "ERROR: /dev/kvm is missing or not writeable."
    echo "Please ensure KVM virtualization is enabled in your BIOS and OS."
    echo "Try running: sudo chmod a+rw /dev/kvm"
    exit 1
fi
echo "KVM is available."

# Check for basic dependencies
for cmd in curl tar ip; do
    if ! command -v $cmd &> /dev/null; then
        echo "ERROR: Missing required utility: $cmd. Please install it."
        exit 1
    fi
done

# ==========================================
# === 2. Workspace Setup & Downloads ===
# ==========================================
# Create a temporary workspace to keep things clean
WORKSPACE=$(mktemp -d -t fc-demo-XXXXXX)
cd "$WORKSPACE"
echo "--- 2. Setting up workspace in $WORKSPACE ---"

ARCH="$(uname -m)"
echo "Detected architecture: $ARCH"

# --- Download Firecracker Binary ---
FC_BINARY="$WORKSPACE/firecracker"
if [ ! -f "$FC_BINARY" ]; then
    echo "Downloading Firecracker $FC_VERSION..."
    DOWNLOAD_URL="https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}/firecracker-${FC_VERSION}-${ARCH}.tgz"
    
    # Download and extract to a temporary location to handle varying directory structures in tarballs
    mkdir -p temp_extract
    curl -L --fail "$DOWNLOAD_URL" | tar -xz -C temp_extract
    
    # Find the binary regardless of the directory structure inside the tarball
    FOUND_BIN=$(find temp_extract -type f -name "firecracker*" | head -n 1)
    if [ -z "$FOUND_BIN" ]; then
        echo "ERROR: Could not find firecracker binary in downloaded archive."
        exit 1
    fi
    mv "$FOUND_BIN" "$FC_BINARY"
    rm -rf temp_extract
    chmod +x "$FC_BINARY"
fi

# --- Download Kernel and Rootfs (UPDATED to current Quickstart S3 URLs) ---
KERNEL_PATH="$WORKSPACE/vmlinux"
ROOTFS_PATH="$WORKSPACE/rootfs.ext4"

# Using the currently active Quickstart URLs (Ubuntu Bionic image)
KERNEL_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/x86_64/kernels/vmlinux.bin"
ROOTFS_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/x86_64/rootfs/bionic.rootfs.ext4"

if [ ! -f "$KERNEL_PATH" ]; then
    echo "Downloading demo Kernel image..."
    curl -L --fail "$KERNEL_URL" -o "$KERNEL_PATH"
fi

if [ ! -f "$ROOTFS_PATH" ]; then
    echo "Downloading demo Root Filesystem (Ubuntu Bionic - approx 375MB, please wait)..."
    curl -L --fail "$ROOTFS_URL" -o "$ROOTFS_PATH"
fi

# ==========================================
# === 3. Host Network Setup ===
# ==========================================
echo "--- 3. Setting up host network interface $TAP_DEV ---"

# Clean up tap device if it already exists from a previous run
if ip link show "$TAP_DEV" &> /dev/null; then
    echo "Removing existing $TAP_DEV interface..."
    ip link del "$TAP_DEV"
fi

# Create tap device, assign IP, and set it up
ip tuntap add dev "$TAP_DEV" mode tap
ip addr add "${HOST_IP}${NETMASK_LEN}" dev "$TAP_DEV"
ip link set dev "$TAP_DEV" up
echo "Network configured: Host ($HOST_IP) <--> VM ($VM_IP)"

# ==========================================
# === 4. Create Firecracker Config File ===
# ==========================================
CONFIG_FILE="$WORKSPACE/vm_config.json"
echo "--- 4. Generating Firecracker configuration to $CONFIG_FILE ---"

# Boot args for Ubuntu image (removed init=/bin/sh, increased memory)
cat <<EOF > "$CONFIG_FILE"
{
  "boot-source": {
    "kernel_image_path": "$KERNEL_PATH",
    "boot_args": "console=ttyS0 reboot=t panic=1 pci=off root=/dev/vda rw ip=$VM_IP::$HOST_IP:$NETMASK_LEN::eth0:off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "$ROOTFS_PATH",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "$FC_MAC",
      "host_dev_name": "$TAP_DEV"
    }
  ],
  "machine-config": {
    "vcpu_count": 1,
    "mem_size_mib": 512
  }
}
EOF

# ==========================================
# === 5. Launch Firecracker ===
# ==========================================
echo "----------------------------------------------------------------"
echo ">>> Launching Firecracker VM... <<<"
echo "You will see kernel boot messages below, followed by an Ubuntu login prompt."
echo "Default login: 'root', password: 'root'."
echo "To exit the VM and stop Firecracker, type 'reboot' inside the VM."
echo "----------------------------------------------------------------"

# Run Firecracker in the foreground using the config file
"$FC_BINARY" --no-api --config-file "$CONFIG_FILE"

# ==========================================
# === 6. Cleanup (Runs after VM exits) ===
# ==========================================
echo
echo "--- VM exited. Cleaning up... ---"
# Remove the network interface
ip link del "$TAP_DEV" 2>/dev/null || true
# Remove downloaded files
rm -rf "$WORKSPACE"
echo "Cleanup complete. Goodbye."