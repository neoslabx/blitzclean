# BlitzClean — Ubuntu Cleanup GUI

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**BlitzClean** is a fast, no-nonsense GUI utility to clean common caches, logs, and stale data on Ubuntu (and Debian-based) systems. It supports **dry-run previews**, **live streaming logs**, **optional aggressive cleanup**, and **root-aware** system tasks (journald vacuum, Snap/Flatpak pruning, old kernel removal, etc.).

* * *

## Features

* **Dry-run mode:** See *exactly* what would be removed, with full path listings.
* **Real mode mirrors dry-run listings:** Every file/dir removed is listed in the log.
* **User cleanup:** Wipes common caches, histories, “recent files,” and browser caches.
* **System cleanup (root):** Cleans `/tmp`, `/var/tmp`, prunes logs/crashes, journals, Snap/Flatpak leftovers, orphaned packages, and (optionally) old kernels.
* **Aggressive mode (optional):** Extra, potentially disruptive cleanup (e.g., `~/snap`, `~/.ssh`). **Off by default.**
* **Per-user target:** Select which home directory to clean.
* **Progress + responsive UI:** Background worker with live logs.
* **Persistent settings:** All toggles & values are saved across sessions.

* * *

## What gets cleaned (safe by default)

### User-level (safe)

* Generic caches: `~/.cache/*` including `fontconfig`, `mesa_shader_cache`, `pip`, `npm`, `yarn`, `pnpm`, `thunderbird`, `vscode`
* VS Code: `~/.config/Code/Cache`, `CachedData`, `logs`
* Discord caches: `~/.cache/discord`, `~/.config/discord/Cache`, `Code Cache`
* Browser caches:

  * Firefox profiles: `cache2`, `startupCache`
  * Chromium/Chrome/Brave: `Cache`, `Code Cache` under `~/.cache` and `~/.config/*`

* Flatpak user caches: `~/.var/app/*/cache`
* Shell history (emptied, file preserved with secure perms): `~/.bash_history`, `~/.zsh_history`
* Recent files metadata: `~/.cache/recently-used.xbel`, `~/.local/share/RecentDocuments`, `~/.local/share/recently-used.xbel`
* Misc small artifacts: `.profile.bak`, `.shell.pre-oh-my-zsh`, `.wget-hsts`, `.zcompdump*`, `.thumbnails`, `.shutter`

### System-level (safe, requires root)

* Temp dirs: `/tmp`, `/var/tmp`
* APT: `autoremove --purge`, `autoclean`, `clean`
* Logs/Crashes: `/var/crash/*.crash`, `/var/log/*.[0-9]`, `/var/log/*.gz`
* Journald: `journalctl --vacuum-time=<days>`, `--vacuum-size=<size>`
* Snap: `snap set system refresh.retain=<N>`, remove **disabled revisions** only
* Flatpak: `flatpak uninstall --unused -y`
* Orphans: `deborphan` + purge
* Extra caches: `/var/cache/fontconfig`, `/var/cache/man`, `/var/lib/systemd/coredump`, `/var/lib/snapd/cache`
* Optional kernel cleanup: remove old `linux-image-*` (keeps current) and `update-grub`

### Aggressive (optional, **risky**, off by default)

* Remove `~/snap` entirely (application data)
* Remove `~/.ssh` (keys/known_hosts) — may break SSH access

> You can toggle **Aggressive app data cleanup** in the UI. Only enable this if you fully understand the impact.

* * *

## Requirements

* **Python:** 3.10+ (recommended)
* **Libraries (pip):**

  * `PyQt6`
  
* **Optional system tools (used if present):**

  * `policykit-1` (`pkexec`) — for elevation from the GUI
  * `trash-empty` — for trash cleanup
  * `flatpak` — if you use Flatpak
  * `snapd` — if you use Snap
  * `deborphan` — for orphan package detection

Install Python deps:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Install optional tools (Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y policykit-1 trash-cli flatpak snapd deborphan
```

* * *

## Running

### Normal user (safe for user-level cleanup)

```bash
python3 blitzclean.py
```

### With system cleanup (root privileges)

BlitzClean can self-elevate via **pkexec** when needed:

* Run normally; select options (e.g., kernel cleanup). System tasks will execute if the app is running as root.
* If your environment lacks pkexec, start as root manually:

```bash
sudo -H python3 blitzclean.py
```

> The app streams every command and file/dir path it touches in the output pane.

* * *

## Modes & Options

* **Dry-run (preview only):** *Default recommended for first pass*

  * Lists everything that would be removed.
  * Shows bytes **estimated**.

* **Real execution:**

  * Mirrors dry-run listings and deletes the printed paths.
  * Shows bytes **recovered** (root `/` and selected `~`).
* **Clean browser caches:** Firefox/Chrome/Chromium/Brave (safe)
* **Remove old kernels:** Keeps current kernel; runs `update-grub`
* **Shutdown after cleanup:** Schedules immediate shutdown on success
* **Run at boot / Run at shutdown:** Flags are persisted in the config (you can wire these into your own scheduler/service)
* **Aggressive app data cleanup (risky):** Off by default; see above

* * *

## Configuration

BlitzClean persists settings to:

```
~/.config/blitzclean/config
```

Example keys:

```
dryrun=1
clearbrowsers=1
clearkernels=0
vacuumdays=7
vacuumsize=100M
keepsnaps=2
shutafter=0
username=<selected_user>
userhome=/home/<selected_user>
bootrun=0
shutrun=0
aggressive=0
```

You can safely edit this file while the app is closed.

* * *

## Permissions & Elevation

* User-level actions run without elevation.
* System actions require root. If not root, they no-op gracefully.
* If `pkexec` is available, BlitzClean can launch a worker with elevated privileges internally. Otherwise, start the app with `sudo`.

> **Wayland note:** If `pkexec` GUI prompts don’t appear, you may need `polkit-gnome` or a polkit agent running in your session.

* * *

## Build (optional, PyInstaller)

To produce a standalone binary:

```bash
python3 -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name BlitzClean blitzclean.py
```

The binary will be in `dist/BlitzClean/`.

* * *

## 🪲 Troubleshooting

* **Snap removal shows “invalid revision”:** Fixed in v4.3 by pulling the **Rev** column (`$3`) from `snap list --all` instead of the Version column (`$2`).
* **No files listed in real mode:** v4.3 logs every file/dir before deletion in both dry-run and real runs (see `FileOps.removefile/removetree`).
* **`trash-empty not found`:** Install `trash-cli` or ignore the message (the step is skipped).
* **No system cleanup happening:** Ensure you’re running as root (via `pkexec` or `sudo`).
* **Deborphan failures in shells without process substitution:** v4.3 uses a portable approach (no `<(...)`).

* * *

## Changelog

* **v4.3-GUI**

  * Log *every* file/dir in **real mode**, mirroring dry-run
  * Fix Snap disabled revision parsing (use **Rev** column)
  * Add many safe caches (pip/npm/yarn/pnpm, VS Code, Discord, Flatpak user caches)
  * Add safe system caches (`/var/cache/fontconfig`, `/var/cache/man`, `/var/lib/systemd/coredump`, `/var/lib/snapd/cache`)
  * Optional **Aggressive** toggle (off by default)
  * Portable `deborphan` purge invocation

* **v4.2-GUI**

  * Initial public GUI with dry-run, system/user cleanup, journald vacuum, kernel removal, logs, and pkexec worker

* * *

## Safety Notes

* **Dry-run first.** Review the log to confirm scope.
* Aggressive mode can remove app data or credentials — leave it **off** unless you know you want this.
* Kernel removal keeps the **current** kernel by design; still, use with care.
* This tool assumes Ubuntu/Debian conventions; on other distros results may vary.

* * *

## Roadmap / Ideas

* Per-component bytes report (top offenders)
* Log export to file
* Configurable include/exclude patterns
* CLI flags mirroring the GUI for headless use

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