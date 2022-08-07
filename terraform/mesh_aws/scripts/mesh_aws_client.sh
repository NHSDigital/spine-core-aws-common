#!/bin/bash
# mesh_aws_client.sh

set -e
set -u
set -x
set -o pipefail

CODE_DIR="../mesh_aws_client/mesh_aws_client"
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
cp -r ../../../mesh_aws_client/*.py ${CODE_DIR}/

# This will then be zipped by terraform
exit 0
