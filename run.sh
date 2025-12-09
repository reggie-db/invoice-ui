#!/bin/bash
# Run the Invoice UI Reflex application

set -e

# Default port
PORT=${DATABRICKS_APP_PORT:-8000}

# Run with reflex
reflex run --port $PORT
