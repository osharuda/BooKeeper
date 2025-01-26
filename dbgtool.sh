#!/bin/bash
SCRIPT_PATH=$(dirname "$(realpath $0)")
pushd $SCRIPT_PATH > /dev/null
./.venv/bin/python dbg_tool.py "${1}" "${2}"
popd > /dev/null

