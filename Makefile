dev:
	pip install --upgrade pip pre-commit poetry==1.1.4
	poetry install --extras "pydantic"
	pre-commit install
	
format:
	poetry run isort aws_ tests
	poetry run black spine_aws_lambda tests

lint: format
	poetry run flake8 spine_aws_lambda/* tests/*

test:
	poetry run pytest -m "not perf" --cov=spine_aws_lambda --cov-report=xml
	poetry run pytest --cache-clear tests/performance