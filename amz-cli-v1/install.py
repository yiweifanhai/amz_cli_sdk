#!/usr/bin/env python3
"""Install the bundled amz CLI into an isolated, versioned environment."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path


BUNDLE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"missing release manifest: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture,
    )


def find_sdk_wheel(wheel_dir: Path, version: str) -> Path:
    matches = sorted(wheel_dir.glob(f"amz_cli_sdk-{version}-*.whl"))
    if len(matches) != 1:
        raise SystemExit(
            f"expected one amz-cli-sdk {version} wheel in {wheel_dir}, found {len(matches)}"
        )
    return matches[0]


def install_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_link = destination.with_name(destination.name + ".new")
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    temp_link.symlink_to(source)
    temp_link.replace(destination)


def main() -> int:
    manifest = load_manifest()
    version = manifest["version"]

    default_target = (
        Path.home() / ".local" / "share" / "amz-cli" / version /
        f"py{sys.version_info.major}{sys.version_info.minor}"
    )
    parser = argparse.ArgumentParser(description="Install the bundled amz CLI")
    parser.add_argument(
        "--target",
        type=Path,
        default=default_target,
        help="versioned virtual environment path",
    )
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path.home() / ".local" / "bin",
        help="directory that receives the amz command",
    )
    parser.add_argument("--index-url", help="optional Python package index URL")
    args = parser.parse_args()

    if sys.version_info < (3, 11):
        raise SystemExit("amz-cli requires Python 3.11 or newer")

    wheel_dir = BUNDLE_DIR / "wheels"
    sdk_wheel = find_sdk_wheel(wheel_dir, version)
    target = args.target.expanduser().resolve()
    bin_dir = args.bin_dir.expanduser().resolve()

    target.parent.mkdir(parents=True, exist_ok=True)
    if not (target / "pyvenv.cfg").exists():
        venv.EnvBuilder(with_pip=True).create(target)

    if os.name == "nt":
        env_python = target / "Scripts" / "python.exe"
        env_amz = target / "Scripts" / "amz.exe"
    else:
        env_python = target / "bin" / "python"
        env_amz = target / "bin" / "amz"

    package_spec = f"{sdk_wheel}[full]"
    command = [str(env_python), "-m", "pip", "install", "--upgrade"]
    if args.index_url:
        command.extend(["--index-url", args.index_url])
    command.append(package_spec)

    try:
        run(command)
    except subprocess.CalledProcessError as exc:
        print("dependency download or installation failed", file=sys.stderr)
        return exc.returncode or 1

    if os.name == "nt":
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher = bin_dir / "amz.cmd"
        launcher.write_text(f'@"{env_amz}" %*\r\n', encoding="utf-8")
        command_path = launcher
    else:
        command_path = bin_dir / "amz"
        install_link(env_amz, command_path)

    version_result = run([str(env_amz), "version", "--json"], capture=True)
    caps_result = run([str(env_amz), "capabilities"], capture=True)
    count_match = re.search(r"Total:\s*(\d+)\s+capabilities", caps_result.stdout)
    count = int(count_match.group(1)) if count_match else None
    expected = manifest.get("capability_count")
    if expected is not None and count != expected:
        raise SystemExit(f"capability check failed: expected {expected}, got {count}")

    info = json.loads(version_result.stdout)
    print(json.dumps({
        "installed": True,
        "version": info["version"],
        "capabilities": count,
        "command": str(command_path),
        "environment": str(target),
        "path_note": f"add {bin_dir} to PATH" if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep) else "",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
