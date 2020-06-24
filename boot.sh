#! /bin/sh

if [ "$DEVCONTAINER" = "true" ]; then
    while sleep 1000; do :; done
fi

/opt/app/.venv/bin/python -u run.py
