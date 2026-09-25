# resolve-connect

Connects to **DaVinci Resolve 21** through Blackmagic's official Python scripting API (`DaVinciResolveScript`). It includes:

- a Python function: `resolve_connect.connect()`
- a CLI: `resolve-connect`
- an MCP server so Claude (Claude Code / Claude Desktop) can drive Resolve: `resolve-connect-mcp`

## 1. Enable scripting in Resolve 21

1. Open DaVinci Resolve 21.
2. Go to **Preferences → System → General → External scripting using** and set it to **Local**.
3. Restart Resolve, and keep it running while you use this tool.

> External scripting needs **DaVinci Resolve Studio**. In the free edition, scripts only run from inside Resolve (Workspace → Console / Scripts).

## 2. Install

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e '.[mcp]'
```

Use the same architecture as Resolve (64-bit Python 3.10+).

## 3. Check the connection

```bash
resolve-connect paths    # where the scripting API is expected
resolve-connect status   # {"product": "DaVinci Resolve Studio", "version": "21.x", ...}
```

The standard install paths are detected on each OS:

| OS | `RESOLVE_SCRIPT_API` | `RESOLVE_SCRIPT_LIB` |
|---|---|---|
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting` | `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so` |
| Windows | `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting` | `%PROGRAMFILES%\Blackmagic Design\DaVinci Resolve\fusionscript.dll` |
| Linux | `/opt/resolve/Developer/Scripting` | `/opt/resolve/libs/Fusion/fusionscript.so` |

If Resolve is installed somewhere else, export those two variables first. Connecting fails with a clear error when the running Resolve is not version 21. Pass `--any-version` to skip that check.

## CLI

```bash
resolve-connect projects
resolve-connect open-project "My Film"
resolve-connect timelines
resolve-connect page color
resolve-connect import /footage/a.mov /footage/b.mov
resolve-connect marker 240 "Fix colour" --color Red --note "shot 12"
resolve-connect presets
resolve-connect render --preset "YouTube - 1080p" --target-dir ~/Renders --name final --wait
```

## Use from Python

```python
from resolve_connect import connect

resolve = connect()              # raises ResolveConnectionError if Resolve 21 isn't reachable
project = resolve.GetProjectManager().GetCurrentProject()
print(project.GetName())
```

## Connect Claude via MCP

Claude Code:

```bash
claude mcp add davinci-resolve -- /absolute/path/to/.venv/bin/resolve-connect-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "davinci-resolve": {
      "command": "/absolute/path/to/.venv/bin/resolve-connect-mcp"
    }
  }
}
```

Tools: `resolve_status`, `list_projects`, `open_project`, `list_timelines`, `open_page`, `import_media`, `add_marker`, `list_render_presets`, `render`.

## Tests

```bash
pip install -e '.[dev,mcp]'
pytest
```

The tests use a fake `DaVinciResolveScript` module, so they run without Resolve installed.
