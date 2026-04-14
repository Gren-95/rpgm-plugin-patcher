"""
RPG Maker MV/MZ plugin patcher.

Finds plugins.js in the target game directory, copies any plugin files
from the plugins/ folder (next to this binary) into the game, and
registers each one in plugins.js.
"""

import sys
import re
import shutil
import json
import argparse
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
    if re.search(r"\[\s*\]", content):
        return re.sub(r"\[\s*\]", f"[\n{entry_json}\n]", content, count=1)

    pattern = r"(\})([ \t]*\n[ \t]*\];)"

    def replacement(m: re.Match) -> str:
        return m.group(1) + ",\n" + entry_json + m.group(2)

    new_content, n = re.subn(pattern, replacement, content, count=1)
    if n > 0:
        return new_content

    idx = content.rfind("];")
    if idx == -1:
        raise ValueError("Could not find the closing ]; in plugins.js")
    return content[:idx] + ",\n" + entry_json + "\n" + content[idx:]


def remove_entry(content: str, name: str) -> str:
    """
    Remove a plugin entry from the $plugins array.
    Handles entries with or without a trailing comma.
    """
    # Match the full entry line, including its trailing comma if present
    pattern = rf'[ \t]*\{{"name":"{re.escape(name)}"[^\n]*\}},?\n'
    new_content, n = re.subn(pattern, "", content)
    if n == 0:
        return content

    # Clean up a dangling comma left on the previous line if we removed
    # the last entry (previous line ends with ,  and next non-empty is ];)
    new_content = re.sub(r",(\s*\n\s*\];)", r"\1", new_content)
    return new_content


def patch(game_dir: Path, source_plugins_dir: Path, overwrite: bool) -> None:
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

    js_files = sorted(source_plugins_dir.glob("*.js"))
    if not js_files:
        print(f"ERROR: No .js files found in {source_plugins_dir}")
        sys.exit(1)

    print("Plugins to install:")
    for f in js_files:
        print(f"  - {f.stem}")

    for src_file in sorted(source_plugins_dir.iterdir()):
        if not src_file.is_file():
            continue
        dest = target_plugin_dir / src_file.name
        if dest.exists() and not overwrite:
            print(f"  Skipped (already exists): {src_file.name}")
        else:
            shutil.copy2(src_file, dest)
            print(f"  {'Overwrote' if dest.exists() else 'Copied'}: {src_file.name}")

    content = plugins_js.read_text(encoding="utf-8")

    backup = plugins_js.with_suffix(".js.bak")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")
        print(f"Backup saved: {backup}")

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


def uninstall(game_dir: Path, source_plugins_dir: Path) -> None:
    plugins_js = find_plugins_js(game_dir)
    if plugins_js is None:
        print(
            "ERROR: Could not find plugins.js in any of:\n"
            + "\n".join(f"  {game_dir / c}" for c in PLUGINS_JS_CANDIDATES)
        )
        sys.exit(1)

    print(f"Found: {plugins_js}")
    target_plugin_dir = plugins_js.parent / "plugins"

    js_files = sorted(source_plugins_dir.glob("*.js"))
    if not js_files:
        print(f"ERROR: No .js files found in {source_plugins_dir}")
        sys.exit(1)

    # Remove plugin files
    for src_file in sorted(source_plugins_dir.iterdir()):
        if not src_file.is_file():
            continue
        dest = target_plugin_dir / src_file.name
        if dest.exists():
            dest.unlink()
            print(f"  Removed: {dest}")
        else:
            print(f"  Skipped (not found): {src_file.name}")

    # Deregister from plugins.js
    content = plugins_js.read_text(encoding="utf-8")

    backup = plugins_js.with_suffix(".js.bak")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")
        print(f"Backup saved: {backup}")

    changed = False
    for js_file in js_files:
        name = js_file.stem
        if not is_registered(content, name):
            print(f"  Skipped (not registered): {name}")
            continue
        content = remove_entry(content, name)
        print(f"  Deregistered: {name}")
        changed = True

    if changed:
        plugins_js.write_text(content, encoding="utf-8")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="patch_plugins",
        description="Install or remove RPG Maker MV/MZ plugins.",
    )
    parser.add_argument(
        "game_dir",
        nargs="?",
        default=".",
        metavar="game_dir",
        help="path to the game root folder (default: current directory)",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="remove plugins from the game and deregister them from plugins.js",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite plugin files that already exist in the game",
    )

    args = parser.parse_args()
    game_dir = Path(args.game_dir)

    if not game_dir.is_dir():
        print(f"ERROR: Not a directory: {game_dir}")
        sys.exit(1)

    source_plugins_dir = find_source_plugins_dir()
    if not source_plugins_dir.is_dir():
        print(f"ERROR: plugins/ folder not found at {source_plugins_dir}")
        sys.exit(1)

    if args.uninstall:
        uninstall(game_dir, source_plugins_dir)
    else:
        patch(game_dir, source_plugins_dir, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
