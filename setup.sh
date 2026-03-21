#!/bin/bash
# ============================================================
# setup.sh
# Description: Setup script to create venv, install dependencies,
#              create output folder, and run analysis scripts.
# ============================================================

# Exit immediately if a command exits with a non-zero status
set -e

# -------------------------------
# Step 1: Create a virtual environment
# -------------------------------
echo "[1/4] Creating virtual environment..."
python3 -m venv .venv --prompt MicroGreen

# Activate the virtual environment
source .venv/bin/activate

# -------------------------------
# Step 2: Install dependencies
# -------------------------------
echo "[2/4] Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt