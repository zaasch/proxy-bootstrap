#!/usr/bin/env bash

#
# ZaaS managed proxy bootstrap script v0.1.0
# This script can be used to bootstrap a new managed proxy instance.
#

# Set strict mode
set -euo pipefail

# Check if we are running in a VM
if [ -f /var/run/virtif ]; then
  echo "Running in a VM"
else
  echo "Not running in a VM"
fi
