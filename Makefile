PYTHON ?= python
REPRODUCE_SMALL_OUTPUT ?= outputs/reproduce-small

.PHONY: reproduce-small
reproduce-small:
	$(PYTHON) scripts/reproduce_small.py --output-dir $(REPRODUCE_SMALL_OUTPUT)
