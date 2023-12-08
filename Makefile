setup-venv:
	if [ ! -d venv/ ] ; then python3.8 -m venv venv ; fi
	. venv/bin/activate && pip install -r test-requirements.txt

build: setup-venv
	. venv/bin/activate && python -m build

test: setup-venv
	. venv/bin/activate && tox --recreate

black:
	. venv/bin/activate && black .

isort:
	. venv/bin/activate && isort .
