"""Locate DaVinci Resolve's scripting API and connect to a running Resolve 21."""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_MAJOR_VERSION = 21


class ResolveConnectionError(RuntimeError):
    """Raised when Resolve cannot be reached or is the wrong version."""


@dataclass(frozen=True)
class ScriptingPaths:
    api: Path  # RESOLVE_SCRIPT_API
    lib: Path  # RESOLVE_SCRIPT_LIB

    @property
    def modules(self) -> Path:
        return self.api / "Modules"


def default_paths(platform: str | None = None, env: dict[str, str] | None = None) -> ScriptingPaths:
    """Return the standard install locations Blackmagic documents for each OS."""
    platform = platform or sys.platform
    env = os.environ if env is None else env

    if platform.startswith("darwin"):
        return ScriptingPaths(
            api=Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"),
            lib=Path("/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"),
        )
    if platform.startswith("win"):
        program_data = env.get("PROGRAMDATA", r"C:\ProgramData")
        program_files = env.get("PROGRAMFILES", r"C:\Program Files")
        return ScriptingPaths(
            api=Path(program_data) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting",
            lib=Path(program_files) / "Blackmagic Design" / "DaVinci Resolve" / "fusionscript.dll",
        )
    return ScriptingPaths(
        api=Path("/opt/resolve/Developer/Scripting"),
        lib=Path("/opt/resolve/libs/Fusion/fusionscript.so"),
    )


def resolve_paths(env: dict[str, str] | None = None, platform: str | None = None) -> ScriptingPaths:
    """Prefer RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB when set, else the OS defaults."""
    env = os.environ if env is None else env
    defaults = default_paths(platform, env)
    return ScriptingPaths(
        api=Path(env["RESOLVE_SCRIPT_API"]) if env.get("RESOLVE_SCRIPT_API") else defaults.api,
        lib=Path(env["RESOLVE_SCRIPT_LIB"]) if env.get("RESOLVE_SCRIPT_LIB") else defaults.lib,
    )


def configure_environment(paths: ScriptingPaths | None = None) -> ScriptingPaths:
    """Export the env vars and sys.path entry DaVinciResolveScript expects."""
    paths = paths or resolve_paths()
    os.environ["RESOLVE_SCRIPT_API"] = str(paths.api)
    os.environ["RESOLVE_SCRIPT_LIB"] = str(paths.lib)
    modules = str(paths.modules)
    if modules not in sys.path:
        sys.path.append(modules)
    return paths


def parse_major_version(version: str) -> int:
    try:
        return int(str(version).strip().split(".")[0])
    except ValueError as exc:
        raise ResolveConnectionError(f"Unrecognised Resolve version string: {version!r}") from exc


def connect(require_version: int | None = REQUIRED_MAJOR_VERSION, paths: ScriptingPaths | None = None):
    """Return the live ``Resolve`` scripting object.

    Resolve must already be running with
    Preferences > System > General > External scripting using = Local (or Network).
    """
    paths = configure_environment(paths)
    try:
        dvr = importlib.import_module("DaVinciResolveScript")
    except ImportError as exc:
        raise ResolveConnectionError(
            f"Could not import DaVinciResolveScript from {paths.modules}. "
            "Is DaVinci Resolve installed? Set RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB if it lives elsewhere."
        ) from exc

    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise ResolveConnectionError(
            "DaVinci Resolve is not reachable. Start Resolve and set "
            "Preferences > System > General > 'External scripting using' to Local."
        )

    if require_version is not None:
        version = resolve.GetVersionString()
        major = parse_major_version(version)
        if major != require_version:
            raise ResolveConnectionError(
                f"Connected to DaVinci Resolve {version}, but version {require_version} is required."
            )
    return resolve
