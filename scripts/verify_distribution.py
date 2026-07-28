"""Verify that built distributions contain the files needed for a release."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


class DistributionError(RuntimeError):
    """Raised when a built distribution is incomplete or ambiguous."""


def _single_match(dist_dir: Path, pattern: str, label: str) -> Path:
    matches = sorted(dist_dir.glob(pattern))
    if len(matches) != 1:
        raise DistributionError(
            f"expected exactly one {label} matching {pattern!r}, found {len(matches)}"
        )
    return matches[0]


def _wheel_members(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {
            PurePosixPath(name).as_posix() for name in archive.namelist() if not name.endswith("/")
        }


def _sdist_members(path: Path) -> set[str]:
    with tarfile.open(path, mode="r:gz") as archive:
        members = {PurePosixPath(member.name) for member in archive.getmembers() if member.isfile()}

    roots = {member.parts[0] for member in members if member.parts}
    if len(roots) != 1:
        raise DistributionError(f"expected one source distribution root, found {sorted(roots)}")

    return {
        PurePosixPath(*member.parts[1:]).as_posix() for member in members if len(member.parts) > 1
    }


def _require_members(members: set[str], required: set[str], archive_name: str) -> None:
    missing = sorted(required - members)
    if missing:
        formatted = "\n".join(f"- {member}" for member in missing)
        raise DistributionError(f"{archive_name} is missing required files:\n{formatted}")


def verify(dist_dir: Path) -> tuple[Path, Path]:
    """Verify one wheel and one source distribution in ``dist_dir``."""

    wheel = _single_match(dist_dir, "*.whl", "wheel")
    sdist = _single_match(dist_dir, "*.tar.gz", "source distribution")

    wheel_members = _wheel_members(wheel)
    _require_members(
        wheel_members,
        {"rag_observatory/__init__.py"},
        wheel.name,
    )
    if not any(member.endswith(".dist-info/METADATA") for member in wheel_members):
        raise DistributionError(f"{wheel.name} is missing dist-info/METADATA")
    if any(member.startswith("tests/") for member in wheel_members):
        raise DistributionError(f"{wheel.name} unexpectedly contains the test suite")

    sdist_members = _sdist_members(sdist)
    _require_members(
        sdist_members,
        {
            "CHANGELOG.md",
            "LICENSE",
            "README.md",
            "pyproject.toml",
            "tests/test_cli_report.py",
            "tests/fixtures/toy_runs/unsupported_answer.json",
            "examples/evals-as-code/synthetic_failure_eval/dataset.jsonl",
        },
        sdist.name,
    )
    return wheel, sdist


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dist_dir",
        nargs="?",
        type=Path,
        default=Path("dist"),
        help="directory containing exactly one wheel and one .tar.gz source distribution",
    )
    args = parser.parse_args()

    try:
        wheel, sdist = verify(args.dist_dir)
    except (DistributionError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.error(str(error))

    print(f"verified {wheel.name} and {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
