#!/bin/bash
# build.sh

set -e
set -u
set -x
set -o pipefail

CODE_DIR="../build/splunk_formatter"
PYTHON_BIN="python3"

# Deterministic dir
SCRIPT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
cd ${SCRIPT_DIR}

# Check for python
which ${PYTHON_BIN}

# Create code dir
mkdir -p ${CODE_DIR}
rm -rf ${CODE_DIR}/*

# Copy code
cp -r ../../../../splunk_formatter/*.py ${CODE_DIR}/
cp -r ../../../../splunk_formatter/*.cfg ${CODE_DIR}/

# This will then be zipped by terraform
exit 0
