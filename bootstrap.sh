#!/usr/bin/env bash

# Install required packages
sudo apt install -y python3-requests python3-poetry git

# Clone full repository
git clone https://github.com/zaasch/proxy-bootstrap.git proxy-bootstrap

# Install python dependencies with poetry
cd proxy-bootstrap
poetry install

# Run the bootstrap script with poetry
poetry run python3 zaas_bootstrap.py
