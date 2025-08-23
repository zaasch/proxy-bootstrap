#!/usr/bin/env bash

#
# ZaaS managed proxy bootstrap script v0.1.0
# This script can be used to bootstrap a new managed proxy instance.
#

# Set strict mode
set -euo pipefail

# Non-interactive Debian frontend
DEBIAN_FRONTEND=noninteractive

# Configuration
LOGFILE="/var/log/zaas-bootstrap.log"
CONFIG_DIR="/etc/zaas"
CONFIG_FILE="$CONFIG_DIR/zaas.json"

# Check we are running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

# Logfile
touch "$LOGFILE"
chmod 600 "$LOGFILE"

# Function to log as JSON with a timestamp
log() {
    local message="$1"
    # Print the message in JSON format with a timestamp to the logfile
    echo "{\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"message\": \"$message\"}" >> "$LOGFILE"
    echo "$message"
}

# Installing dependencies
apt-get update
apt-get install -y uuid jq

# Check if the configuration folder exists, if not, create it
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    log "Created configuration directory: $CONFIG_DIR"
fi

# Check if we are running in a VM
HYPERVISOR=$(systemd-detect-virt)
VM=$(( $? == 0 ? 1 : 0 ))

# Handling case we are in a VM
if [ "$VM" -eq 1 ]; then

    # Inform the user about the VM environment
    log "We detected that we are running in a VM ($HYPERVISOR)."

    # Check if the configuration file already exists
    if [ ! -f "$CONFIG_FILE" ]; then
        
        # Inform user
        log "Configuration file not found."

        # Generate a new UUID serial number
        SN=$(uuid)
        log "Generated new serial number: $SN"

    else

        # Read the existing serial number from the configuration file
        SN=$(jq -r '.serial' "$CONFIG_FILE" 2>/dev/null || echo "")
        if [ -z "$SN" ]; then
            log "No serial number found in the configuration file, generating a new one."
            SN=$(uuid)
        else
            log "Found existing serial number: $SN"
        fi

    fi

    # Add the serial number to the configuration file using jq
    jq -n --arg serial "$SN" '{serial: $serial}' > "$CONFIG_FILE"

    # Inform the user about the configuration file update
    log "Updated configuration file: $CONFIG_FILE"

    # Now we need to ask the user to perform the manual registration of the serial number in ZaaS Manager
    echo "****************************"
    echo "Please register the following serial number in ZaaS Manager:"
    echo "$SN"
    echo "Press [Enter] when you are done."
    echo "****************************"
    read -r < /dev/tty

    # Ask for the JSON configuration produced by ZaaS Manager
    echo "****************************"
    echo "Please provide the JSON configuration produced by ZaaS Manager:"
    echo "****************************"
    read -r json_config < /dev/tty
    echo "$json_config" | jq . > "$CONFIG_FILE"
    log "Saved ZaaS Manager configuration to: $CONFIG_FILE"

else
    log "Not running in a VM"
fi
