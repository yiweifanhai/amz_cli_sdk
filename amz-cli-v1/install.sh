#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

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
"$python_cmd" "$bundle_dir/install.py"
"$uv_cmd" tool update-shell >/dev/null 2>&1 || true

export PATH="$HOME/.local/bin:$PATH"
amz version --json
echo "amz is installed. Ask your Agent: 帮我配置 amz-cli"
echo "Restart the terminal if the command is not on PATH."
