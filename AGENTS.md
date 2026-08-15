# LazyProx Agent Instructions

## Project Overview
LazyProx is a Proxmox TUI (Terminal User Interface) tool for managing Proxmox infrastructure. It provides a clean UI for viewing and acting on nodes, containers, and virtual machines.

## Key Commands
- Run: `lazyprox` (in terminal)
- Install with uv: `uv tool install git+https://github.com/benzino77/lazyprox.git`
- Install with pipx: `pipx install git+https://github.com/benzino77/lazyprox.git`

## Architecture
- Written in Python 3.13+
- Uses Textual framework for TUI
- Uses Proxmoxer library for API communication
- Configuration via TOML file (default location: `$XDG_CONFIG_HOME/lazyprox/config.toml` or `~/.config/lazyprox/config.toml`)
- Entry point: `src/lazyprox/__init__.py`

## Configuration
The tool requires a configuration file with Proxmox server credentials. The config file should contain:
- Server name, host, user, realm, token_name, and token_value
- Optional application settings like refresh intervals

## Running Tests
No explicit test commands found in project files. Run with `pytest` if tests exist.

## Docker Usage
Build: `docker build -t lazyprox .`
Run: `docker run --name lazyprox -it --rm -v /path/to/config.toml:/config.toml ghcr.io/benzino77/lazyprox:latest -c /config.toml`

## Key Directories
- `src/lazyprox/` - Main application code
- `src/lazyprox/app/` - Application logic and main class
- `src/lazyprox/common/` - Common utilities and config handling
- `src/lazyprox/screens/` - UI screens
- `src/lazyprox/widgets/` - UI widgets

## Environment
- Requires Python 3.13+
- Uses uv for dependency management (install with `uv tool install`)