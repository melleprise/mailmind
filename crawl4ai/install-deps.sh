#!/bin/bash
set -e

# Node-Module initialisieren
if [ ! -d node_modules ]; then
  npm init -y
fi

npm install playwright 