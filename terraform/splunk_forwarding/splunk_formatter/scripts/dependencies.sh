#!/bin/bash
# dependencies.sh

set -e
set -u
set -x
set -o pipefail

DEPS_DIR="../build/splunk_formatter_dependencies/python"
PYTHON_BIN="python3"

# Deterministic dir
SCRIPT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
cd ${SCRIPT_DIR}

# Check for python
which ${PYTHON_BIN}

# Create deps dir
mkdir -p ${DEPS_DIR}
rm -rf ${DEPS_DIR}/*

# Install deps
${PYTHON_BIN} -m pip install --upgrade pip
${PYTHON_BIN} -m pip install \
  -r ../../../../splunk_formatter/requirements.txt \
  --target ${DEPS_DIR}

# Get the spine common library
cp -r ../../../../spine_aws_common ${DEPS_DIR}/

# This will then be zipped by terraform
exit 0
