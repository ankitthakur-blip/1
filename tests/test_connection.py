import sys
import types
from pathlib import Path

import pytest

from resolve_connect import connection, operations as ops
from resolve_connect.cli import main


class FakeTimeline:
    def __init__(self, name):
        self.name, self.markers = name, {}

    def GetName(self): return self.name
    def GetStartFrame(self): return 86400
    def GetEndFrame(self): return 87000
    def GetTrackCount(self, kind): return 2 if kind == "video" else 4

    def AddMarker(self, frame, color, name, note, duration):
        if frame in self.markers:
            return False
        self.markers[frame] = (color, name, note, duration)
        return True


class FakeProject:
    def __init__(self):
        self.timelines = [FakeTimeline("Main"), FakeTimeline("Alt")]

    def GetName(self): return "Demo"
    def GetCurrentTimeline(self): return self.timelines[0]
    def GetTimelineCount(self): return len(self.timelines)
    def GetTimelineByIndex(self, i): return self.timelines[i - 1]
    def GetRenderPresetList(self): return ["YouTube - 1080p"]


class FakeProjectManager:
    def __init__(self): self.project = FakeProject()
    def GetCurrentProject(self): return self.project
    def GetProjectListInCurrentFolder(self): return ["Demo", "Other"]


class FakeResolve:
    def __init__(self, version="21.0.0.12"):
        self.version, self.pm, self.page = version, FakeProjectManager(), "edit"

    def GetVersionString(self): return self.version
    def GetProductName(self): return "DaVinci Resolve Studio"
    def GetCurrentPage(self): return self.page
    def GetProjectManager(self): return self.pm

    def OpenPage(self, page):
        self.page = page
        return True


@pytest.fixture
def fake_dvr(monkeypatch, tmp_path):
    state = {"resolve": FakeResolve()}
    module = types.ModuleType("DaVinciResolveScript")
    module.scriptapp = lambda name: state["resolve"] if name == "Resolve" else None
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", module)
    monkeypatch.setenv("RESOLVE_SCRIPT_API", str(tmp_path / "api"))
    monkeypatch.setenv("RESOLVE_SCRIPT_LIB", str(tmp_path / "fusionscript.so"))
    return state


@pytest.mark.parametrize("platform, api_part, lib_name", [
    ("darwin", "Developer/Scripting", "fusionscript.so"),
    ("linux", "/opt/resolve/Developer/Scripting", "fusionscript.so"),
    ("win32", "Support", "fusionscript.dll"),
])
def test_default_paths(platform, api_part, lib_name):
    paths = connection.default_paths(platform, env={})
    assert api_part.replace("/", "") in str(paths.api).replace("/", "").replace("\\", "")
    assert paths.lib.name == lib_name


def test_env_overrides_defaults():
    paths = connection.resolve_paths(env={"RESOLVE_SCRIPT_API": "/x/api", "RESOLVE_SCRIPT_LIB": "/x/lib.so"}, platform="linux")
    assert paths.api == Path("/x/api") and paths.modules == Path("/x/api/Modules")
    assert paths.lib == Path("/x/lib.so")


def test_connect_resolve_21(fake_dvr):
    resolve = connection.connect()
    assert resolve.GetVersionString().startswith("21")


def test_connect_rejects_other_version(fake_dvr):
    fake_dvr["resolve"] = FakeResolve("20.2.1")
    with pytest.raises(connection.ResolveConnectionError, match="version 21 is required"):
        connection.connect()
    assert connection.connect(require_version=None) is fake_dvr["resolve"]


def test_connect_when_resolve_not_running(fake_dvr):
    fake_dvr["resolve"] = None
    with pytest.raises(connection.ResolveConnectionError, match="External scripting"):
        connection.connect()


def test_connect_without_scripting_module(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", None)
    with pytest.raises(connection.ResolveConnectionError, match="Could not import"):
        connection.connect(paths=connection.ScriptingPaths(tmp_path, tmp_path / "lib.so"))


def test_operations(fake_dvr):
    resolve = connection.connect()
    assert ops.status(resolve)["timeline"] == "Main"
    assert ops.list_projects(resolve) == ["Demo", "Other"]
    assert [t["name"] for t in ops.list_timelines(resolve)] == ["Main", "Alt"]
    assert ops.open_page(resolve, "Color") == "color"
    with pytest.raises(ops.ResolveOperationError):
        ops.open_page(resolve, "photo")
    assert ops.add_marker(resolve, 24, "Cut here", color="red")["color"] == "Red"
    with pytest.raises(ops.ResolveOperationError, match="already exist"):
        ops.add_marker(resolve, 24, "Again")


def test_cli_status(fake_dvr, capsys):
    assert main(["status"]) == 0
    assert '"version": "21.0.0.12"' in capsys.readouterr().out


def test_cli_reports_errors(fake_dvr, capsys):
    fake_dvr["resolve"] = FakeResolve("19.1")
    assert main(["status"]) == 1
    assert "version 21 is required" in capsys.readouterr().err
    assert main(["--any-version", "status"]) == 0


def test_mcp_server_registers_tools(fake_dvr):
    import asyncio
    pytest.importorskip("mcp")
    from resolve_connect import mcp_server

    names = {tool.name for tool in asyncio.run(mcp_server.server.list_tools())}
    assert {"resolve_status", "list_timelines", "add_marker", "render"} <= names
    mcp_server._resolve = None
    assert mcp_server.resolve_status()["project"] == "Demo"
