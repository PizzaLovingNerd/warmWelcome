#!/bin/bash

TRIES=0

while [ $TRIES -lt 3 ]; do
    pkexec bash "$@"
    if [ $? -ne 126 ]; then
        exit $?
    fi
    TRIES=$((TRIES+1))
done

echo "pkexec failed after 3 attempts"
exit 126