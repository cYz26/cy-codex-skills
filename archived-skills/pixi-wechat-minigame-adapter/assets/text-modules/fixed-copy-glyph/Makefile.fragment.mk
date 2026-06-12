.PHONY: copy-glyph-atlas

PYTHON ?= python3

copy-glyph-atlas:
	$(PYTHON) tools/build-copy-glyph-atlas.py
