SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV_DIR ?= .venv
UV ?= uv

define CHECK_PYTHON
import sys
v = sys.version_info
if not ((3, 8) <= (v.major, v.minor) <= (3, 14)):
	raise SystemExit(f"Unsupported Python {v.major}.{v.minor}. Use 3.8-3.14.")
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

.PHONY: init build serve mem-profile py-profile run web-install web-build test test-coverage clean

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
	$(PYTHON) utilities/generate_diff2html_identifiers.py; \
	$(ENSURE_UV_VENV) \
	$(UV) run mkdocs build; \
	$(MAKE) web-build; \
	$(UV) build


serve:
	set -e; \
	$(PYTHON) utilities/generate_diff2html_identifiers.py; \
	$(ENSURE_UV_VENV) \
	$(UV) run mkdocs build; \
	$(MAKE) web-build; \
	$(UV) run pymfcad

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
	npm --prefix src/pymfcad/site install

web-build:
	set -e; \
	npm --prefix src/pymfcad/site run build

test:
	set -e; \
	$(ENSURE_UV_VENV) \
	$(UV) run pytest -v
# 	$(UV) run pytest -v -m "fast"

test-coverage:
	set -e; \
	$(ENSURE_UV_VENV) \
# 	$(UV) run pytest -v --cov=pymfcad --cov-report=html -m "fast" \
 	$(UV) run pytest -v --cov=pymfcad --cov-report=html

clean:
	set -e; \
	rm -rf .pytest_cache .coverage htmlcov dist; \
	rm -rf src/pymfcad/site/dist src/pymfcad/site/docs; \
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +; \
	find . -type d -name "*_cache" -prune -exec rm -rf {} +; \
	find . -type f -name "*.pyc" -delete

.PHONY: release release-major release-minor release-patch

release-major: RELEASE_TYPE := major
release-minor: RELEASE_TYPE := minor
release-patch: RELEASE_TYPE := patch

release-major release-minor release-patch: release
	@:

release:
	set -euo pipefail; \
	if [[ -z "$(RELEASE_TYPE)" ]]; then \
		echo "Usage: make release-[major|minor|patch]"; \
		exit 1; \
	fi; \
	\
	DRY_RUN=$${DRY_RUN:-false}; \
	if [[ "$$DRY_RUN" == "true" ]]; then \
		echo "🔍 DRY RUN MODE - No commits or releases will be created"; \
	fi; \
	echo ""; \
	echo "Starting $(RELEASE_TYPE) release process..."; \
	\
	read -p "Is this a pre-release? (y/n) " -n 1 -r; \
	echo; \
	IS_PRERELEASE=false; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		IS_PRERELEASE=true; \
	fi; \
	\
	EDITOR=$${EDITOR:-$$(git config --global core.editor || echo nano)}; \
	NOTES_FILE=$$(mktemp); \
	trap "rm -f $$NOTES_FILE" EXIT; \
	\
	CURRENT_VERSION=$$(grep "^version" pyproject.toml | head -1 | sed 's/version = "//;s/"//'); \
	\
	if [[ "$$DRY_RUN" == "true" ]]; then \
		echo "📋 Would bump version: $(RELEASE_TYPE)"; \
		$(UV) version --bump $(RELEASE_TYPE); \
		NEW_VERSION=$$(grep "^version" pyproject.toml | head -1 | sed 's/version = "//;s/"//'); \
		git restore pyproject.toml uv.lock 2>/dev/null || git checkout pyproject.toml uv.lock 2>/dev/null || true; \
	else \
		echo "Bumping version: $(RELEASE_TYPE)"; \
		$(UV) version --bump $(RELEASE_TYPE); \
		NEW_VERSION=$$(grep "^version" pyproject.toml | head -1 | sed 's/version = "//;s/"//'); \
	fi; \
	\
	GIT_REMOTE=$$(git config --get remote.origin.url | sed 's|.*github.com[:/]\(.*\)/\(.*\)\.git|\1/\2|'); \
	COMPARE_URL="https://github.com/$$GIT_REMOTE/compare/v$$CURRENT_VERSION...v$$NEW_VERSION"; \
	RELEASE_DATE=$$(date +%Y-%m-%d); \
	\
	printf "## [$$CURRENT_VERSION -> $$NEW_VERSION]($$COMPARE_URL) ($$RELEASE_DATE)\n\n> Description\n\n### Upgrade Steps\n* [ACTION REQUIRED]\n* \n\n### Breaking Changes\n* \n* \n\n### New Features\n* \n* \n\n### Bug Fixes\n* \n* \n\n### Performance Improvements\n* \n* \n\n### Known Issues\n* \n* \n\n### Other Changes\n* \n* \n" > "$$NOTES_FILE"; \
	\
	echo "Opening editor to collect release notes. Save and exit to continue."; \
	sleep 2; \
	$$EDITOR "$$NOTES_FILE" || true; \
	\
	\
	RELEASE_NOTES=$$(cat "$$NOTES_FILE"); \
	if [[ -z "$$RELEASE_NOTES" ]]; then \
		echo "Error: No release notes provided."; \
		exit 1; \
	fi; \
	\
	echo "New version: $$NEW_VERSION"; \
	\
	if [[ "$$DRY_RUN" != "true" ]]; then \
		echo "Committing version bump..."; \
		git add pyproject.toml uv.lock; \
		git commit -m "chore: bump version to $$NEW_VERSION"; \
	else \
		echo "📋 Would commit: pyproject.toml and uv.lock"; \
	fi; \
	\
	echo "Running make clean..."; \
	$(MAKE) clean; \
	\
	echo "Running make build..."; \
	$(MAKE) build; \
	\
	RELEASE_TITLE="v$$NEW_VERSION"; \
	TAG="v$$NEW_VERSION"; \
	\
	if command -v gh &> /dev/null; then \
		echo ""; \
		echo "Release Summary:"; \
		echo "  Tag: $$TAG"; \
		echo "  Title: $$RELEASE_TITLE"; \
		echo "  Pre-release: $$IS_PRERELEASE"; \
		echo "  Binaries:"; \
		for binary in dist/*; do \
			if [[ -f "$$binary" ]]; then \
				echo "    - $$(basename $$binary)"; \
			fi; \
		done; \
		echo "  Notes:"; \
		echo "$$RELEASE_NOTES" | sed 's/^/    /'; \
		\
		RELEASE_FLAGS="--title '$$RELEASE_TITLE' --notes '$$RELEASE_NOTES'"; \
		if [[ "$$IS_PRERELEASE" == "true" ]]; then \
			RELEASE_FLAGS="$$RELEASE_FLAGS --prerelease"; \
		fi; \
		\
		if [[ "$$DRY_RUN" == "true" ]]; then \
			RELEASE_FLAGS="$$RELEASE_FLAGS --draft"; \
			echo ""; \
			echo "📋 Creating GitHub release (DRAFT)"; \
		else \
			echo ""; \
			echo "Creating GitHub release"; \
		fi; \
		\
		BINARY_FILES=""; \
		for binary in dist/*; do \
			if [[ -f "$$binary" ]]; then \
				BINARY_FILES="$$BINARY_FILES '$$binary'"; \
			fi; \
		done; \
		\
		eval "gh release create '$$TAG' $$RELEASE_FLAGS $$BINARY_FILES"; \
		\
		if [[ "$$DRY_RUN" == "true" ]]; then \
			echo "Draft release created. Reverting version changes..."; \
			git restore pyproject.toml uv.lock 2>/dev/null || git checkout pyproject.toml uv.lock 2>/dev/null || true; \
			echo "Release created successfully (as draft)!"; \
		else \
			echo "Release published successfully!"; \
		fi; \
	else \
		echo "WARNING: 'gh' CLI not found. Please create the GitHub release manually:"; \
		echo "  Tag: $$TAG"; \
		echo "  Title: $$RELEASE_TITLE"; \
		echo "  Release notes: See the release notes file"; \
		echo "  Binaries: dist/*"; \
	fi