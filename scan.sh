#!/bin/bash
SCRIPT_PATH=$(dirname "$(realpath $0)")
pushd $SCRIPT_PATH > /dev/null
./.venv/bin/python main.py "${1}"
popd > /dev/null

