SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV_DIR ?= .venv
UV ?= uv

define CHECK_PYTHON
import sys
v = sys.version_info
if not ((3, 8) <= (v.major, v.minor) <= (3, 13)):
	raise SystemExit(f"Unsupported Python {v.major}.{v.minor}. Use 3.8-3.13.")
endef
export CHECK_PYTHON

define CONVERT_TO_MODULE
import os, sys
path = sys.argv[1]
path = os.path.normpath(path)
if path.endswith('.py'):
	path = path[:-3]
path = path.lstrip('./')
if path.startswith('src' + os.sep):
	path = path[4:]
print(path.replace(os.sep, '.'))
endef
export CONVERT_TO_MODULE

ENSURE_UV_VENV = if [[ ! -d "$(VENV_DIR)" ]]; then $(UV) venv "$(VENV_DIR)"; fi;

CMD_TARGETS := mem-profile py-profile run
ifneq ($(filter $(CMD_TARGETS),$(MAKECMDGOALS)),)
FILE := $(word 2,$(MAKECMDGOALS))
$(eval $(FILE):;@:)
endif

.PHONY: init build serve mem-profile py-profile run web-install web-build test

init:
	set -euo pipefail; \
	$(PYTHON) -c "$$CHECK_PYTHON"; \
	$(ENSURE_UV_VENV) \
	$(UV) pip install -U pip; \
	$(UV) pip install -e ".[dev]"; \
	echo "Initialized uv venv at $(VENV_DIR)."
	$(MAKE) web-install

build:
	set -e; \
	$(ENSURE_UV_VENV) \
	$(UV) run mkdocs build; \
	$(MAKE) web-build; \
	$(UV) build

serve:
	set -e; \
	$(ENSURE_UV_VENV) \
	$(UV) run mkdocs build; \
	$(MAKE) web-build; \
	$(UV) run omfd

mem-profile:
	set -e; \
	$(ENSURE_UV_VENV) \
	if [[ -z "$(FILE)" ]]; then echo "Usage: make mem-profile path/to/script.py"; exit 1; fi; \
	module=$$($(UV) run python -c "$$CONVERT_TO_MODULE" "$(FILE)"); \
	$(UV) run heaptrack python -m $$module

py-profile:
	set -e; \
	$(ENSURE_UV_VENV) \
	if [[ -z "$(FILE)" ]]; then echo "Usage: make py-profile path/to/script.py"; exit 1; fi; \
	module=$$($(UV) run python -c "$$CONVERT_TO_MODULE" "$(FILE)"); \
	$(UV) run python -m cProfile -o prof.prof -m $$module

run:
	set -e; \
	$(ENSURE_UV_VENV) \
	if [[ -z "$(FILE)" ]]; then echo "Usage: make run path/to/script.py"; exit 1; fi; \
	module=$$($(UV) run python -c "$$CONVERT_TO_MODULE" "$(FILE)"); \
	time $(UV) run python -m $$module

web-install:
	set -e; \
	npm --prefix src/openmfd/site install

web-build:
	set -e; \
	npm --prefix src/openmfd/site run build

test:
	set -e; \
	$(ENSURE_UV_VENV) \
	$(UV) run pytest -v