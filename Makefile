.PHONY: env-check gnpy-help install-arm64 test lint phase1 phase1-smoke

PYTHON ?= .venv/Scripts/python.exe

# Show the selected interpreter and installed GNPy package version.
env-check:
	$(PYTHON) --version
	$(PYTHON) -m pip show gnpy

# Verify that the documented GNPy transmission example entry point is installed.
gnpy-help:
	gnpy-transmission-example --help

# Build the pinned native YANG libraries before installing on Linux ARM64.
install-arm64:
	bash scripts/install_gnpy_arm64.sh

test:
	PYTHONPATH=src $(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

phase1:
	PYTHONPATH=src $(PYTHON) scripts/phase1_convert.py

phase1-smoke:
	PYTHONPATH=src $(PYTHON) scripts/phase1_smoke.py
