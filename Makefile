# Puzzle Cracker - Makefile
#
# Front door for the puzzle-cracking harness: environment setup, data
# download (token-gated Kaggle API), solver runs, verification, and the
# "deploy as an agent" installer that scaffolds a separate working project
# and registers this repo as an agent in OpenCode / DeepSeek Harness /
# Claude Code / Cursor / pi.

SHELL := /bin/bash
PY     ?= python3
VENV   ?= .venv
PIP    := $(VENV)/bin/pip
PYBIN  := $(VENV)/bin/python

DATA_DIR ?= data
OUT_DIR  ?= outputs
REF      ?= santa-2023
METHOD   ?= auto
PUZZLE   ?=
LIMIT    ?=
BUDGET   ?= 30

.DEFAULT_GOAL := help

.PHONY: help setup venv data run demo verify scorecard install uninstall \
        clean tables

help:
	@echo "Puzzle Cracker targets:"
	@echo "  make setup       create venv, install deps, write Kaggle creds"
	@echo "  make data        download competition data (uses KAGGLE_KEY)"
	@echo "  make run         run the harness (REF, METHOD, PUZZLE, LIMIT)"
	@echo "  make data-all    download every CayleyPy competition reachable"
	@echo "  make run-all     harness over every locally-available comp"
	@echo "  make demo        end-to-end demo on random 3x3x3 scrambles"
	@echo "  make verify      correctness oracle (random scrambles solve)"
	@echo "  make scorecard   append today's scorecard to docs/scorecards/"
	@echo "  make install     deploy as an agent into a separate project"
	@echo "  make uninstall   remove what install added"
	@echo "  make clean       remove build artifacts"

setup: venv
	@$(PYBIN) -m puzzle_cracker.kaggle_client 2>/dev/null || true
	@echo "setup done. If you have a KAGGLE key, data-all:
	@mkdir -p $(DATA_DIR)
	KAGGLE_KEY=$${KAGGLE_KEY:?set KAGGLE_KEY (KGAT_...) first} \
	$(PYBIN) -c "from puzzle_cracker import competitions as c; \
	  ok=c.fetch_all('$(DATA_DIR)'); print('ready:', len(ok))"

run-all:
	@$(PYBIN) -m puzzle_cracker.harness --all --method $(METHOD) \
	  --data-dir $(DATA_DIR) --out-dir $(OUT_DIR) \
	  $(if $(LIMIT),--limit $(LIMIT)) --budget $(BUDGET)

run:"
	@echo "  export KAGGLE_KEY=KGAT_...  && make data"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e . || $(PIP) install -q .

data:
	@mkdir -p $(DATA_DIR)
	KAGGLE_KEY=$${KAGGLE_KEY:?set KAGGLE_KEY (KGAT_...) first} \
	$(PYBIN) -c \
	"import sys; sys.path.insert(0,'.'); from puzzle_cracker import kaggle_client as k; \
	 ok = [r for r in k.ensure_data('$(DATA_DIR)')]; print('ready:', ok)"

data-all:
	@mkdir -p $(DATA_DIR)
	KAGGLE_KEY=$${KAGGLE_KEY:?set KAGGLE_KEY (KGAT_...) first} \
	$(PYBIN) -c "from puzzle_cracker import competitions as c; \
	  ok=c.fetch_all('$(DATA_DIR)'); print('ready:', len(ok))"

run-all:
	@$(PYBIN) -m puzzle_cracker.harness --all --method $(METHOD) \
	  --data-dir $(DATA_DIR) --out-dir $(OUT_DIR) \
	  $(if $(LIMIT),--limit $(LIMIT)) --budget $(BUDGET)

run:
	@$(PYBIN) -m puzzle_cracker.harness --ref $(REF) --method $(METHOD) \
	  --data-dir $(DATA_DIR) --out-dir $(OUT_DIR) \
	  $(if $(PUZZLE),--puzzle $(PUZZLE)) $(if $(LIMIT),--limit $(LIMIT)) \
	  --budget $(BUDGET)

demo:
	@$(PYBIN) scripts/demo.py

verify:
	@$(PYBIN) scripts/verify.py

scorecard:
	@mkdir -p docs/scorecards
	@date +%Y%m%d > /tmp/pz-date
	@touch docs/scorecards/$(REF)-$$(cat /tmp/pz-date).md
	@echo "scorecard file: docs/scorecards/$(REF)-$$(cat /tmp/pz-date).md"

install:
	@bash deploy/install.sh

uninstall:
	@bash deploy/uninstall.sh

tables:
	@mkdir -p cache/tables
	@echo "staged-solver table cache lives in cache/tables/ (used when --table-dir set)"

clean:
	rm -rf $(VENV) build dist *.egg-info cache/tables
	@echo "cleaned"