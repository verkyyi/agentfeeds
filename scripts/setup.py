#!/usr/bin/env python3
"""Install the Agent Feeds runtime into a local virtual environment."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import venv
from pathlib import Path


DEFAULT_VENV = Path.home() / ".agentfeeds" / "runtime-venv"
# Keep in sync with pyproject.toml `requires-python`.
MIN_PYTHON = (3, 11)


def venv_python(path: Path) -> Path:
    if sys.platform == "win32":
        return path / "Scripts" / "python.exe"
    return path / "bin" / "python"


def python_version(executable: Path) -> tuple[int, int] | None:
    if not executable.exists():
        return None
    try:
        out = subprocess.run(
            [
                str(executable),
                "-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        major, minor = out.split(".")
        return (int(major), int(minor))
    except (subprocess.CalledProcessError, ValueError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install Agent Feeds skill runtime")
    parser.add_argument("--venv", type=Path, default=DEFAULT_VENV, help="runtime virtualenv path")
    parser.add_argument(
        "--python",
        default=None,
        help=(
            "Python interpreter spec passed to `uv venv --python` (e.g. 3.12, "
            "/usr/local/bin/python3.12). Defaults to the running interpreter when it "
            f"satisfies >={MIN_PYTHON[0]}.{MIN_PYTHON[1]}, otherwise uv provisions a "
            "compatible Python."
        ),
    )
    return parser


def create_venv(path: Path, python_override: str | None) -> None:
    existing = python_version(venv_python(path))
    if existing is not None and python_override is None and existing >= MIN_PYTHON:
        return
    if path.exists():
        shutil.rmtree(path)

    uv = shutil.which("uv")
    needed = f">={MIN_PYTHON[0]}.{MIN_PYTHON[1]}"

    if python_override is not None:
        if not uv:
            raise RuntimeError(
                "--python requires uv to provision the venv; install uv "
                "(https://docs.astral.sh/uv/)."
            )
        subprocess.run([uv, "venv", "--python", python_override, str(path)], check=True)
        return

    if sys.version_info[:2] >= MIN_PYTHON:
        venv.EnvBuilder(with_pip=True).create(path)
        return

    if not uv:
        raise RuntimeError(
            f"Agent Feeds requires Python {needed}, but {sys.executable} reports "
            f"{sys.version_info[0]}.{sys.version_info[1]}. Install uv "
            "(https://docs.astral.sh/uv/), pass --python <interpreter>, or run "
            "setup.py with a newer python3."
        )
    subprocess.run(
        [uv, "venv", "--python", f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}", str(path)],
        check=True,
    )


def install_runtime(python: Path, root: Path) -> None:
    has_pip = subprocess.run(
        [str(python), "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if has_pip:
        subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "-e", str(root)], check=True)
        return
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError(f"pip is unavailable in {python}; install pip or install uv")
    subprocess.run([uv, "pip", "install", "--python", str(python), "-e", str(root)], check=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    venv_path = args.venv.expanduser()
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    create_venv(venv_path, args.python)
    python = venv_python(venv_path)
    install_runtime(python, root)
    print(f"installed Agent Feeds runtime: {venv_path}")
    print(f"management CLI: {python} {root / 'scripts' / 'agentfeeds.py'}")
    print(f"refresh worker: {python} {root / 'scripts' / 'agentfeeds_fetch.py'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
