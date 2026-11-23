.PHONY: env-check gnpy-help install-arm64 test lint

PYTHON ?= python

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
	$(PYTHON) -m pytest

lint:
	ruff check .
	ruff format --check .
