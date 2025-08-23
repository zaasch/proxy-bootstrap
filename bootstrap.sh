#!/usr/bin/env bash

# Install required packages
sudo apt install -y python3-venv

# Clone full repository
rm -rf proxy-bootstrap
git clone https://github.com/zaasch/proxy-bootstrap.git proxy-bootstrap

# Create virtual environment
cd proxy-bootstrap
python3 -m venv .venv

# Install python dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run the bootstrap script
sudo ./.venv/bin/python3 zaas_bootstrap.py
