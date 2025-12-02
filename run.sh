#!/bin/bash
set -e

# Function to find uv in common locations
find_uv() {
    # Check if uv is already in PATH
    if command -v uv &> /dev/null; then
        return 0
    fi
    
    # Check common installation locations
    local uv_paths=(
        "$HOME/.local/bin/uv"
        "$HOME/.cargo/bin/uv"
        "/home/app/.local/bin/uv"
        "/usr/local/bin/uv"
    )
    
    for path in "${uv_paths[@]}"; do
        if [ -f "$path" ]; then
            export PATH="$(dirname "$path"):$PATH"
            return 0
        fi
    done
    
    return 1
}

# Install uv if not already installed
if ! find_uv; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the env file if it exists (uv installer creates this)
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    elif [ -f "/home/app/.local/bin/env" ]; then
        source "/home/app/.local/bin/env"
    fi
    
    # Try to find uv again after installation
    if ! find_uv; then
        # Add common paths to PATH
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/home/app/.local/bin:$PATH"
    fi
    
    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo "Error: Failed to install uv or uv not found in PATH" >&2
        echo "PATH: $PATH" >&2
        exit 1
    fi
fi

# Run the command with all passed arguments
exec uv run invoice_ui "$@"

