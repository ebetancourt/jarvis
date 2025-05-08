.PHONY: lint

lint:
	black . --target-version py311 && flake8 .
