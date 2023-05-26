setup-venv:
	if [ ! -d venv/ ] ; then python3.8 -m venv venv ; fi
	. venv/bin/activate && pip install -r test-requirements.txt

build: setup-venv
	. venv/bin/activate && python -m build

test: setup-venv
	. venv/bin/activate && tox --recreate

install-python:
	sudo apt update
	sudo apt install software-properties-common
	sudo add-apt-repository ppa:deadsnakes/ppa
	sudo apt update
	sudo apt install python3.8 python3.8-dev python3.8-venv python3-venv