#!/usr/bin/env bash

# Make sure we are root
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root" 1>&2
  exit 1
fi

# Install required packages
echo -n "Installing required packages..."
apt install -y python3-venv > /dev/null 2>&1
echo " done."

# Clone full repository
echo -n "Cloning repository..."
rm -rf proxy-bootstrap > /dev/null 2>&1
git clone https://github.com/zaasch/proxy-bootstrap.git proxy-bootstrap > /dev/null 2>&1
echo " done."

# Create virtual environment
echo -n "Creating virtual environment..."
cd proxy-bootstrap
python3 -m venv .venv > /dev/null 2>&1
echo " done."

# Install python dependencies
echo -n "Installing python dependencies..."
source .venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
echo " done."

# Run the bootstrap process
./.venv/bin/python3 bootstrap.py

# Run the register process
./.venv/bin/python3 register.py

# Create the zaas user if it does not exist
if ! id -u zaas > /dev/null 2>&1; then
  useradd -m -U zaas
fi

# Run ansible-pull for the first time
chmod +x askpass.sh
GIT_ASKPASS=$(pwd)/askpass.sh \
GIT_TERMINAL_PROMPT=0 \
./.venv/bin/ansible-pull -U https://github.com/zaasch/managed-proxy.git -i localhost
