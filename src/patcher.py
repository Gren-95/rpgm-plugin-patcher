"""
RPG Maker MV/MZ plugin patcher.

Finds plugins.js in the target game directory, copies any plugin files
from the plugins/ folder (next to this binary) into the game, and
registers each one in plugins.js.

Usage:
    patch_plugins [game_dir]

    game_dir  Path to the game root folder (default: current directory).
"""

import sys
import re
import shutil
import json
from pathlib import Path


PLUGINS_JS_CANDIDATES = [
    "www/js/plugins.js",
    "js/plugins.js",
    "plugins.js",
]


def find_plugins_js(game_dir: Path) -> Path | None:
    for candidate in PLUGINS_JS_CANDIDATES:
        p = game_dir / candidate
        if p.is_file():
            return p
    return None


def find_source_plugins_dir() -> Path:
    """
    Return the plugins/ folder that sits next to this executable/script.
    Works both when run as a PyInstaller binary and as a plain script.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller sets sys.executable to the binary path
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent  # src/ -> project root
    return base / "plugins"


def make_entry(name: str) -> dict:
    return {
        "name": name,
        "status": True,
        "description": "",
        "parameters": {},
    }


def is_registered(content: str, name: str) -> bool:
    return f'"name":"{name}"' in content


def inject_entry(content: str, entry_json: str) -> str:
    """
    Insert entry_json before the closing ]; of the $plugins array.
    Handles three cases:
      1. Empty array:  [ ] or [\n]
      2. Normal array: last entry ends with } then newline + ];
      3. Fallback:     file ends with ];
    """
    # Case 1: empty array
    if re.search(r"\[\s*\]", content):
        return re.sub(r"\[\s*\]", f"[\n{entry_json}\n]", content, count=1)

    # Case 2: insert after last } before ]; — use a callable replacement
    # to avoid re interpreting backslashes in entry_json
    pattern = r"(\})([ \t]*\n[ \t]*\];)"

    def replacement(m: re.Match) -> str:
        return m.group(1) + ",\n" + entry_json + m.group(2)

    new_content, n = re.subn(pattern, replacement, content, count=1)
    if n > 0:
        return new_content

    # Case 3: fallback — just find the last ]; in the file
    idx = content.rfind("];")
    if idx == -1:
        raise ValueError("Could not find the closing ]; in plugins.js")
    return content[:idx] + ",\n" + entry_json + "\n" + content[idx:]


def patch(game_dir: Path, source_plugins_dir: Path) -> None:
    # ── locate plugins.js ────────────────────────────────────────────────────
    plugins_js = find_plugins_js(game_dir)
    if plugins_js is None:
        print(
            "ERROR: Could not find plugins.js in any of:\n"
            + "\n".join(f"  {game_dir / c}" for c in PLUGINS_JS_CANDIDATES)
        )
        sys.exit(1)

    print(f"Found: {plugins_js}")
    target_plugin_dir = plugins_js.parent / "plugins"
    target_plugin_dir.mkdir(parents=True, exist_ok=True)

    # ── collect source .js plugin files ─────────────────────────────────────
    js_files = sorted(source_plugins_dir.glob("*.js"))
    if not js_files:
        print(f"ERROR: No .js files found in {source_plugins_dir}")
        sys.exit(1)

    print("Plugins to install:")
    for f in js_files:
        print(f"  - {f.stem}")

    # ── copy all plugin files (js + css + anything else) ────────────────────
    for src_file in sorted(source_plugins_dir.iterdir()):
        if not src_file.is_file():
            continue
        dest = target_plugin_dir / src_file.name
        if dest.exists():
            print(f"  Skipped (already exists): {src_file.name}")
        else:
            shutil.copy2(src_file, dest)
            print(f"  Copied: {src_file.name} -> {target_plugin_dir}/")

    # ── read plugins.js ──────────────────────────────────────────────────────
    content = plugins_js.read_text(encoding="utf-8")

    # ── backup ───────────────────────────────────────────────────────────────
    backup = plugins_js.with_suffix(".js.bak")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")
        print(f"Backup saved: {backup}")

    # ── inject each plugin ───────────────────────────────────────────────────
    changed = False
    for js_file in js_files:
        name = js_file.stem
        if is_registered(content, name):
            print(f"  Skipped (already registered): {name}")
            continue
        entry_json = json.dumps(make_entry(name), separators=(",", ":"))
        content = inject_entry(content, entry_json)
        print(f"  Registered: {name}")
        changed = True

    if changed:
        plugins_js.write_text(content, encoding="utf-8")

    print("Done.")


def main() -> None:
    game_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    if not game_dir.is_dir():
        print(f"ERROR: Not a directory: {game_dir}")
        sys.exit(1)

    source_plugins_dir = find_source_plugins_dir()
    if not source_plugins_dir.is_dir():
        print(f"ERROR: plugins/ folder not found at {source_plugins_dir}")
        sys.exit(1)

    patch(game_dir, source_plugins_dir)


if __name__ == "__main__":
    main()
