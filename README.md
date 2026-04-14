# rpgm-plugin-patcher

Installs plugins into RPG Maker MV/MZ games on Linux without needing Wine or the original Windows patcher.

Finds `plugins.js` in the game directory, copies plugin files into the game's plugin folder, and registers each one — without touching anything already there.

## Usage

Drop `patch_plugins` and the `plugins/` folder into the game's root directory, then run:

```bash
./patch_plugins
```

Or point it at a game elsewhere:

```bash
./patch_plugins /path/to/game
```

It supports all common RPG Maker folder layouts:

| Layout | plugins.js location |
|--------|---------------------|
| Standard MV | `www/js/plugins.js` |
| Standard MZ | `js/plugins.js` |
| Flat | `plugins.js` |

### What it does

1. Locates `plugins.js` in the game directory
2. Copies all files from `plugins/` into the game's plugin folder
3. Registers each `.js` plugin in `plugins.js` (skips any already registered)
4. Creates a `plugins.js.bak` backup before making changes

Re-running is safe — already-registered plugins and already-copied files are skipped.

## Adding plugins

Drop any `.js` (and optional `.css`) files into `plugins/` and re-run. The patcher auto-discovers everything in that folder.

## Building from source

Requires Python 3.10+ and pip.

```bash
bash build.sh
```

Output binary: `dist/patch_plugins`

The build script installs [PyInstaller](https://pyinstaller.org) if it isn't already present.

## Project structure

```
src/patcher.py      source code
plugins/            plugin files to install
build.sh            build script
dist/               compiled binary + plugins/ (distribute these)
```
