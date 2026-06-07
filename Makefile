.PHONY: all run test test-quiet check clean distclean

PYTHON := .venv/bin/python
MAIN   := src/main.py
TESTS  := tests/

all: test

# ── Compilação ──────────────────────────────────────────────────────
run:
	$(PYTHON) $(MAIN) examples/valid/movimento.homi

check:
	@echo "=== Valid ==="
	@for f in examples/valid/*.homi; do \
		$(PYTHON) $(MAIN) $$f > /dev/null 2>&1 \
			&& echo "  OK  $$f" \
			|| echo "  FAIL $$f"; \
	done
	@echo
	@echo "=== Invalid ==="
	@for f in examples/invalid/*.homi; do \
		$(PYTHON) $(MAIN) $$f > /dev/null 2>&1 \
			&& echo "  FAIL $$f (esperado exit 1)" \
			|| echo "  OK  $$f"; \
	done

# ── Testes ──────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest $(TESTS) -v

test-quiet:
	$(PYTHON) -m pytest $(TESTS) -q

# ── Limpeza ─────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

distclean: clean
	rm -rf .pytest_cache .venv
