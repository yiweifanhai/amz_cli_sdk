#!/usr/bin/env python3
"""Install and update the amz CLI from this distribution repository.

This module intentionally uses only the Python standard library.  The shell
bootstrap scripts provide a uv-managed Python, so users do not need to have
Python installed before running the installer.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterator


BUNDLE_DIR_NAME = "amz-cli-v1"
DEFAULT_INTERVAL_HOURS = 24.0
FAILED_RETRY_HOURS = 1.0
LOCK_STALE_SECONDS = 10 * 60
VERSION_RE = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ManagerError(RuntimeError):
    """An expected install or update failure."""


def log(message: str, *, quiet: bool = False, error: bool = False) -> None:
    if quiet and not error:
        return
    print(message, file=sys.stderr)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=True,
            text=True,
            capture_output=capture,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ManagerError(f"command timed out after {timeout}s: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise ManagerError(f"command failed ({exc.returncode}): {command[0]}{suffix}") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def install_root() -> Path:
    override = os.environ.get("AMZ_CLI_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".local" / "share" / "amz-cli").resolve()


def user_bin_dir() -> Path:
    override = os.environ.get("AMZ_CLI_BIN_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".local" / "bin").resolve()


def state_path(root: Path | None = None) -> Path:
    return (root or install_root()) / "state.json"


def load_state(root: Path | None = None) -> dict:
    path = state_path(root)
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(data: dict, root: Path | None = None) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if os.name != "nt":
            os.chmod(temp, 0o600)
        os.replace(temp, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(bundle: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ManagerError(f"unsafe checksum path: {value}")
    path = (bundle / relative).resolve()
    try:
        path.relative_to(bundle.resolve())
    except ValueError as exc:
        raise ManagerError(f"checksum path escapes bundle: {value}") from exc
    return path


def verify_bundle(bundle: Path) -> dict:
    """Verify every listed file and the wheel metadata before installation."""
    bundle = bundle.resolve()
    manifest_path = bundle / "manifest.json"
    checksums_path = bundle / "CHECKSUMS.sha256"
    if not manifest_path.is_file() or not checksums_path.is_file():
        raise ManagerError(f"invalid bundle: {bundle}")

    checked = 0
    for line_number, raw_line in enumerate(
        checksums_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
        if not match:
            raise ManagerError(f"invalid checksum line {line_number}")
        expected, relative = match.groups()
        path = _safe_relative_path(bundle, relative)
        if not path.is_file():
            raise ManagerError(f"bundle file is missing: {relative}")
        actual = sha256(path)
        if actual.lower() != expected.lower():
            raise ManagerError(f"checksum mismatch: {relative}")
        checked += 1
    if checked == 0:
        raise ManagerError("checksum file is empty")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManagerError("manifest.json is invalid") from exc
    version = manifest.get("version")
    if not isinstance(version, str) or parse_version(version) is None:
        raise ManagerError("manifest version must use X.Y.Z")
    wheels = manifest.get("wheels")
    if not isinstance(wheels, list) or len(wheels) != 1:
        raise ManagerError("manifest must contain exactly one CLI wheel")
    wheel_info = wheels[0]
    wheel_name = wheel_info.get("file") if isinstance(wheel_info, dict) else None
    if not isinstance(wheel_name, str):
        raise ManagerError("manifest wheel name is missing")
    wheel_path = _safe_relative_path(bundle, f"wheels/{wheel_name}")
    if not wheel_path.is_file():
        raise ManagerError(f"wheel is missing: {wheel_name}")
    expected_wheel_sha = wheel_info.get("sha256")
    if not isinstance(expected_wheel_sha, str) or sha256(wheel_path) != expected_wheel_sha.lower():
        raise ManagerError(f"manifest wheel checksum mismatch: {wheel_name}")
    normalized_name = wheel_name.replace("-", "_")
    if f"_{version}_" not in normalized_name:
        raise ManagerError(f"wheel filename does not match manifest version: {wheel_name}")
    return manifest


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def version_text(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _tool_paths(root: Path) -> tuple[Path, Path, Path]:
    tool_dir = root / "tools"
    tool_bin = root / "tool-bin"
    if os.name == "nt":
        python = tool_dir / "amz-cli-sdk" / "Scripts" / "python.exe"
        executable = tool_bin / "amz.exe"
    else:
        python = tool_dir / "amz-cli-sdk" / "bin" / "python"
        executable = tool_bin / "amz"
    return tool_dir, python, executable


def _uv_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(root / "uv-cache")
    env["UV_PYTHON_INSTALL_BIN"] = "0"
    env["UV_PYTHON_INSTALL_DIR"] = str(root / "python")
    env["UV_TOOL_DIR"] = str(root / "tools")
    env["UV_TOOL_BIN_DIR"] = str(root / "tool-bin")
    return env


def _atomic_text(path: Path, content: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(content, encoding="utf-8", newline="")
        if executable and os.name != "nt":
            os.chmod(temp, 0o755)
        os.replace(temp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


def _write_wrappers(root: Path, repository: Path) -> tuple[Path, Path]:
    bin_dir = user_bin_dir()
    _, python, real_amz = _tool_paths(root)
    manager = repository / "manager.py"
    setup_app = repository / "setup_app.py"
    if os.name == "nt":
        amz_path = bin_dir / "amz.cmd"
        update_path = bin_dir / "amz-update.cmd"
        amz_content = (
            "@echo off\r\n"
            "if not \"%AMZ_CLI_SKIP_UPDATE%\"==\"1\" (\r\n"
            f'  "{python}" "{manager}" update --quiet 1>nul\r\n'
            ")\r\n"
            'if "%~1"=="setup" goto setup\r\n'
            f'"{real_amz}" %*\r\n'
            "exit /b %ERRORLEVEL%\r\n"
            ':setup\r\n'
            f'"{python}" "{setup_app}" --dispatch "{real_amz}" %*\r\n'
            "exit /b %ERRORLEVEL%\r\n"
        )
        update_content = (
            "@echo off\r\n"
            f'"{python}" "{manager}" update %*\r\n'
            "exit /b %ERRORLEVEL%\r\n"
        )
        _atomic_text(amz_path, amz_content)
        _atomic_text(update_path, update_content)
        # An older uv install can leave amz.exe in the public bin directory.
        old_executable = bin_dir / "amz.exe"
        with contextlib.suppress(FileNotFoundError):
            old_executable.unlink()
    else:
        amz_path = bin_dir / "amz"
        update_path = bin_dir / "amz-update"
        python_q = shlex.quote(str(python))
        manager_q = shlex.quote(str(manager))
        real_amz_q = shlex.quote(str(real_amz))
        amz_content = (
            "#!/bin/sh\n"
            'if [ "${AMZ_CLI_SKIP_UPDATE:-0}" != "1" ]; then\n'
            f"  {python_q} {manager_q} update --quiet >/dev/null || true\n"
            "fi\n"
            'if [ "${1:-}" = "setup" ]; then\n'
            f'  exec {python_q} {shlex.quote(str(setup_app))} --dispatch {real_amz_q} "$@"\n'
            'fi\n'
            f'exec {real_amz_q} "$@"\n'
        )
        update_content = (
            "#!/bin/sh\n"
            f'exec {python_q} {manager_q} update "$@"\n'
        )
        _atomic_text(amz_path, amz_content, executable=True)
        _atomic_text(update_path, update_content, executable=True)
    return amz_path, update_path


def _verify_installed_cli(executable: Path, manifest: dict) -> str:
    if not executable.is_file():
        raise ManagerError(f"installed command is missing: {executable}")
    result = run([str(executable), "version", "--json"], capture=True, timeout=60)
    try:
        info = json.loads(result.stdout)
        version = info["version"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ManagerError("installed CLI returned an invalid version") from exc
    if not isinstance(version, str):
        raise ManagerError("installed CLI returned an invalid version")
    capabilities = run([str(executable), "capabilities"], capture=True, timeout=120)
    match = re.search(r"Total:\s*(\d+)\s+capabilities", capabilities.stdout)
    actual_count = int(match.group(1)) if match else None
    expected_count = manifest.get("capability_count")
    if isinstance(expected_count, int) and actual_count != expected_count:
        raise ManagerError(
            f"capability check failed: expected {expected_count}, got {actual_count}"
        )
    return version


def install_bundle(
    bundle: Path,
    *,
    repository: Path,
    uv: str,
    quiet: bool = False,
) -> dict:
    """Install one verified bundle without reading or writing user configuration."""
    manifest = verify_bundle(bundle)
    root = install_root()
    root.mkdir(parents=True, exist_ok=True)
    wheel_name = manifest["wheels"][0]["file"]
    wheel = bundle / "wheels" / wheel_name
    env = _uv_environment(root)

    log(f"Installing amz-cli {manifest['version']}...", quiet=quiet)
    run([uv, "python", "install", "3.12"], env=env, timeout=600)
    run(
        [uv, "tool", "install", "--force", "--python", "3.12", f"{wheel}[full]"],
        env=env,
        timeout=900,
    )
    _, _, real_amz = _tool_paths(root)
    actual_version = _verify_installed_cli(real_amz, manifest)
    if actual_version != manifest["version"]:
        raise ManagerError(
            f"installed version mismatch: expected {manifest['version']}, got {actual_version}"
        )

    prior = load_state(root)
    now = int(time.time())
    state = {
        **prior,
        "auto_update": prior.get("auto_update", True),
        "installed_at": now,
        "interval_hours": prior.get("interval_hours", DEFAULT_INTERVAL_HOURS),
        "repo_path": str(repository.resolve()),
        "version": actual_version,
    }
    save_state(state, root)
    amz_path, update_path = _write_wrappers(root, repository.resolve())
    return {
        "installed": True,
        "version": actual_version,
        "command": str(amz_path),
        "update_command": str(update_path),
        "environment": str(root / "tools" / "amz-cli-sdk"),
        "config_preserved": [
            str(Path.home() / ".amz" / "config.yaml"),
            str(Path.home() / ".amz" / ".env"),
            str(Path.home() / ".sif_token"),
        ],
        "path_note": (
            f"add {user_bin_dir()} to PATH"
            if str(user_bin_dir()) not in os.environ.get("PATH", "").split(os.pathsep)
            else ""
        ),
    }


def _git(repository: Path, arguments: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if not git:
        raise ManagerError("git is required for automatic updates")
    return run([git, "-C", str(repository), *arguments], **kwargs)


def _latest_stable_tag(repository: Path) -> tuple[str, tuple[int, int, int]] | None:
    result = _git(repository, ["tag", "--list", "v*"], capture=True)
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for line in result.stdout.splitlines():
        tag = line.strip()
        version = parse_version(tag)
        if version is not None:
            candidates.append((version, tag))
    if not candidates:
        return None
    version, tag = max(candidates)
    return tag, version


def _tracked_tree_is_clean(repository: Path) -> bool:
    result = _git(
        repository,
        ["status", "--porcelain", "--untracked-files=no"],
        capture=True,
    )
    return not result.stdout.strip()


@contextlib.contextmanager
def update_lock(root: Path) -> Iterator[bool]:
    path = root / "update.lock"
    root.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            age = 0
        if age <= LOCK_STALE_SECONDS:
            yield False
            return
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            yield False
            return
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield True
    finally:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def _interval_hours(state: dict) -> float:
    override = os.environ.get("AMZ_CLI_UPDATE_INTERVAL_HOURS")
    value = override if override is not None else state.get("interval_hours", DEFAULT_INTERVAL_HOURS)
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_HOURS
    return max(0.0, hours)


def _auto_update_enabled(state: dict) -> bool:
    override = os.environ.get("AMZ_CLI_AUTO_UPDATE")
    if override is not None:
        return override.strip().lower() not in {"0", "false", "no", "off"}
    return bool(state.get("auto_update", True))


def _check_is_due(state: dict, *, now: int, force: bool) -> bool:
    if force:
        return True
    interval = int(_interval_hours(state) * 3600)
    last_checked = int(state.get("last_checked_at", 0) or 0)
    if now - last_checked < interval:
        return False
    last_attempt = int(state.get("last_attempt_at", 0) or 0)
    return now - last_attempt >= int(FAILED_RETRY_HOURS * 3600)


def _update_state(root: Path, **values: object) -> dict:
    state = load_state(root)
    state.update(values)
    save_state(state, root)
    return state


def update(*, uv: str, force: bool = False, quiet: bool = False) -> dict:
    root = install_root()
    state = load_state(root)
    if not _auto_update_enabled(state) and not force:
        return {"checked": False, "reason": "disabled", "version": state.get("version")}
    now = int(time.time())
    if not _check_is_due(state, now=now, force=force):
        return {"checked": False, "reason": "interval", "version": state.get("version")}

    with update_lock(root) as acquired:
        if not acquired:
            return {"checked": False, "reason": "locked", "version": state.get("version")}
        state = load_state(root)
        now = int(time.time())
        if not _check_is_due(state, now=now, force=force):
            return {"checked": False, "reason": "interval", "version": state.get("version")}
        _update_state(root, last_attempt_at=now)

        repository_value = state.get("repo_path")
        repository = Path(repository_value).expanduser().resolve() if repository_value else repo_root()
        if not (repository / ".git").exists():
            raise ManagerError("automatic update requires a persistent git clone of the release repository")
        if not _tracked_tree_is_clean(repository):
            raise ManagerError("release repository has local changes; automatic update was skipped")

        _git(repository, ["fetch", "--quiet", "--tags", "origin"], timeout=90)
        latest = _latest_stable_tag(repository)
        if latest is None:
            raise ManagerError("no stable vX.Y.Z release tag was found")
        tag, target_version = latest
        current_version = parse_version(str(state.get("version", "")))
        if current_version is not None and target_version <= current_version:
            _update_state(root, last_checked_at=now)
            return {
                "checked": True,
                "updated": False,
                "version": version_text(current_version),
                "latest": version_text(target_version),
            }

        old_commit = _git(repository, ["rev-parse", "HEAD"], capture=True).stdout.strip()
        target_commit = _git(
            repository, ["rev-list", "-n", "1", tag], capture=True
        ).stdout.strip()
        if not target_commit:
            raise ManagerError(f"release tag has no commit: {tag}")
        ancestry = subprocess.run(
            [
                shutil.which("git") or "git",
                "-C",
                str(repository),
                "merge-base",
                "--is-ancestor",
                old_commit,
                target_commit,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if ancestry.returncode != 0:
            raise ManagerError(f"release {tag} is not a fast-forward update")

        stage_parent = root / "staging"
        stage_parent.mkdir(parents=True, exist_ok=True)
        stage_path = Path(tempfile.mkdtemp(prefix="release-", dir=stage_parent))
        stage_path.rmdir()
        worktree_added = False
        try:
            _git(repository, ["worktree", "add", "--detach", "--force", str(stage_path), tag])
            worktree_added = True
            bundle = stage_path / BUNDLE_DIR_NAME
            manifest = verify_bundle(bundle)
            if manifest["version"] != version_text(target_version):
                raise ManagerError(
                    f"tag {tag} does not match manifest version {manifest['version']}"
                )
            try:
                result = install_bundle(
                    bundle,
                    repository=repository,
                    uv=uv,
                    quiet=quiet,
                )
            except Exception:
                # uv replaces one named tool environment. Reinstall the verified
                # old wheel if the new environment cannot pass its smoke tests.
                old_bundle = repository / BUNDLE_DIR_NAME
                with contextlib.suppress(Exception):
                    install_bundle(
                        old_bundle,
                        repository=repository,
                        uv=uv,
                        quiet=True,
                    )
                raise
            try:
                _git(repository, ["checkout", "--detach", "--force", tag])
            except ManagerError:
                # The old checkout and bundle are still intact. Restore the old CLI too.
                old_bundle = repository / BUNDLE_DIR_NAME
                with contextlib.suppress(Exception):
                    install_bundle(
                        old_bundle,
                        repository=repository,
                        uv=uv,
                        quiet=True,
                    )
                raise
            _update_state(
                root,
                last_checked_at=now,
                last_attempt_at=now,
                repo_path=str(repository),
                version=result["version"],
            )
            log(f"amz-cli updated to {result['version']}", quiet=quiet)
            return {
                "checked": True,
                "updated": True,
                "version": result["version"],
                "tag": tag,
            }
        finally:
            if worktree_added:
                with contextlib.suppress(Exception):
                    _git(repository, ["worktree", "remove", "--force", str(stage_path)])
            shutil.rmtree(stage_path, ignore_errors=True)


def find_uv(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return str(path.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise ManagerError(f"uv command was not found: {explicit}")
    found = shutil.which("uv")
    if not found:
        fallback = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
        if fallback.is_file():
            return str(fallback)
        raise ManagerError("uv is not installed; run install.sh or install.ps1")
    return found


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install_parser = subparsers.add_parser("install", help="install the bundled CLI")
    install_parser.add_argument("--uv", help="path to the uv command")
    install_parser.add_argument("--quiet", action="store_true")
    update_parser = subparsers.add_parser("update", help="check stable tags and update")
    update_parser.add_argument("--uv", help="path to the uv command")
    update_parser.add_argument("--force", action="store_true")
    update_parser.add_argument("--quiet", action="store_true")
    verify_parser = subparsers.add_parser("verify", help="verify the bundled release")
    verify_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify":
            manifest = verify_bundle(repo_root() / BUNDLE_DIR_NAME)
            if args.json:
                print(json.dumps({"valid": True, "version": manifest["version"]}))
            else:
                print(f"bundle verified: {manifest['version']}")
            return 0
        uv = find_uv(args.uv)
        if args.command == "install":
            result = install_bundle(
                repo_root() / BUNDLE_DIR_NAME,
                repository=repo_root(),
                uv=uv,
                quiet=args.quiet,
            )
        else:
            result = update(uv=uv, force=args.force, quiet=args.quiet)
        if not args.quiet:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ManagerError as exc:
        log(f"amz-cli manager: {exc}", error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
