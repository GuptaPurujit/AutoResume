#!/bin/bash
# Wrapper script for macOS — WeasyPrint requires Homebrew's pango/gobject libraries.
# On Linux this is not needed.

BREW_LIB="/opt/homebrew/lib"

if [[ "$(uname)" == "Darwin" ]] && [[ -d "$BREW_LIB" ]]; then
    export DYLD_LIBRARY_PATH="$BREW_LIB:${DYLD_LIBRARY_PATH:-}"
fi

exec uv run autoresume "$@"
