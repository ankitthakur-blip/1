"""Command line interface: ``resolve-connect <command>``."""

from __future__ import annotations

import argparse
import json
import sys

from . import operations as ops
from .connection import REQUIRED_MAJOR_VERSION, ResolveConnectionError, connect, resolve_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resolve-connect", description="Control DaVinci Resolve 21 from the terminal.")
    parser.add_argument("--any-version", action="store_true", help="Skip the Resolve 21 version check.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("paths", help="Show the scripting API paths that will be used.")
    sub.add_parser("status", help="Show Resolve version, page, project and timeline.")
    sub.add_parser("projects", help="List projects in the current Project Manager folder.")
    p = sub.add_parser("open-project", help="Open a project by name.")
    p.add_argument("name")
    sub.add_parser("timelines", help="List timelines in the current project.")
    p = sub.add_parser("page", help="Switch Resolve page.")
    p.add_argument("page", choices=ops.PAGES)
    p = sub.add_parser("import", help="Import media files into the media pool.")
    p.add_argument("paths", nargs="+")
    p = sub.add_parser("marker", help="Add a marker to the current timeline.")
    p.add_argument("frame", type=int, help="Frame offset from the timeline start.")
    p.add_argument("name")
    p.add_argument("--note", default="")
    p.add_argument("--color", default="Blue", choices=ops.MARKER_COLORS)
    p.add_argument("--duration", type=int, default=1)
    sub.add_parser("presets", help="List render presets.")
    p = sub.add_parser("render", help="Queue and start a render of the current timeline.")
    p.add_argument("--preset")
    p.add_argument("--target-dir")
    p.add_argument("--name", dest="custom_name")
    p.add_argument("--wait", action="store_true", help="Block until rendering finishes.")
    return parser


def run(args: argparse.Namespace):
    if args.command == "paths":
        paths = resolve_paths()
        return {"RESOLVE_SCRIPT_API": str(paths.api), "RESOLVE_SCRIPT_LIB": str(paths.lib),
                "api_exists": paths.api.exists(), "lib_exists": paths.lib.exists()}

    resolve = connect(require_version=None if args.any_version else REQUIRED_MAJOR_VERSION)
    commands = {
        "status": lambda: ops.status(resolve),
        "projects": lambda: ops.list_projects(resolve),
        "open-project": lambda: ops.open_project(resolve, args.name),
        "timelines": lambda: ops.list_timelines(resolve),
        "page": lambda: ops.open_page(resolve, args.page),
        "import": lambda: ops.import_media(resolve, args.paths),
        "marker": lambda: ops.add_marker(resolve, args.frame, args.name, args.note, args.color, args.duration),
        "presets": lambda: ops.list_render_presets(resolve),
        "render": lambda: ops.render(resolve, args.preset, args.target_dir, args.custom_name, args.wait),
    }
    return commands[args.command]()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except (ResolveConnectionError, ops.ResolveOperationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
