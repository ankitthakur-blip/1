"""MCP server exposing DaVinci Resolve 21 to Claude and other MCP clients.

Run with ``resolve-connect-mcp`` (stdio transport).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import operations as ops
from .connection import connect

server = MCPServer("davinci-resolve")
_resolve = None


def _get_resolve():
    # Connect lazily so the server starts even if Resolve is launched later.
    global _resolve
    if _resolve is None:
        _resolve = connect()
    return _resolve


@server.tool()
def resolve_status() -> dict:
    """Resolve version, current page, open project and active timeline."""
    return ops.status(_get_resolve())


@server.tool()
def list_projects() -> list[str]:
    """Projects in the current Project Manager folder."""
    return ops.list_projects(_get_resolve())


@server.tool()
def open_project(name: str) -> str:
    """Open a project by name."""
    return ops.open_project(_get_resolve(), name)


@server.tool()
def list_timelines() -> list[dict]:
    """Timelines in the current project with frame range and track counts."""
    return ops.list_timelines(_get_resolve())


@server.tool()
def open_page(page: str) -> str:
    """Switch page: media, cut, edit, fusion, color, fairlight or deliver."""
    return ops.open_page(_get_resolve(), page)


@server.tool()
def import_media(paths: list[str]) -> list[str]:
    """Import files (absolute paths on the Resolve machine) into the media pool."""
    return ops.import_media(_get_resolve(), paths)


@server.tool()
def add_marker(frame: int, name: str, note: str = "", color: str = "Blue", duration: int = 1) -> dict:
    """Add a marker to the current timeline at a frame offset from its start."""
    return ops.add_marker(_get_resolve(), frame, name, note, color, duration)


@server.tool()
def list_render_presets() -> list[str]:
    """Render presets available in the current project."""
    return ops.list_render_presets(_get_resolve())


@server.tool()
def render(preset: str | None = None, target_dir: str | None = None, custom_name: str | None = None) -> dict:
    """Queue and start rendering the current timeline; returns the job id and status."""
    return ops.render(_get_resolve(), preset, target_dir, custom_name)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
