.PHONY: run test clean

run:
	python src/main.py examples/valid/movimento.homi

test:
	python -m pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
