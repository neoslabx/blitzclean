# BlitzClean — Ubuntu Cleanup GUI

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**BlitzClean** is a fast, no-nonsense GUI utility to clean common caches, logs, and stale data on Ubuntu (and Debian-based) systems. It supports **dry-run previews**, **live streaming logs**, **optional aggressive cleanup**, and **root-aware** system tasks (journald vacuum, Snap/Flatpak pruning, old kernel removal, etc.).

* * *

## Features

- GUI-based cleanup — no terminal fiddling
- Lists and empties **Trash** for all users
- User-space cleanup (caches, histories, browser caches)
- System cleanup (tmp, logs, journal vacuum by **days**/**size**)
- Snap/Flatpak leftovers removal, optional old-kernel purge
- **Dry-Run** preview, **Stop** button, graceful process closing
- **Freed Space** live counter (top-right)
- Per-path toggles in **Preferences**
- Root-aware with `pkexec`, optional shutdown after run
- Config at `~/.config/blitzclean/config`

* * *

## Requirements

- Ubuntu 22.04+ (or Debian-based)
- Python **3.9+**
- Packages:

```bash
sudo apt update
sudo apt install -y python3-pyqt6 python3-pyqt6.qt6-tools trash-cli
```

* * *

## Installation

### Option A — Run from source (recommended for development)

```bash
git clone https://github.com/neoslab/blitzclean.git
cd blitzclean
chmod +x blitzclean.py
./blitzclean.py
```

> Tip: Use a venv if you prefer `pip install PyQt6` instead of system packages.

### Option B — System-wide install

```bash
sudo install -m 755 blitzclean.py /usr/local/bin/blitzclean
blitzclean
```

### Desktop launcher (optional)

1. Copy icon to system pixmaps (if you have one):

```bash
sudo install -m 644 assets/blitzclean.png /usr/share/pixmaps/blitzclean.png
```

2. Create a desktop entry:

```bash
cat <<'EOF' | sudo tee /usr/share/applications/blitzclean.desktop
[Desktop Entry]
Name=BlitzClean
Comment=Ubuntu Cleanup GUI
Exec=blitzclean
Icon=blitzclean
Terminal=false
Type=Application
Categories=System;Utility;
EOF
```

3. Find **BlitzClean** in your application menu.

### Root mode

System-wide cleanup needs root. Either:

* Start normally and select **root** in the app (it will invoke `pkexec`), or
* Launch via:

```bash
sudo blitzclean
```

* * *

## Usage

* **Dry-Run**: preview deletions
* **Run**: perform cleanup
* **Stop**: cancel safely

The table streams files as they’re discovered; the **Freed Space** counter updates live.

* * *

## Preferences

* **Vacuum days / size** (journald)
* **Keep Snap revisions**
* **Shutdown after cleanup**
* Per-path toggles for:

  * User caches/histories/patterns
  * System dirs (`/tmp`, `/var/tmp`, `/var/cache/*`)
  * Log & crash globs (`/var/log/*.[0-9]`, `/var/crash/*.crash`)
  * Root items (e.g., `/root/.cache`)
  * Aggressive paths (`.ssh`, `snap`) — **use with care**

* * *

## Safety

* Designed to be conservative; **Dry-Run** first
* Gracefully stops/ignores protected/system processes
* Trash is **listed first** (with sizes/mtime) then emptied
* Fallback emptying if `trash-cli` is unavailable

* * *

## Technical Design

Core modules:

* `SysUtils`, `ShellExec`, `ProcessManager`, `FileOps`
* `SysCleaner` (orchestration + totals + stop handling)
* `ConfigManager`, `UserDiscovery`
* `PrefsDialog`, `AboutDialog`, `BlitzClean`, `App`

* * *

## Know bugs

### PyCharm warning:

```
Cannot find reference 'connect' in 'pyqtSignal | function'
```

**Fix (stub tweak):** Edit `QtCore.pyi` in your environment’s `site-packages/PyQt6` and add `connect`/`emit` to `pyqtSignal`:

```python
# Support for new-style signals and slots.
class pyqtSignal:

    signatures = ...    # type: tuple[str, ...]

    def __init__(self, *types: typing.Any, name: str = ...) -> None: ...

    @typing.overload
    def __get__(self, instance: None, owner: type['QObject']) -> 'pyqtSignal': ...

    @typing.overload
    def __get__(self, instance: 'QObject', owner: type['QObject']) -> 'pyqtBoundSignal': ...

    # Added
    def connect(self, slot: 'PYQT_SLOT') -> 'QMetaObject.Connection': ...
    def emit(self, *args: typing.Any) -> None: ...
```

> Note: Editing stubs is brittle. Alternatively, add `# type: ignore[attr-defined]` on lines where `connect`/`emit` are flagged.

### PyQt6 type-stubs error with `QDialogButtonBox`

**Error example:**

```
Unexpected type(s):(Literal[StandardButton.Cancel])
Possible type(s):(Literal[StandardButton.Ok])(Literal[StandardButton.Ok])
```

**Cause:** Some PyQt6 stubs model `setStandardButtons` as a single `StandardButton`, but at runtime it’s a flag enum, so `Ok | Cancel` gets flagged.

```python
from typing import cast
btns = QDialogButtonBox(parent=self)
buttons = cast(
    QDialogButtonBox.StandardButton,
    int(QDialogButtonBox.StandardButton.Ok) | int(QDialogButtonBox.StandardButton.Cancel)
)
btns.setStandardButtons(buttons)
```

* * *


* * *

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit them (`git commit -m "Add your feature"`).
4. Push to your branch (`git push origin feature/your-feature`).
5. Open a pull request with a clear description of your changes.

Ensure your code follows PEP 8 style guidelines and includes appropriate tests.

* * *

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

* * *

## Contact

For any issues, suggestions, or questions regarding the project, please open a new issue on the official GitHub repository or reach out directly to the maintainer through the [GitHub Issues](issues) page for further assistance and follow-up.