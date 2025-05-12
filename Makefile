.PHONY: lint test ci coverage

lint:
	black . --target-version py311 && flake8 .

test:
	pytest tests

ci:
	coverage run --source=. -m pytest tests
	coverage report
	coverage xml

coverage:
	coverage run --source=. -m pytest tests
	coverage report
	coverage html
	coverage xml
	@echo "Open htmlcov/index.html to view the coverage report."
