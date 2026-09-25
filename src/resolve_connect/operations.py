"""High-level operations on a connected Resolve instance, shared by the CLI and MCP server."""

from __future__ import annotations

import time

PAGES = ("media", "cut", "edit", "fusion", "color", "fairlight", "deliver")
MARKER_COLORS = (
    "Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia",
    "Rose", "Lavender", "Sky", "Mint", "Lemon", "Sand", "Cocoa", "Cream",
)


class ResolveOperationError(RuntimeError):
    pass


def _current_project(resolve):
    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        raise ResolveOperationError("No project is open in DaVinci Resolve.")
    return project


def _current_timeline(resolve):
    timeline = _current_project(resolve).GetCurrentTimeline()
    if timeline is None:
        raise ResolveOperationError("The current project has no active timeline.")
    return timeline


def status(resolve) -> dict:
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    return {
        "product": resolve.GetProductName(),
        "version": resolve.GetVersionString(),
        "page": resolve.GetCurrentPage(),
        "project": project.GetName() if project else None,
        "timeline": timeline.GetName() if timeline else None,
    }


def list_projects(resolve) -> list[str]:
    return list(resolve.GetProjectManager().GetProjectListInCurrentFolder() or [])


def open_project(resolve, name: str) -> str:
    if not resolve.GetProjectManager().LoadProject(name):
        raise ResolveOperationError(f"Could not open project {name!r}.")
    return name


def list_timelines(resolve) -> list[dict]:
    project = _current_project(resolve)
    timelines = []
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        timelines.append({
            "index": index,
            "name": timeline.GetName(),
            "start_frame": timeline.GetStartFrame(),
            "end_frame": timeline.GetEndFrame(),
            "video_tracks": timeline.GetTrackCount("video"),
            "audio_tracks": timeline.GetTrackCount("audio"),
        })
    return timelines


def open_page(resolve, page: str) -> str:
    page = page.lower()
    if page not in PAGES:
        raise ResolveOperationError(f"Unknown page {page!r}. Choose one of: {', '.join(PAGES)}.")
    if not resolve.OpenPage(page):
        raise ResolveOperationError(f"Resolve refused to open the {page} page.")
    return page


def import_media(resolve, paths: list[str]) -> list[str]:
    media_pool = _current_project(resolve).GetMediaPool()
    items = media_pool.ImportMedia(list(paths)) or []
    if not items:
        raise ResolveOperationError("Resolve did not import any of the given files.")
    return [item.GetName() for item in items]


def add_marker(resolve, frame: int, name: str, note: str = "", color: str = "Blue", duration: int = 1) -> dict:
    color = color.capitalize()
    if color not in MARKER_COLORS:
        raise ResolveOperationError(f"Unknown marker color {color!r}. Choose one of: {', '.join(MARKER_COLORS)}.")
    timeline = _current_timeline(resolve)
    # AddMarker takes a frame offset from the timeline start.
    if not timeline.AddMarker(frame, color, name, note, duration):
        raise ResolveOperationError(f"Could not add marker at frame {frame} (one may already exist there).")
    return {"timeline": timeline.GetName(), "frame": frame, "name": name, "color": color}


def list_render_presets(resolve) -> list[str]:
    return list(_current_project(resolve).GetRenderPresetList() or [])


def render(resolve, preset: str | None = None, target_dir: str | None = None, custom_name: str | None = None,
           wait: bool = False, poll_seconds: float = 1.0) -> dict:
    project = _current_project(resolve)
    if preset and not project.LoadRenderPreset(preset):
        raise ResolveOperationError(f"Render preset {preset!r} not found.")
    settings = {}
    if target_dir:
        settings["TargetDir"] = target_dir
    if custom_name:
        settings["CustomName"] = custom_name
    if settings and not project.SetRenderSettings(settings):
        raise ResolveOperationError(f"Resolve rejected render settings {settings}.")

    job_id = project.AddRenderJob()
    if not job_id:
        raise ResolveOperationError("Resolve could not queue a render job for the current timeline.")
    if not project.StartRendering(job_id):
        raise ResolveOperationError(f"Render job {job_id} failed to start.")

    if wait:
        while project.IsRenderingInProgress():
            time.sleep(poll_seconds)
    return {"job_id": job_id, **(project.GetRenderJobStatus(job_id) or {})}
