#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
run_setup=0
if [ "${1:-}" = "--setup" ]; then
    run_setup=1
    shift
fi
if [ "$#" -ne 0 ]; then
    echo "Usage: install.sh [--setup]" >&2
    exit 2
fi
install_root=${AMZ_CLI_HOME:-"$HOME/.local/share/amz-cli"}
public_bin=${AMZ_CLI_BIN_DIR:-"$HOME/.local/bin"}
export UV_CACHE_DIR="$install_root/uv-cache"
export UV_PYTHON_INSTALL_BIN=0
export UV_PYTHON_INSTALL_DIR="$install_root/python"

if command -v uv >/dev/null 2>&1; then
    uv_cmd=$(command -v uv)
elif [ -x "$HOME/.local/bin/uv" ]; then
    uv_cmd="$HOME/.local/bin/uv"
else
    echo "Installing uv..." >&2
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "curl or wget is required to bootstrap Python" >&2
        exit 1
    fi
    uv_cmd="$HOME/.local/bin/uv"
fi

"$uv_cmd" python install 3.12
python_cmd=$("$uv_cmd" python find 3.12)
"$python_cmd" "$repo_dir/manager.py" verify
"$python_cmd" "$repo_dir/manager.py" install --uv "$uv_cmd"

echo "amz-cli is installed. Existing files under ~/.amz were not changed."
echo "Restart the terminal if ~/.local/bin is not on PATH."

if [ "$run_setup" -eq 1 ]; then
    AMZ_CLI_SKIP_UPDATE=1 "$public_bin/amz" setup --web
fi
