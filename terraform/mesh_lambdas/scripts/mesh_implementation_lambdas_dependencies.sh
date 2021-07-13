#!/bin/bash
# mesh_implementation_lambdas_dependencies.sh

set -e
set -u
set -x
set -o pipefail

# deterministic dir
SCRIPT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
cd ${SCRIPT_DIR}
DEPS_DIR="../mesh_implementation_lambdas_dependencies/python"
PYTHON_BIN="python3.8"

# Check for python and zip
which ${PYTHON_BIN}
which zip

# Create target dir
mkdir -p ${DEPS_DIR}
rm -rf ${DEPS_DIR}/*

# Install deps
# TODO is there a requirements.txt?
${PYTHON_BIN} -m pip install --upgrade pip
${PYTHON_BIN} -m pip download --dest ${DEPS_DIR} \
  aws_lambda_powertools \
  mesh_client \
  requests \
  urllib3

# get the spine common library
mkdir -p ${DEPS_DIR}/spine_aws_common
cp -r ../../../spine_aws_common/* ${DEPS_DIR}/spine_aws_common

# This will then be zipped by terraform
exit 0
