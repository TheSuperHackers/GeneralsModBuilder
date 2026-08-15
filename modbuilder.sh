#!/bin/sh
# Runs the Generals Mod Builder, installing everything it needs on first use.
#
# This requires nothing on the machine but this script. It installs uv if it is
# missing, and uv then downloads a suitable Python and the locked dependencies
# into a virtual environment next to this script. Later runs reuse both.
#
# All arguments are forwarded to the mod builder, for example:
#   ./modbuilder.sh --build --install --config-list MyMod.json

set -e

ThisDir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
    export PATH
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Failed to install uv. See https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

exec uv run --project "$ThisDir" generalsmodbuilder "$@"
