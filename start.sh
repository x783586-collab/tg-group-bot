#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "先运行： bash install.sh"
  exit 1
fi
. .venv/bin/activate
exec python bot.py
