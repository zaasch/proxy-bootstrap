#!/usr/bin/env bash

# Install required packages
echo -n "Installing required packages..."
sudo apt install -y python3-venv > /dev/null 2>&1
echo " done."

# Clone full repository
echo -n "Cloning repository..."
sudo rm -rf proxy-bootstrap > /dev/null 2>&1
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
sudo ./.venv/bin/python3 bootstrap.py

# Run the register process
sudo ./.venv/bin/python3 register.py
