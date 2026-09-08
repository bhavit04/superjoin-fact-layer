.PHONY: help install demo ingest serve test cases stats verify export-cases reset clean

VENV ?= .venv
PY   := $(VENV)/bin/python
STARTER := data_raw/starter-datasets

help:
	@echo "make install   create a venv and install the project"
	@echo "make demo      rebuild the knowledge layer from the committed cache (no API key)"
	@echo "make serve     run the API and UI on http://127.0.0.1:8000"
	@echo "make ingest    ingest the starter corpus using your configured provider"
	@echo "make test      run the test suite (no API key needed)"
	@echo "make cases     print the four required cases"
	@echo "make verify    check the submission is complete (exits non-zero if not)"
	@echo "make reset     delete the database"

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install -qU pip
	$(PY) -m pip install -q -e ".[dev]"
	@echo "installed. next: make demo"

# Replays the committed model responses: no API key, no network.
demo: reset
	FACTLAYER_PROVIDER=replay $(PY) -m factlayer.cli ingest $(STARTER)/*/*.pdf
	@echo
	@echo "knowledge layer rebuilt offline. now run: make serve"

ingest:
	$(PY) -m factlayer.cli ingest $(STARTER)/*/*.pdf

serve:
	$(PY) -m factlayer.cli serve

test:
	$(PY) -m pytest -q

cases:
	$(PY) -m factlayer.cli cases

stats:
	$(PY) -m factlayer.cli stats

export-cases:
	$(PY) scripts/export_cases.py

verify:
	$(PY) scripts/verify_submission.py

reset:
	@$(PY) -m factlayer.cli reset || true

clean: reset
	rm -rf .pytest_cache **/__pycache__ data/uploads/*
