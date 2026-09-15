from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


OUTPUT_DIR = Path(__file__).resolve().parents[1]
BUNDLE_DIR = OUTPUT_DIR / "amz-cli-v1"
MANAGER_PATH = OUTPUT_DIR / "manager.py"

SPEC = importlib.util.spec_from_file_location("amz_release_manager", MANAGER_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup guard
    raise RuntimeError(f"cannot load manager module from {MANAGER_PATH}")
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


GIT = shutil.which("git")


def run_git(repository: Path, *arguments: str) -> str:
    if GIT is None:  # pragma: no cover - guarded by skipUnless
        raise RuntimeError("git is required for this test")
    result = subprocess.run(
        [GIT, "-C", str(repository), *arguments],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def init_git_repository(parent: Path) -> tuple[Path, Path]:
    if GIT is None:  # pragma: no cover - guarded by skipUnless
        raise RuntimeError("git is required for this test")
    repository = parent / "release"
    remote = parent / "remote.git"
    subprocess.run(
        [GIT, "init", "--bare", str(remote)],
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        [GIT, "init", str(repository)],
        check=True,
        text=True,
        capture_output=True,
    )
    run_git(repository, "config", "user.name", "Release Test")
    run_git(repository, "config", "user.email", "release-test@example.invalid")
    run_git(repository, "remote", "add", "origin", str(remote))
    return repository, remote


def commit_release(repository: Path, version: str) -> str:
    bundle = repository / manager.BUNDLE_DIR_NAME
    bundle.mkdir(exist_ok=True)
    (bundle / "VERSION").write_text(version + "\n", encoding="utf-8")
    run_git(repository, "add", manager.BUNDLE_DIR_NAME)
    run_git(repository, "commit", "-m", f"release {version}")
    return run_git(repository, "rev-parse", "HEAD")


class SemVerTests(unittest.TestCase):
    def test_parse_version_accepts_stable_versions(self) -> None:
        cases = {
            "0.0.0": (0, 0, 0),
            "1.2.3": (1, 2, 3),
            "v10.20.300": (10, 20, 300),
            "  v2.0.1  ": (2, 0, 1),
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(manager.parse_version(value), expected)

    def test_parse_version_rejects_non_release_versions(self) -> None:
        invalid = (
            "",
            "1",
            "1.2",
            "1.2.3.4",
            "V1.2.3",
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2.3-alpha",
            "1.2.3+build",
            "-1.2.3",
        )

        for value in invalid:
            with self.subTest(value=value):
                self.assertIsNone(manager.parse_version(value))

    def test_version_text_is_canonical(self) -> None:
        self.assertEqual(manager.version_text((12, 0, 45)), "12.0.45")


class UpdatePolicyTests(unittest.TestCase):
    def test_update_is_skipped_when_auto_update_is_disabled(self) -> None:
        state = {"auto_update": True, "version": "1.2.3"}

        with (
            mock.patch.dict(os.environ, {"AMZ_CLI_AUTO_UPDATE": "off"}, clear=False),
            mock.patch.object(manager, "install_root", return_value=Path("/unused")),
            mock.patch.object(manager, "load_state", return_value=state),
            mock.patch.object(manager, "_git") as git_mock,
        ):
            result = manager.update(uv="unused")

        self.assertEqual(
            result,
            {"checked": False, "reason": "disabled", "version": "1.2.3"},
        )
        git_mock.assert_not_called()

    def test_update_is_skipped_before_interval_expires(self) -> None:
        now = 1_000_000
        state = {
            "auto_update": True,
            "interval_hours": 24,
            "last_checked_at": now - 60,
            "last_attempt_at": 0,
            "version": "1.2.3",
        }

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(manager, "install_root", return_value=Path("/unused")),
            mock.patch.object(manager, "load_state", return_value=state),
            mock.patch.object(manager.time, "time", return_value=now),
            mock.patch.object(manager, "_git") as git_mock,
        ):
            result = manager.update(uv="unused")

        self.assertEqual(
            result,
            {"checked": False, "reason": "interval", "version": "1.2.3"},
        )
        git_mock.assert_not_called()

    def test_check_due_honors_interval_retry_delay_and_force(self) -> None:
        now = 1_000_000
        day = 24 * 60 * 60
        hour = 60 * 60

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(
                manager._check_is_due(
                    {"last_checked_at": now - day + 1}, now=now, force=False
                )
            )
            self.assertTrue(
                manager._check_is_due(
                    {"last_checked_at": now - day}, now=now, force=False
                )
            )
            self.assertFalse(
                manager._check_is_due(
                    {"last_checked_at": 0, "last_attempt_at": now - hour + 1},
                    now=now,
                    force=False,
                )
            )
            self.assertTrue(
                manager._check_is_due(
                    {"last_checked_at": now, "last_attempt_at": now},
                    now=now,
                    force=True,
                )
            )


@unittest.skipUnless(GIT, "git is required for updater integration tests")
class UpdateGitTests(unittest.TestCase):
    @staticmethod
    def _save_update_state(install_root: Path, repository: Path) -> None:
        manager.save_state(
            {
                "auto_update": True,
                "interval_hours": 24,
                "repo_path": str(repository.resolve()),
                "version": "1.0.0",
            },
            install_root,
        )

    @staticmethod
    def _fake_manifest(bundle: Path) -> dict[str, str]:
        version = (bundle / "VERSION").read_text(encoding="utf-8").strip()
        return {"version": version}

    def test_update_selects_highest_stable_tag_and_checks_it_out(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir).resolve()
            repository, _ = init_git_repository(temp)
            old_commit = commit_release(repository, "1.0.0")
            run_git(repository, "tag", "v1.0.0")
            commit_release(repository, "1.2.0")
            run_git(repository, "tag", "v1.2.0")
            target_commit = commit_release(repository, "1.10.0")
            run_git(repository, "tag", "v1.10.0")
            run_git(repository, "tag", "v99.0.0-rc1")
            run_git(repository, "tag", "v01.0.0")
            run_git(repository, "push", "--tags", "origin")
            run_git(repository, "checkout", "--detach", old_commit)

            install_root = temp / "install"
            self._save_update_state(install_root, repository)
            environment = {
                "AMZ_CLI_AUTO_UPDATE": "1",
                "AMZ_CLI_HOME": str(install_root),
            }

            with (
                mock.patch.dict(os.environ, environment, clear=False),
                mock.patch.object(
                    manager, "verify_bundle", side_effect=self._fake_manifest
                ) as verify_mock,
                mock.patch.object(
                    manager,
                    "install_bundle",
                    return_value={"version": "1.10.0"},
                ) as install_mock,
            ):
                result = manager.update(uv="fake-uv", force=True, quiet=True)

            self.assertEqual(
                result,
                {
                    "checked": True,
                    "updated": True,
                    "version": "1.10.0",
                    "tag": "v1.10.0",
                },
            )
            self.assertEqual(run_git(repository, "rev-parse", "HEAD"), target_commit)
            self.assertEqual(
                run_git(repository, "rev-parse", "v1.10.0^{commit}"), target_commit
            )
            verify_mock.assert_called_once()
            install_mock.assert_called_once()
            self.assertEqual(
                install_mock.call_args.kwargs,
                {
                    "repository": repository.resolve(),
                    "uv": "fake-uv",
                    "quiet": True,
                },
            )
            self.assertEqual(manager.load_state(install_root)["version"], "1.10.0")

    def test_update_failure_keeps_worktree_at_old_commit(self) -> None:
        cases = (
            ("non-fast-forward", True, "is not a fast-forward update"),
            ("install-validation", False, "installed CLI validation failed"),
        )

        for name, divergent, expected_error in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir).resolve()
                repository, _ = init_git_repository(temp)
                base_commit = commit_release(repository, "1.0.0")
                run_git(repository, "tag", "v1.0.0")
                commit_release(repository, "2.0.0")
                run_git(repository, "tag", "v2.0.0")

                if divergent:
                    run_git(repository, "checkout", "--detach", base_commit)
                    (repository / "local-release.txt").write_text(
                        "divergent release\n", encoding="utf-8"
                    )
                    run_git(repository, "add", "local-release.txt")
                    run_git(repository, "commit", "-m", "divergent local release")
                    old_commit = run_git(repository, "rev-parse", "HEAD")
                else:
                    old_commit = base_commit

                run_git(repository, "push", "--tags", "origin")
                run_git(repository, "checkout", "--detach", old_commit)
                install_root = temp / "install"
                self._save_update_state(install_root, repository)
                def fail_new_install(bundle: Path, **_: object) -> dict[str, str]:
                    if bundle == repository / manager.BUNDLE_DIR_NAME:
                        return {"version": "1.0.0"}
                    raise manager.ManagerError("installed CLI validation failed")

                install_effect = None if divergent else fail_new_install
                environment = {
                    "AMZ_CLI_AUTO_UPDATE": "1",
                    "AMZ_CLI_HOME": str(install_root),
                }

                with (
                    mock.patch.dict(os.environ, environment, clear=False),
                    mock.patch.object(
                        manager, "verify_bundle", side_effect=self._fake_manifest
                    ),
                    mock.patch.object(
                        manager, "install_bundle", side_effect=install_effect
                    ) as install_mock,
                ):
                    with self.assertRaisesRegex(
                        manager.ManagerError, expected_error
                    ):
                        manager.update(uv="fake-uv", force=True, quiet=True)

                self.assertEqual(
                    run_git(repository, "rev-parse", "HEAD"), old_commit
                )
                self.assertEqual(
                    (repository / manager.BUNDLE_DIR_NAME / "VERSION")
                    .read_text(encoding="utf-8")
                    .strip(),
                    "1.0.0",
                )
                self.assertEqual(run_git(repository, "status", "--porcelain"), "")
                if divergent:
                    install_mock.assert_not_called()
                else:
                    self.assertEqual(install_mock.call_count, 2)
                    self.assertEqual(
                        install_mock.call_args_list[1].args[0],
                        repository / manager.BUNDLE_DIR_NAME,
                    )


class BundleVerificationTests(unittest.TestCase):
    def test_real_release_bundle_is_valid(self) -> None:
        manifest = manager.verify_bundle(BUNDLE_DIR)

        self.assertEqual(manifest["bundle"], manager.BUNDLE_DIR_NAME)
        self.assertIsNotNone(manager.parse_version(manifest["version"]))
        self.assertEqual(len(manifest["wheels"]), 1)

    def test_tampered_bundle_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "bundle"
            shutil.copytree(BUNDLE_DIR, bundle)
            with (bundle / "README.md").open("ab") as handle:
                handle.write(b"\ntampered\n")

            with self.assertRaisesRegex(
                manager.ManagerError, r"checksum mismatch: README\.md"
            ):
                manager.verify_bundle(bundle)

    def test_tampered_checksum_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "bundle"
            shutil.copytree(BUNDLE_DIR, bundle)
            checksums = bundle / "CHECKSUMS.sha256"
            lines = checksums.read_text(encoding="utf-8").splitlines()
            first_hash, first_path = lines[0].split("  ", maxsplit=1)
            replacement = "0" if first_hash[0] != "0" else "1"
            lines[0] = replacement + first_hash[1:] + "  " + first_path
            checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(manager.ManagerError, "checksum mismatch"):
                manager.verify_bundle(bundle)


class InstallPreservesConfigTests(unittest.TestCase):
    def test_install_does_not_modify_existing_credentials(self) -> None:
        version = manager.verify_bundle(BUNDLE_DIR)["version"]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            home = temp / "home"
            config_dir = home / ".amz"
            config_dir.mkdir(parents=True)
            credentials = {
                config_dir / "config.yaml": b"region: us-east-1\napi_key: keep-me\n",
                config_dir / ".env": b"AMZ_API_KEY=keep-this-too\n",
                home / ".sif_token": b"existing-sif-token\n",
            }
            for path, content in credentials.items():
                path.write_bytes(content)
            snapshots = {
                path: (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
                for path in credentials
            }

            install_root = temp / "install"
            bin_dir = temp / "bin"
            environment = {
                "HOME": str(home),
                "AMZ_CLI_HOME": str(install_root),
                "AMZ_CLI_BIN_DIR": str(bin_dir),
            }
            command_paths = (bin_dir / "amz", bin_dir / "amz-update")
            completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")

            with (
                mock.patch.dict(os.environ, environment, clear=False),
                mock.patch.object(manager, "run", return_value=completed) as run_mock,
                mock.patch.object(
                    manager, "_verify_installed_cli", return_value=version
                ) as verify_mock,
                mock.patch.object(
                    manager, "_write_wrappers", return_value=command_paths
                ) as wrappers_mock,
            ):
                result = manager.install_bundle(
                    BUNDLE_DIR,
                    repository=OUTPUT_DIR,
                    uv="fake-uv",
                    quiet=True,
                )

            self.assertEqual(run_mock.call_count, 2)
            self.assertEqual(
                run_mock.call_args_list[0].args[0],
                ["fake-uv", "python", "install", "3.12"],
            )
            self.assertEqual(
                run_mock.call_args_list[1].args[0][:6],
                ["fake-uv", "tool", "install", "--force", "--python", "3.12"],
            )
            verify_mock.assert_called_once()
            wrappers_mock.assert_called_once_with(
                install_root.resolve(), OUTPUT_DIR.resolve()
            )
            self.assertEqual(result["version"], version)
            self.assertEqual(
                set(result["config_preserved"]),
                {str(path) for path in credentials},
            )

            for path, snapshot in snapshots.items():
                with self.subTest(path=path):
                    self.assertTrue(path.is_file())
                    self.assertEqual(
                        (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns),
                        snapshot,
                    )


if __name__ == "__main__":
    unittest.main()
