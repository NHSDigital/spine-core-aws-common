#!/bin/bash
# mesh_implementation_lambdas_dependencies.sh

set -e
set -u
set -x
set -o pipefail

# deterministic dir
SCRIPT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
cd ${SCRIPT_DIR}

# Check for python3.8 and zip
which python
python -V | grep 3.8
which zip

# Create venv
python -m venv venv
source venv/bin/activate

# Install deps
python -m pip install --upgrade pip
python -m pip install \
  aws_lambda_powertools \
  mesh_client \
  requests \
  urllib3

# Create target dir
mkdir -p ../mesh_implementation_lambdas_dependencies/python
rm -rf ../mesh_implementation_lambdas_dependencies/python/*

# do this as we cannot cp a parent dir to sub dir
mkdir -p /tmp/spine_aws_common
cp -r ../../../spine_aws_common/* /tmp/spine_aws_common
mv /tmp/spine_aws_common ../mesh_implementation_lambdas_dependencies/python/spine_aws_common

# copy packages from venv
cp -r ./venv/lib/python3.8/site-packages/* ../mesh_implementation_lambdas_dependencies/python/

# This will then be zipped by terraform
exit 0
