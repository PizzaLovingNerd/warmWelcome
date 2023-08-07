#!/bin/bash

TRIES=0

mkdir -p ~/.local/share/risiWelcome
touch ~/.local/share/risiWelcome/root_requested

while [ $TRIES -lt 3 ]; do
    rm ~/.local/share/risiWelcome/root_requested
    pkexec bash "$@"
    if [ $? -ne 126 ]; then
        exit $?
    fi
    TRIES=$((TRIES+1))
done

echo "pkexec failed after 3 attempts"
exit 126