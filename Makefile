setup-venv:
	python3.8 -m venv venv
	. venv/bin/activate
	pip install -r test-requirements.txt

build:
	. venv/bin/activate && python -m build
